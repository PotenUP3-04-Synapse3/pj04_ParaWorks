"""Phase A — Slack models + DecisionRecord + model changes.

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. 기존 ENUM 확장 ────────────────────────────────────────────────────
    # PostgreSQL ENUM에 값 추가 (트랜잭션 밖에서 실행해야 함)
    op.execute("ALTER TYPE reviewitemstatus ADD VALUE IF NOT EXISTS 'pending_review'")
    op.execute("ALTER TYPE reviewitemstatus ADD VALUE IF NOT EXISTS 'needs_more_evidence'")
    op.execute("ALTER TYPE reviewitemstatus ADD VALUE IF NOT EXISTS 'archived'")
    op.execute("ALTER TYPE reviewitemtype ADD VALUE IF NOT EXISTS 'decision_record'")
    op.execute("ALTER TYPE reviewitemtype ADD VALUE IF NOT EXISTS 'slack_thread_summary'")

    # ── 2. history_events 변경 ───────────────────────────────────────────────
    op.add_column(
        'history_events',
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        'ix_history_events_organization_id', 'history_events', ['organization_id'],
    )
    op.create_foreign_key(
        'fk_history_events_organization_id',
        'history_events', 'organizations',
        ['organization_id'], ['id'],
        ondelete='CASCADE',
    )
    op.alter_column('history_events', 'project_id', nullable=True)
    op.drop_constraint('history_events_project_id_fkey', 'history_events', type_='foreignkey')
    op.create_foreign_key(
        'fk_history_events_project_id',
        'history_events', 'projects',
        ['project_id'], ['id'],
        ondelete='SET NULL',
    )

    # ── 3. timeline_events 변경 ──────────────────────────────────────────────
    op.add_column(
        'timeline_events',
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        'ix_timeline_events_organization_id', 'timeline_events', ['organization_id'],
    )
    op.create_foreign_key(
        'fk_timeline_events_organization_id',
        'timeline_events', 'organizations',
        ['organization_id'], ['id'],
        ondelete='CASCADE',
    )
    op.alter_column('timeline_events', 'project_id', nullable=True)
    op.drop_constraint('timeline_events_project_id_fkey', 'timeline_events', type_='foreignkey')
    op.create_foreign_key(
        'fk_timeline_events_project_id',
        'timeline_events', 'projects',
        ['project_id'], ['id'],
        ondelete='SET NULL',
    )

    # ── 4. todos 변경 ────────────────────────────────────────────────────────
    op.add_column(
        'todos',
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index('ix_todos_organization_id', 'todos', ['organization_id'])
    op.create_foreign_key(
        'fk_todos_organization_id',
        'todos', 'organizations',
        ['organization_id'], ['id'],
        ondelete='CASCADE',
    )
    op.alter_column('todos', 'project_id', nullable=True)
    op.drop_constraint('todos_project_id_fkey', 'todos', type_='foreignkey')
    op.create_foreign_key(
        'fk_todos_project_id',
        'todos', 'projects',
        ['project_id'], ['id'],
        ondelete='SET NULL',
    )

    # ── 5. slack_workspaces 신규 테이블 ──────────────────────────────────────
    op.create_table(
        'slack_workspaces',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('slack_team_id', sa.String(64), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('bot_user_id', sa.String(64), nullable=True),
        sa.Column('access_token_encrypted', sa.Text(), nullable=True),
        sa.Column('installed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('installed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['installed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slack_team_id', name='uq_slack_workspace_team_id'),
    )
    op.create_index('ix_slack_workspaces_organization_id', 'slack_workspaces', ['organization_id'])
    op.create_index('ix_slack_workspaces_slack_team_id', 'slack_workspaces', ['slack_team_id'])

    # ── 6. slack_channels 신규 테이블 ────────────────────────────────────────
    # DO $$ ... EXCEPTION WHEN duplicate_object THEN null 으로 idempotent하게 생성
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE slackchannelpermission AS ENUM ('public', 'team', 'restricted');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$""")

    op.create_table(
        'slack_channels',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('slack_channel_id', sa.String(64), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('is_private', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_collection_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('permission_level', postgresql.ENUM('public', 'team', 'restricted',
                  name='slackchannelpermission', create_type=False), nullable=False, server_default='team'),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['slack_workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'slack_channel_id', name='uq_slack_channel'),
    )
    op.create_index('ix_slack_channels_organization_id', 'slack_channels', ['organization_id'])
    op.create_index('ix_slack_channels_workspace_id', 'slack_channels', ['workspace_id'])
    op.create_index('ix_slack_channels_slack_channel_id', 'slack_channels', ['slack_channel_id'])

    # ── 7. slack_messages 신규 테이블 ────────────────────────────────────────
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE slackmessagetype AS ENUM ('message', 'reply', 'bot_message');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$""")

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE slackingestionstatus AS ENUM ('pending', 'processing', 'done', 'failed');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$""")

    op.create_table(
        'slack_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('slack_message_ts', sa.String(32), nullable=False),
        sa.Column('thread_ts', sa.String(32), nullable=True),
        sa.Column('parent_message_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('author_slack_user_id', sa.String(64), nullable=False),
        sa.Column('author_display_name', sa.String(255), nullable=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('normalized_text', sa.Text(), nullable=True),
        sa.Column('message_type', postgresql.ENUM('message', 'reply', 'bot_message',
                  name='slackmessagetype', create_type=False), nullable=False, server_default='message'),
        sa.Column('permalink', sa.String(1024), nullable=True),
        sa.Column('has_attachments', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('attachments_json', postgresql.JSONB(), nullable=True),
        sa.Column('reactions_json', postgresql.JSONB(), nullable=True),
        sa.Column('mentioned_user_ids', postgresql.JSONB(), nullable=True),
        sa.Column('edited_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('event_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ingestion_status', postgresql.ENUM('pending', 'processing', 'done', 'failed',
                  name='slackingestionstatus', create_type=False), nullable=False, server_default='pending'),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['slack_workspaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['channel_id'], ['slack_channels.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_message_id'], ['slack_messages.id'],
                                ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('channel_id', 'slack_message_ts', name='uq_slack_message_ts'),
    )
    op.create_index('ix_slack_messages_organization_id', 'slack_messages', ['organization_id'])
    op.create_index('ix_slack_messages_workspace_id', 'slack_messages', ['workspace_id'])
    op.create_index('ix_slack_messages_channel_id', 'slack_messages', ['channel_id'])
    op.create_index('ix_slack_messages_slack_message_ts', 'slack_messages', ['slack_message_ts'])
    op.create_index('ix_slack_messages_thread_ts', 'slack_messages', ['thread_ts'])
    op.create_index('ix_slack_messages_author_slack_user_id', 'slack_messages',
                    ['author_slack_user_id'])
    op.create_index('ix_slack_messages_event_time', 'slack_messages', ['event_time'])

    # ── 8. slack_threads 신규 테이블 ─────────────────────────────────────────
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE slackthreadstatus AS ENUM (
                'unprocessed', 'processing', 'done', 'failed', 'needs_review');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$""")

    op.create_table(
        'slack_threads',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('thread_ts', sa.String(32), nullable=False),
        sa.Column('title', sa.String(512), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('participant_user_ids', postgresql.JSONB(), nullable=True),
        sa.Column('message_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('first_message_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('permalink', sa.String(1024), nullable=True),
        sa.Column('mapped_project_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('mapped_department_id', sa.String(255), nullable=True),
        sa.Column('mapped_business_domain', sa.String(255), nullable=True),
        sa.Column('processing_status', postgresql.ENUM(
            'unprocessed', 'processing', 'done', 'failed', 'needs_review',
            name='slackthreadstatus', create_type=False), nullable=False, server_default='unprocessed'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['slack_workspaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['channel_id'], ['slack_channels.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['mapped_project_id'], ['projects.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('channel_id', 'thread_ts', name='uq_slack_thread_ts'),
    )
    op.create_index('ix_slack_threads_organization_id', 'slack_threads', ['organization_id'])
    op.create_index('ix_slack_threads_workspace_id', 'slack_threads', ['workspace_id'])
    op.create_index('ix_slack_threads_channel_id', 'slack_threads', ['channel_id'])
    op.create_index('ix_slack_threads_thread_ts', 'slack_threads', ['thread_ts'])
    op.create_index('ix_slack_threads_first_message_at', 'slack_threads', ['first_message_at'])

    # ── 9. decision_records 신규 테이블 ──────────────────────────────────────
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE decisionrecordstatus AS ENUM ('draft', 'approved', 'rejected');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$""")

    op.create_table(
        'decision_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('title', sa.String(512), nullable=False),
        sa.Column('decision_summary', sa.Text(), nullable=False),
        sa.Column('situation', sa.Text(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('alternatives_considered', postgresql.JSONB(), nullable=True),
        sa.Column('constraints', sa.Text(), nullable=True),
        sa.Column('final_decision', sa.Text(), nullable=True),
        sa.Column('decision_maker', sa.String(255), nullable=True),
        sa.Column('participants', postgresql.JSONB(), nullable=True),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('source_links', postgresql.JSONB(), nullable=True),
        sa.Column('source_snippets', postgresql.JSONB(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('missing_evidence', sa.Text(), nullable=True),
        sa.Column('needs_human_review', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('status', postgresql.ENUM('draft', 'approved', 'rejected',
                  name='decisionrecordstatus', create_type=False), nullable=False, server_default='draft'),
        sa.Column('source_slack_thread_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['source_slack_thread_id'], ['slack_threads.id'],
                                ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_decision_records_organization_id', 'decision_records',
                    ['organization_id'])
    op.create_index('ix_decision_records_project_id', 'decision_records', ['project_id'])
    op.create_index('ix_decision_records_decided_at', 'decision_records', ['decided_at'])


def downgrade() -> None:
    # ── 9. decision_records 삭제 ─────────────────────────────────────────────
    op.drop_table('decision_records')
    op.execute("DROP TYPE IF EXISTS decisionrecordstatus")

    # ── 8. slack_threads 삭제 ────────────────────────────────────────────────
    op.drop_table('slack_threads')
    op.execute("DROP TYPE IF EXISTS slackthreadstatus")

    # ── 7. slack_messages 삭제 ───────────────────────────────────────────────
    op.drop_table('slack_messages')
    op.execute("DROP TYPE IF EXISTS slackmessagetype")
    op.execute("DROP TYPE IF EXISTS slackingestionstatus")

    # ── 6. slack_channels 삭제 ───────────────────────────────────────────────
    op.drop_table('slack_channels')
    op.execute("DROP TYPE IF EXISTS slackchannelpermission")

    # ── 5. slack_workspaces 삭제 ─────────────────────────────────────────────
    op.drop_table('slack_workspaces')

    # ── 4. todos 복구 ────────────────────────────────────────────────────────
    op.drop_constraint('fk_todos_project_id', 'todos', type_='foreignkey')
    op.create_foreign_key(
        'todos_project_id_fkey', 'todos', 'projects',
        ['project_id'], ['id'], ondelete='CASCADE',
    )
    op.alter_column('todos', 'project_id', nullable=False)
    op.drop_constraint('fk_todos_organization_id', 'todos', type_='foreignkey')
    op.drop_index('ix_todos_organization_id', table_name='todos')
    op.drop_column('todos', 'organization_id')

    # ── 3. timeline_events 복구 ──────────────────────────────────────────────
    op.drop_constraint('fk_timeline_events_project_id', 'timeline_events', type_='foreignkey')
    op.create_foreign_key(
        'timeline_events_project_id_fkey', 'timeline_events', 'projects',
        ['project_id'], ['id'], ondelete='CASCADE',
    )
    op.alter_column('timeline_events', 'project_id', nullable=False)
    op.drop_constraint('fk_timeline_events_organization_id', 'timeline_events',
                       type_='foreignkey')
    op.drop_index('ix_timeline_events_organization_id', table_name='timeline_events')
    op.drop_column('timeline_events', 'organization_id')

    # ── 2. history_events 복구 ───────────────────────────────────────────────
    op.drop_constraint('fk_history_events_project_id', 'history_events', type_='foreignkey')
    op.create_foreign_key(
        'history_events_project_id_fkey', 'history_events', 'projects',
        ['project_id'], ['id'], ondelete='CASCADE',
    )
    op.alter_column('history_events', 'project_id', nullable=False)
    op.drop_constraint('fk_history_events_organization_id', 'history_events', type_='foreignkey')
    op.drop_index('ix_history_events_organization_id', table_name='history_events')
    op.drop_column('history_events', 'organization_id')

    # ── 1. ENUM 값 제거는 PostgreSQL에서 지원하지 않으므로 스킵 ─────────────
