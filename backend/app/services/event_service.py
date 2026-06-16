from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, extract, func
from typing import Optional
from app.models.event import Event, SportType, RegStatus
from app.db.elastic import es_client, EVENT_INDEX
from app.db.redis import cache_get, cache_set
from app.schemas.event import EventOut, EventListOut


# ══════════════════════════════════════════
#  1. 赛事列表（MySQL分页 + 多条件筛选）
# ══════════════════════════════════════════
async def get_event_list(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    sport_type: Optional[SportType] = None,
    province: Optional[str] = None,
    month: Optional[int] = None,
    reg_status: Optional[RegStatus] = None,
) -> EventListOut:

    # 构建缓存key：所有筛选条件拼成字符串
    cache_key = f"events:list:{page}:{page_size}:{sport_type}:{province}:{month}:{reg_status}"

    # ① 先查缓存
    cached = await cache_get(cache_key)
    if cached:
        return EventListOut(**cached)

    # ② 缓存未命中，查MySQL
    # 构建动态过滤条件
    conditions = []
    if sport_type:
        conditions.append(Event.sport_type == sport_type)
    if province:
        conditions.append(Event.province == province)
    if month:
        # extract是SQL的MONTH()函数
        conditions.append(extract("month", Event.event_date) == month)
    if reg_status:
        conditions.append(Event.reg_status == reg_status)

    where_clause = and_(*conditions) if conditions else True

    # 查总数
    count_stmt = select(func.count()).select_from(Event).where(where_clause)
    total = (await db.execute(count_stmt)).scalar()

    # 查分页数据，按比赛日期排序
    stmt = (
        select(Event)
        .where(where_clause)
        .order_by(Event.event_date.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(stmt)).scalars().all()

    result = EventListOut(
        total=total,
        page=page,
        page_size=page_size,
        items=[EventOut.model_validate(r) for r in rows],
    )

    # ③ 写入缓存，列表缓存5分钟
    await cache_set(cache_key, result.model_dump(), ttl=300)
    return result


# ══════════════════════════════════════════
#  2. 赛事搜索（ES全文检索）
# ══════════════════════════════════════════
async def search_events(
    keyword: str,
    sport_type: Optional[str] = None,
    province: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:

    # 构建ES查询
    # must = 必须匹配，filter = 精确过滤（不影响评分，性能更好）
    must = []
    filters = []

    if keyword:
        must.append({
            "multi_match": {
                "query": keyword,
                "fields": ["title^3", "city^2", "description"],
                # title权重3倍，city权重2倍，让标题匹配排在前面
            }
        })

    if sport_type:
        filters.append({"term": {"sport_type": sport_type}})
    if province:
        filters.append({"term": {"province": province}})

    query = {
        "bool": {
            "must": must if must else [{"match_all": {}}],
            "filter": filters,
        }
    }

    resp = await es_client.search(
        index=EVENT_INDEX,
        query=query,
        from_=(page - 1) * page_size,
        size=page_size,
        sort=[{"event_date": {"order": "asc"}}],
    )

    hits = resp["hits"]
    total = hits["total"]["value"]
    items = [hit["_source"] for hit in hits["hits"]]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


# ══════════════════════════════════════════
#  3. 赛事详情（MySQL + Redis缓存）
# ══════════════════════════════════════════
async def get_event_detail(event_id: int, db: AsyncSession) -> Optional[EventOut]:
    st = sport_type.value if sport_type else ""
    rs = reg_status.value if reg_status else ""
    pv = province or ""
    mo = month or ""
    cache_key = f"events:list:{page}:{page_size}:{st}:{pv}:{mo}:{rs}"
    # ① 查缓存
    cached = await cache_get(cache_key)
    if cached:
        return EventOut(**cached)

    # ② 查DB
    stmt = select(Event).where(Event.id == event_id)
    row = (await db.execute(stmt)).scalar_one_or_none()

    if not row:
        return None

    result = EventOut.model_validate(row)

    # ③ 详情缓存时间更长，30分钟（详情数据变化少）
    await cache_set(cache_key, result.model_dump(), ttl=1800)
    return result