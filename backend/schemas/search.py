from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── 검색 요청 ──────────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description='자연어 질문')
    organization_id: str
    # 선택적 필터
    department_id: str | None = None
    business_domain: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    top_k: int = Field(default=8, ge=1, le=50)


# ── 검색 결과 구조 (에이전트 structured output 기준) ─────────────────────────────

class SourceSnippet(BaseModel):
    source_url: str | None = None
    source_type: str | None = None   # "gmail"|"slack"|"drive"|"calendar"
    snippet: str
    document_version: str | None = None
    page_number: int | None = None
    paragraph_index: int | None = None


class TimelineEvent(BaseModel):
    event_type: str
    title: str
    occurred_at: datetime | None = None
    actor: str | None = None
    source_url: str | None = None


class DecisionSummary(BaseModel):
    id: str
    title: str
    decision_summary: str
    decision_maker: str | None = None
    decided_at: datetime | None = None
    confidence_score: float | None = None
    source_url: str | None = None


class SearchResponse(BaseModel):
    """에이전트 structured output — 8개 필드 전체 반환 필수."""
    answer: str = Field(..., description='사용자 질문에 대한 종합 답변')
    related_timeline: list[TimelineEvent] = Field(default_factory=list)
    related_history: list[str] = Field(default_factory=list, description='관련 히스토리 요약 목록')
    related_decision_records: list[DecisionSummary] = Field(default_factory=list)
    source_links: list[str] = Field(default_factory=list)
    source_snippets: list[SourceSnippet] = Field(default_factory=list)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    missing_evidence: list[str] = Field(default_factory=list, description='근거 부족한 부분 목록')
    permission_notice: str | None = Field(default=None, description='접근 권한 제한 안내')
