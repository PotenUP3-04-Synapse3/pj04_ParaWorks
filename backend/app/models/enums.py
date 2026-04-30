from enum import StrEnum


class SourceType(StrEnum):
    drive = 'drive'
    gmail = 'gmail'
    slack = 'slack'
    calendar = 'calendar'


class ReviewStatus(StrEnum):
    pending_review = 'pending_review'
    approved = 'approved'
    rejected = 'rejected'
    needs_more_evidence = 'needs_more_evidence'


class KnowledgeType(StrEnum):
    decision_record = 'decision_record'
    history_event = 'history_event'
    timeline_event = 'timeline_event'
    todo = 'todo'
