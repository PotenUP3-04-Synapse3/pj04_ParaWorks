from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.demo_auth import DemoUser
from backend.app.models.messages import Message, MessageChannel
from backend.app.models.review import ReviewItem

KST = timezone(timedelta(hours=9))


SEED_CHANNELS = [
    {
        'id': 'announcements',
        'name': '전체공지',
        'description': '전사 공지와 운영 변경 사항을 공유합니다.',
        'unread_count': 2,
        'display_order': 0,
    },
    {
        'id': 'project-alpha',
        'name': '프로젝트-alpha',
        'description': 'Redis 결정, 작업 상태, 출시 준비를 논의합니다.',
        'unread_count': 1,
        'display_order': 1,
    },
    {
        'id': 'review-queue',
        'name': '검토-큐',
        'description': '출처 검증과 승인 대기 항목을 함께 확인합니다.',
        'unread_count': 0,
        'display_order': 2,
    },
]

SEED_MESSAGES = {
    'announcements': [
        {
            'id': 'ann-1',
            'channel_id': 'announcements',
            'author_name': '박서연',
            'author_role': '운영 리드',
            'body': 'ParaWorks 하네스는 오늘부터 한국어 기본 UI로 검증합니다.',
            'created_at': '2026-05-01T09:10:00+09:00',
        },
        {
            'id': 'ann-2',
            'channel_id': 'announcements',
            'author_name': '이도현',
            'author_role': '보안 담당',
            'body': '검색 결과의 출처 권한 상속 정책은 MVP에서도 계속 유지합니다.',
            'created_at': '2026-05-01T09:18:00+09:00',
        },
    ],
    'project-alpha': [
        {
            'id': 'alpha-1',
            'channel_id': 'project-alpha',
            'author_name': '김민준',
            'author_role': '백엔드',
            'body': 'Redis 기반 job progress와 Celery queue 흐름은 현재 mock sync에서 정상 확인됐습니다.',
            'created_at': '2026-05-01T09:24:00+09:00',
        },
        {
            'id': 'alpha-2',
            'channel_id': 'project-alpha',
            'author_name': '최하늘',
            'author_role': 'PM',
            'body': '검토 큐에서 evidence drawer까지 이어지는 흐름을 한국어 사용자 기준으로 다시 봐주세요.',
            'created_at': '2026-05-01T09:31:00+09:00',
        },
    ],
    'review-queue': [
        {
            'id': 'review-1',
            'channel_id': 'review-queue',
            'author_name': '정유진',
            'author_role': '지식 관리자',
            'body': '승인 전에는 반드시 원문 링크와 snippet을 확인하는 방식으로 데모합니다.',
            'created_at': '2026-05-01T09:37:00+09:00',
        }
    ],
}


def serialize_channel(channel: MessageChannel) -> dict:
    return {
        'id': channel.id,
        'name': channel.name,
        'description': channel.description,
        'unread_count': channel.unread_count,
    }


def serialize_message(message: Message) -> dict:
    return {
        'id': message.id,
        'channel_id': message.channel_id,
        'author_name': message.author_name,
        'author_role': message.author_role,
        'body': message.body,
        'created_at': message.created_at.isoformat(),
    }


def ensure_seed_data(db: Session) -> None:
    existing = db.scalar(select(MessageChannel.id).limit(1))
    if existing is not None:
        return

    for channel in SEED_CHANNELS:
        db.add(MessageChannel(**channel))

    for messages in SEED_MESSAGES.values():
        for message in messages:
            db.add(
                Message(
                    id=message['id'],
                    channel_id=message['channel_id'],
                    author_name=message['author_name'],
                    author_role=message['author_role'],
                    body=message['body'],
                    created_at=datetime.fromisoformat(message['created_at']),
                )
            )

    db.commit()


def list_channels(db: Session) -> list[dict]:
    ensure_seed_data(db)
    channels = db.scalars(
        select(MessageChannel).order_by(MessageChannel.display_order)
    ).all()
    return [serialize_channel(channel) for channel in channels]


def get_channel(db: Session, channel_id: str) -> dict | None:
    ensure_seed_data(db)
    channel = db.get(MessageChannel, channel_id)
    return serialize_channel(channel) if channel else None


def list_messages(db: Session, channel_id: str) -> list[dict]:
    ensure_seed_data(db)
    messages = db.scalars(
        select(Message)
        .where(Message.channel_id == channel_id)
        .order_by(Message.created_at, Message.id)
    ).all()
    return [serialize_message(message) for message in messages]


def append_message(db: Session, channel_id: str, body: str, user: DemoUser) -> dict:
    message = Message(
        id=f'msg-{uuid4().hex}',
        channel_id=channel_id,
        author_name='관리자' if user.role == 'admin' else '뷰어',
        author_role=user.role,
        body=body,
        created_at=datetime.now(KST),
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return serialize_message(message)


def get_message_record(db: Session, message_id: str) -> Message | None:
    ensure_seed_data(db)
    return db.get(Message, message_id)


def create_review_item_from_message(db: Session, message: Message) -> ReviewItem:
    review_item = ReviewItem(
        item_type='message_review',
        payload={
            'title': '메신저 검토 요청',
            'summary': message.body,
            'channel_id': message.channel_id,
            'message_id': message.id,
            'author_name': message.author_name,
        },
        source_links=[f'paraworks://messages/{message.id}'],
        source_snippets=[message.body],
        confidence_score=0.9,
        permission_level='internal',
        status='pending_review',
    )
    db.add(review_item)
    db.commit()
    db.refresh(review_item)
    return review_item
