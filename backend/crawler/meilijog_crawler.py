import httpx
import re
import json
from typing import List, Dict
from datetime import datetime
from .base import BaseCrawler


class MeilijogCrawler(BaseCrawler):
    """
    美丽跑 API 爬虫
    美丽跑有公开JSON接口，比HTML解析更稳定
    """
    API_URL = "https://www.meilijog.com/api/race/list"

    async def fetch_list_with_client(self, page: int, client: httpx.AsyncClient) -> List[Dict]:
        params = {
            "page": page,
            "pageSize": 20,
            "raceType": "",  # 全部类型
            "status": "",
        }
        try:
            resp = await client.get(self.API_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            return self._parse_api_response(data)
        except Exception as e:
            print(f"  美丽跑接口请求失败: {e}")
            return []

    def _parse_api_response(self, data: dict) -> List[Dict]:
        events = []
        items = data.get("data", {}).get("list", [])

        for item in items:
            race_id = item.get("id") or item.get("raceId")
            if not race_id:
                continue

            # 解析运动类型
            sport_type = self._map_sport_type(item.get("raceType", ""))

            # 解析日期
            event_date = None
            date_str = item.get("raceDate") or item.get("startDate")
            if date_str:
                try:
                    event_date = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
                except:
                    pass

            reg_end = None
            reg_end_str = item.get("regEndDate") or item.get("enrollEndDate")
            if reg_end_str:
                try:
                    reg_end = datetime.strptime(reg_end_str[:10], "%Y-%m-%d").date()
                except:
                    pass

            events.append({
                "source_id": f"meilijog_{race_id}",
                "source": "meilijog.com",
                "title": item.get("raceName") or item.get("title", ""),
                "sport_type": sport_type,
                "province": item.get("province", ""),
                "city": item.get("city", ""),
                "event_date": event_date,
                "reg_end_date": reg_end,
                "distances": item.get("groups") or item.get("distance", ""),
                "official_url": item.get("officialUrl") or item.get("url", ""),
                "image_url": item.get("cover") or item.get("image", ""),
                "description": item.get("desc") or item.get("description", ""),
            })

        return events

    def _map_sport_type(self, raw: str) -> str:
        mapping = {
            "马拉松": "马拉松", "跑步": "马拉松", "trail": "越野",
            "越野": "越野", "骑行": "骑行", "自行车": "骑行",
        }
        for k, v in mapping.items():
            if k in raw:
                return v
        return "其他"

    async def fetch_list(self, page: int) -> List[Dict]:
        pass

    async def parse_detail(self, url: str, client: httpx.AsyncClient) -> Dict:
        return {}