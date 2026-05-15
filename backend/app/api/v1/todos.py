from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.demo_auth import DemoUser, get_demo_user
from backend.app.db.session import get_db
from backend.app.models import Todo
from backend.app.permissions.service import can_access_permission

router = APIRouter(prefix='/todos', tags=['todos'])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[DemoUser, Depends(get_demo_user)]


@router.post('/{todo_id}/complete')
def complete_todo(todo_id: int, db: DbSession, user: CurrentUser) -> dict:
    todo = db.scalars(select(Todo).where(Todo.id == todo_id)).first()
    if todo is None:
        raise HTTPException(status_code=404, detail='Todo not found.')
    if not can_access_permission(user, todo.permission_level):
        raise HTTPException(status_code=403, detail='Todo permission denied.')

    if todo.completed_at is None:
        todo.completed_at = datetime.now(UTC)
        todo.completed_by = user.id
        db.commit()
        db.refresh(todo)

    return {
        'id': todo.id,
        'title': todo.title,
        'status': 'completed',
        'completed_at': todo.completed_at.isoformat() if todo.completed_at else None,
        'completed_by': todo.completed_by,
    }
