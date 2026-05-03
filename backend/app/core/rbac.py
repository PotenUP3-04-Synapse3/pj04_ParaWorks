from fastapi import HTTPException

from backend.app.core.demo_auth import DemoUser

ROLE_ORDER = {
    'employee': 10,
    'reviewer': 20,
    'manager': 30,
    'admin': 40,
}

PERMISSION_ORDER = {
    'public': 10,
    'internal': 20,
    'restricted': 30,
}

REVIEW_APPROVAL_PERMISSIONS = {
    'reviewer': {'public', 'internal'},
    'manager': {'public', 'internal', 'restricted'},
    'admin': {'public', 'internal', 'restricted'},
}

VALID_ROLES = frozenset(ROLE_ORDER)
VALID_STATUSES = frozenset({'active', 'suspended'})
VALID_PERMISSION_LEVELS = frozenset(PERMISSION_ORDER)


def has_role_at_least(user: DemoUser, minimum_role: str) -> bool:
    return ROLE_ORDER.get(user.role, 0) >= ROLE_ORDER.get(minimum_role, 10_000)


def require_role(user: DemoUser, *roles: str) -> None:
    if user.role not in roles:
        raise HTTPException(status_code=403, detail='Permission denied.')


def require_role_at_least(user: DemoUser, minimum_role: str) -> None:
    if not has_role_at_least(user, minimum_role):
        raise HTTPException(status_code=403, detail=f'{minimum_role} role required.')


def ensure_can_review_permission(user: DemoUser, permission_level: str) -> None:
    allowed_permissions = REVIEW_APPROVAL_PERMISSIONS.get(user.role, set())
    if permission_level not in allowed_permissions:
        raise HTTPException(status_code=403, detail='Review approval permission required.')


def validate_role(role: str) -> str:
    normalized = role.strip().lower()
    if normalized not in VALID_ROLES:
        raise HTTPException(status_code=400, detail='Unsupported role.')
    return normalized


def validate_status(status: str) -> str:
    normalized = status.strip().lower()
    if normalized not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail='Unsupported user status.')
    return normalized


def validate_permission_levels(permission_levels: list[str]) -> list[str]:
    normalized = sorted({level.strip().lower() for level in permission_levels if level.strip()})
    unsupported = [level for level in normalized if level not in VALID_PERMISSION_LEVELS]
    if unsupported:
        raise HTTPException(status_code=400, detail='Unsupported permission level.')
    return normalized
