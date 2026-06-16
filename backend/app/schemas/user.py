from pydantic import BaseModel

class RegisterIn(BaseModel):
    username: str
    email: str
    password: str

class LoginIn(BaseModel):
    username: str
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"  # 固定值，OAuth2规范


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    avatar_url: str

    model_config = {"from_attributes": True}  # 和 EventOut 一样，支持ORM对象转换