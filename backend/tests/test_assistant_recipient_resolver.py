from sqlalchemy.orm import Session

from backend.app.assistant.recipient_resolver import resolve_email_recipients
from backend.app.models import AuthUser, Source


def test_recipient_resolver_uses_recent_conversation_contact_pair(db_session: Session) -> None:
    resolution = resolve_email_recipients(
        db=db_session,
        latest_message='김용희님한테 오늘 회의 3시에 있다고 메일 보내줘.',
        conversation_context='문의처\nCTO: 김용희 (yonghee199702@gmail.com)',
    )

    assert resolution.status == 'resolved'
    assert [candidate.email for candidate in resolution.candidates] == ['yonghee199702@gmail.com']


def test_recipient_resolver_uses_auth_user_display_name(db_session: Session) -> None:
    db_session.add(
        AuthUser(
            external_id='google-yonghee',
            email='yonghee199702@gmail.com',
            display_name='김용희',
            role='admin',
            department='Platform',
            title='CTO',
            status='active',
            permission_levels=['public', 'internal', 'restricted'],
        )
    )
    db_session.commit()

    resolution = resolve_email_recipients(
        db=db_session,
        latest_message='김용희님한테 오늘 회의 3시에 있다고 메일 보내줘.',
        conversation_context='[]',
    )

    assert resolution.status == 'resolved'
    assert resolution.candidates[0].email == 'yonghee199702@gmail.com'
    assert resolution.candidates[0].source_type == 'auth_user'


def test_recipient_resolver_uses_google_source_metadata(db_session: Session) -> None:
    db_session.add(
        Source(
            source_type='gmail',
            source_id='gmail:yonghee-contact',
            source_url='https://mail.google.com/mail/u/0/#all/yonghee-contact',
            title='회의 일정',
            author='김용희 <yonghee199702@gmail.com>',
            permission_level='internal',
            raw_metadata={
                'participants': ['김미나 <mina@paraworks.com>', '김용희 <yonghee199702@gmail.com>'],
            },
        )
    )
    db_session.commit()

    resolution = resolve_email_recipients(
        db=db_session,
        latest_message='김용희님한테 오늘 회의 3시에 있다고 메일 보내줘.',
        conversation_context='[]',
    )

    assert resolution.status == 'resolved'
    assert resolution.candidates[0].email == 'yonghee199702@gmail.com'
    assert 'source:gmail:yonghee-contact' in resolution.candidates[0].evidence


def test_recipient_resolver_marks_duplicate_names_ambiguous(db_session: Session) -> None:
    db_session.add_all(
        [
            AuthUser(
                external_id='google-yonghee-1',
                email='yonghee1@example.com',
                display_name='김용희',
                role='employee',
                department='Platform',
                title='CTO',
                status='active',
                permission_levels=['public', 'internal'],
            ),
            AuthUser(
                external_id='google-yonghee-2',
                email='yonghee2@example.com',
                display_name='김용희',
                role='employee',
                department='Sales',
                title='Account Owner',
                status='active',
                permission_levels=['public', 'internal'],
            ),
        ]
    )
    db_session.commit()

    resolution = resolve_email_recipients(
        db=db_session,
        latest_message='김용희님한테 메일 보내줘.',
        conversation_context='[]',
    )

    assert resolution.status == 'ambiguous'
    assert sorted(candidate.email for candidate in resolution.candidates) == [
        'yonghee1@example.com',
        'yonghee2@example.com',
    ]


def test_recipient_resolver_resolves_department_group(db_session: Session) -> None:
    db_session.add_all(
        [
            AuthUser(
                external_id='product-1',
                email='pm1@example.com',
                display_name='PM One',
                role='employee',
                department='Product',
                title='PM',
                status='active',
                permission_levels=['public', 'internal'],
            ),
            AuthUser(
                external_id='product-2',
                email='pm2@example.com',
                display_name='PM Two',
                role='employee',
                department='Product',
                title='PM',
                status='active',
                permission_levels=['public', 'internal'],
            ),
        ]
    )
    db_session.commit()

    resolution = resolve_email_recipients(
        db=db_session,
        latest_message='Product팀 전체에 회의 공지 메일 보내줘.',
        conversation_context='[]',
    )

    assert resolution.status == 'resolved'
    assert sorted(candidate.email for candidate in resolution.candidates) == [
        'mina@paraworks.com',
        'pm1@example.com',
        'pm2@example.com',
    ]
