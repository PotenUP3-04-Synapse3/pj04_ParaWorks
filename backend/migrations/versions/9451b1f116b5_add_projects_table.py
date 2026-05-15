"""add projects table

Revision ID: 9451b1f116b5
Revises: 5f8d874023d7
Create Date: 2026-05-14 14:45:50.965191
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = '9451b1f116b5'
down_revision = '5f8d874023d7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    _create_projects_table_if_missing()
    _create_index_if_missing('ix_projects_project_key', 'projects', ['project_key'], unique=True)


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if 'projects' not in inspector.get_table_names():
        return
    index_names = {item['name'] for item in inspector.get_indexes('projects')}
    if 'ix_projects_project_key' in index_names:
        op.drop_index(op.f('ix_projects_project_key'), table_name='projects')
    op.drop_table('projects')


def _create_projects_table_if_missing() -> None:
    inspector = inspect(op.get_bind())
    if 'projects' in inspector.get_table_names():
        return
    table_name = 'projects'
    op.create_table(
        table_name,
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_key', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=300), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def _create_index_if_missing(index_name: str, table_name: str, columns: list[str], *, unique: bool) -> None:
    inspector = inspect(op.get_bind())
    index_names = {item['name'] for item in inspector.get_indexes(table_name)}
    if index_name not in index_names:
        op.create_index(index_name, table_name, columns, unique=unique)
