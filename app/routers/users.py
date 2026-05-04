"""
用户管理路由：个人信息、管理员操作
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.database import db_manager
from app.models import User, Role
from app.dependencies import get_current_user, RoleChecker
from app.schemas import UserResponse, UserUpdateRequest, ChangePasswordRequest
from app.auth import get_password_hash, verify_password

router = APIRouter(prefix="/api/users", tags=["用户"])


@router.get("/me", response_model=UserResponse)
async def read_me(current_user: User = Depends(get_current_user)):
    roles = [role.name for role in current_user.roles]
    return UserResponse(
        id=str(current_user.id),
        username=current_user.username,
        full_name=current_user.full_name,
        phone=current_user.phone,
        is_active=current_user.is_active,
        tenant_id=str(current_user.tenant_id),
        roles=roles,
        created_at=current_user.created_at,
    )


@router.put("/me", response_model=UserResponse)
async def update_me(
    req: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_db),
):
    if req.full_name is not None:
        current_user.full_name = req.full_name
    if req.phone is not None:
        current_user.phone = req.phone
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return await read_me(current_user)


@router.put("/me/password")
async def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_db),
):
    if not verify_password(req.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="原密码错误")
    current_user.hashed_password = get_password_hash(req.new_password)
    db.add(current_user)
    await db.commit()
    return {"message": "密码修改成功"}


# 管理员查看用户列表
@router.get("/admin", dependencies=[Depends(RoleChecker(["admin"]))])
async def list_users(
    db: AsyncSession = Depends(db_manager.get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(User).where(User.tenant_id == current_user.tenant_id)
    )
    users = result.scalars().all()
    return [
        {
            "id": str(u.id),
            "username": u.username,
            "full_name": u.full_name,
            "is_active": u.is_active,
        }
        for u in users
    ]


# 管理员分配角色
@router.post("/admin/{user_id}/roles", dependencies=[Depends(RoleChecker(["admin"]))])
async def assign_role(
    user_id: str,
    role_name: str,
    db: AsyncSession = Depends(db_manager.get_db),
    current_user: User = Depends(get_current_user),
):
    # 查找目标用户（必须同租户）
    target_user = await db.get(User, user_id)
    if not target_user or target_user.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="用户不存在")

    role = await db.execute(select(Role).where(Role.name == role_name))
    role = role.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=400, detail="角色不存在")

    if role not in target_user.roles:
        target_user.roles.append(role)
        await db.commit()

    return {"message": f"已为用户 {target_user.email} 分配角色 {role_name}"}