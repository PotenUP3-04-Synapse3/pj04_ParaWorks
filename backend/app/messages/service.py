from copy import deepcopy
from datetime import UTC, datetime
from uuid import uuid4

from backend.app.core.demo_auth import DemoUser


CHANNELS = [
    {
        'id': 'announcements',
        'name': '전체공지',
        'description': '전사 공지와 운영 변경 사항을 공유합니다.',
        'unread_count': 2,
    },
    {
        'id': 'project-alpha',
        'name': '프로젝트-alpha',
        'description': 'Redis 결정, 작업 상태, 출시 준비를 논의합니다.',
        'unread_count': 1,
    },
    {
        'id': 'review-queue',
        'name': '검토-큐',
        'description': '출처 검증과 승인 대기 항목을 함께 확인합니다.',
        'unread_count': 0,
    },
]

MESSAGES = {
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


def list_channels() -> list[dict]:
    return deepcopy(CHANNELS)


def get_channel(channel_id: str) -> dict | None:
    for channel in CHANNELS:
        if channel['id'] == channel_id:
            return deepcopy(channel)
    return None


def list_messages(channel_id: str) -> list[dict]:
    return deepcopy(MESSAGES.get(channel_id, []))


def append_message(channel_id: str, body: str, user: DemoUser) -> dict:
    message = {
        'id': f'msg-{uuid4().hex}',
        'channel_id': channel_id,
        'author_name': '관리자' if user.role == 'admin' else '뷰어',
        'author_role': user.role,
        'body': body,
        'created_at': datetime.now(UTC).isoformat(),
    }
    MESSAGES.setdefault(channel_id, []).append(message)
    return deepcopy(message)
