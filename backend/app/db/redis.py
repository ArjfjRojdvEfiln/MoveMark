import json
import redis.asyncio as aioredis
from app.core.config import settings

# 全局redis客户端（单例）
_redis_client = None

async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
        if settings.REDIS_PASSWORD:
            redis_url = f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}"
        _redis_client = aioredis.from_url(redis_url, decode_responses=True)
    return _redis_client


async def cache_get(key: str):
    """从缓存取数据，返回反序列化后的对象，不存在返回None"""
    redis = await get_redis()
    val = await redis.get(key)
    if val is None:
        return None
    return json.loads(val)


async def cache_set(key: str, value, ttl: int = 300):
    """写入缓存，ttl单位秒，默认5分钟"""
    redis = await get_redis()
    await redis.set(key, json.dumps(value, ensure_ascii=False, default=str), ex=ttl)


async def cache_delete(key: str):
    redis = await get_redis()
    await redis.delete(key)