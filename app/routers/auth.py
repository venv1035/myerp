"""
认证相关路由：注册、登录、刷新令牌、登出
"""
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import db_manager
from app.models import User, Tenant, Role, UserRole, RefreshToken   # 注意这里导入了 UserRole
from app.schemas import RegisterRequest, LoginRequest, TokenResponse, RefreshRequest
from app.auth import get_password_hash, verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", status_code=201)
async def register(req: RegisterRequest, db: AsyncSession = Depends(db_manager.get_db)):
    # 检查用户名唯一
    existing = await db.execute(select(User).where(User.username == req.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 创建租户
    tenant = Tenant(name=req.tenant_name)
    db.add(tenant)
    await db.flush()

    # 创建用户
    user = User(
        username=req.username,
        hashed_password=get_password_hash(req.password),
        full_name=req.full_name,
        phone=req.phone,
        tenant_id=tenant.id,
    )
    db.add(user)
    await db.flush()

    # 分配默认角色 "user"，直接插入中间表，避免异步延迟加载
    result = await db.execute(select(Role).where(Role.name == "user"))
    user_role = result.scalar_one()
    # 关键改动：直接操作 UserRole 表
    db.add(UserRole(user_id=user.id, role_id=user_role.id))

    await db.commit()
    return {"message": "注册成功", "user_id": str(user.id)}


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(db_manager.get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="用户已停用")

    access_token = create_access_token({"sub": str(user.id)})

    refresh_token = None
    if req.remember_me:
        raw_token = secrets.token_urlsafe(64)
        token_hash = get_password_hash(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        refresh_db = RefreshToken(
            token_hash=token_hash,
            user_id=user.id,
            expires_at=expires_at,
        )
        db.add(refresh_db)
        await db.commit()
        refresh_token = raw_token

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(req: RefreshRequest, db: AsyncSession = Depends(db_manager.get_db)):
    raw_token = req.refresh_token
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.expires_at > datetime.now(timezone.utc))
    )
    all_tokens = result.scalars().all()

    valid_token = None
    for rt in all_tokens:
        if verify_password(raw_token, rt.token_hash):
            valid_token = rt
            break

    if not valid_token:
        raise HTTPException(status_code=401, detail="无效的 refresh token")

    access_token = create_access_token({"sub": str(valid_token.user_id)})
    return TokenResponse(access_token=access_token, refresh_token=None)


@router.post("/logout")
async def logout():
    raise HTTPException(status_code=501, detail="暂未实现")