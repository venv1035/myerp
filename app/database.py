"""
数据库连接管理（异步）—— dataclass 版本，提供全局 db_manager 实例
"""
import os
from dataclasses import dataclass, field
from typing import AsyncGenerator
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
    AsyncEngine,
)
from sqlmodel import SQLModel

load_dotenv()


@dataclass(kw_only=True)
class DatabaseManager:
    """异步数据库连接管理器"""

    database_url: str
    echo: bool = False

    engine: AsyncEngine = field(init=False)
    session_factory: async_sessionmaker = field(init=False)

    def __post_init__(self):
        self.engine = create_async_engine(
            self.database_url, echo=self.echo, future=True
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def init_db(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    async def get_db(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def close(self) -> None:
        await self.engine.dispose()


# 全局数据库管理器实例
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("未设置 DATABASE_URL 环境变量")

db_manager = DatabaseManager(database_url=DATABASE_URL)