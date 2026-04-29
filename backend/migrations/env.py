"""Alembic env.py — sync PostgreSQL migration environment (psycopg2)."""
from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection

# Import all models so Alembic detects them
from app.models.base import Base  # noqa: F401
from app.models import (  # noqa: F401
    Organization, User, Project, Campaign, Ticket,
    Todo, TimelineEvent, HistoryEvent,
    Source, SourceSnippet, Document, DocumentVersion,
    Integration, ReviewItem, Notification, AuditLog, PermissionPolicy,
    # Phase A — Slack + DecisionRecord
    SlackWorkspace, SlackChannel, SlackMessage, SlackThread,
    DecisionRecord,
)

config = context.config

# SYNC_DATABASE_URL 을 우선 사용 (psycopg2). 없으면 asyncpg URL을 변환
_async_url = os.environ.get('ASYNC_DATABASE_URL', '')
_sync_url = os.environ.get(
    'SYNC_DATABASE_URL',
    _async_url.replace('+asyncpg', '').replace('postgresql+', 'postgresql://').replace('postgresql://', 'postgresql+psycopg2://')
    if _async_url else ''
)
if not _sync_url:
    raise RuntimeError('SYNC_DATABASE_URL 또는 ASYNC_DATABASE_URL 환경변수를 설정해야 합니다.')

config.set_main_option('sqlalchemy.url', _sync_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option('sqlalchemy.url')
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        do_run_migrations(connection)
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
