from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.user import User
from app.schemas.user import RegisterIn, LoginIn, TokenOut, UserOut
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from fastapi.security import OAuth2PasswordBearer

router = APIRouter()


@router.post("/register", response_model=UserOut)
async def register(data: RegisterIn, db: AsyncSession = Depends(get_db)):
    # 第一步：检查用户名是否已存在
    existing = await db.execute(select(User).where(User.username == data.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 第二步：检查邮箱是否已存在
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="邮箱已存在")

    # 第三步：创建用户对象，密码要hash
    user = User(
        username=data.username,
        email=data.email,
        hashed_pwd=hash_password(data.password),
    )

    # 第四步：存库并返回
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenOut)
async def login(data: LoginIn, db: AsyncSession = Depends(get_db)):
    # 第一步：查用户
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="用户名不存在")

    # 第二步：验证密码
    if not verify_password(data.password, user.hashed_pwd):
        raise HTTPException(status_code=400, detail="密码错误")

    # 第三步：生成token并返回
    token = create_access_token(user.id)
    return TokenOut(access_token=token)



oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login")
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    # 第一步：解析token，拿到user_id
    user_id = decode_access_token(token)
    # 第二步：user_id无效则报错401
    if user_id is None:
        raise HTTPException(status_code=401, detail="无效的token")
    # 第三步：查数据库，返回user对象
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


# 接口：用 Depends 调用上面的依赖函数
@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

