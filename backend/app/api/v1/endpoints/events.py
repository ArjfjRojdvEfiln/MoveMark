from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.db.database import get_db
from app.models.event import SportType, RegStatus
from app.services import event_service

router = APIRouter()


@router.get("/", summary="赛事列表")
async def list_events(
    page:       int            = Query(1, ge=1, description="页码"),
    page_size:  int            = Query(20, ge=1, le=100, description="每页数量"),
    sport_type: Optional[SportType]  = Query(None, description="运动类型"),
    province:   Optional[str]        = Query(None, description="省份"),
    month:      Optional[int]        = Query(None, ge=1, le=12, description="月份"),
    reg_status: Optional[RegStatus]  = Query(None, description="报名状态"),
    db: AsyncSession = Depends(get_db),
):
    return await event_service.get_event_list(
        db=db,
        page=page,
        page_size=page_size,
        sport_type=sport_type,
        province=province,
        month=month,
        reg_status=reg_status,
    )


@router.get("/search", summary="赛事搜索（ES全文检索）")
async def search_events(
    keyword:    str            = Query(..., min_length=1, description="搜索关键词"),
    sport_type: Optional[str] = Query(None),
    province:   Optional[str] = Query(None),
    page:       int           = Query(1, ge=1),
    page_size:  int           = Query(20, ge=1, le=100),
):
    return await event_service.search_events(
        keyword=keyword,
        sport_type=sport_type,
        province=province,
        page=page,
        page_size=page_size,
    )


@router.get("/{event_id}", summary="赛事详情")
async def get_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    event = await event_service.get_event_detail(event_id, db)
    if not event:
        raise HTTPException(status_code=404, detail="赛事不存在")
    return event