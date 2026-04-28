"""initial schema with pgvector

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-29
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # ENUM types
    op.execute("CREATE TYPE user_role AS ENUM ('admin', 'manager', 'member', 'viewer')")
    op.execute("CREATE TYPE permission_level AS ENUM ('public', 'team', 'department', 'restricted', 'confidential')")
    op.execute("CREATE TYPE review_status AS ENUM ('pending', 'approved', 'rejected', 'archived')")
    op.execute("CREATE TYPE asset_type AS ENUM ('document', 'decision', 'process', 'pattern', 'template', 'faq', 'other')")

    # organizations
    op.create_table(
        'organizations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('allowed_domains', postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # departments
    op.create_table(
        'departments',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('parent_dept_id', sa.String(36), sa.ForeignKey('departments.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # teams
    op.create_table(
        'teams',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('department_id', sa.String(36), sa.ForeignKey('departments.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # business_domains
    op.create_table(
        'business_domains',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # users
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('email', sa.String(320), unique=True, nullable=False),
        sa.Column('display_name', sa.String(255), nullable=True),
        sa.Column('role', postgresql.ENUM('admin', 'manager', 'member', 'viewer', name='user_role', create_type=False), nullable=False),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=True),
        sa.Column('department_id', sa.String(36), sa.ForeignKey('departments.id'), nullable=True),
        sa.Column('team_id', sa.String(36), sa.ForeignKey('teams.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    # decision_records
    op.create_table(
        'decision_records',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('related_project_id', sa.String(36), nullable=True),
        sa.Column('related_department_id', sa.String(36), sa.ForeignKey('departments.id'), nullable=True),
        sa.Column('business_domain', sa.String(255), nullable=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('decision_summary', sa.Text, nullable=False),
        sa.Column('situation', sa.Text, nullable=True),
        sa.Column('reason', sa.Text, nullable=True),
        sa.Column('alternatives_considered', postgresql.JSONB, nullable=True),
        sa.Column('constraints', sa.Text, nullable=True),
        sa.Column('final_decision', sa.Text, nullable=False),
        sa.Column('decision_maker', sa.String(320), nullable=True),
        sa.Column('participants', postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('source_links', postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column('source_snippets', postgresql.JSONB, nullable=True),
        sa.Column('confidence_score', sa.Numeric(4, 3), nullable=True),
        sa.Column('permission_level', postgresql.ENUM(
            'public', 'team', 'department', 'restricted', 'confidential',
            name='permission_level', create_type=False,
        ), nullable=False),
        sa.Column('review_status', postgresql.ENUM(
            'pending', 'approved', 'rejected', 'archived',
            name='review_status', create_type=False,
        ), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_decision_records_org', 'decision_records', ['organization_id'])

    # decision_participants
    op.create_table(
        'decision_participants',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('decision_id', sa.String(36), sa.ForeignKey('decision_records.id'), nullable=False),
        sa.Column('user_email', sa.String(320), nullable=False),
        sa.Column('role', sa.String(100), nullable=True),
    )
    op.create_index('ix_decision_participants_decision', 'decision_participants', ['decision_id'])

    # evidence_sources
    op.create_table(
        'evidence_sources',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('decision_id', sa.String(36), sa.ForeignKey('decision_records.id'), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('source_id', sa.String(255), nullable=True),
        sa.Column('source_url', sa.Text, nullable=True),
        sa.Column('snippet', sa.Text, nullable=True),
    )
    op.create_index('ix_evidence_sources_decision', 'evidence_sources', ['decision_id'])

    # knowledge_assets
    op.create_table(
        'knowledge_assets',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('summary', sa.Text, nullable=True),
        sa.Column('asset_type', postgresql.ENUM(
            'document', 'decision', 'process', 'pattern', 'template', 'faq', 'other',
            name='asset_type', create_type=False,
        ), nullable=False),
        sa.Column('related_projects', postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column('related_departments', postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column('related_decisions', postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column('source_links', postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column('permission_level', postgresql.ENUM(
            'public', 'team', 'department', 'restricted', 'confidential',
            name='permission_level', create_type=False,
        ), nullable=False),
        sa.Column('freshness_score', sa.Numeric(4, 3), nullable=True),
        sa.Column('is_external_client', sa.Boolean, default=False, nullable=False),
        sa.Column('external_data_policy', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_knowledge_assets_org', 'knowledge_assets', ['organization_id'])

    # document_collections
    op.create_table(
        'document_collections',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('source_id', sa.String(255), nullable=True),
        sa.Column('source_url', sa.Text, nullable=True),
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_document_collections_source', 'document_collections', ['source_id'])

    # document_versions
    op.create_table(
        'document_versions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('collection_id', sa.String(36), sa.ForeignKey('document_collections.id'), nullable=False),
        sa.Column('version_label', sa.String(50), nullable=True),
        sa.Column('content_hash', sa.String(64), nullable=True),
        sa.Column('diff_from_previous', sa.Text, nullable=True),
        sa.Column('full_text', sa.Text, nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_document_versions_collection', 'document_versions', ['collection_id'])

    # document_chunks (embedding vector column 포함)
    op.create_table(
        'document_chunks',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('collection_id', sa.String(36), sa.ForeignKey('document_collections.id'), nullable=False),
        sa.Column('version_id', sa.String(36), sa.ForeignKey('document_versions.id'), nullable=True),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('chunk_index', sa.Integer, nullable=False),
        sa.Column('page_number', sa.Integer, nullable=True),
        sa.Column('paragraph_index', sa.Integer, nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
    )
    op.create_index('ix_document_chunks_collection', 'document_chunks', ['collection_id'])
    # pgvector embedding column
    op.execute('ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding vector(1536)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_doc_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)')

    # source_permissions
    op.create_table(
        'source_permissions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('source_id', sa.String(255), nullable=False),
        sa.Column('user_email', sa.String(320), nullable=False),
        sa.Column('permission_role', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_source_permissions_source', 'source_permissions', ['source_id'])
    op.create_index('ix_source_permissions_user', 'source_permissions', ['user_email'])

    # handover_packets
    op.create_table(
        'handover_packets',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('from_user_email', sa.String(320), nullable=False),
        sa.Column('to_user_email', sa.String(320), nullable=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('summary', sa.Text, nullable=True),
        sa.Column('related_projects', postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column('decision_record_ids', postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column('knowledge_asset_ids', postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column('key_contacts', postgresql.JSONB, nullable=True),
        sa.Column('open_issues', postgresql.JSONB, nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # similar_cases
    op.create_table(
        'similar_cases',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('source_record_type', sa.String(50), nullable=False),
        sa.Column('source_record_id', sa.String(36), nullable=False),
        sa.Column('similar_record_type', sa.String(50), nullable=False),
        sa.Column('similar_record_id', sa.String(36), nullable=False),
        sa.Column('similarity_score', sa.Numeric(5, 4), nullable=True),
        sa.Column('similarity_reason', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # retrospective_insights
    op.create_table(
        'retrospective_insights',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('insight', sa.Text, nullable=False),
        sa.Column('related_decision_ids', postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # risk_patterns
    op.create_table(
        'risk_patterns',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('frequency', sa.Integer, nullable=False, server_default='1'),
        sa.Column('mitigation', sa.Text, nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # repeated_mistake_patterns
    op.create_table(
        'repeated_mistake_patterns',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('occurrence_count', sa.Integer, nullable=False, server_default='1'),
        sa.Column('last_occurred_decision_id', sa.String(36), nullable=True),
        sa.Column('prevention_note', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('repeated_mistake_patterns')
    op.drop_table('risk_patterns')
    op.drop_table('retrospective_insights')
    op.drop_table('similar_cases')
    op.drop_table('handover_packets')
    op.drop_table('source_permissions')
    op.drop_table('document_chunks')
    op.drop_table('document_versions')
    op.drop_table('document_collections')
    op.drop_table('knowledge_assets')
    op.drop_table('evidence_sources')
    op.drop_table('decision_participants')
    op.drop_table('decision_records')
    op.drop_table('users')
    op.drop_table('business_domains')
    op.drop_table('teams')
    op.drop_table('departments')
    op.drop_table('organizations')
    op.execute('DROP TYPE IF EXISTS asset_type')
    op.execute('DROP TYPE IF EXISTS review_status')
    op.execute('DROP TYPE IF EXISTS permission_level')
    op.execute('DROP TYPE IF EXISTS user_role')
