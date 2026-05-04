"""
请求与响应的数据模型
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ---------- 认证 ----------
class RegisterRequest(BaseModel):
    username: str
    password: str
    tenant_name: str
    full_name: Optional[str] = None
    phone: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str
    remember_me: bool = False


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# ---------- 用户 ----------
class UserResponse(BaseModel):
    id: str
    username: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    tenant_id: str
    roles: list[str] = []
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str