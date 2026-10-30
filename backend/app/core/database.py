from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config.settings import settings

# Create async engine
engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,  # Check kết nối từ pool.
    hide_parameters=True,  # Ẩn log, chỉ hiện tại môi trường dev
    echo=(settings.environment == "development"),
)

#  Bộ sinh session với thuộc tính mặc định
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,  # Tránh tải lại nhiều lần
)


# Lớp chung của ORM model
class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy database models."""

    pass


# Tạo 1 session
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an active async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
