from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.agents.rag_orchestrator_agent.service import (
    citation_from_candidate,
    retrieve_matching_evidence_candidates,
)
from backend.app.core.demo_auth import DemoUser, get_demo_user
from backend.app.db.session import get_db
from backend.app.permissions.service import can_access_permission
from backend.app.schemas.search import SearchRequest

router = APIRouter(prefix='/search', tags=['search'])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[DemoUser, Depends(get_demo_user)]


@router.post('')
def search_knowledge(
    request: SearchRequest,
    db: DbSession,
    user: CurrentUser,
) -> dict:
    candidates = retrieve_matching_evidence_candidates(db=db, question=request.query)
    visible_candidates = [
        candidate for candidate in candidates if can_access_permission(user, candidate.permission_level)
    ]
    hidden_matches = len(candidates) - len(visible_candidates)

    response = {
        'hidden_match_count': hidden_matches,
        'results': [
            {
                'id': int(candidate.metadata.get('chunk_id') or index + 1),
                'source_id': candidate.source_id,
                'text': candidate.text,
                'source_snippet': candidate.source_snippet,
                'source_url': candidate.source_url,
                'source_type': candidate.metadata.get('source_type'),
                'permission_level': candidate.permission_level,
                'relevance_score': candidate.relevance_score,
                'matched_terms': candidate.matched_terms,
                'citation': citation_from_candidate(candidate),
            }
            for index, candidate in enumerate(visible_candidates)
        ]
    }
    if hidden_matches:
        response['permission_notice'] = 'Some sources may be hidden by permissions.'
    return response
