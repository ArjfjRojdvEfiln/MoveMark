from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"  # 签名算法

def hash_password(password: str) -> str:
    # 把明文密码 → hash值，用于存库
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    # 验证用户输入的密码是否和库里的hash匹配
    return pwd_context.verify(plain, hashed)

def create_access_token(user_id: int) -> str:
    # 过期时间怎么设？
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    # payload 里放什么？
    payload = {"sub": str(user_id),
               "exp": expire}
    # 用 jwt.encode() 生成
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        return int(user_id)
    except JWTError:
        return None
    # 用 jwt.decode() 解析
    # 如果 token 无效或过期，jwt 会抛出 JWTError
    # 从 payload 里取出 sub，转成 int 返回
    # 出错就返回 None