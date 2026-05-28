"""数据库连接管理 - SQLAlchemy 2.0 异步引擎"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# SQLite 不支持 pool_size，需要区分处理
_connect_args = {}
if settings.database_url.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}
    engine = create_async_engine(
        settings.database_url,
        echo=settings.DEBUG,
        connect_args=_connect_args,
    )
else:
    engine = create_async_engine(
        settings.database_url,
        echo=settings.DEBUG,
        pool_size=20,
        max_overflow=10,
    )

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI 依赖注入：获取数据库会话"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
