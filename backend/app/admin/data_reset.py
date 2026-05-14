from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.models import (
    AgentRun,
    AssistantConversation,
    AssistantMessage,
    DecisionRecord,
    Document,
    DocumentChunk,
    DocumentParserRun,
    DocumentVersion,
    HistoryEvent,
    ReviewItem,
    Source,
    SyncJob,
    TimelineEvent,
    Todo,
    VectorIndexState,
)

RESET_MODELS = (
    AssistantMessage,
    AssistantConversation,
    AgentRun,
    VectorIndexState,
    ReviewItem,
    DecisionRecord,
    HistoryEvent,
    TimelineEvent,
    Todo,
    DocumentParserRun,
    DocumentChunk,
    DocumentVersion,
    Document,
    Source,
    SyncJob,
)


@dataclass(frozen=True)
class DataResetResult:
    dry_run: bool
    deleted_counts: dict[str, int]
    preserved_tables: tuple[str, ...]


def reset_connector_derived_data(
    db: Session,
    *,
    settings: Settings,
    dry_run: bool = True,
    confirm: bool = False,
) -> DataResetResult:
    counts = {model.__tablename__: db.query(model).count() for model in RESET_MODELS}
    if dry_run:
        return _result(dry_run=True, counts=counts)
    if settings.paraworks_env != 'local':
        raise ValueError('connector data reset is only allowed in local environment')
    if not confirm:
        raise ValueError('connector data reset requires confirm=True')

    for model in RESET_MODELS:
        db.query(model).delete(synchronize_session=False)
    db.commit()
    return _result(dry_run=False, counts=counts)


def _result(*, dry_run: bool, counts: dict[str, int]) -> DataResetResult:
    return DataResetResult(
        dry_run=dry_run,
        deleted_counts=counts,
        preserved_tables=('auth_users', 'refresh_tokens', 'integration_connections', 'message_channels', 'messages'),
    )
