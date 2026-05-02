from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models import DecisionRecord, HistoryEvent, TimelineEvent, Todo

router = APIRouter(prefix='/knowledge', tags=['knowledge'])
DbSession = Annotated[Session, Depends(get_db)]


@router.get('')
def list_knowledge(db: DbSession) -> dict:
    decisions = db.scalars(select(DecisionRecord).order_by(DecisionRecord.created_at.desc(), DecisionRecord.id.desc())).all()
    history_events = db.scalars(select(HistoryEvent).order_by(HistoryEvent.created_at.desc(), HistoryEvent.id.desc())).all()
    timeline_events = db.scalars(select(TimelineEvent).order_by(TimelineEvent.created_at.desc(), TimelineEvent.id.desc())).all()
    todos = db.scalars(select(Todo).order_by(Todo.created_at.desc(), Todo.id.desc())).all()

    return {
        'counts': {
            'decisions': len(decisions),
            'history_events': len(history_events),
            'timeline_events': len(timeline_events),
            'todos': len(todos),
        },
        'decisions': [
            {
                'id': item.id,
                'title': item.title,
                'summary': item.decision_summary,
                'source_links': item.source_links,
                'source_snippets': item.source_snippets,
                'confidence_score': item.confidence_score,
                'permission_level': item.permission_level,
                'review_status': item.review_status,
                'created_at': item.created_at.isoformat(),
            }
            for item in decisions
        ],
        'history_events': [
            {
                'id': item.id,
                'title': item.title,
                'summary': item.reason,
                'source_links': item.source_links,
                'source_snippets': item.source_snippets,
                'confidence_score': item.confidence_score,
                'permission_level': item.permission_level,
                'review_status': item.review_status,
                'created_at': item.created_at.isoformat(),
            }
            for item in history_events
        ],
        'timeline_events': [
            {
                'id': item.id,
                'title': item.title,
                'summary': item.result_summary,
                'source_links': item.source_links,
                'source_snippets': item.source_snippets,
                'confidence_score': item.confidence_score,
                'permission_level': item.permission_level,
                'review_status': item.review_status,
                'created_at': item.created_at.isoformat(),
            }
            for item in timeline_events
        ],
        'todos': [
            {
                'id': item.id,
                'title': item.title,
                'summary': item.priority_reason,
                'priority': item.priority,
                'source_links': item.source_links,
                'source_snippets': item.source_snippets,
                'confidence_score': item.confidence_score,
                'permission_level': item.permission_level,
                'review_status': item.review_status,
                'created_at': item.created_at.isoformat(),
            }
            for item in todos
        ],
    }
