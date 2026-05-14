from dataclasses import asdict, replace
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.demo_auth import DemoUser, get_demo_user, require_admin_user
from backend.app.db.session import get_db
from backend.app.permissions.service import can_access_permission
from backend.app.projects import build_project_memory
from backend.app.projects.classifier import (
    build_project_assignment_candidates,
    create_project_assignment_review_items,
)

router = APIRouter(prefix='/projects', tags=['projects'])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[DemoUser, Depends(get_demo_user)]
AdminUser = Annotated[DemoUser, Depends(require_admin_user)]


@router.get('')
def list_projects(db: DbSession, user: CurrentUser) -> dict:
    projects = build_project_memory(db)
    visible_projects = [_visible_project(project, user) for project in projects]
    hidden_evidence_count = sum(project.evidence_count - len(visible.evidence) for project, visible in zip(projects, visible_projects, strict=True))
    return {
        'project_count': len(visible_projects),
        'hidden_project_count': 0,
        'hidden_evidence_count': hidden_evidence_count,
        'projects': [asdict(project) for project in visible_projects],
    }


@router.post('/reclassify')
def reclassify_projects(db: DbSession, user: AdminUser, dry_run: bool = True) -> dict:
    candidates = build_project_assignment_candidates(db)
    if dry_run:
        created_count = 0
    else:
        created = create_project_assignment_review_items(db)
        created_count = len(created)
        db.commit()
    counts_by_project: dict[str, int] = {}
    for candidate in candidates:
        counts_by_project[candidate.project_key] = counts_by_project.get(candidate.project_key, 0) + 1
    return {
        'dry_run': dry_run,
        'candidate_count': len(candidates),
        'created_review_items': created_count,
        'counts_by_project': counts_by_project,
        'cost_policy': {
            'paid_llm_calls': False,
            'estimated_input_tokens': 0,
            'estimated_cost_usd': 0,
            'strategy': 'deterministic_project_classifier',
            'requires_human_review_state': True,
        },
    }


def _visible_project(project, user: DemoUser):
    visible_evidence = [
        evidence for evidence in project.evidence if can_access_permission(user, evidence.permission_level)
    ]
    visible_timeline = [
        item for item in project.timeline_items if can_access_permission(user, item.permission_level)
    ]
    visible_levels = [item.permission_level for item in visible_evidence] + [item.permission_level for item in visible_timeline]
    return replace(
        project,
        evidence=visible_evidence,
        timeline_items=visible_timeline,
        evidence_count=len(visible_evidence),
        permission_level=project.permission_level if visible_levels else 'internal',
    )
