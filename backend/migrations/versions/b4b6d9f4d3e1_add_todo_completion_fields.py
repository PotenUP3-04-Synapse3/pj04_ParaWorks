"""add todo completion fields

Revision ID: b4b6d9f4d3e1
Revises: 9451b1f116b5
Create Date: 2026-05-15 00:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision = 'b4b6d9f4d3e1'
down_revision = '9451b1f116b5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    if 'todos' not in inspect(op.get_bind()).get_table_names():
        return

    _add_column_if_missing('todos', sa.Column('assignee', sa.String(length=300), nullable=True))
    _add_column_if_missing('todos', sa.Column('due_date', sa.String(length=32), nullable=True))
    _add_column_if_missing('todos', sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing('todos', sa.Column('completed_by', sa.String(length=100), nullable=True))
    _create_index_if_missing('ix_todos_due_date', 'todos', ['due_date'], unique=False)
    _create_index_if_missing('ix_todos_completed_at', 'todos', ['completed_at'], unique=False)
    _backfill_todo_review_payload_fields()


def downgrade() -> None:
    if 'todos' not in inspect(op.get_bind()).get_table_names():
        return
    _drop_index_if_exists('ix_todos_completed_at', 'todos')
    _drop_index_if_exists('ix_todos_due_date', 'todos')
    for column_name in ('completed_by', 'completed_at', 'due_date', 'assignee'):
        _drop_column_if_exists('todos', column_name)


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    inspector = inspect(op.get_bind())
    column_names = {item['name'] for item in inspector.get_columns(table_name)}
    if column.name not in column_names:
        op.add_column(table_name, column)


def _drop_column_if_exists(table_name: str, column_name: str) -> None:
    inspector = inspect(op.get_bind())
    column_names = {item['name'] for item in inspector.get_columns(table_name)}
    if column_name in column_names:
        op.drop_column(table_name, column_name)


def _create_index_if_missing(index_name: str, table_name: str, columns: list[str], *, unique: bool) -> None:
    inspector = inspect(op.get_bind())
    index_names = {item['name'] for item in inspector.get_indexes(table_name)}
    if index_name not in index_names:
        op.create_index(index_name, table_name, columns, unique=unique)


def _drop_index_if_exists(index_name: str, table_name: str) -> None:
    inspector = inspect(op.get_bind())
    index_names = {item['name'] for item in inspector.get_indexes(table_name)}
    if index_name in index_names:
        op.drop_index(op.f(index_name), table_name=table_name)


def _backfill_todo_review_payload_fields() -> None:
    bind = op.get_bind()
    if bind.dialect.name != 'postgresql':
        return
    bind.execute(
        text(
            """
            UPDATE todos AS todo
            SET
                assignee = COALESCE(todo.assignee, review_items.payload ->> 'assignee'),
                due_date = COALESCE(todo.due_date, review_items.payload ->> 'due_date')
            FROM review_items
            WHERE review_items.item_type = 'todo'
              AND review_items.status = 'approved'
              AND review_items.payload ->> 'title' = todo.title
              AND (
                    review_items.payload ->> 'project_key' = todo.project_key
                    OR todo.project_key IS NULL
                    OR review_items.payload ->> 'project_key' IS NULL
                  )
            """
        )
    )
