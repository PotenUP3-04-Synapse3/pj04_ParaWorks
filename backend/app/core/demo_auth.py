from dataclasses import dataclass

from fastapi import Header


@dataclass(frozen=True)
class DemoUser:
    id: str
    email: str
    role: str
    permission_levels: set[str]


USERS = {
    'admin': DemoUser('demo-admin', 'admin@paraworks.local', 'admin', {'public', 'internal', 'restricted'}),
    'viewer': DemoUser('demo-viewer', 'viewer@paraworks.local', 'viewer', {'public', 'internal'}),
}


def get_demo_user(x_demo_user: str = Header(default='admin')) -> DemoUser:
    return USERS.get(x_demo_user, USERS['viewer'])
