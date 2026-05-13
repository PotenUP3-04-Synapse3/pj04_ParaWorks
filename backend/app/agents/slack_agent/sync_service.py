import os
import sys
from datetime import UTC, datetime, timedelta
from typing import List, Dict, Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import Source, ReviewItem, AgentRun, Document, DocumentVersion
from backend.app.agent_runtime.contracts import ReviewCandidate, TokenUsage, AgentRunCost

# 프로젝트 루트를 경로에 추가하여 agent_slack 임포트 가능하게 함
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
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

def trigger_slack_agent_analysis(db: Session, days: int = 7):
    """
    최근 N일간의 슬랙 데이터를 분석하여 지식 후보(ReviewItem)를 생성합니다.
    """
    if process_daily_slack_sync is None:
        print("[!] Error: agent_slack.agent_slack module not found.")
        return

    # 1. 최근 N일간의 Slack 데이터 및 본문(body) 조회 (Document join 필요)
    start_date = datetime.now(UTC) - timedelta(days=days)
    
    # Source와 DocumentVersion을 조인하여 본문 데이터를 함께 가져옴
    results = db.execute(
        select(Source, DocumentVersion.body)
        .join(Document, Source.id == Document.source_id)
        .join(DocumentVersion, Document.id == DocumentVersion.document_id)
        .where(Source.source_type == 'slack')
        .where(Source.created_at >= start_date)
    ).all()

    if not results:
        return

    # 2. 채널별로 메시지 그룹화
    messages_by_channel: Dict[str, List[Dict[str, Any]]] = {}
    for source, body in results:
        channel_id = source.raw_metadata.get('channel_id', 'unknown')
        if channel_id not in messages_by_channel:
            messages_by_channel[channel_id] = []
        
        # agent_slack.py가 기대하는 메시지 포맷으로 변환
        messages_by_channel[channel_id].append({
            'ts': source.raw_metadata.get('ts', source.created_at.timestamp()),
            'user': source.author,
            'text': body, # 조인된 DocumentVersion.body 사용
            'user_name': source.author # 일단 author를 이름으로 사용
        })

    # 3. 각 채널별 분석 실행
    total_created = 0
    for channel_id, messages in messages_by_channel.items():
        try:
            # 에이전트 실행
            result = process_daily_slack_sync(channel_id, messages)
            
            # AgentRun 기록 저장
            run_cost = result.get('run_cost')
            agent_run = AgentRun(
                agent_name='slack_agent_v2',
                prompt_version='slack-taxonomy:v1',
                status='complete',
                source_window=f'slack:last_{days}days:{channel_id}',
                cache_key=f'sync-{datetime.now(UTC).isoformat()}',
                model_name=result.get('model_name', 'gpt-4o-mini'),
                input_tokens=run_cost.token_usage.input_tokens if run_cost else 0,
                output_tokens=run_cost.token_usage.output_tokens if run_cost else 0,
                total_tokens=run_cost.token_usage.total_tokens if run_cost else 0,
                estimated_cost_usd=run_cost.estimated_cost_usd if run_cost else 0,
                permission_level='internal',
                metadata_={
                    'channel_id': channel_id,
                    'message_count': len(messages),
                    'is_work_related': result.get('is_work_related', False)
                }
            )
            db.add(agent_run)
            db.flush()

            # 4. 분석된 후보들을 ReviewItem으로 저장
            candidates: List[ReviewCandidate] = result.get('candidates', [])
            for candidate in candidates:
                # payload_fields에 추가 정보(assignee, due_date, category 등)가 포함되어 있음
                payload = {
                    'title': candidate.title,
                    'summary': candidate.summary,
                    'category': candidate.payload_fields.get('category', 'Ad-hoc'),
                    'topic_tag': candidate.payload_fields.get('topic_tag', 'N/A'),
                    'assignee': candidate.payload_fields.get('assignee', '미지정'),
                    'due_date': candidate.payload_fields.get('due_date', '기한없음'),
                    'source_channel_id': channel_id,
                    'agent_run_id': agent_run.id
                }
                
                review_item = ReviewItem(
                    status='pending_review',
                    item_type=candidate.item_type,
                    payload=payload,
                    source_links=candidate.source_links,
                    source_snippets=candidate.source_snippets,
                    confidence_score=candidate.confidence_score,
                    permission_level=candidate.permission_level
                    # agent_run_id 제거 (모델에 없음)
                )
                db.add(review_item)
                total_created += 1

            db.commit()
        except Exception as e:
            print(f"[!] Error analyzing channel {channel_id}: {e}")
            db.rollback()
            continue
    
    return total_created
