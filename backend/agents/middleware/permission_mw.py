from __future__ import annotations

from typing import Any, Callable

import structlog
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse

log = structlog.get_logger(__name__)

# 권한이 필요한 tool 이름 → 필요한 permission_level
_RESTRICTED_TOOLS: dict[str, str] = {
    'get_confidential_decisions': 'confidential',
    'get_restricted_documents': 'restricted',
    'get_personal_handover': 'restricted',
}


@wrap_model_call
def permission_check_middleware(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    """사용자 권한에 따라 민감 tool을 동적으로 필터링."""
    state = request.state
    user_permission_levels: set[str] = set(state.get('accessible_permission_levels', ['public', 'team']))

    # 접근 불가 tool 제거
    filtered_tools = []
    removed = []
    for tool in request.tools:
        required = _RESTRICTED_TOOLS.get(tool.name)
        if required and required not in user_permission_levels:
            removed.append(tool.name)
        else:
            filtered_tools.append(tool)

    if removed:
        log.info('permission.tools_filtered', removed=removed)
        request = request.override(tools=filtered_tools)

    return handler(request)
