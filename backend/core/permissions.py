from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = 'admin'
    MANAGER = 'manager'
    MEMBER = 'member'
    VIEWER = 'viewer'


class PermissionLevel(StrEnum):
    PUBLIC = 'public'        # 조직 내 누구나
    TEAM = 'team'            # 팀 내부
    DEPARTMENT = 'department'  # 부서 내부
    RESTRICTED = 'restricted'  # 명시적 권한 보유자만
    CONFIDENTIAL = 'confidential'  # 임원급 이상


ROLE_PERMISSION_MAP: dict[UserRole, set[PermissionLevel]] = {
    UserRole.ADMIN: {
        PermissionLevel.PUBLIC,
        PermissionLevel.TEAM,
        PermissionLevel.DEPARTMENT,
        PermissionLevel.RESTRICTED,
        PermissionLevel.CONFIDENTIAL,
    },
    UserRole.MANAGER: {
        PermissionLevel.PUBLIC,
        PermissionLevel.TEAM,
        PermissionLevel.DEPARTMENT,
        PermissionLevel.RESTRICTED,
    },
    UserRole.MEMBER: {
        PermissionLevel.PUBLIC,
        PermissionLevel.TEAM,
    },
    UserRole.VIEWER: {
        PermissionLevel.PUBLIC,
    },
}


class PermissionResolver:
    """원본 소스 권한(source_permission) + RBAC 레이어를 혼합하여 접근 가능 여부를 판단."""

    def __init__(self, user_role: UserRole, source_permission_levels: set[PermissionLevel] | None = None):
        self.user_role = user_role
        # source_permission_levels: Google Drive/Slack 원본 권한에서 추론된 레벨 집합
        self.source_permissions = source_permission_levels or set()

    def can_access(self, required_level: PermissionLevel) -> bool:
        role_ok = required_level in ROLE_PERMISSION_MAP[self.user_role]
        # 원본 권한이 명시된 경우 AND 조건 적용
        if self.source_permissions:
            source_ok = required_level in self.source_permissions
            return role_ok and source_ok
        return role_ok

    def accessible_levels(self) -> set[PermissionLevel]:
        role_levels = ROLE_PERMISSION_MAP[self.user_role]
        if self.source_permissions:
            return role_levels & self.source_permissions
        return role_levels
