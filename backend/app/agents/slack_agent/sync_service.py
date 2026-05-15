import logging
import os
import sys
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.agent_runtime.contracts import (
    ReviewCandidate,
)
from backend.app.core.config import Settings
from backend.app.models import (
    AgentRun,
    Document,
    DocumentVersion,
    Project,
    ReviewItem,
    Source,
)

logger = logging.getLogger(__name__)

# 프로젝트 루트를 경로에 추가하여 agent_slack 임포트 가능하게 함
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from agent_slack.agent_slack import process_daily_slack_sync
except ImportError:
    # 폴더 구조에 따라 다를 수 있으므로 폴백 시도
    try:
        from pj04_ParaWorks.agent_slack.agent_slack import process_daily_slack_sync
    except ImportError:
        process_daily_slack_sync = None


def trigger_slack_agent_analysis(
    db: Session,
    days: int = 7,
    source_ids: list[str] | None = None,
    settings: Settings | None = None,
) -> int:
    """
    최근 N일간의 슬랙 데이터를 분석하여 지식 후보(ReviewItem)를 생성합니다.
    ID 기반 중복 체크를 통해 이미 분석된 메시지는 완벽하게 제외합니다.
    """
    if process_daily_slack_sync is None:
        logger.error('agent_slack.agent_slack module not found')
        return 0

    # 1. 이미 존재하는 ReviewItem들의 source_id 수집 (중복 분석 방지)
    existing_items = (
        db.execute(
            select(ReviewItem.payload).where(
                ReviewItem.created_at >= datetime.now(UTC) - timedelta(days=days)
            )
        )
        .scalars()
        .all()
    )

    processed_source_ids = set()
    for p in existing_items:
        if isinstance(p, dict) and 'source_ids' in p:
            processed_source_ids.update(p['source_ids'])

    # 2. 최근 N일간의 Slack 데이터 조회
    query = (
        select(Source, DocumentVersion.body)
        .join(Document, Source.id == Document.source_id)
        .join(DocumentVersion, Document.id == DocumentVersion.document_id)
        .where(Source.source_type == 'slack')
    )
    if source_ids:
        query = query.where(Source.source_id.in_(source_ids))
    else:
        start_date = datetime.now(UTC) - timedelta(days=days)
        query = query.where(Source.created_at >= start_date)

    results = db.execute(query).all()

    if not results:
        return 0

    # 3. 채널별 메시지 그룹화 및 ID 기반 필터링
    messages_by_channel: dict[str, list[dict[str, Any]]] = {}
    id_to_author: dict[str, str] = {}

    skipped_count = 0
    for source, body in results:
        # ID 기반 중복 체크 (가장 확실함)
        if source.source_id in processed_source_ids:
            skipped_count += 1
            continue

        channel_id = (
            source.raw_metadata.get('channel_id') or source.source_id.split(':', 1)[0]
        )
        if channel_id not in messages_by_channel:
            messages_by_channel[channel_id] = []

        messages_by_channel[channel_id].append(
            {
                'ts': source.raw_metadata.get('ts'),
                'source_id': source.source_id,
                'user': source.author,
                'text': body,
                'user_name': source.author,
            }
        )

        # ID -> 작성자 매핑 저장
        id_to_author[source.source_id] = source.author

    if skipped_count > 0:
        logger.info('Skipping already analyzed Slack messages count=%s', skipped_count)

    if not messages_by_channel:
        logger.info('No new Slack messages to analyze')
        return 0

    # 4. 각 채널별 분석 실행
    total_created = 0
    from backend.app.core.config import get_settings

    settings = settings or get_settings()

    for channel_id, messages in messages_by_channel.items():
        try:
            project_options = _registered_project_options(db)
            # 에이전트 실행
            result = process_daily_slack_sync(
                channel_id,
                messages,
                openai_api_key=settings.openai_api_key,
                gemini_api_key=settings.gemini_api_key or settings.google_api_key,
                projects=project_options,
            )

            run_cost = result.get('run_cost')
            candidates: list[ReviewCandidate] = result.get('candidates', [])

            agent_run = AgentRun(
                agent_name='slack_agent_v2',
                prompt_version='slack-taxonomy:v3',
                status='complete',
                source_window=f'slack:{channel_id}',
                cache_key=f'sync-{uuid4().hex}',
                model_name=result.get('model_name', 'gpt-4o-mini'),
                input_tokens=run_cost.token_usage.input_tokens if run_cost else 0,
                output_tokens=run_cost.token_usage.output_tokens if run_cost else 0,
                total_tokens=run_cost.token_usage.total_tokens if run_cost else 0,
                estimated_cost_usd=run_cost.estimated_cost_usd if run_cost else 0,
                permission_level='internal',
                metadata_={
                    'channel_id': channel_id,
                    'is_work_related': result.get('is_work_related', False),
                    'project_routing': {
                        'enabled': bool(project_options),
                        'method': 'langchain_tools',
                        'project_count': len(project_options),
                        'model_name': result.get('project_model_name'),
                        'input_tokens': result.get('project_prompt_tokens', 0),
                        'output_tokens': result.get('project_completion_tokens', 0),
                    },
                },
            )
            db.add(agent_run)
            db.flush()

            # 5. 분석된 후보들을 ReviewItem으로 저장
            for candidate in candidates:
                source_ids = []
                source_authors = []
                for url in candidate.source_links:
                    # URL에서 p 뒤의 숫자 10자리.6자리 추출 (슬랙 ID 규칙)
                    if '/p' in url:
                        raw_ts = url.split('/p')[-1].split('?')[0]
                        if len(raw_ts) >= 16:
                            # 1715000123456789 -> 1715000123.456789
                            formatted_ts = f'{raw_ts[:10]}.{raw_ts[10:]}'
                            sid = f'{channel_id}:{formatted_ts}'
                            source_ids.append(sid)
                            source_authors.append(id_to_author.get(sid, 'Unknown'))

                topic_tag = candidate.payload_fields.get('topic_tag', 'N/A')
                project_fields = {
                    key: candidate.payload_fields.get(key)
                    for key in (
                        'project_key',
                        'project_name',
                        'project_assignment_method',
                        'project_assignment_summary',
                        'project_assignment_reason',
                        'project_assignment_confidence',
                        'project_alternatives',
                        'project_needs_user_selection',
                    )
                    if key in candidate.payload_fields
                }

                payload = {
                    'title': candidate.title,
                    'summary': candidate.summary,
                    'category': candidate.payload_fields.get('category', 'Ad-hoc'),
                    'topic_tag': topic_tag,
                    'importance': candidate.payload_fields.get('importance', 'Medium'),
                    'assignee': candidate.payload_fields.get('assignee', '미지정'),
                    'due_date': candidate.payload_fields.get('due_date', '기한없음'),
                    'project_key': project_fields.get('project_key'),
                    'project_name': project_fields.get('project_name'),
                    'is_new_project': False,
                    'agent_run_id': agent_run.id,
                    'agent_name': 'slack_agent',
                    'prompt_version': agent_run.prompt_version,
                    'estimated_cost_usd': agent_run.estimated_cost_usd,
                    'source_ids': source_ids,  # 중복 체크를 위한 고유 ID 저장
                    'source_authors': source_authors,  # 작성자 이름 직접 저장
                    **project_fields,
                }

                review_item = ReviewItem(
                    status='pending_review',
                    item_type=candidate.item_type,
                    payload=payload,
                    source_links=candidate.source_links,
                    source_snippets=candidate.source_snippets,
                    confidence_score=candidate.confidence_score,
                    permission_level=candidate.permission_level,
                )
                db.add(review_item)
                total_created += 1

            db.commit()
        except Exception:
            logger.exception('Slack channel analysis failed channel_id=%s', channel_id)
            db.rollback()
            continue

    return total_created


def _registered_project_options(db: Session) -> list[dict[str, str]]:
    projects = db.scalars(select(Project).order_by(Project.created_at.desc(), Project.id.desc())).all()
    return [
        {
            'project_key': project.project_key,
            'name': project.name,
            'summary': project.summary,
        }
        for project in projects
    ]
