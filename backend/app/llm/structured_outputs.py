"""LLM structured output schemas — all agent outputs are validated against these."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ── Shared base ────────────────────────────────────────────────────────────


class SourceSnippetOut(BaseModel):
    text: str
    source_url: str


class AgentOutputBase(BaseModel):
    """Fields required on every LLM output."""
    source_links: List[str] = Field(default_factory=list)
    source_snippets: List[SourceSnippetOut] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0)
    missing_evidence: List[str] = Field(default_factory=list)
    needs_human_review: bool = False


# ── Todo Extraction ────────────────────────────────────────────────────────


class TodoItem(BaseModel):
    title: str
    assignee: Optional[str] = None
    due_date: Optional[str] = None   # ISO8601 date string
    priority: Literal['critical', 'high', 'medium', 'low'] = 'medium'
    priority_reason: str
    blocker: bool = False
    needs_approval: bool = False


class TodoExtractionResult(AgentOutputBase):
    todos: List[TodoItem] = Field(default_factory=list)


# ── Timeline Extraction ────────────────────────────────────────────────────


class TimelineItem(BaseModel):
    title: str
    result_summary: str
    event_time: Optional[str] = None   # ISO8601 datetime string


class TimelineExtractionResult(AgentOutputBase):
    events: List[TimelineItem] = Field(default_factory=list)


# ── History Extraction ─────────────────────────────────────────────────────


class HistoryItem(BaseModel):
    title: str
    situation: str
    reason: str
    process: str
    constraints: str
    decision: str
    decision_maker: str
    participants: List[str] = Field(default_factory=list)
    event_time: Optional[str] = None   # ISO8601 datetime string


class HistoryExtractionResult(AgentOutputBase):
    events: List[HistoryItem] = Field(default_factory=list)


# ── Project Mapping ────────────────────────────────────────────────────────


class NewProjectCandidate(BaseModel):
    name: str
    description: str
    participants: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)


class ProjectMappingResult(AgentOutputBase):
    matched_project_id: Optional[str] = None    # UUID str if matched
    match_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    new_project_candidate: Optional[NewProjectCandidate] = None


# ── Priority Decision ──────────────────────────────────────────────────────


class PriorityFactors(BaseModel):
    deadline_urgency: int = Field(ge=0, le=10, default=0)
    customer_impact: int = Field(ge=0, le=10, default=0)
    decision_maker_needed: bool = False
    is_blocker: bool = False
    needs_consensus: bool = False
    external_collaboration: bool = False
    c_level_report: bool = False
    project_risk: int = Field(ge=0, le=10, default=0)


class PriorityDecisionResult(AgentOutputBase):
    priority: Literal['critical', 'high', 'medium', 'low']
    priority_score: int = Field(ge=0, le=100)
    reason: str
    factors: PriorityFactors


# ── Validation ─────────────────────────────────────────────────────────────


class ValidationResult(BaseModel):
    is_valid: bool
    faithfulness_score: float = Field(ge=0.0, le=1.0)
    hallucination_detected: bool
    source_validation_passed: bool
    missing_sources: List[str] = Field(default_factory=list)
    issues: List[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0)
    recommendation: Literal['approve', 'reject', 'needs_review']
