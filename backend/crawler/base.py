import httpx
import asyncio
from abc import ABC, abstractmethod
from typing import List, Dict


class BaseCrawler(ABC):
    """所有爬虫的基类，定义接口规范"""

    # 请求头，模拟浏览器，避免被反爬
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    def __init__(self):
        # 限速：每次请求间隔，做个文明爬虫
        self.request_delay = 1.5

    @abstractmethod
    async def fetch_list(self, page: int) -> List[Dict]:
        """爬取列表页，返回原始数据"""
        pass

    @abstractmethod
    async def parse_detail(self, url: str, client: httpx.AsyncClient) -> Dict:
        """爬取详情页"""
        pass

    async def crawl(self, max_pages: int = 10) -> List[Dict]:
        """主入口：爬取多页并汇总"""
        all_events = []
        async with httpx.AsyncClient(headers=self.HEADERS, timeout=15, follow_redirects=True) as client:
            for page in range(1, max_pages + 1):
                print(f"📄 正在爬取第 {page} 页...")
                try:
                    events = await self.fetch_list_with_client(page, client)
                    if not events:
                        print(f"第 {page} 页无数据，停止")
                        break
                    all_events.extend(events)
                    print(f" 获取 {len(events)} 条")
                    await asyncio.sleep(self.request_delay)  # 礼貌等待
                except Exception as e:
                    print(f" 第 {page} 页出错: {e}")
                    continue
        return all_events

    @abstractmethod
    async def fetch_list_with_client(self, page: int, client: httpx.AsyncClient) -> List[Dict]:
        pass