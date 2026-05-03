from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import AuditLog, AuthUser


def test_admin_users_endpoint_seeds_manageable_users(client, db_session: Session) -> None:
    response = client.get('/api/v1/admin/users', headers={'X-Demo-User': 'hanvv-admin'})

    assert response.status_code == 200
    users = response.json()['users']
    emails = {user['email'] for user in users}
    assert 'hanvv3@gmail.com' in emails
    assert 'hanvv3@koreacu.ac.kr' in emails
    assert db_session.scalar(select(AuthUser).where(AuthUser.email == 'hanvv3@koreacu.ac.kr')) is not None


def test_employee_cannot_patch_user_role(client) -> None:
    response = client.patch(
        '/api/v1/admin/users/google-hanvv-employee',
        headers={'X-Demo-User': 'viewer'},
        json={'role': 'reviewer'},
    )

    assert response.status_code == 403


def test_admin_can_patch_user_role_and_audit_log_is_created(client, db_session: Session) -> None:
    client.get('/api/v1/admin/users', headers={'X-Demo-User': 'hanvv-admin'})

    response = client.patch(
        '/api/v1/admin/users/google-hanvv-employee',
        headers={'X-Demo-User': 'hanvv-admin'},
        json={'role': 'reviewer', 'permission_levels': ['public', 'internal']},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['user']['role'] == 'reviewer'
    assert payload['user']['permission_levels'] == ['internal', 'public']
    stored = db_session.scalar(select(AuthUser).where(AuthUser.email == 'hanvv3@koreacu.ac.kr'))
    assert stored is not None
    assert stored.role == 'reviewer'
    audit_log = db_session.scalar(select(AuditLog).where(AuditLog.action == 'admin.user.update'))
    assert audit_log is not None
    assert audit_log.actor_email == 'hanvv3@gmail.com'
    assert audit_log.target_id == 'google-hanvv-employee'
    assert audit_log.metadata_['previous']['role'] == 'employee'
    assert audit_log.metadata_['next']['role'] == 'reviewer'


def test_admin_patch_rejects_unsupported_role(client) -> None:
    client.get('/api/v1/admin/users', headers={'X-Demo-User': 'hanvv-admin'})

    response = client.patch(
        '/api/v1/admin/users/google-hanvv-employee',
        headers={'X-Demo-User': 'hanvv-admin'},
        json={'role': 'owner'},
    )

    assert response.status_code == 400
    assert response.json()['detail'] == 'Unsupported role.'


def test_admin_can_suspend_user(client, db_session: Session) -> None:
    client.get('/api/v1/admin/users', headers={'X-Demo-User': 'hanvv-admin'})

    response = client.patch(
        '/api/v1/admin/users/google-hanvv-employee',
        headers={'X-Demo-User': 'hanvv-admin'},
        json={'status': 'suspended'},
    )

    assert response.status_code == 200
    assert response.json()['user']['status'] == 'suspended'
    stored = db_session.scalar(select(AuthUser).where(AuthUser.email == 'hanvv3@koreacu.ac.kr'))
    assert stored is not None
    assert stored.status == 'suspended'
