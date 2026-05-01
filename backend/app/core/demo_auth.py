from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException


@dataclass(frozen=True)
class DemoUser:
    id: str
    email: str
    role: str
    permission_levels: set[str]
    name: str
    title: str
    department: str


USERS = {
    'admin': DemoUser(
        'demo-admin',
        'admin@paraworks.com',
        'admin',
        {'public', 'internal', 'restricted'},
        'ParaWorks Admin',
        'Workspace Administrator',
        'Platform',
    ),
    'viewer': DemoUser(
        'employee-mina',
        'mina@paraworks.com',
        'employee',
        {'public', 'internal'},
        'Kim Mina',
        'Product Manager',
        'Product',
    ),
    'employee-jun': DemoUser(
        'employee-jun',
        'jun@paraworks.com',
        'employee',
        {'public', 'internal'},
        'Lee Jun',
        'Backend Engineer',
        'Engineering',
    ),
    'employee-soyeon': DemoUser(
        'employee-soyeon',
        'soyeon@paraworks.com',
        'employee',
        {'public'},
        'Park Soyeon',
        'Operations Associate',
        'Operations',
    ),
}


def get_demo_user(x_demo_user: str = Header(default='admin')) -> DemoUser:
    return find_demo_user(x_demo_user) or USERS['viewer']


def find_demo_user(value: str) -> DemoUser | None:
    normalized = value.strip().lower()
    if not normalized:
        return None
    if normalized in USERS:
        return USERS[normalized]
    return next(
        (
            user
            for user in USERS.values()
            if user.id.lower() == normalized or user.email.lower() == normalized
        ),
        None,
    )


def authenticate_demo_user(email: str) -> DemoUser:
    user = find_demo_user(email)
    if user is None or user.email.lower() != email.strip().lower():
        raise HTTPException(status_code=401, detail='Demo account not found.')
    return user


def serialize_demo_user(user: DemoUser) -> dict:
    return {
        'id': user.id,
        'email': user.email,
        'role': user.role,
        'permission_levels': sorted(user.permission_levels),
        'name': user.name,
        'title': user.title,
        'department': user.department,
    }


def list_demo_users() -> list[dict]:
    return [serialize_demo_user(user) for user in USERS.values()]


def require_admin_user(user: DemoUser = Depends(get_demo_user)) -> DemoUser:
    if user.role != 'admin':
        raise HTTPException(status_code=403, detail='Admin permission required.')
    return user
