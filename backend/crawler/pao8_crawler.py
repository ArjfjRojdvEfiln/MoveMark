import httpx
import re
from bs4 import BeautifulSoup
from typing import List, Dict
from datetime import datetime
from .base import BaseCrawler


class Pao8Crawler(BaseCrawler):
    """
    跑步天地 pao8.net 爬虫
    目标页面：https://www.pao8.net/race/list/
    """
    BASE_URL = "https://www.pao8.net"
    LIST_URL = "https://www.pao8.net/race/list/"

    async def fetch_list(self, page: int) -> List[Dict]:
        pass  # 实现在 fetch_list_with_client

    async def fetch_list_with_client(self, page: int, client: httpx.AsyncClient) -> List[Dict]:
        url = f"{self.LIST_URL}?page={page}"
        resp = await client.get(url)
        resp.raise_for_status()
        return self._parse_list_page(resp.text)

    def _parse_list_page(self, html: str) -> List[Dict]:
        soup = BeautifulSoup(html, "html.parser")
        events = []

        # 找所有赛事卡片（根据实际页面结构调整选择器）
        items = soup.select(".race-list-item, .event-item, article.race")

        if not items:
            # 备用：找所有包含赛事链接的条目
            items = soup.select("ul.race-list > li, .list-group-item")

        for item in items:
            try:
                event = self._parse_list_item(item)
                if event:
                    events.append(event)
            except Exception as e:
                print(f"  解析条目失败: {e}")
                continue

        return events

    def _parse_list_item(self, item) -> Dict | None:
        # 提取链接
        link = item.select_one("a[href]")
        if not link:
            return None

        href = link.get("href", "")
        if not href.startswith("http"):
            href = self.BASE_URL + href

        # 提取赛事ID（从URL解析）
        race_id = re.search(r'/race/(\d+)', href)
        source_id = f"pao8_{race_id.group(1)}" if race_id else None
        if not source_id:
            return None

        title = link.get_text(strip=True)

        return {
            "source_id": source_id,
            "source": "pao8.net",
            "title": title,
            "detail_url": href,
        }

    async def parse_detail(self, url: str, client: httpx.AsyncClient) -> Dict:
        resp = await client.get(url)
        resp.raise_for_status()
        return self._parse_detail_page(resp.text, url)

    def _parse_detail_page(self, html: str, url: str) -> Dict:
        soup = BeautifulSoup(html, "html.parser")
        detail = {}

        # 赛事名称
        title_el = soup.select_one("h1.race-title, h1.title, .page-title h1")
        if title_el:
            detail["title"] = title_el.get_text(strip=True)

        # 从页面文本中用正则提取日期、城市等信息
        page_text = soup.get_text()

        # 尝试提取日期 格式：2025-06-15 或 2025年6月15日
        date_match = re.search(r'(\d{4}[-年]\d{1,2}[-月]\d{1,2})', page_text)
        if date_match:
            date_str = date_match.group(1).replace('年', '-').replace('月', '-').replace('日', '')
            try:
                detail["event_date"] = datetime.strptime(date_str, "%Y-%m-%d").date()
            except:
                pass

        # 提取省市
        province_map = {
            "北京": "北京", "上海": "上海", "广东": "广东", "广州": "广东",
            "深圳": "广东", "浙江": "浙江", "杭州": "浙江", "江苏": "江苏",
            "南京": "江苏", "四川": "四川", "成都": "四川", "云南": "云南",
            "昆明": "云南", "新疆": "新疆", "西藏": "西藏", "青海": "青海",
        }
        for kw, province in province_map.items():
            if kw in page_text[:500]:
                detail["province"] = province
                break

        # 提取官网图片
        og_image = soup.select_one('meta[property="og:image"]')
        if og_image:
            detail["image_url"] = og_image.get("content", "")

        # 赛事描述
        desc_el = soup.select_one(".race-desc, .description, .intro")
        if desc_el:
            detail["description"] = desc_el.get_text(strip=True)[:500]

        detail["official_url"] = url
        return detail