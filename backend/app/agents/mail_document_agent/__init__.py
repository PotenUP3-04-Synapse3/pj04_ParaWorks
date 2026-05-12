"""
메일 및 문서 에이전트 패키지.
이 패키지는 Gmail, Google Drive, Calendar 등의 소스에서 증거를 추출하고 요약하여
검토 가능한 회사 지식 후보를 생성하는 기능을 제공합니다.
"""
from backend.app.agents.mail_document_agent.agent import (
    MAIL_DOCUMENT_AGENT_MANIFEST,
    MAIL_DOCUMENT_AGENT_MODEL_NAME,
    MAIL_DOCUMENT_AGENT_NAME,
    MAIL_DOCUMENT_AGENT_PROMPT_VERSION,
    DeterministicMailDocumentAgentModel,
    MailDocumentAgent,
    MailDocumentAgentModel,
    MailDocumentAgentModelResponse,
)
from backend.app.agents.mail_document_agent.service import (
    MAIL_DOCUMENT_SOURCE_TYPES,
    build_mail_document_evidence_packet,
    create_mail_document_agent_review_items,
)

__all__ = [
    'MAIL_DOCUMENT_AGENT_MANIFEST',
    'MAIL_DOCUMENT_AGENT_MODEL_NAME',
    'MAIL_DOCUMENT_AGENT_NAME',
    'MAIL_DOCUMENT_AGENT_PROMPT_VERSION',
    'MAIL_DOCUMENT_SOURCE_TYPES',
    'DeterministicMailDocumentAgentModel',
    'MailDocumentAgent',
    'MailDocumentAgentModel',
    'MailDocumentAgentModelResponse',
    'build_mail_document_evidence_packet',
    'create_mail_document_agent_review_items',
]
