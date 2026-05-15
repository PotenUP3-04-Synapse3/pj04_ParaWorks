from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.agent_runtime import EvidencePacket, PermissionContext
from backend.app.agents.mail_document_agent import (
    MailDocumentAgent,
    MailDocumentAgentModelResponse,
    build_mail_document_evidence_packet,
    create_mail_document_agent_review_items,
    create_mail_document_agent_review_items_for_changed_sources,
)
from backend.app.models import (
    AgentRun,
    Document,
    DocumentChunk,
    DocumentVersion,
    Project,
    ReviewItem,
    Source,
)


class FakeMailDocumentModel:
    def extract(self, packet: EvidencePacket) -> MailDocumentAgentModelResponse:
        included_types = {message.metadata['source_type'] for message in packet.messages}
        assert packet.source_type == 'mail_document'
        assert included_types == {'gmail', 'drive'}
        assert packet.strictest_permission == 'restricted'
        return MailDocumentAgentModelResponse(
            title='Redis source-of-record decision',
            summary='Gmail and Drive evidence agree on Redis for transient state and PostgreSQL for records.',
            item_type='decision',
            confidence_score=0.9,
            input_tokens=1000,
            output_tokens=180,
        )


class FlexibleMailDocumentModel:
    def extract(self, packet: EvidencePacket) -> MailDocumentAgentModelResponse:
        return MailDocumentAgentModelResponse(
            title='Grouped source review',
            summary='Grouped mail/document evidence produced one review candidate.',
            item_type='history_event',
            confidence_score=0.82,
            input_tokens=100,
            output_tokens=40,
        )


class StructuredOverrideMailDocumentModel:
    def extract(self, packet: EvidencePacket) -> MailDocumentAgentModelResponse:
        return MailDocumentAgentModelResponse(
            title='K테크 1개월 파일럿 제안 검토 및 회신',
            summary='K테크 솔루션즈가 ParaWorks 1개월 파일럿 도입을 제안했습니다.',
            item_type='todo',
            confidence_score=0.91,
            input_tokens=120,
            output_tokens=60,
            model_name='gpt-5.4-mini',
            structured_data={
                'title': 'RE: [논의] K테크 솔루션즈 파일럿 제안 검토 요청',
                'summary': 'From: "김종우" <kjw4work@gmail.com> Date: Wed, 13 May 2026',
                'source_ids': ['malicious-source-override'],
                'agent_run_id': '99999',
                'estimated_cost_usd': '999',
                'business_context': 'K테크 솔루션즈가 ParaWorks 파일럿 도입에 관심을 보였습니다.',
                'action_required': 'true',
                'task_summary': '1개월 파일럿 제안의 범위와 성공 기준을 검토합니다.',
                'recommended_next_step': '파일럿 범위, 성공 지표, 일정 초안을 정리해 회신합니다.',
                'counterparty': 'K테크 솔루션즈',
                'source_subject': '[논의] K테크 솔루션즈 파일럿 제안 검토 요청',
                'summary_quality': 'actionable',
            },
        )


class FakeProjectRouter:
    def __init__(self, *, project_key: str | None, project_name: str | None, needs_user_selection: bool) -> None:
        self.project_key = project_key
        self.project_name = project_name
        self.needs_user_selection = needs_user_selection
        self.seen_candidates = []
        self.seen_projects = []

    def route(self, *, candidates, projects):
        self.seen_candidates = candidates
        self.seen_projects = projects
        return {
            'decisions': [
                {
                    'item_index': 0,
                    'source_id': candidates[0].source_id,
                    'project_key': self.project_key,
                    'project_name': self.project_name,
                    'confidence_score': 0.88 if self.project_key else 0.39,
                    'assignment_summary': (
                        'Gmail 본문과 첨부가 Project Alpha 업무와 연결됩니다.'
                        if self.project_key
                        else '등록 프로젝트와 확정 매칭되지 않습니다.'
                    ),
                    'assignment_reason': (
                        '메일 제목, 첨부 파일명, 본문 근거가 프로젝트 설명과 일치합니다.'
                        if self.project_key
                        else '문서 근거와 등록 프로젝트 설명이 충분히 일치하지 않습니다.'
                    ),
                    'alternatives': ['project-beta'] if self.project_key else ['project-alpha'],
                    'needs_user_selection': self.needs_user_selection,
                }
            ],
            'input_tokens': 17,
            'output_tokens': 11,
            'model_name': 'fake-project-router',
        }


def seed_chunk(
    db: Session,
    source_type: str,
    source_id: str,
    permission_level: str,
    metadata: dict | None = None,
    text: str | None = None,
    source_snippet: str | None = None,
) -> None:
    body = text or f'{source_type} body'
    source = Source(
        source_type=source_type,
        source_id=source_id,
        source_url=f'https://{source_type}.mock/{source_id}',
        title=f'{source_type} evidence',
        author='owner@example.com',
        permission_level=permission_level,
        raw_metadata={'ts': '2026-04-30T10:00:00+00:00', 'scenario': 'agent-bridge-test', **(metadata or {})},
    )
    db.add(source)
    db.flush()

    document = Document(source_id=source.id, title=source.title, current_version='v1')
    db.add(document)
    db.flush()

    version = DocumentVersion(document_id=document.id, version='v1', body=body)
    db.add(version)
    db.flush()

    db.add(
        DocumentChunk(
            version_id=version.id,
            source_id=source.id,
            chunk_index=0,
            text=body,
            source_snippet=source_snippet or body,
            permission_level=permission_level,
            metadata_={'source_url': source.source_url, 'source_type': source_type, **(metadata or {})},
        )
    )
    db.commit()


def seed_project(db: Session, project_key: str = 'project-alpha', name: str = 'Project Alpha') -> None:
    db.add(
        Project(
            project_key=project_key,
            name=name,
            summary='Redis-backed worker status and Project Alpha source evidence review.',
        )
    )
    db.commit()


def test_mail_document_agent_bridge_filters_sources_and_persists_run(db_session: Session) -> None:
    seed_chunk(db_session, 'gmail', 'gmail-agent-test', 'internal')
    seed_chunk(db_session, 'drive', 'drive-agent-test', 'restricted')
    seed_chunk(db_session, 'slack', 'slack-agent-test', 'internal')
    agent = MailDocumentAgent(model=FakeMailDocumentModel())

    created = create_mail_document_agent_review_items(
        db=db_session,
        agent=agent,
        permission_context=PermissionContext(
            user_id='demo-admin',
            role='admin',
            allowed_permission_levels=('public', 'internal', 'restricted'),
        ),
        source_window='mail-docs:2026-05-01',
    )

    assert len(created) == 1
    agent_run = db_session.scalars(select(AgentRun)).one()
    review_item = db_session.scalars(select(ReviewItem)).one()
    assert agent_run.agent_name == 'mail_document_agent'
    assert agent_run.prompt_version == 'mail-document-history:v1'
    assert agent_run.status == 'complete'
    assert agent_run.source_window == 'mail-docs:2026-05-01'
    assert agent_run.total_tokens == 1180
    assert agent_run.permission_level == 'restricted'
    assert agent_run.metadata_['included_source_types'] == ['drive', 'gmail']
    assert agent_run.metadata_['mail_document_workflow']['nodes'] == [
        'preprocess',
        'classify_reviewability',
        'extract_candidate',
        'project_route',
        'build_result',
    ]
    assert agent_run.metadata_['mail_document_workflow']['candidate_count'] == 1
    assert agent_run.metadata_['evidence_summary'] == [
        {
            'rank': 1,
            'source_id': 'gmail-agent-test',
            'source_url': 'https://gmail.mock/gmail-agent-test',
            'source_type': 'gmail',
            'timestamp': '2026-04-30T10:00:00+00:00',
            'author': 'owner@example.com',
            'permission_level': 'internal',
            'importance_score': 0,
            'snippet': 'gmail body',
        },
        {
            'rank': 2,
            'source_id': 'drive-agent-test',
            'source_url': 'https://drive.mock/drive-agent-test',
            'source_type': 'drive',
            'timestamp': '2026-04-30T10:00:00+00:00',
            'author': 'owner@example.com',
            'permission_level': 'restricted',
            'importance_score': 0,
            'snippet': 'drive body',
        },
    ]
    assert review_item.payload['agent_run_id'] == agent_run.id
    assert review_item.payload['agent_name'] == 'mail_document_agent'
    assert review_item.payload['source_ids'] == ['gmail-agent-test', 'drive-agent-test']
    assert review_item.payload['source_types'] == ['gmail', 'drive']
    assert review_item.payload['source_urls'] == [
        'https://gmail.mock/gmail-agent-test',
        'https://drive.mock/drive-agent-test',
    ]
    assert review_item.payload['source_authors'] == ['owner@example.com']
    assert review_item.source_links == [
        'https://gmail.mock/gmail-agent-test',
        'https://drive.mock/drive-agent-test',
    ]


def test_mail_document_evidence_packet_preserves_parser_status_metadata(db_session: Session) -> None:
    seed_chunk(
        db_session,
        'drive',
        'drive-pdf-test',
        'restricted',
        metadata={
            'parser_name': 'google_drive_metadata',
            'parser_status': 'metadata_only',
            'parser_status_reason': 'pdf_parser_not_enabled',
            'document_version': '42',
            'revision_id': 'rev-42',
            'content_signature': 'drive:file-1:42:rev-42',
            'content_hash': 'hash-42',
        },
    )

    packet = build_mail_document_evidence_packet(
        db=db_session,
        permission_context=PermissionContext(
            user_id='demo-admin',
            role='admin',
            allowed_permission_levels=('public', 'internal', 'restricted'),
        ),
        source_window='mail-docs:2026-05-01',
    )

    message = packet.messages[0]
    assert message.metadata['parser_name'] == 'google_drive_metadata'
    assert message.metadata['parser_status'] == 'metadata_only'
    assert message.metadata['parser_status_reason'] == 'pdf_parser_not_enabled'
    assert message.metadata['document_version'] == '42'
    assert message.metadata['revision_id'] == 'rev-42'
    assert message.metadata['content_signature'] == 'drive:file-1:42:rev-42'
    assert message.metadata['content_hash'] == 'hash-42'


def test_mail_document_evidence_packet_includes_gmail_attachment_sources(db_session: Session) -> None:
    seed_chunk(
        db_session,
        'gmail_attachment',
        'gmail_attachment:msg-1:att-1',
        'internal',
        metadata={
            'parser_name': 'gmail_attachment_metadata',
            'parser_status': 'metadata_only',
            'parser_status_reason': 'pdf_parser_not_enabled',
            'mime_type': 'application/pdf',
            'document_version': '1777600800000',
            'revision_id': 'att-1',
            'content_signature': 'gmail_attachment:msg-1:att-1:2048',
        },
    )

    packet = build_mail_document_evidence_packet(
        db=db_session,
        permission_context=PermissionContext(user_id='demo-admin', role='admin'),
        source_window='mail-docs:2026-05-01',
    )

    assert len(packet.messages) == 1
    message = packet.messages[0]
    assert message.source_id == 'gmail_attachment:msg-1:att-1'
    assert message.metadata['source_type'] == 'gmail_attachment'
    assert message.metadata['parser_name'] == 'gmail_attachment_metadata'
    assert message.metadata['parser_status'] == 'metadata_only'
    assert message.metadata['parser_status_reason'] == 'pdf_parser_not_enabled'


def test_mail_document_evidence_packet_can_scope_to_source_ids(db_session: Session) -> None:
    seed_chunk(db_session, 'gmail', 'gmail-agent-test', 'internal')
    seed_chunk(db_session, 'drive', 'drive-agent-test', 'restricted')

    packet = build_mail_document_evidence_packet(
        db=db_session,
        permission_context=PermissionContext(user_id='demo-admin', role='admin'),
        source_window='mail-docs:gmail-sync',
        source_ids=['gmail-agent-test'],
    )

    assert [message.source_id for message in packet.messages] == ['gmail-agent-test']
    assert {message.metadata['source_type'] for message in packet.messages} == {'gmail'}


def test_mail_document_evidence_packet_excludes_disallowed_permissions(db_session: Session) -> None:
    seed_chunk(db_session, 'gmail', 'gmail-agent-test', 'internal')
    seed_chunk(db_session, 'drive', 'drive-restricted-test', 'restricted')

    packet = build_mail_document_evidence_packet(
        db=db_session,
        permission_context=PermissionContext(
            user_id='hanvv-employee',
            role='employee',
            allowed_permission_levels=('public', 'internal'),
        ),
        source_window='mail-docs:employee',
    )

    assert [message.source_id for message in packet.messages] == ['gmail-agent-test']
    assert packet.strictest_permission == 'internal'


def test_mail_document_evidence_packet_excludes_disallowed_source_permission_even_when_chunk_is_internal(
    db_session: Session,
) -> None:
    source = Source(
        source_type='drive',
        source_id='drive-restricted-source-internal-chunk',
        source_url='https://drive.mock/restricted-source',
        title='Restricted source',
        author='owner@example.com',
        permission_level='restricted',
        raw_metadata={'ts': '2026-05-14T09:00:00+09:00'},
    )
    db_session.add(source)
    db_session.flush()
    document = Document(source_id=source.id, title=source.title, current_version='v1')
    db_session.add(document)
    db_session.flush()
    version = DocumentVersion(document_id=document.id, version='v1', body='Restricted source text.')
    db_session.add(version)
    db_session.flush()
    db_session.add(
        DocumentChunk(
            version_id=version.id,
            source_id=source.id,
            chunk_index=0,
            text='Restricted source text.',
            source_snippet='Restricted source text.',
            permission_level='internal',
            metadata_={'source_type': 'drive'},
        )
    )
    db_session.commit()

    packet = build_mail_document_evidence_packet(
        db=db_session,
        permission_context=PermissionContext(
            user_id='hanvv-employee',
            role='employee',
            allowed_permission_levels=('public', 'internal'),
        ),
        source_window='mail-docs:employee',
    )

    assert packet.messages == []


def test_mail_document_changed_source_review_items_preserve_group_local_source_ids(
    db_session: Session,
) -> None:
    seed_chunk(db_session, 'gmail', 'gmail:message-1', 'internal')
    seed_chunk(
        db_session,
        'gmail_attachment',
        'gmail_attachment:message-1:att-1',
        'internal',
        metadata={'parent_source_id': 'gmail:message-1'},
    )
    seed_chunk(db_session, 'drive', 'drive:file-1', 'internal')
    agent = MailDocumentAgent(model=FlexibleMailDocumentModel())

    created = create_mail_document_agent_review_items_for_changed_sources(
        db=db_session,
        agent=agent,
        permission_context=PermissionContext(
            user_id='demo-admin',
            role='admin',
            allowed_permission_levels=('public', 'internal', 'restricted'),
        ),
        source_window='mail-docs:changed',
        source_ids=['gmail:message-1', 'gmail_attachment:message-1:att-1', 'drive:file-1'],
    )

    assert len(created) == 2
    payloads = [item.payload for item in sorted(created, key=lambda item: item.id)]
    assert payloads[0]['source_ids'] == ['gmail:message-1', 'gmail_attachment:message-1:att-1']
    assert payloads[1]['source_ids'] == ['drive:file-1']


def test_mail_document_agent_routes_gmail_group_with_project_tool(
    db_session: Session,
) -> None:
    seed_project(db_session)
    seed_chunk(
        db_session,
        'gmail',
        'gmail:message-1',
        'internal',
        text='Subject: Project Alpha Redis summary\n\nRedis worker 상태 업데이트 검토를 요청합니다.',
        source_snippet='Project Alpha Redis summary',
    )
    seed_chunk(
        db_session,
        'gmail_attachment',
        'gmail_attachment:message-1:att-1',
        'internal',
        metadata={'parent_source_id': 'gmail:message-1'},
        text='Attachment: project-alpha-budget.pdf',
        source_snippet='project-alpha-budget.pdf 첨부',
    )
    router = FakeProjectRouter(
        project_key='project-alpha',
        project_name='Project Alpha',
        needs_user_selection=False,
    )
    agent = MailDocumentAgent(model=FlexibleMailDocumentModel())

    created = create_mail_document_agent_review_items_for_changed_sources(
        db=db_session,
        agent=agent,
        permission_context=PermissionContext(user_id='demo-admin', role='admin'),
        source_window='mail-docs:gmail-project',
        source_ids=['gmail:message-1', 'gmail_attachment:message-1:att-1'],
        project_router=router,
    )

    assert len(created) == 1
    assert router.seen_projects[0].project_key == 'project-alpha'
    assert router.seen_candidates[0].source_id == 'gmail:message-1|gmail_attachment:message-1:att-1'
    assert router.seen_candidates[0].source_links == [
        'https://gmail.mock/gmail:message-1',
        'https://gmail_attachment.mock/gmail_attachment:message-1:att-1',
    ]
    payload = created[0].payload
    assert payload['source_ids'] == ['gmail:message-1', 'gmail_attachment:message-1:att-1']
    assert payload['project_assignment_method'] == 'llm_tool'
    assert payload['project_key'] == 'project-alpha'
    assert payload['project_name'] == 'Project Alpha'
    assert payload['project_assignment_confidence'] == 0.88
    assert payload['project_needs_user_selection'] is False
    assert payload['project_alternatives'] == ['project-beta']
    agent_run = db_session.scalars(select(AgentRun)).one()
    assert agent_run.metadata_['project_routing'] == {
        'enabled': True,
        'method': 'langchain_tools',
        'project_count': 1,
        'model_name': 'fake-project-router',
        'input_tokens': 17,
        'output_tokens': 11,
    }


def test_mail_document_agent_marks_unmatched_drive_project_for_user_selection(
    db_session: Session,
) -> None:
    seed_project(db_session)
    seed_chunk(
        db_session,
        'drive',
        'drive:file-unknown',
        'restricted',
        text='Restricted pricing memo that does not mention any registered project.',
        source_snippet='Restricted pricing memo',
    )
    router = FakeProjectRouter(project_key=None, project_name=None, needs_user_selection=True)
    agent = MailDocumentAgent(model=FlexibleMailDocumentModel())

    created = create_mail_document_agent_review_items_for_changed_sources(
        db=db_session,
        agent=agent,
        permission_context=PermissionContext(
            user_id='demo-admin',
            role='admin',
            allowed_permission_levels=('public', 'internal', 'restricted'),
        ),
        source_window='mail-docs:drive-unmatched',
        source_ids=['drive:file-unknown'],
        project_router=router,
    )

    assert len(created) == 1
    payload = created[0].payload
    assert payload['source_ids'] == ['drive:file-unknown']
    assert payload['source_types'] == ['drive']
    assert payload['project_assignment_method'] == 'llm_tool'
    assert 'project_key' not in payload
    assert 'project_name' not in payload
    assert payload['project_needs_user_selection'] is True
    assert payload['project_assignment_confidence'] == 0.39
    assert payload['project_alternatives'] == ['project-alpha']


def test_mail_document_review_payload_filters_reserved_structured_fields(
    db_session: Session,
) -> None:
    seed_chunk(
        db_session,
        'gmail',
        'gmail:k-tech-pilot',
        'internal',
        text=(
            'Subject: [논의] K테크 솔루션즈 파일럿 제안 검토 요청\n\n'
            'K테크 솔루션즈 측에서 ParaWorks 1개월 파일럿 도입에 큰 관심을 보이고 있습니다. '
            '파일럿 범위와 성공 기준을 검토해 회신이 필요합니다.'
        ),
        source_snippet='K테크 솔루션즈 측에서 ParaWorks 1개월 파일럿 도입에 큰 관심을 보이고 있습니다.',
    )
    agent = MailDocumentAgent(model=StructuredOverrideMailDocumentModel())

    created = create_mail_document_agent_review_items(
        db=db_session,
        agent=agent,
        permission_context=PermissionContext(
            user_id='demo-admin',
            role='admin',
            allowed_permission_levels=('public', 'internal', 'restricted'),
        ),
        source_window='mail-docs:k-tech',
        source_ids=['gmail:k-tech-pilot'],
    )

    assert len(created) == 1
    item = created[0]
    assert item.item_type == 'todo'
    assert item.payload['title'] == 'K테크 1개월 파일럿 제안 검토 및 회신'
    assert item.payload['summary'] == 'K테크 솔루션즈가 ParaWorks 1개월 파일럿 도입을 제안했습니다.'
    assert item.payload['source_ids'] == ['gmail:k-tech-pilot']
    assert item.payload['agent_run_id'] != '99999'
    assert item.payload['estimated_cost_usd'] != '999'
    assert item.payload['recommended_next_step'] == '파일럿 범위, 성공 지표, 일정 초안을 정리해 회신합니다.'
    assert 'From:' not in item.payload['summary']


def test_mail_document_evidence_packet_includes_calendar_sources(db_session: Session) -> None:
    seed_chunk(
        db_session,
        'calendar',
        'calendar-project-alpha-review',
        'internal',
        metadata={
            'calendar_id': 'team@example.com',
            'calendar_summary': 'Team Calendar',
            'calendar_primary': False,
            'calendar_access_role': 'reader',
            'content_signature': 'calendar:team@example.com:event-1:2026-05-01T10:00:00Z',
            'event_context_key': 'event-1:2026-05-01T10:00:00Z',
            'event_status': 'confirmed',
            'organizer_email': 'lead@example.com',
            'event_start': '2026-05-02T09:00:00+09:00',
            'event_end': '2026-05-02T10:00:00+09:00',
            'duration_minutes': 60,
        },
    )

    packet = build_mail_document_evidence_packet(
        db=db_session,
        permission_context=PermissionContext(
            user_id='demo-admin',
            role='admin',
            allowed_permission_levels=('public', 'internal', 'restricted'),
        ),
        source_window='mail-docs-calendar:2026-05-01',
    )

    assert len(packet.messages) == 1
    message = packet.messages[0]
    assert message.source_id == 'calendar-project-alpha-review'
    assert message.metadata['source_type'] == 'calendar'
    assert message.metadata['event_context_key'] == 'event-1:2026-05-01T10:00:00Z'
    assert message.metadata['event_status'] == 'confirmed'
    assert message.metadata['organizer_email'] == 'lead@example.com'
    assert message.metadata['calendar_id'] == 'team@example.com'
    assert message.metadata['calendar_summary'] == 'Team Calendar'
    assert message.metadata['calendar_access_role'] == 'reader'
    assert message.metadata['content_signature'] == 'calendar:team@example.com:event-1:2026-05-01T10:00:00Z'
    assert message.metadata['event_start'] == '2026-05-02T09:00:00+09:00'


def test_mail_document_evidence_packet_preserves_chunk_snippet_and_calendar_due_metadata(db_session: Session) -> None:
    seed_chunk(
        db_session,
        'calendar',
        'calendar-alpha-deadline',
        'internal',
        text='프로젝트 Alpha 공유본 마감 회의입니다. 김하나님이 고객사 공유본을 준비합니다.',
        source_snippet='김하나님 고객사 공유본 준비 일정',
        metadata={
            'event_context_key': 'event-deadline:2026-05-20T09:00:00Z',
            'event_status': 'confirmed',
            'organizer_email': 'lead@example.com',
            'start': '2026-05-20T09:00:00+09:00',
            'end': '2026-05-20T09:30:00+09:00',
            'section_path': '일정',
        },
    )

    packet = build_mail_document_evidence_packet(
        db=db_session,
        permission_context=PermissionContext(user_id='demo-admin', role='admin'),
        source_window='mail-docs-calendar:2026-05-01',
    )

    message = packet.messages[0]
    assert message.source_snippet == '김하나님 고객사 공유본 준비 일정'
    assert message.metadata['source_type'] == 'calendar'
    assert message.metadata['start'] == '2026-05-20T09:00:00+09:00'
    assert message.metadata['section_path'] == '일정'
