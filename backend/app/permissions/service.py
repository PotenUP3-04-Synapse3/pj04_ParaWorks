from backend.app.core.demo_auth import DemoUser


def can_access_permission(user: DemoUser, permission_level: str) -> bool:
    return permission_level in user.permission_levels
