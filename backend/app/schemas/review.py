from typing import Any

from pydantic import BaseModel


class ReviewItemUpdate(BaseModel):
    payload: dict[str, Any] | None = None
    source_links: list[str] | None = None
    source_snippets: list[str] | None = None
    confidence_score: float | None = None
    permission_level: str | None = None


class ReviewEvidenceRequest(BaseModel):
    note: str | None = None
