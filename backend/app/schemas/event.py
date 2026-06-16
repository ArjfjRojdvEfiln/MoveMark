from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional
from app.models.event import SportType, RegStatus


# ────── 响应：单个赛事 ──────
class EventOut(BaseModel):
    id: int
    title: str
    sport_type: SportType
    province: Optional[str] = None
    city: Optional[str] = None
    event_date: Optional[date] = None
    reg_start_date: Optional[date] = None
    reg_end_date: Optional[date] = None
    distances: Optional[str] = None
    official_url: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    reg_status: RegStatus
    source: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}  # 允许从ORM对象直接转换


# ────── 响应：分页列表 ──────
class EventListOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[EventOut]