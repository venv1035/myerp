import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from dotenv import load_dotenv

from app.database import db_manager
from app.models import Role
from app.routers import auth, users

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动逻辑
    try:
        await db_manager.init_db()

        # 创建默认角色
        async with db_manager.session_factory() as session:
            default_roles = ["admin", "manager", "user"]
            for role_name in default_roles:
                result = await session.execute(
                    select(Role).where(Role.name == role_name)
                )
                if not result.scalar_one_or_none():
                    session.add(Role(name=role_name))
            await session.commit()

        logger.info("数据库表初始化及默认角色就绪")
    except Exception as e:
        logger.warning(f"初始化失败（可能数据库暂时不可用）: {e}")

    yield  # 应用运行中

    # 关闭逻辑
    await db_manager.close()
    logger.info("数据库连接池已释放")


app = FastAPI(title="Tire ERP SaaS", lifespan=lifespan)

# 静态文件服务
app.mount("/static", StaticFiles(directory="static"), name="static")

# 注册路由
app.include_router(auth.router)
app.include_router(users.router)


@app.get("/api/health/db")
async def health_db(db: AsyncSession = Depends(db_manager.get_db)):
    """数据库连接健康检查"""
    try:
        await db.execute(text("SELECT 1"))
        return {"database": "ok"}
    except Exception as e:
        logger.error(f"数据库健康检查失败: {e}")
        return {"database": "error", "detail": str(e)}