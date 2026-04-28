"""projects, notifications, audit_logs, integrations tables

Revision ID: 0002_projects_notifications_audit
Revises: 0001_initial
Create Date: 2026-04-29
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0002_projects_notifications_audit'
down_revision: Union[str, None] = '0001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # ENUM types (신규)
    # ------------------------------------------------------------------
    op.execute(
        "CREATE TYPE project_status AS ENUM ('active', 'completed', 'archived')"
    )
    op.execute(
        "CREATE TYPE notification_type AS ENUM "
        "('review_request', 'sync_complete', 'sync_error', 'hitl_approval', "
        "'handover_request', 'system')"
    )
    op.execute(
        "CREATE TYPE integration_type AS ENUM "
        "('google_drive', 'gmail', 'slack', 'google_calendar')"
    )
    op.execute(
        "CREATE TYPE integration_status AS ENUM "
        "('connected', 'disconnected', 'error', 'syncing')"
    )

    # ------------------------------------------------------------------
    # projects
    # ------------------------------------------------------------------
    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('status', sa.Enum('active', 'completed', 'archived', name='project_status'), nullable=False, server_default='active'),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('department_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata_', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index('ix_projects_organization_id', 'projects', ['organization_id'])
    op.create_index('ix_projects_status', 'projects', ['status'])

    # ------------------------------------------------------------------
    # notifications
    # ------------------------------------------------------------------
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('type', sa.Enum('review_request', 'sync_complete', 'sync_error', 'hitl_approval', 'handover_request', 'system', name='notification_type'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('body', sa.Text, nullable=True),
        sa.Column('link', sa.String(512), nullable=True),
        sa.Column('is_read', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('payload', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])
    op.create_index('ix_notifications_is_read', 'notifications', ['is_read'])

    # ------------------------------------------------------------------
    # audit_logs
    # ------------------------------------------------------------------
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('actor_email', sa.String(255), nullable=True),
        sa.Column('action', sa.String(128), nullable=False),          # e.g. decision.create
        sa.Column('resource_type', sa.String(64), nullable=True),
        sa.Column('resource_id', sa.String(255), nullable=True),
        sa.Column('detail', sa.Text, nullable=True),
        sa.Column('metadata_', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index('ix_audit_logs_organization_id', 'audit_logs', ['organization_id'])
    op.create_index('ix_audit_logs_actor_id', 'audit_logs', ['actor_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])

    # ------------------------------------------------------------------
    # integrations
    # ------------------------------------------------------------------
    op.create_table(
        'integrations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('type', sa.Enum('google_drive', 'gmail', 'slack', 'google_calendar', name='integration_type'), nullable=False),
        sa.Column('status', sa.Enum('connected', 'disconnected', 'error', 'syncing', name='integration_status'), nullable=False, server_default='disconnected'),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('config', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.UniqueConstraint('organization_id', 'type', name='uq_integrations_org_type'),
    )
    op.create_index('ix_integrations_organization_id', 'integrations', ['organization_id'])

    # ------------------------------------------------------------------
    # decision_records에 related_project_id 컬럼 추가 (프로젝트 타임라인 조인용)
    # ------------------------------------------------------------------
    op.add_column(
        'decision_records',
        sa.Column('related_project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='SET NULL'), nullable=True),
    )
    op.create_index('ix_decision_records_related_project_id', 'decision_records', ['related_project_id'])


def downgrade() -> None:
    op.drop_index('ix_decision_records_related_project_id', 'decision_records')
    op.drop_column('decision_records', 'related_project_id')

    op.drop_index('ix_integrations_organization_id', 'integrations')
    op.drop_table('integrations')

    op.drop_index('ix_audit_logs_action', 'audit_logs')
    op.drop_index('ix_audit_logs_actor_id', 'audit_logs')
    op.drop_index('ix_audit_logs_organization_id', 'audit_logs')
    op.drop_table('audit_logs')

    op.drop_index('ix_notifications_is_read', 'notifications')
    op.drop_index('ix_notifications_user_id', 'notifications')
    op.drop_table('notifications')

    op.drop_index('ix_projects_status', 'projects')
    op.drop_index('ix_projects_organization_id', 'projects')
    op.drop_table('projects')

    op.execute('DROP TYPE IF EXISTS integration_status')
    op.execute('DROP TYPE IF EXISTS integration_type')
    op.execute('DROP TYPE IF EXISTS notification_type')
    op.execute('DROP TYPE IF EXISTS project_status')
