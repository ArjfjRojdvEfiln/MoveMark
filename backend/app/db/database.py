from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# 创建异步引擎
# pool_pre_ping=True：每次使用连接前先 ping 一下，防止连接失效
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False,  # True 会打印所有SQL，调试时可以开
)

# Session工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # commit后对象属性不过期，避免懒加载报错
)

class Base(DeclarativeBase):
    pass

# FastAPI依赖注入用
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session