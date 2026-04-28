from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class RawDocument:
    """커넥터가 반환하는 원시 문서 컨테이너."""
    source_type: str              # "google_drive" | "gmail" | "slack" | "calendar"
    source_id: str                # 원본 시스템 고유 ID
    source_url: str | None
    title: str | None
    raw_content: bytes | str      # 바이너리 or 텍스트
    mime_type: str | None
    metadata: dict[str, Any] = field(default_factory=dict)
    permissions: list[dict] = field(default_factory=list)  # [{email, role}]
    version_label: str | None = None
    modified_at: datetime | None = None


class BaseConnector(ABC):
    """모든 데이터 소스 커넥터의 추상 기반 클래스."""

    @abstractmethod
    async def authenticate(self) -> None:
        """인증/토큰 갱신."""

    @abstractmethod
    async def fetch_recent(self, since: datetime | None = None) -> list[RawDocument]:
        """최근 변경된 문서/메시지 수집."""

    @abstractmethod
    async def fetch_permissions(self, source_id: str) -> list[dict]:
        """원본 권한 조회 → [{email, role}]."""
