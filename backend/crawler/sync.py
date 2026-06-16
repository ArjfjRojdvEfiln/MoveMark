"""
爬虫数据同步脚本
流程：爬虫获取数据 → 布隆过滤器去重 → 入库MySQL → 同步ES
"""
import asyncio
import redis.asyncio as aioredis
from datetime import date, datetime
from sqlalchemy import select

from app.db.database import AsyncSessionLocal, engine, Base
from app.db.elastic import es_client, init_es_index, EVENT_INDEX
from app.models.event import Event, SportType, RegStatus
from app.utils.bloom_filter import crawler_bloom, event_id_bloom
from app.core.config import settings
from crawler.pao8_crawler import Pao8Crawler
from crawler.meilijog_crawler import MeilijogCrawler


def determine_sport_type(raw: str) -> SportType:
    """智能判断运动类型"""
    if not raw:
        return SportType.other
    raw = str(raw)
    if any(k in raw for k in ["马拉松", "跑步", "长跑", "半马", "全马"]):
        return SportType.marathon
    if any(k in raw for k in ["骑行", "自行车", "单车", "公路车"]):
        return SportType.cycling
    if any(k in raw for k in ["越野", "trail", "山地", "登山"]):
        return SportType.trail
    return SportType.other


def determine_reg_status(reg_end_date) -> RegStatus:
    """根据报名截止日期判断状态"""
    if not reg_end_date:
        return RegStatus.open
    today = date.today()
    if isinstance(reg_end_date, str):
        try:
            reg_end_date = datetime.strptime(reg_end_date[:10], "%Y-%m-%d").date()
        except:
            return RegStatus.open
    if reg_end_date < today:
        return RegStatus.closed
    return RegStatus.open


async def sync_events_to_es(events: list[Event], es):
    """批量同步到ES"""
    if not events:
        return

    actions = []
    for ev in events:
        actions.append({"index": {"_index": EVENT_INDEX, "_id": str(ev.id)}})
        actions.append({
            "id": ev.id,
            "title": ev.title,
            "sport_type": ev.sport_type,
            "province": ev.province or "",
            "city": ev.city or "",
            "event_date": ev.event_date.isoformat() if ev.event_date else None,
            "reg_end_date": ev.reg_end_date.isoformat() if ev.reg_end_date else None,
            "reg_status": ev.reg_status,
            "distances": ev.distances or "",
            "description": ev.description or "",
            "official_url": ev.official_url or "",
            "image_url": ev.image_url or "",
            "source": ev.source or "",
            "source_id": ev.source_id,
        })

    resp = await es.bulk(operations=actions)
    if resp.get("errors"):
        print(f"ES bulk有错误")
    else:
        print(f"ES同步 {len(events)} 条成功")


async def run_sync(use_mock: bool = False):
    """
    主同步流程
    use_mock=True: 使用模拟数据（爬虫被反爬时的备用方案）
    """
    print("=" * 50)
    print("MoveMark 数据同步开始")
    print("=" * 50)

    # 1. 初始化Redis
    redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
    if settings.REDIS_PASSWORD:
        redis_url = f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}"

    redis_client = aioredis.from_url(redis_url, decode_responses=False)

    # 2. 初始化ES索引
    await init_es_index()

    # 3. 爬取数据
    all_raw_events = []

    if use_mock:
        print("使用模拟数据...")
        all_raw_events = generate_mock_events()
    else:
        # 爬美丽跑（API方式，比较稳定）
        print("\n爬取美丽跑数据...")
        try:
            meilijog = MeilijogCrawler()
            events = await meilijog.crawl(max_pages=5)
            all_raw_events.extend(events)
            print(f"美丽跑爬取完成: {len(events)} 条")
        except Exception as e:
            print(f"美丽跑爬取失败: {e}")

        # 爬跑步天地
        print("\n 爬取跑步天地数据...")
        try:
            pao8 = Pao8Crawler()
            events = await pao8.crawl(max_pages=5)
            all_raw_events.extend(events)
            print(f"跑步天地爬取完成: {len(events)} 条")
        except Exception as e:
            print(f"跑步天地爬取失败: {e}")

    print(f"\n 共获取原始数据: {len(all_raw_events)} 条")

    # 4. 布隆过滤器去重 + 入库
    new_count = 0
    skip_count = 0
    new_events_for_es = []

    async with AsyncSessionLocal() as session:
        for raw in all_raw_events:
            source_id = raw.get("source_id")
            if not source_id:
                continue

            # 布隆过滤器快速判断：已存在则跳过
            if await crawler_bloom.exists(source_id, redis_client):
                skip_count += 1
                continue

            # 布隆说"不存在"，还需二次确认（因为布隆无漏判但有误判反向）
            # 实际上布隆说不存在就一定不存在，说存在才需要二次确认
            # 这里的逻辑：布隆exists=True时才需要DB确认（防假阳性）
            # 但为简单起见，我们直接入库，用数据库unique约束兜底

            # 5. 构建Event对象
            ev = Event(
                source_id=source_id,
                source=raw.get("source", ""),
                title=raw.get("title", "未知赛事")[:200],
                sport_type=determine_sport_type(raw.get("sport_type", "")),
                province=raw.get("province", ""),
                city=raw.get("city", ""),
                event_date=raw.get("event_date"),
                reg_start_date=raw.get("reg_start_date"),
                reg_end_date=raw.get("reg_end_date"),
                distances=str(raw.get("distances", ""))[:200],
                official_url=raw.get("official_url", "")[:500],
                image_url=raw.get("image_url", "")[:500],
                description=raw.get("description", "")[:1000],
                reg_status=determine_reg_status(raw.get("reg_end_date")),
            )

            try:
                session.add(ev)
                await session.flush()  # 让MySQL分配ID，但还未commit
                new_events_for_es.append(ev)

                # 加入布隆过滤器
                await crawler_bloom.add(source_id, redis_client)
                new_count += 1

            except Exception as e:
                await session.rollback()
                if "Duplicate" in str(e):
                    # source_id唯一约束触发，说明布隆有漏网之鱼（正常）
                    await crawler_bloom.add(source_id, redis_client)  # 补充进布隆
                    skip_count += 1
                else:
                    print(f"入库失败: {source_id} - {e}")
                continue

        await session.commit()
        print(f"\n MySQL入库完成: 新增{new_count}条, 跳过{skip_count}条")

        # 同时把event id也加入event_id_bloom（缓存穿透防护用）
        if new_events_for_es:
            ids = [str(ev.id) for ev in new_events_for_es]
            await event_id_bloom.add_batch(ids, redis_client)

    # 6. 同步到ES
    if new_events_for_es:
        print(f"\n 同步到Elasticsearch...")
        await sync_events_to_es(new_events_for_es, es_client)

    await redis_client.aclose()
    await es_client.close()

    print("\n" + "=" * 50)
    print(f"同步完成！新增: {new_count} 条")
    print("=" * 50)


def generate_mock_events():
    """
    模拟数据生成器
    当爬虫被反爬时使用，保证项目可以运行
    """
    from datetime import date, timedelta
    import random

    cities = [
        ("北京", "北京"), ("上海", "上海"), ("广州", "广东"), ("深圳", "广东"),
        ("杭州", "浙江"), ("南京", "江苏"), ("成都", "四川"), ("重庆", "重庆"),
        ("昆明", "云南"), ("西安", "陕西"), ("厦门", "福建"), ("青岛", "山东"),
        ("大理", "云南"), ("丽江", "云南"), ("张家界", "湖南"), ("黄山", "安徽"),
    ]

    sport_configs = [
        ("马拉松", "42km,21km,10km,5km"),
        ("越野", "50km,25km,10km"),
        ("骑行", "100km,50km,30km"),
        ("马拉松", "全马,半马"),
    ]

    events = []
    today = date.today()

    race_names = [
        "{city}国际马拉松", "{city}越野挑战赛", "{city}环湖骑行赛",
        "{city}山地越野跑", "{city}城市半程马拉松", "{city}铁人三项赛",
        "2025{city}春季马拉松", "{city}全国越野锦标赛", "{city}骑行嘉年华",
        "{city}山地超级越野", "{city}公路自行车赛", "{city}夜跑马拉松",
    ]

    for i in range(200):
        city, province = random.choice(cities)
        sport_type, distances = random.choice(sport_configs)
        name_tpl = random.choice(race_names)
        title = name_tpl.format(city=city)

        event_date = today + timedelta(days=random.randint(30, 365))
        reg_end = event_date - timedelta(days=random.randint(7, 30))

        events.append({
            "source_id": f"mock_{i:04d}",
            "source": "mock_data",
            "title": title,
            "sport_type": sport_type,
            "province": province,
            "city": city,
            "event_date": event_date,
            "reg_start_date": today,
            "reg_end_date": reg_end,
            "distances": distances,
            "official_url": f"https://example.com/race/{i}",
            "image_url": "",
            "description": f"{city}{sport_type}赛事，赛程包含{distances}，欢迎参与！",
        })

    return events


if __name__ == "__main__":
    import sys

    use_mock = "--mock" in sys.argv
    asyncio.run(run_sync(use_mock=use_mock))