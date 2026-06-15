from fastapi import APIRouter
from app.api.v1.endpoints import events, users, favorites, notifications, ai

router = APIRouter()
router.include_router(events.router,        prefix="/events",        tags=["赛事"])
router.include_router(users.router,         prefix="/users",         tags=["用户"])
router.include_router(favorites.router,     prefix="/favorites",     tags=["收藏"])
router.include_router(notifications.router, prefix="/notifications", tags=["通知"])
router.include_router(ai.router,            prefix="/ai",            tags=["AI助手"])