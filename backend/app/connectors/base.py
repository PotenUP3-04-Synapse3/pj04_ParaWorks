from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class SourceEvent:
    source_type: str
    source_id: str
    source_url: str
    title: str
    body: str
    author: str | None
    participants: list[str]
    timestamp: datetime
    permission_level: str
    raw_metadata: dict = field(default_factory=dict)


class Connector(Protocol):
    source_type: str

    def fetch_events(self) -> list[SourceEvent]:
        raise NotImplementedError
