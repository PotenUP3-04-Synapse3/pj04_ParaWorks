# RAG Orchestrator Assistant Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a database-backed, per-user AI assistant conversation memory for `/search` while keeping cost visibility in `/agent-runs`.

**Architecture:** Add assistant-specific SQLAlchemy models, a focused service layer, and `/api/v1/assistant` routes that wrap the existing RAG orchestrator. Then refactor only `frontend/src/app/search/page.tsx` into a conversation UI that persists messages, shows evidence and permission state, and hides token/cost/cache details.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, pytest, Next.js App Router, React, TypeScript, Tailwind, Playwright.

---

## File Structure

Create:

- `backend/app/models/assistant.py`
  - Owns assistant conversation and assistant message tables.
- `backend/app/assistant/__init__.py`
  - Exposes assistant service helpers.
- `backend/app/assistant/service.py`
  - Owns user-scoped conversation CRUD, message persistence, compact context building, and serialization.
- `backend/app/schemas/assistant.py`
  - Defines request/response shapes for assistant APIs.
- `backend/app/api/v1/assistant.py`
  - Provides `/api/v1/assistant` endpoints.
- `backend/tests/test_assistant_models.py`
  - Covers DB persistence basics.
- `backend/tests/test_assistant_service.py`
  - Covers user scoping and compact context.
- `backend/tests/test_assistant_api.py`
  - Covers API conversation flow and cost-field hiding.
- `frontend/e2e/assistant-memory.spec.ts`
  - Covers `/search` persisted assistant UX with mocked assistant APIs.

Modify:

- `backend/app/models/__init__.py`
  - Registers assistant models with SQLAlchemy metadata.
- `backend/app/agents/rag_orchestrator_agent/agent.py`
  - Adds optional `agent_run_id` to `RagAnswer`.
- `backend/app/agents/rag_orchestrator_agent/service.py`
  - Flushes the created `AgentRun` id into `RagAnswer`.
- `backend/app/api/v1/ask.py`
  - Includes `agent_run_id` for compatibility and observability.
- `backend/app/api/v1/router.py`
  - Includes the assistant router.
- `backend/tests/test_rag_orchestrator_service.py`
  - Verifies RAG answer exposes its created `AgentRun`.
- `frontend/src/lib/api/types.ts`
  - Adds assistant API types.
- `frontend/src/app/search/page.tsx`
  - Converts the page into the persisted AI assistant conversation surface.

Do not modify:

- any page except `frontend/src/app/search/page.tsx`;
- Slack, Gmail, Google Drive, Calendar connector internals;
- `/agent-runs` UI;
- `frontend/next-env.d.ts`, which is already modified outside this task.

---

### Task 1: Add Assistant Persistence Models

**Files:**

- Create: `backend/app/models/assistant.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_assistant_models.py`

- [ ] **Step 1: Write the failing model test**

Create `backend/tests/test_assistant_models.py`:

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import AssistantConversation, AssistantMessage


def test_assistant_conversation_and_messages_persist(db_session: Session) -> None:
    conversation = AssistantConversation(
        user_id='employee-mina',
        title='Redis 회의 준비',
        summary='Redis 관련 이전 대화 요약',
    )
    db_session.add(conversation)
    db_session.flush()

    message = AssistantMessage(
        conversation_id=conversation.id,
        role='assistant',
        content='Redis는 일시적인 작업 상태 공유에 사용됩니다.',
        citations=[
            {
                'source_id': 'gmail-redis',
                'source_url': 'https://gmail.mock/redis',
                'permission_level': 'internal',
            }
        ],
        source_ids=['gmail-redis'],
        source_links=['https://gmail.mock/redis'],
        source_snippets=['Redis 작업 상태 근거'],
        permission_level='internal',
        hidden_match_count=0,
        permission_notice=None,
        agent_run_id=7,
        metadata_={'retrieval_backend': 'deterministic_lexical'},
    )
    db_session.add(message)
    db_session.commit()

    stored = db_session.scalar(
        select(AssistantConversation).where(AssistantConversation.user_id == 'employee-mina')
    )

    assert stored is not None
    assert stored.title == 'Redis 회의 준비'
    assert stored.summary == 'Redis 관련 이전 대화 요약'
    assert len(stored.messages) == 1
    assert stored.messages[0].content == 'Redis는 일시적인 작업 상태 공유에 사용됩니다.'
    assert stored.messages[0].citations[0]['source_id'] == 'gmail-redis'
    assert stored.messages[0].agent_run_id == 7
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
uv run pytest backend/tests/test_assistant_models.py -v
```

Expected: FAIL because `AssistantConversation` and `AssistantMessage` are not exported yet.

- [ ] **Step 3: Add the assistant models**

Create `backend/app/models/assistant.py`:

```python
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class AssistantConversation(Base):
    __tablename__ = 'assistant_conversations'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(120), index=True)
    title: Mapped[str] = mapped_column(String(160), default='새 대화')
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        index=True,
    )
    messages: Mapped[list['AssistantMessage']] = relationship(
        back_populates='conversation',
        cascade='all, delete-orphan',
        order_by='AssistantMessage.created_at',
    )


class AssistantMessage(Base):
    __tablename__ = 'assistant_messages'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey('assistant_conversations.id'), index=True)
    role: Mapped[str] = mapped_column(String(24), index=True)
    content: Mapped[str] = mapped_column(Text)
    citations: Mapped[list] = mapped_column(MutableList.as_mutable(JSON), default=list)
    source_ids: Mapped[list] = mapped_column(MutableList.as_mutable(JSON), default=list)
    source_links: Mapped[list] = mapped_column(MutableList.as_mutable(JSON), default=list)
    source_snippets: Mapped[list] = mapped_column(MutableList.as_mutable(JSON), default=list)
    permission_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    hidden_match_count: Mapped[int] = mapped_column(Integer, default=0)
    permission_notice: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    metadata_: Mapped[dict] = mapped_column('metadata', MutableDict.as_mutable(JSON), default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True,
    )
    conversation: Mapped[AssistantConversation] = relationship(back_populates='messages')
```

- [ ] **Step 4: Export the models**

Modify `backend/app/models/__init__.py`:

```python
from backend.app.models.assistant import AssistantConversation, AssistantMessage
```

Add both names to `__all__`:

```python
    'AssistantConversation',
    'AssistantMessage',
```

- [ ] **Step 5: Run the model test**

Run:

```powershell
uv run pytest backend/tests/test_assistant_models.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```powershell
git add backend/app/models/assistant.py backend/app/models/__init__.py backend/tests/test_assistant_models.py
git commit -m "feat: add assistant conversation models"
```

---

### Task 2: Add Assistant Service Layer

**Files:**

- Create: `backend/app/assistant/__init__.py`
- Create: `backend/app/assistant/service.py`
- Test: `backend/tests/test_assistant_service.py`

- [ ] **Step 1: Write the failing service tests**

Create `backend/tests/test_assistant_service.py`:

```python
import pytest
from sqlalchemy.orm import Session

from backend.app.assistant.service import (
    RECENT_CONTEXT_MESSAGE_LIMIT,
    append_assistant_message,
    append_user_message,
    build_contextual_question,
    create_conversation,
    get_owned_conversation,
    list_conversations,
    list_messages,
)
from backend.app.core.demo_auth import USERS


def test_conversations_are_scoped_to_user(db_session: Session) -> None:
    viewer = USERS['viewer']
    employee = USERS['employee-jun']
    create_conversation(db_session, viewer, title='Viewer private thread')
    create_conversation(db_session, employee, title='Employee private thread')

    viewer_conversations = list_conversations(db_session, viewer)

    assert [conversation.title for conversation in viewer_conversations] == ['Viewer private thread']


def test_get_owned_conversation_rejects_other_user(db_session: Session) -> None:
    viewer = USERS['viewer']
    employee = USERS['employee-jun']
    conversation = create_conversation(db_session, viewer, title='Viewer private thread')

    with pytest.raises(ValueError, match='assistant conversation not found'):
        get_owned_conversation(db_session, employee, conversation.id)


def test_append_messages_and_context_window(db_session: Session) -> None:
    viewer = USERS['viewer']
    conversation = create_conversation(db_session, viewer, title='Redis')
    for index in range(8):
        append_user_message(db_session, conversation, f'사용자 질문 {index}')
        append_assistant_message(
            db_session,
            conversation,
            content=f'비서 답변 {index}',
            citations=[],
            source_ids=[],
            source_links=[],
            source_snippets=[],
            permission_level='internal',
            hidden_match_count=0,
            permission_notice=None,
            agent_run_id=None,
            metadata={'turn': index},
        )
    conversation.summary = '이전 대화는 Redis 작업 상태에 관한 내용입니다.'
    db_session.commit()

    messages = list_messages(db_session, viewer, conversation.id)
    contextual_question = build_contextual_question(
        conversation=conversation,
        messages=messages,
        new_message='그 다음 할 일은?',
    )

    assert len(messages) == 16
    assert '대화 요약: 이전 대화는 Redis 작업 상태에 관한 내용입니다.' in contextual_question
    assert '현재 질문: 그 다음 할 일은?' in contextual_question
    assert '사용자 질문 0' not in contextual_question
    assert '비서 답변 7' in contextual_question
    assert contextual_question.count('assistant:') <= RECENT_CONTEXT_MESSAGE_LIMIT // 2 + 1
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
uv run pytest backend/tests/test_assistant_service.py -v
```

Expected: FAIL because `backend.app.assistant.service` does not exist.

- [ ] **Step 3: Create the service package**

Create `backend/app/assistant/__init__.py`:

```python
from backend.app.assistant.service import (
    RECENT_CONTEXT_MESSAGE_LIMIT,
    append_assistant_message,
    append_user_message,
    build_contextual_question,
    create_conversation,
    get_owned_conversation,
    list_conversations,
    list_messages,
    serialize_conversation,
    serialize_message,
)

__all__ = [
    'RECENT_CONTEXT_MESSAGE_LIMIT',
    'append_assistant_message',
    'append_user_message',
    'build_contextual_question',
    'create_conversation',
    'get_owned_conversation',
    'list_conversations',
    'list_messages',
    'serialize_conversation',
    'serialize_message',
]
```

- [ ] **Step 4: Add the service implementation**

Create `backend/app/assistant/service.py`:

```python
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.demo_auth import DemoUser
from backend.app.models import AssistantConversation, AssistantMessage

RECENT_CONTEXT_MESSAGE_LIMIT = 6
DEFAULT_CONVERSATION_TITLE = '새 대화'


def create_conversation(db: Session, user: DemoUser, *, title: str | None = None) -> AssistantConversation:
    conversation = AssistantConversation(
        user_id=user.id,
        title=_conversation_title(title),
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def list_conversations(db: Session, user: DemoUser) -> list[AssistantConversation]:
    return list(
        db.scalars(
            select(AssistantConversation)
            .where(AssistantConversation.user_id == user.id)
            .order_by(AssistantConversation.updated_at.desc(), AssistantConversation.id.desc())
        )
    )


def get_owned_conversation(db: Session, user: DemoUser, conversation_id: int) -> AssistantConversation:
    conversation = db.scalar(
        select(AssistantConversation)
        .options(selectinload(AssistantConversation.messages))
        .where(
            AssistantConversation.id == conversation_id,
            AssistantConversation.user_id == user.id,
        )
    )
    if conversation is None:
        raise ValueError('assistant conversation not found')
    return conversation


def list_messages(db: Session, user: DemoUser, conversation_id: int) -> list[AssistantMessage]:
    conversation = get_owned_conversation(db, user, conversation_id)
    return list(conversation.messages)


def append_user_message(db: Session, conversation: AssistantConversation, content: str) -> AssistantMessage:
    message = AssistantMessage(
        conversation_id=conversation.id,
        role='user',
        content=content.strip(),
    )
    conversation.updated_at = datetime.now(UTC)
    if conversation.title == DEFAULT_CONVERSATION_TITLE:
        conversation.title = _conversation_title(content)
    db.add(message)
    db.commit()
    db.refresh(message)
    db.refresh(conversation)
    return message


def append_assistant_message(
    db: Session,
    conversation: AssistantConversation,
    *,
    content: str,
    citations: list,
    source_ids: list,
    source_links: list,
    source_snippets: list,
    permission_level: str | None,
    hidden_match_count: int,
    permission_notice: str | None,
    agent_run_id: int | None,
    metadata: dict,
) -> AssistantMessage:
    message = AssistantMessage(
        conversation_id=conversation.id,
        role='assistant',
        content=content,
        citations=citations,
        source_ids=source_ids,
        source_links=source_links,
        source_snippets=source_snippets,
        permission_level=permission_level,
        hidden_match_count=hidden_match_count,
        permission_notice=permission_notice,
        agent_run_id=agent_run_id,
        metadata_=metadata,
    )
    conversation.updated_at = datetime.now(UTC)
    conversation.summary = update_summary(conversation.summary, message.content)
    conversation.summary_updated_at = datetime.now(UTC)
    db.add(message)
    db.commit()
    db.refresh(message)
    db.refresh(conversation)
    return message


def build_contextual_question(
    *,
    conversation: AssistantConversation,
    messages: list[AssistantMessage],
    new_message: str,
) -> str:
    parts: list[str] = []
    if conversation.summary:
        parts.append(f'대화 요약: {conversation.summary}')

    # 전체 대화를 보내지 않고 최근 메시지만 사용해 토큰 사용량을 제한한다.
    recent_messages = messages[-RECENT_CONTEXT_MESSAGE_LIMIT:]
    if recent_messages:
        parts.append('최근 대화:')
        parts.extend(f'{message.role}: {message.content}' for message in recent_messages)

    parts.append(f'현재 질문: {new_message.strip()}')
    return '\n'.join(parts)


def update_summary(existing_summary: str | None, latest_answer: str) -> str:
    summary_basis = f'{existing_summary or ""}\n{latest_answer}'.strip()
    return summary_basis[:1000]


def serialize_conversation(conversation: AssistantConversation) -> dict:
    return {
        'id': conversation.id,
        'title': conversation.title,
        'summary': conversation.summary,
        'created_at': conversation.created_at.isoformat(),
        'updated_at': conversation.updated_at.isoformat(),
    }


def serialize_message(message: AssistantMessage) -> dict:
    return {
        'id': message.id,
        'conversation_id': message.conversation_id,
        'role': message.role,
        'content': message.content,
        'citations': message.citations,
        'source_ids': message.source_ids,
        'source_links': message.source_links,
        'source_snippets': message.source_snippets,
        'permission_level': message.permission_level,
        'hidden_match_count': message.hidden_match_count,
        'permission_notice': message.permission_notice,
        'agent_run_id': message.agent_run_id,
        'metadata': message.metadata_,
        'created_at': message.created_at.isoformat(),
    }


def _conversation_title(value: str | None) -> str:
    normalized = (value or DEFAULT_CONVERSATION_TITLE).strip() or DEFAULT_CONVERSATION_TITLE
    return normalized[:80]
```

- [ ] **Step 5: Run the service tests**

Run:

```powershell
uv run pytest backend/tests/test_assistant_service.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```powershell
git add backend/app/assistant backend/tests/test_assistant_service.py
git commit -m "feat: add assistant conversation service"
```

---

### Task 3: Expose Created AgentRun Id From RAG Answers

**Files:**

- Modify: `backend/app/agents/rag_orchestrator_agent/agent.py`
- Modify: `backend/app/agents/rag_orchestrator_agent/service.py`
- Modify: `backend/app/api/v1/ask.py`
- Modify: `backend/tests/test_rag_orchestrator_service.py`

- [ ] **Step 1: Add the failing RAG service assertion**

In `backend/tests/test_rag_orchestrator_service.py`, update
`test_rag_service_persists_agent_run_metadata`:

```python
    assert answer.agent_run_id == agent_run.id
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run:

```powershell
uv run pytest backend/tests/test_rag_orchestrator_service.py::test_rag_service_persists_agent_run_metadata -v
```

Expected: FAIL because `RagAnswer` has no `agent_run_id`.

- [ ] **Step 3: Add the field to `RagAnswer`**

Modify `backend/app/agents/rag_orchestrator_agent/agent.py`:

```python
@dataclass(frozen=True)
class RagAnswer:
    agent_name: str
    prompt_version: str
    question: str
    answer: str
    source_ids: list[str]
    source_links: list[str]
    source_snippets: list[str]
    citations: list[dict[str, object]]
    permission_level: str
    hidden_match_count: int
    permission_notice: str | None
    cost: AgentRunCost
    cache_key: str
    agent_run_id: int | None = None
```

- [ ] **Step 4: Flush the created run id into the answer**

Modify `backend/app/agents/rag_orchestrator_agent/service.py` imports:

```python
from dataclasses import dataclass, field, replace
```

Replace the `db.add(AgentRun(...))` block in `answer_question_with_rag` with:

```python
    agent_run = AgentRun(
        agent_name=answer.agent_name,
        prompt_version=answer.prompt_version,
        status='complete',
        source_window=packet.source_window,
        cache_key=answer.cache_key,
        model_name=answer.cost.model_name,
        input_tokens=answer.cost.token_usage.input_tokens,
        output_tokens=answer.cost.token_usage.output_tokens,
        total_tokens=answer.cost.token_usage.total_tokens,
        estimated_cost_usd=answer.cost.estimated_cost_usd,
        permission_level=answer.permission_level,
        metadata_={
            'source_type': packet.source_type,
            'question': question,
            'source_count': len(answer.source_links),
            'hidden_match_count': hidden_match_count,
            'cache_hit': answer.cost.cache_hit,
        },
    )
    db.add(agent_run)
    db.flush()
    answer = replace(answer, agent_run_id=agent_run.id)
    db.commit()
```

- [ ] **Step 5: Include `agent_run_id` in `/ask`**

Modify `backend/app/api/v1/ask.py` response:

```python
        'agent_run_id': answer.agent_run_id,
```

- [ ] **Step 6: Run targeted tests**

Run:

```powershell
uv run pytest backend/tests/test_rag_orchestrator_agent.py backend/tests/test_rag_orchestrator_service.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```powershell
git add backend/app/agents/rag_orchestrator_agent/agent.py backend/app/agents/rag_orchestrator_agent/service.py backend/app/api/v1/ask.py backend/tests/test_rag_orchestrator_service.py
git commit -m "feat: link rag answers to agent runs"
```

---

### Task 4: Add Assistant API Routes

**Files:**

- Create: `backend/app/schemas/assistant.py`
- Create: `backend/app/api/v1/assistant.py`
- Modify: `backend/app/api/v1/router.py`
- Test: `backend/tests/test_assistant_api.py`

- [ ] **Step 1: Write failing API tests**

Create `backend/tests/test_assistant_api.py`:

```python
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models import AgentRun
from backend.tests.test_rag_orchestrator_service import seed_chunk


def test_assistant_conversation_api_is_user_scoped(client: TestClient) -> None:
    create_response = client.post(
        '/api/v1/assistant/conversations',
        json={'title': 'Viewer Redis 질문'},
        headers={'X-Demo-User': 'viewer'},
    )
    assert create_response.status_code == 200
    conversation_id = create_response.json()['conversation']['id']

    other_user_response = client.get(
        f'/api/v1/assistant/conversations/{conversation_id}/messages',
        headers={'X-Demo-User': 'employee-jun'},
    )

    assert other_user_response.status_code == 404
    assert other_user_response.json()['detail'] == 'assistant conversation not found'


def test_assistant_message_flow_stores_rag_answer_without_cost_fields(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_chunk(
        db_session,
        'gmail',
        'gmail-redis-assistant',
        'Redis should be used for transient job state while PostgreSQL stores durable records.',
        'internal',
    )
    create_response = client.post(
        '/api/v1/assistant/conversations',
        json={'title': 'Redis 질문'},
        headers={'X-Demo-User': 'viewer'},
    )
    conversation_id = create_response.json()['conversation']['id']

    turn_response = client.post(
        f'/api/v1/assistant/conversations/{conversation_id}/messages',
        json={'content': 'Redis job state'},
        headers={'X-Demo-User': 'viewer'},
    )

    assert turn_response.status_code == 200
    payload = turn_response.json()
    assert payload['user_message']['role'] == 'user'
    assert payload['assistant_message']['role'] == 'assistant'
    assert payload['assistant_message']['source_links'] == ['https://gmail.mock/gmail-redis-assistant']
    assert payload['assistant_message']['hidden_match_count'] == 0
    assert payload['assistant_message']['agent_run_id'] == db_session.query(AgentRun).one().id
    assert 'estimated_cost_usd' not in payload['assistant_message']
    assert 'token_usage' not in payload['assistant_message']
    assert 'cache_key' not in payload['assistant_message']


def test_assistant_lists_persisted_messages(client: TestClient, db_session: Session) -> None:
    seed_chunk(
        db_session,
        'drive',
        'drive-redis-assistant',
        'Redis powers short-lived orchestration state.',
        'internal',
    )
    create_response = client.post(
        '/api/v1/assistant/conversations',
        json={'title': 'Persisted conversation'},
        headers={'X-Demo-User': 'viewer'},
    )
    conversation_id = create_response.json()['conversation']['id']
    client.post(
        f'/api/v1/assistant/conversations/{conversation_id}/messages',
        json={'content': 'Redis orchestration state'},
        headers={'X-Demo-User': 'viewer'},
    )

    messages_response = client.get(
        f'/api/v1/assistant/conversations/{conversation_id}/messages',
        headers={'X-Demo-User': 'viewer'},
    )

    assert messages_response.status_code == 200
    messages = messages_response.json()['messages']
    assert [message['role'] for message in messages] == ['user', 'assistant']
```

- [ ] **Step 2: Run API tests to verify failure**

Run:

```powershell
uv run pytest backend/tests/test_assistant_api.py -v
```

Expected: FAIL because `/api/v1/assistant` is not registered.

- [ ] **Step 3: Add assistant schemas**

Create `backend/app/schemas/assistant.py`:

```python
from pydantic import BaseModel, Field


class AssistantConversationCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=160)


class AssistantMessageCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class AssistantConversationResponse(BaseModel):
    id: int
    title: str
    summary: str | None
    created_at: str
    updated_at: str


class AssistantMessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    citations: list
    source_ids: list
    source_links: list
    source_snippets: list
    permission_level: str | None
    hidden_match_count: int
    permission_notice: str | None
    agent_run_id: int | None
    metadata: dict
    created_at: str


class AssistantConversationsResponse(BaseModel):
    conversations: list[AssistantConversationResponse]


class AssistantConversationCreatedResponse(BaseModel):
    conversation: AssistantConversationResponse


class AssistantMessagesResponse(BaseModel):
    conversation: AssistantConversationResponse
    messages: list[AssistantMessageResponse]


class AssistantTurnResponse(BaseModel):
    conversation: AssistantConversationResponse
    user_message: AssistantMessageResponse
    assistant_message: AssistantMessageResponse
```

- [ ] **Step 4: Add assistant route**

Create `backend/app/api/v1/assistant.py`:

```python
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.agents.rag_orchestrator_agent import answer_question_with_rag
from backend.app.assistant.service import (
    append_assistant_message,
    append_user_message,
    build_contextual_question,
    create_conversation,
    get_owned_conversation,
    list_conversations,
    list_messages,
    serialize_conversation,
    serialize_message,
)
from backend.app.core.config import Settings, get_settings
from backend.app.core.demo_auth import DemoUser, get_demo_user
from backend.app.db.session import get_db
from backend.app.rag.search_store import build_pgvector_search_store
from backend.app.schemas.assistant import (
    AssistantConversationCreateRequest,
    AssistantConversationCreatedResponse,
    AssistantConversationsResponse,
    AssistantMessageCreateRequest,
    AssistantMessagesResponse,
    AssistantTurnResponse,
)

router = APIRouter(prefix='/assistant', tags=['assistant'])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[DemoUser, Depends(get_demo_user)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def require_conversation(db: Session, user: DemoUser, conversation_id: int):
    try:
        return get_owned_conversation(db, user, conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail='assistant conversation not found') from exc


@router.get('/conversations', response_model=AssistantConversationsResponse)
def get_assistant_conversations(db: DbSession, user: CurrentUser) -> dict:
    return {'conversations': [serialize_conversation(item) for item in list_conversations(db, user)]}


@router.post('/conversations', response_model=AssistantConversationCreatedResponse)
def create_assistant_conversation(
    request: AssistantConversationCreateRequest,
    db: DbSession,
    user: CurrentUser,
) -> dict:
    conversation = create_conversation(db, user, title=request.title)
    return {'conversation': serialize_conversation(conversation)}


@router.get('/conversations/{conversation_id}/messages', response_model=AssistantMessagesResponse)
def get_assistant_messages(conversation_id: int, db: DbSession, user: CurrentUser) -> dict:
    conversation = require_conversation(db, user, conversation_id)
    return {
        'conversation': serialize_conversation(conversation),
        'messages': [serialize_message(message) for message in list_messages(db, user, conversation_id)],
    }


@router.post('/conversations/{conversation_id}/messages', response_model=AssistantTurnResponse)
def create_assistant_message(
    conversation_id: int,
    request: AssistantMessageCreateRequest,
    db: DbSession,
    user: CurrentUser,
    settings: AppSettings,
) -> dict:
    conversation = require_conversation(db, user, conversation_id)
    user_message = append_user_message(db, conversation, request.content)
    messages = list_messages(db, user, conversation_id)
    contextual_question = build_contextual_question(
        conversation=conversation,
        messages=messages,
        new_message=request.content,
    )
    answer = answer_question_with_rag(
        db=db,
        user=user,
        question=contextual_question,
        vector_store=build_pgvector_search_store(db=db, settings=settings),
    )
    assistant_message = append_assistant_message(
        db,
        conversation,
        content=answer.answer,
        citations=answer.citations,
        source_ids=answer.source_ids,
        source_links=answer.source_links,
        source_snippets=answer.source_snippets,
        permission_level=answer.permission_level,
        hidden_match_count=answer.hidden_match_count,
        permission_notice=answer.permission_notice,
        agent_run_id=answer.agent_run_id,
        metadata={'rag_question': contextual_question},
    )
    return {
        'conversation': serialize_conversation(conversation),
        'user_message': serialize_message(user_message),
        'assistant_message': serialize_message(assistant_message),
    }
```

- [ ] **Step 5: Register the router**

Modify `backend/app/api/v1/router.py` imports:

```python
    assistant,
```

Add the router before `ask.router`:

```python
api_router.include_router(assistant.router)
```

- [ ] **Step 6: Run assistant backend tests**

Run:

```powershell
uv run pytest backend/tests/test_assistant_models.py backend/tests/test_assistant_service.py backend/tests/test_assistant_api.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```powershell
git add backend/app/schemas/assistant.py backend/app/api/v1/assistant.py backend/app/api/v1/router.py backend/tests/test_assistant_api.py
git commit -m "feat: add assistant conversation api"
```

---

### Task 5: Add Frontend Types and Refactor `/search`

**Files:**

- Modify: `frontend/src/lib/api/types.ts`
- Modify: `frontend/src/app/search/page.tsx`

- [ ] **Step 1: Add assistant API types**

Modify `frontend/src/lib/api/types.ts` after `AskResponse`:

```ts
export type AssistantConversation = {
  id: number;
  title: string;
  summary?: string | null;
  created_at: string;
  updated_at: string;
};

export type AssistantMessage = {
  id: number;
  conversation_id: number;
  role: "user" | "assistant" | string;
  content: string;
  citations: RagCitation[];
  source_ids: string[];
  source_links: string[];
  source_snippets: string[];
  permission_level?: string | null;
  hidden_match_count: number;
  permission_notice?: string | null;
  agent_run_id?: number | null;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AssistantConversationsResponse = {
  conversations: AssistantConversation[];
};

export type AssistantConversationCreatedResponse = {
  conversation: AssistantConversation;
};

export type AssistantMessagesResponse = {
  conversation: AssistantConversation;
  messages: AssistantMessage[];
};

export type AssistantTurnResponse = {
  conversation: AssistantConversation;
  user_message: AssistantMessage;
  assistant_message: AssistantMessage;
};
```

- [ ] **Step 2: Refactor `/search` imports**

Modify the import from `@/lib/api/types` in `frontend/src/app/search/page.tsx`:

```ts
import type {
  AssistantConversation,
  AssistantConversationCreatedResponse,
  AssistantConversationsResponse,
  AssistantMessage,
  AssistantMessagesResponse,
  AssistantTurnResponse,
  RagCitation,
  RagIndexingJobSummary,
  RagIndexingSummaryResponse,
} from "@/lib/api/types";
```

Remove unused imports for `AskResponse`, `SearchResponse`, and `CircleDollarSign`.

- [ ] **Step 3: Replace one-shot search state with conversation state**

Inside `SearchPageContent`, replace the existing response state with:

```ts
  const [conversations, setConversations] = useState<AssistantConversation[]>([]);
  const [activeConversation, setActiveConversation] = useState<AssistantConversation>();
  const [messages, setMessages] = useState<AssistantMessage[]>([]);
  const [selectedEvidenceMessageId, setSelectedEvidenceMessageId] = useState<number>();
  const [query, setQuery] = useState(initialQuery);
  const [ragIndexing, setRagIndexing] = useState<RagIndexingSummaryResponse>();
  const [loading, setLoading] = useState(false);
  const [booting, setBooting] = useState(true);
  const [error, setError] = useState<string>();
  const [initialQuerySent, setInitialQuerySent] = useState(false);
```

- [ ] **Step 4: Add conversation loader helpers**

Add these helpers inside `SearchPageContent`:

```ts
  const loadMessages = useCallback(async (conversation: AssistantConversation) => {
    const result = await apiGet<AssistantMessagesResponse>(`/api/v1/assistant/conversations/${conversation.id}/messages`);
    setActiveConversation(result.conversation);
    setMessages(result.messages);
    setSelectedEvidenceMessageId(result.messages.findLast((message) => message.role === "assistant")?.id);
  }, []);

  const createConversation = useCallback(async (title?: string) => {
    const result = await apiPost<AssistantConversationCreatedResponse>("/api/v1/assistant/conversations", {
      title: title || "새 대화",
    });
    setConversations((current) => [result.conversation, ...current]);
    await loadMessages(result.conversation);
    return result.conversation;
  }, [loadMessages]);

  const loadConversations = useCallback(async () => {
    setBooting(true);
    setError(undefined);
    try {
      const result = await apiGet<AssistantConversationsResponse>("/api/v1/assistant/conversations");
      setConversations(result.conversations);
      if (result.conversations[0]) {
        await loadMessages(result.conversations[0]);
      } else {
        await createConversation(initialQuery || "새 대화");
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "AI 비서 대화를 불러오지 못했습니다.");
    } finally {
      setBooting(false);
    }
  }, [createConversation, initialQuery, loadMessages]);
```

- [ ] **Step 5: Add persisted send behavior**

Add:

```ts
  const sendMessage = useCallback(async (content: string) => {
    const trimmed = content.trim();
    if (!trimmed) return;

    let conversation = activeConversation;
    if (!conversation) {
      conversation = await createConversation(trimmed);
    }

    setLoading(true);
    setError(undefined);
    try {
      const result = await apiPost<AssistantTurnResponse>(
        `/api/v1/assistant/conversations/${conversation.id}/messages`,
        { content: trimmed },
      );
      setActiveConversation(result.conversation);
      setMessages((current) => [...current, result.user_message, result.assistant_message]);
      setConversations((current) => [
        result.conversation,
        ...current.filter((item) => item.id !== result.conversation.id),
      ]);
      setSelectedEvidenceMessageId(result.assistant_message.id);
      setQuery("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "AI 비서가 답변을 생성하지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, [activeConversation, createConversation]);
```

Update submit:

```ts
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void sendMessage(query);
  }
```

- [ ] **Step 6: Wire effects**

Replace the current initial query effect with:

```ts
  useEffect(() => {
    void loadConversations();
  }, [loadConversations]);

  useEffect(() => {
    if (initialQuerySent || booting || !initialQuery.trim()) return;
    setInitialQuerySent(true);
    void sendMessage(initialQuery);
  }, [booting, initialQuery, initialQuerySent, sendMessage]);
```

Keep the existing RAG freshness fetch, but do not render cost-policy details in `/search`.

- [ ] **Step 7: Replace the page body with conversation UI**

Use this structure in the returned JSX:

```tsx
      <section className="grid gap-4 xl:grid-cols-[280px_minmax(0,1fr)_360px]">
        <aside className="panel reference-panel h-fit">
          <div className="flex items-center justify-between gap-2 border-b border-line pb-3">
            <h2 className="text-[14px] font-extrabold">대화</h2>
            <button type="button" className="icon-button" onClick={() => void createConversation("새 대화")} title="새 대화">
              <Plus className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
          <div className="mt-3 space-y-2">
            {conversations.map((conversation) => (
              <button
                key={conversation.id}
                type="button"
                onClick={() => void loadMessages(conversation)}
                className={`w-full rounded-lg border px-3 py-2 text-left text-[13px] ${
                  activeConversation?.id === conversation.id
                    ? "border-[var(--primary)] bg-[var(--glass-strong)]"
                    : "border-line bg-[var(--glass-elevated)] hover:bg-[var(--glass-strong)]"
                }`}
              >
                <span className="block truncate font-bold">{conversation.title}</span>
                <span className="mt-1 block text-[11px] text-muted">{formatDateTime(conversation.updated_at)}</span>
              </button>
            ))}
          </div>
        </aside>

        <article className="panel reference-panel min-h-[560px]">
          <div className="flex items-center gap-2 border-b border-line pb-4">
            <Bot className="h-4 w-4 text-[var(--primary)]" aria-hidden="true" />
            <h2 className="text-[15px] font-extrabold">AI 비서와 대화</h2>
          </div>

          <div className="flex min-h-[390px] flex-col gap-3 py-4">
            {booting ? (
              <div className="rounded-lg border border-dashed border-line bg-surface-soft p-8 text-[13px] text-muted">
                대화를 불러오고 있습니다.
              </div>
            ) : messages.length === 0 ? (
              <div className="rounded-lg border border-dashed border-line bg-surface-soft p-8 text-[13px] text-muted">
                질문을 입력하면 AI 비서가 회사 지식과 접근 가능한 근거를 바탕으로 답변합니다.
              </div>
            ) : (
              messages.map((message) => (
                <AssistantBubble
                  key={message.id}
                  message={message}
                  selected={selectedEvidenceMessageId === message.id}
                  onSelectEvidence={() => setSelectedEvidenceMessageId(message.id)}
                />
              ))
            )}
          </div>

          <form onSubmit={submit} className="border-t border-line pt-4">
            <label htmlFor="query" className="sr-only">AI 비서에게 질문</label>
            <div className="flex flex-col gap-2 sm:flex-row">
              <input
                id="query"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                className="h-11 min-w-0 flex-1 rounded-lg border border-line bg-[var(--glass-elevated)] px-3 text-[13px] outline-none focus:border-[var(--primary)]"
                aria-label="예: Redis 작업 상태는 어떻게 관리되고 있나요?"
              />
              <button type="submit" disabled={loading || booting} className="row-action gap-2 px-4 disabled:bg-neutral-300">
                <Send className="h-4 w-4" aria-hidden="true" />
                {loading ? "답변 생성 중" : "보내기"}
              </button>
            </div>
          </form>
        </article>

        <EvidencePanel message={selectedEvidenceMessage} />
      </section>
```

Before the return, compute:

```ts
  const selectedEvidenceMessage = messages.find((message) => message.id === selectedEvidenceMessageId);
```

- [ ] **Step 8: Add focused presentational components in the same file**

Add below `SearchPageFallback`:

```tsx
function AssistantBubble({
  message,
  selected,
  onSelectEvidence,
}: {
  message: AssistantMessage;
  selected: boolean;
  onSelectEvidence: () => void;
}) {
  const isAssistant = message.role === "assistant";
  return (
    <div className={`flex ${isAssistant ? "justify-start" : "justify-end"}`}>
      <div
        className={`max-w-[840px] rounded-lg border px-4 py-3 text-[14px] leading-6 ${
          isAssistant
            ? "border-line bg-[var(--glass-elevated)]"
            : "border-[var(--primary)] bg-[var(--primary)] text-white"
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        {isAssistant ? (
          <div className="mt-3 flex flex-wrap items-center gap-2 text-[12px]">
            <span className="badge green">{message.permission_level || "permission"}</span>
            <span className="badge blue">근거 {message.source_links.length.toLocaleString()}개</span>
            {message.hidden_match_count > 0 ? (
              <span className="badge amber">숨겨진 근거 {message.hidden_match_count.toLocaleString()}개</span>
            ) : null}
            <button
              type="button"
              onClick={onSelectEvidence}
              className={`filter-pill ${selected ? "active" : ""}`}
            >
              근거 보기
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function EvidencePanel({ message }: { message?: AssistantMessage }) {
  if (!message || message.role !== "assistant") {
    return (
      <aside className="panel reference-panel h-fit">
        <h2 className="text-[15px] font-extrabold">근거</h2>
        <p className="mt-3 text-[13px] text-muted">AI 답변을 선택하면 접근 가능한 근거가 표시됩니다.</p>
      </aside>
    );
  }

  return (
    <aside className="panel reference-panel h-fit">
      <div className="flex items-center gap-2 border-b border-line pb-3">
        <Link2 className="h-4 w-4 text-[var(--primary)]" aria-hidden="true" />
        <h2 className="text-[15px] font-extrabold">답변 근거</h2>
      </div>
      {message.permission_notice ? (
        <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-[12px] text-amber-900">
          {message.permission_notice}
        </div>
      ) : null}
      <div className="mt-3 space-y-2">
        {message.citations.map((citation: RagCitation, index: number) => (
          <a
            key={`${citation.source_id}-${index}`}
            href={citation.source_url}
            target="_blank"
            rel="noreferrer"
            className="block rounded-lg border border-line bg-[var(--glass-elevated)] p-3 text-[13px] hover:bg-[var(--glass-strong)]"
          >
            <span className="font-bold text-[var(--primary-dark)]">근거 {index + 1}</span>
            <span className="mt-1 block text-[12px] text-muted">{citation.source_id}</span>
            <span className="mt-1 block text-[12px] text-muted">{citation.permission_level}</span>
            <span className="mt-2 block text-[12px] leading-5">{citation.source_snippet}</span>
          </a>
        ))}
        {message.citations.length === 0 ? (
          <div className="rounded-lg border border-dashed border-line bg-surface-soft p-4 text-[13px] text-muted">
            현재 권한으로 확인 가능한 근거가 없습니다.
          </div>
        ) : null}
      </div>
    </aside>
  );
}
```

- [ ] **Step 9: Remove cost display from `/search` freshness panel**

In `MemoryFreshnessPanel`, remove:

- the `costPolicy` constant;
- the whole JSX block that renders model, budget, and hash-skip details;
- the `CircleDollarSign` import.

Keep indexed count and freshness status visible.

- [ ] **Step 10: Run frontend checks**

Run:

```powershell
Set-Location frontend
npm.cmd run build
```

Expected: PASS.

- [ ] **Step 11: Commit**

Run:

```powershell
git add frontend/src/lib/api/types.ts frontend/src/app/search/page.tsx
git commit -m "feat: persist assistant conversations in search"
```

---

### Task 6: Add `/search` Playwright Coverage

**Files:**

- Create: `frontend/e2e/assistant-memory.spec.ts`

- [ ] **Step 1: Add a Playwright test with mocked assistant APIs**

Create `frontend/e2e/assistant-memory.spec.ts`:

```ts
import { expect, test } from "@playwright/test";

test("search page behaves as a persisted AI assistant without cost labels", async ({ page }) => {
  const conversations = [
    {
      id: 10,
      title: "Redis 질문",
      summary: "Redis 작업 상태 대화",
      created_at: "2026-05-12T01:00:00+00:00",
      updated_at: "2026-05-12T01:00:00+00:00",
    },
  ];
  const messages = [
    {
      id: 100,
      conversation_id: 10,
      role: "assistant",
      content: "Redis는 일시적인 작업 상태 공유에 사용됩니다.",
      citations: [
        {
          source_id: "gmail-redis",
          source_url: "https://gmail.mock/redis",
          source_type: "gmail",
          permission_level: "internal",
          source_snippet: "Redis 작업 상태 근거",
          relevance_score: 1,
          matched_terms: ["redis"],
        },
      ],
      source_ids: ["gmail-redis"],
      source_links: ["https://gmail.mock/redis"],
      source_snippets: ["Redis 작업 상태 근거"],
      permission_level: "internal",
      hidden_match_count: 0,
      permission_notice: null,
      agent_run_id: 77,
      metadata: {},
      created_at: "2026-05-12T01:00:00+00:00",
    },
  ];

  await page.route("**/api/v1/assistant/conversations", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ contentType: "application/json", json: { conversations } });
      return;
    }
    await route.fulfill({ contentType: "application/json", json: { conversation: conversations[0] } });
  });

  await page.route("**/api/v1/assistant/conversations/10/messages", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        contentType: "application/json",
        json: { conversation: conversations[0], messages },
      });
      return;
    }
    await route.fulfill({
      contentType: "application/json",
      json: {
        conversation: conversations[0],
        user_message: {
          id: 101,
          conversation_id: 10,
          role: "user",
          content: "그 다음 할 일은?",
          citations: [],
          source_ids: [],
          source_links: [],
          source_snippets: [],
          permission_level: null,
          hidden_match_count: 0,
          permission_notice: null,
          agent_run_id: null,
          metadata: {},
          created_at: "2026-05-12T01:01:00+00:00",
        },
        assistant_message: {
          ...messages[0],
          id: 102,
          content: "다음 단계는 회의 전 Redis 작업 상태를 공유하는 것입니다.",
        },
      },
    });
  });

  await page.route("**/api/v1/rag/indexing/summary", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        state_counts: { indexed: 1 },
        latest_jobs: [
          {
            job_id: "job-1",
            connector_type: "rag",
            status: "complete",
            message: "indexed",
            progress_pct: 100,
            indexed_count: 1,
            skipped_count: 0,
            saved_embedding_calls: 0,
            updated_at: "2026-05-12T01:00:00+00:00",
          },
        ],
        cost_policy: {
          embedding_model: "text-embedding-3-small",
          embedding_input_cost_per_1m_tokens: 0.02,
          max_estimated_embedding_cost_usd: 0.001,
          preflight_budget_gate: true,
          incremental_hash_skip: true,
        },
      },
    });
  });

  await page.goto("/search");

  await expect(page.getByRole("heading", { name: "AI 비서와 대화" })).toBeVisible();
  await expect(page.getByText("Redis는 일시적인 작업 상태 공유에 사용됩니다.")).toBeVisible();
  await page.getByRole("button", { name: "근거 보기" }).click();
  await expect(page.getByText("Redis 작업 상태 근거")).toBeVisible();

  await page.getByLabel("AI 비서에게 질문").fill("그 다음 할 일은?");
  await page.getByRole("button", { name: "보내기" }).click();
  await expect(page.getByText("다음 단계는 회의 전 Redis 작업 상태를 공유하는 것입니다.")).toBeVisible();

  await expect(page.locator("body")).not.toContainText("token");
  await expect(page.locator("body")).not.toContainText("cache");
  await expect(page.locator("body")).not.toContainText("$");
});
```

- [ ] **Step 2: Run the Playwright test**

Start the app in the normal local mode, then run:

```powershell
Set-Location frontend
npm.cmd run test:visual -- assistant-memory.spec.ts --project=chromium-desktop
```

Expected: PASS.

- [ ] **Step 3: Run search route regression**

Run:

```powershell
Set-Location frontend
npm.cmd run test:visual -- page-regression.spec.ts --grep "search" --project=chromium-desktop
```

Expected: PASS.

- [ ] **Step 4: Commit**

Run:

```powershell
git add frontend/e2e/assistant-memory.spec.ts
git commit -m "test: cover assistant memory search page"
```

---

### Task 7: Final Verification and Portfolio Note

**Files:**

- Modify: `docs/portfolio-log.md`

- [ ] **Step 1: Run backend assistant and RAG tests**

Run:

```powershell
uv run pytest backend/tests/test_assistant_models.py backend/tests/test_assistant_service.py backend/tests/test_assistant_api.py backend/tests/test_rag_orchestrator_agent.py backend/tests/test_rag_orchestrator_service.py -v
```

Expected: PASS.

- [ ] **Step 2: Run full backend tests if time permits**

Run:

```powershell
uv run pytest backend/tests -v
```

Expected: PASS.

- [ ] **Step 3: Run frontend build**

Run:

```powershell
Set-Location frontend
npm.cmd run build
```

Expected: PASS.

- [ ] **Step 4: Run focused Playwright checks**

Run:

```powershell
Set-Location frontend
npm.cmd run test:visual -- assistant-memory.spec.ts page-regression.spec.ts --grep "search|persisted AI assistant" --project=chromium-desktop
```

Expected: PASS.

- [ ] **Step 5: Add a portfolio log entry**

Add this entry near the top of `docs/portfolio-log.md`:

```markdown
## 2026-05-12 AI Assistant Conversation Memory

- Added database-backed, per-user AI assistant conversations for the `AI 비서`
  surface.
- Persisted user and assistant messages with citations, source snippets,
  permission notices, hidden-source counts, and linked AgentRun ids.
- Kept token, cache, and cost details out of the user-facing assistant flow so
  cost observability remains in `Agent Runs`.
- Added regression coverage for user-scoped assistant conversations and the
  `/search` assistant UX.

Portfolio angle:

- Shows ParaWorks evolving from one-shot RAG search into a product-like
  evidence-backed AI assistant with memory, permission safety, and operator
  observability.
```

- [ ] **Step 6: Run status and confirm scope**

Run:

```powershell
git status --short
```

Expected: only files from this assistant-memory plan are modified or staged.
`frontend/next-env.d.ts` may remain modified from outside this task and must not
be staged unless the user explicitly asks.

- [ ] **Step 7: Commit**

Run:

```powershell
git add docs/portfolio-log.md
git commit -m "docs: log assistant memory milestone"
```

---

## Final Acceptance Criteria

- `/search` stores conversations and messages per logged-in user.
- A user cannot read or write another user's assistant conversation.
- Assistant answers preserve citations, source snippets, permission level,
  hidden-source count, and linked `AgentRun` id.
- `/search` does not display token usage, estimated cost, cache keys, or model
  pricing.
- `/agent-runs` remains the cost and model observability surface.
- Only `/search` is changed on the frontend.
- New code comments, if present, are Korean.
- The unrelated `frontend/next-env.d.ts` modification is not included in these
  commits.
