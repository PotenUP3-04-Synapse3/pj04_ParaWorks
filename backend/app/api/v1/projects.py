from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.demo_auth import DemoUser, get_demo_user
from backend.app.db.session import get_db
from backend.app.permissions.service import can_access_permission
from backend.app.projects import build_project_memory

router = APIRouter(prefix='/projects', tags=['projects'])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[DemoUser, Depends(get_demo_user)]


@router.get('')
def list_projects(db: DbSession, user: CurrentUser) -> dict:
    projects = build_project_memory(db)
    visible_projects = [
        project
        for project in projects
        if can_access_permission(user, project.permission_level)
    ]
    return {
        'project_count': len(visible_projects),
        'hidden_project_count': len(projects) - len(visible_projects),
        'projects': [asdict(project) for project in visible_projects],
    }
