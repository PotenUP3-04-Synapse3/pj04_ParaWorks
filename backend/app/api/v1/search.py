from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.demo_auth import DemoUser, get_demo_user
from backend.app.db.session import get_db
from backend.app.models import DocumentChunk
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
    chunks = db.scalars(select(DocumentChunk).order_by(DocumentChunk.id)).all()
    matching_chunks = [chunk for chunk in chunks if query in chunk.text.lower()]
    visible_chunks = [
        chunk for chunk in matching_chunks if can_access_permission(user, chunk.permission_level)
    ]
    hidden_matches = len(matching_chunks) - len(visible_chunks)

    response = {
        'results': [
            {
                'id': chunk.id,
                'text': chunk.text,
                'source_snippet': chunk.source_snippet,
                'source_url': chunk.metadata_.get('source_url'),
                'source_type': chunk.metadata_.get('source_type'),
                'permission_level': chunk.permission_level,
            }
            for chunk in visible_chunks
        ]
    }
    if hidden_matches:
        response['permission_notice'] = 'Some sources may be hidden by permissions.'
    return response
