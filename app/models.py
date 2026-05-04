"""
核心数据库模型：租户、用户、角色、刷新令牌
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, DateTime


# -------------------------------------------------------
# 1. 中间表 UserRole（必须最先定义，否则后边无法引用）
# -------------------------------------------------------
class UserRole(SQLModel, table=True):
    __tablename__ = "user_roles"

    user_id: uuid.UUID = Field(
        sa_type=UUID(as_uuid=True),
        foreign_key="users.id",
        primary_key=True,
    )
    role_id: uuid.UUID = Field(
        sa_type=UUID(as_uuid=True),
        foreign_key="roles.id",
        primary_key=True,
    )


# -------------------------------------------------------
# 2. Tenant —— 租户
# -------------------------------------------------------
class Tenant(SQLModel, table=True):
    __tablename__ = "tenants"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_type=UUID(as_uuid=True),
        primary_key=True,
    )
    name: str = Field(max_length=255, index=True)
    is_active: bool = Field(default=True)
    subscription_expires_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True))
    )
    max_users: Optional[int] = Field(default=None)
    plan: Optional[str] = Field(default=None, max_length=50)
    auto_renew: Optional[bool] = Field(default=None)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True)),
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # 一对多：一个租户下有多个用户
    users: List["User"] = Relationship(back_populates="tenant")


# -------------------------------------------------------
# 3. Role —— 角色
# -------------------------------------------------------
class Role(SQLModel, table=True):
    __tablename__ = "roles"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_type=UUID(as_uuid=True),
        primary_key=True,
    )
    name: str = Field(max_length=50, unique=True, index=True)
    description: Optional[str] = Field(default=None, max_length=255)

    # 多对多：一个角色下多个用户
    users: List["User"] = Relationship(
        back_populates="roles",
        link_model=UserRole,
    )


# -------------------------------------------------------
# 4. User —— 用户
# -------------------------------------------------------
class User(SQLModel, table=True):
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}   # 仅开发期

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_type=UUID(as_uuid=True),
        primary_key=True,
    )
    username: str = Field(max_length=150, unique=True, index=True)
    hashed_password: str = Field(max_length=255)

    full_name: Optional[str] = Field(default=None, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=30)
    phone_verified: bool = Field(default=False)
    wechat_openid: Optional[str] = Field(default=None, max_length=255, index=True)

    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True)),
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # 外键 → 租户
    tenant_id: uuid.UUID = Field(
        sa_type=UUID(as_uuid=True),
        foreign_key="tenants.id",
    )
    tenant: Tenant = Relationship(back_populates="users")

    # 多对多：用户拥有多个角色
    roles: List["Role"] = Relationship(
        back_populates="users",
        link_model=UserRole,
    )


# -------------------------------------------------------
# 5. RefreshToken —— 记住我 / 设备令牌
# -------------------------------------------------------
class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_tokens"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_type=UUID(as_uuid=True),
        primary_key=True,
    )
    token_hash: str = Field(max_length=255, index=True)
    user_id: uuid.UUID = Field(
        sa_type=UUID(as_uuid=True),
        foreign_key="users.id",
    )
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True))
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True)),
        default_factory=lambda: datetime.now(timezone.utc)
    )