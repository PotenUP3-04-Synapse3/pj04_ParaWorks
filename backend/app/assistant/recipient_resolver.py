from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.demo_auth import USERS
from backend.app.models import AuthUser, Source

EMAIL_PATTERN = re.compile(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}')
CONTACT_PAIR_PATTERN = re.compile(
    r'(?P<name>[가-힣A-Za-z0-9 ._·:\-]{1,80})[\s(<（]+(?P<email>[\w.+-]+@[\w.-]+\.[A-Za-z]{2,})[>)）]?',
)
HONORIFIC_SUFFIXES = ('선생님', '대표님', '님', '씨')
GROUP_HINTS = ('전체', '팀', '부서', '그룹')
RESOLVE_THRESHOLD = 0.72


@dataclass
class RecipientCandidate:
    email: str
    display_name: str = ''
    title: str = ''
    department: str = ''
    source_type: str = ''
    confidence_score: float = 0.0
    aliases: set[str] = field(default_factory=set)
    evidence: list[str] = field(default_factory=list)

    def to_prompt_dict(self) -> dict[str, object]:
        return {
            'email': self.email,
            'display_name': self.display_name,
            'title': self.title,
            'department': self.department,
            'source_type': self.source_type,
            'confidence_score': round(self.confidence_score, 3),
        }


@dataclass(frozen=True)
class RecipientResolution:
    status: str
    candidates: list[RecipientCandidate]
    reason: str = ''

    @property
    def resolved_recipients(self) -> list[dict[str, object]]:
        if self.status != 'resolved':
            return []
        return [candidate.to_prompt_dict() for candidate in self.candidates]


def resolve_email_recipients(
    *,
    db: Session,
    latest_message: str,
    conversation_context: str,
) -> RecipientResolution:
    candidates = _collect_candidates(db=db, conversation_context=conversation_context)
    direct_emails = _email_addresses(latest_message)
    if direct_emails:
        return RecipientResolution(
            status='resolved',
            candidates=[
                _candidate(
                    email=email,
                    display_name=email,
                    source_type='latest_message',
                    confidence=1.0,
                    evidence='latest_message.email',
                )
                for email in direct_emails
            ],
            reason='direct_email',
        )

    group_candidates = _resolve_group_candidates(candidates, latest_message)
    if group_candidates:
        return RecipientResolution(status='resolved', candidates=group_candidates, reason='department_group')

    scored = _score_candidates(candidates, latest_message)
    if not scored:
        return RecipientResolution(status='not_found', candidates=[], reason='no_matching_contact')

    top_score = scored[0].confidence_score
    top_candidates = [
        candidate for candidate in scored
        if candidate.confidence_score >= RESOLVE_THRESHOLD and abs(candidate.confidence_score - top_score) < 0.001
    ]
    if len(top_candidates) == 1:
        return RecipientResolution(status='resolved', candidates=top_candidates, reason='single_match')
    if len(top_candidates) > 1:
        return RecipientResolution(status='ambiguous', candidates=top_candidates, reason='multiple_equal_matches')
    return RecipientResolution(status='not_found', candidates=scored[:3], reason='below_confidence_threshold')


def _collect_candidates(*, db: Session, conversation_context: str) -> list[RecipientCandidate]:
    candidates: dict[str, RecipientCandidate] = {}
    for candidate in _conversation_candidates(conversation_context):
        _merge_candidate(candidates, candidate)
    for candidate in _auth_user_candidates(db):
        _merge_candidate(candidates, candidate)
    for candidate in _demo_user_candidates():
        _merge_candidate(candidates, candidate)
    for candidate in _source_candidates(db):
        _merge_candidate(candidates, candidate)
    return list(candidates.values())


def _conversation_candidates(conversation_context: str) -> list[RecipientCandidate]:
    return [
        _candidate(
            email=email,
            display_name=name,
            source_type='conversation',
            confidence=1.0,
            evidence='conversation.contact_pair',
        )
        for name, email in _contact_pairs(conversation_context)
    ]


def _auth_user_candidates(db: Session) -> list[RecipientCandidate]:
    users = db.scalars(select(AuthUser).where(AuthUser.status == 'active')).all()
    return [
        _candidate(
            email=user.email,
            display_name=user.display_name,
            title=user.title,
            department=user.department,
            source_type='auth_user',
            confidence=0.9,
            evidence='auth_user',
        )
        for user in users
    ]


def _demo_user_candidates() -> list[RecipientCandidate]:
    return [
        _candidate(
            email=user.email,
            display_name=user.name,
            title=user.title,
            department=user.department,
            source_type='demo_auth',
            confidence=0.78,
            evidence='demo_auth',
            extra_aliases=set(user.aliases),
        )
        for user in USERS.values()
    ]


def _source_candidates(db: Session) -> list[RecipientCandidate]:
    rows = db.scalars(
        select(Source)
        .where(Source.source_type.in_(('gmail', 'gmail_attachment', 'drive', 'calendar')))
        .order_by(Source.created_at.desc(), Source.id.desc())
        .limit(500)
    ).all()
    candidates: list[RecipientCandidate] = []
    for source in rows:
        for text in _source_contact_texts(source):
            for name, email in _contact_pairs(text):
                candidates.append(
                    _candidate(
                        email=email,
                        display_name=name,
                        source_type='source',
                        confidence=0.78,
                        evidence=f'source:{source.source_id}',
                    )
                )
            for email in _email_addresses(text):
                candidates.append(
                    _candidate(
                        email=email,
                        display_name=email,
                        source_type='source',
                        confidence=0.62,
                        evidence=f'source:{source.source_id}',
                    )
                )
    return candidates


def _source_contact_texts(source: Source) -> list[str]:
    metadata = source.raw_metadata or {}
    values = [
        source.author or '',
        source.title,
        str(metadata.get('author_name') or ''),
        str(metadata.get('owner_name') or ''),
        str(metadata.get('owner_email') or ''),
        str(metadata.get('last_modifying_user_email') or ''),
        str(metadata.get('organizer_email') or ''),
        str(metadata.get('creator_email') or ''),
    ]
    for key in ('participants', 'attendees', 'to', 'cc', 'from'):
        values.extend(_string_values(metadata.get(key)))
    return [value for value in values if value]


def _resolve_group_candidates(candidates: list[RecipientCandidate], latest_message: str) -> list[RecipientCandidate]:
    normalized_message = _normalize(latest_message)
    if not any(_normalize(hint) in normalized_message for hint in GROUP_HINTS):
        return []

    by_department: dict[str, list[RecipientCandidate]] = {}
    for candidate in candidates:
        department_key = _normalize(candidate.department)
        if not department_key:
            continue
        if department_key in normalized_message:
            by_department.setdefault(department_key, []).append(candidate)

    if not by_department:
        return []
    selected = max(by_department.values(), key=len)
    return _dedupe_candidates(selected)


def _score_candidates(candidates: list[RecipientCandidate], latest_message: str) -> list[RecipientCandidate]:
    normalized_message = _normalize(latest_message)
    scored: list[RecipientCandidate] = []
    for candidate in candidates:
        score = candidate.confidence_score
        aliases = {alias for alias in candidate.aliases if len(_normalize(alias)) >= 2}
        alias_matched = any(_normalize(alias) and _normalize(alias) in normalized_message for alias in aliases)
        title_matched = bool(candidate.title and _normalize(candidate.title) in normalized_message)
        if alias_matched:
            score += 0.2
        if title_matched:
            score += 0.08
        if (alias_matched or title_matched) and score >= RESOLVE_THRESHOLD:
            candidate.confidence_score = min(score, 1.0)
            scored.append(candidate)
    return sorted(scored, key=lambda item: (-item.confidence_score, item.email))


def _candidate(
    *,
    email: str,
    display_name: str,
    source_type: str,
    confidence: float,
    evidence: str,
    title: str = '',
    department: str = '',
    extra_aliases: set[str] | None = None,
) -> RecipientCandidate:
    normalized_email = email.strip().lower()
    name = _clean_name(display_name)
    aliases = {
        name,
        normalized_email,
        normalized_email.split('@', 1)[0],
        title,
        department,
    }
    if extra_aliases:
        aliases.update(extra_aliases)
    return RecipientCandidate(
        email=normalized_email,
        display_name=name or normalized_email,
        title=title.strip(),
        department=department.strip(),
        source_type=source_type,
        confidence_score=confidence,
        aliases={alias for alias in aliases if alias},
        evidence=[evidence],
    )


def _merge_candidate(candidates: dict[str, RecipientCandidate], incoming: RecipientCandidate) -> None:
    existing = candidates.get(incoming.email)
    if existing is None:
        candidates[incoming.email] = incoming
        return

    if not existing.display_name or existing.display_name == existing.email:
        existing.display_name = incoming.display_name
    if not existing.title:
        existing.title = incoming.title
    if not existing.department:
        existing.department = incoming.department
    if existing.source_type != incoming.source_type:
        existing.source_type = _preferred_source_type(existing.source_type, incoming.source_type)
    existing.confidence_score = max(existing.confidence_score, incoming.confidence_score)
    existing.aliases.update(incoming.aliases)
    existing.evidence.extend(item for item in incoming.evidence if item not in existing.evidence)


def _preferred_source_type(left: str, right: str) -> str:
    order = ['conversation', 'auth_user', 'demo_auth', 'source', 'latest_message']
    return min((left, right), key=lambda value: order.index(value) if value in order else len(order))


def _dedupe_candidates(candidates: list[RecipientCandidate]) -> list[RecipientCandidate]:
    seen: set[str] = set()
    deduped: list[RecipientCandidate] = []
    for candidate in sorted(candidates, key=lambda item: item.email):
        if candidate.email in seen:
            continue
        seen.add(candidate.email)
        deduped.append(candidate)
    return deduped


def _contact_pairs(text: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for match in CONTACT_PAIR_PATTERN.finditer(text):
        email = match.group('email').lower()
        name = _clean_name(match.group('name'))
        if name:
            pairs.append((name, email))
    return pairs


def _email_addresses(value: str) -> list[str]:
    return [match.group(0).lower() for match in EMAIL_PATTERN.finditer(value or '')]


def _string_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list | tuple | set):
        return [str(item) for item in value if item]
    return [str(value)]


def _clean_name(value: str) -> str:
    name = str(value or '').strip()
    if not name:
        return ''
    name = re.split(r'[\n,;]', name)[-1].strip()
    if ':' in name:
        name = name.rsplit(':', 1)[-1].strip()
    name = name.strip(' "<>()[]{}')
    for suffix in HONORIFIC_SUFFIXES:
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    return name.strip()


def _normalize(value: str) -> str:
    cleaned = _clean_name(value).lower()
    return re.sub(r'[^0-9a-z가-힣@]+', '', cleaned)
