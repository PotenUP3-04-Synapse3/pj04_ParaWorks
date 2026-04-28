from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from backend.core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.debug,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """pgvector extension 활성화 및 테이블 생성."""
    import logging
    import sqlalchemy

    # pgvector는 AUTOCOMMIT 모드에서 별도 연결로 시도 (트랜잭션 오염 방지)
    async with engine.connect() as conn:
        await conn.execution_options(isolation_level='AUTOCOMMIT')
        try:
            await conn.execute(sqlalchemy.text('CREATE EXTENSION IF NOT EXISTS vector'))
        except Exception:
            logging.getLogger(__name__).warning(
                'pgvector extension not available — vector search disabled'
            )

    # 테이블 생성은 별도 트랜잭션
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
