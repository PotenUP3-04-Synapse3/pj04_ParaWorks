from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.demo_auth import DemoUser, get_demo_user
from backend.app.db.session import get_db
from backend.app.models import DocumentChunk, Source
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
    query = request.query.lower()
    rows = db.execute(
        select(DocumentChunk, Source)
        .join(Source, DocumentChunk.source_id == Source.id)
        .order_by(DocumentChunk.id)
    ).all()
    matching_rows = [(chunk, source) for chunk, source in rows if query in chunk.text.lower()]
    visible_chunks = [
        (chunk, source)
        for chunk, source in matching_rows
        if can_access_permission(user, chunk.permission_level)
    ]
    hidden_matches = len(matching_rows) - len(visible_chunks)

    response = {
        'hidden_match_count': hidden_matches,
        'results': [
            {
                'id': chunk.id,
                'source_id': source.source_id,
                'text': chunk.text,
                'source_snippet': chunk.source_snippet,
                'source_url': chunk.metadata_.get('source_url'),
                'source_type': chunk.metadata_.get('source_type'),
                'permission_level': chunk.permission_level,
            }
            for chunk, source in visible_chunks
        ]
    }
    if hidden_matches:
        response['permission_notice'] = 'Some sources may be hidden by permissions.'
    return response
