import asyncio
from app.db.database import engine, Base
from app.models import event, user  # 导入模型，让Base知道有哪些表

async def init():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        print("数据库表创建成功")
    finally:
        # 关闭所有数据库连接
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init())