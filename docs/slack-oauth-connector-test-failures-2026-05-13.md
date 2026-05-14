# Slack/OAuth/Connector 테스트 실패 전달 메모

작성일: 2026-05-13  
작성자: 개발자 C / RAG & Orchestrator 담당

## 배경

AI 비서의 이메일 액션 서브에이전트 작업 후 백엔드 전체 테스트를 확인하는 과정에서, 메일 액션과 직접 관련 없는 Slack/OAuth/connector 계열 테스트 실패가 남아 있는 것을 확인했습니다.

메일 액션 관련 테스트는 별도로 통과했습니다.

```powershell
uv run pytest backend/tests/test_assistant_api.py -q
```

결과:

```text
12 passed
```

하지만 백엔드 전체 테스트는 아래 명령에서 green 상태가 아니었습니다.

```powershell
uv run pytest backend/tests -q
```

확인 당시 결과:

```text
17 failed, 335 passed, 1 skipped
```

아래 내용은 Slack/OAuth/connector 담당자가 이어서 확인하기 쉽도록 실패 지점을 묶어 정리한 것입니다.

## 요약

현재 실패는 크게 네 묶음입니다.

1. Slack connector fake client 계약 불일치
2. Slack OAuth / PKCE install URL 생성 문제
3. Connector ingestion / review item 생성 카운트 불일치
4. Slack agent review payload 계약 불일치

추가로, 문서 에이전트의 한국어/영어 기대 문구 불일치와 token vault 관련 connector factory 실패도 같이 관찰되었습니다.

## Slack Connector 실패

### 실패 테스트

```text
backend/tests/test_slack_connector.py::test_slack_connector_maps_history_messages_to_source_events
backend/tests/test_slack_connector.py::test_slack_connector_fetches_incremental_history_after_channel_cursor
backend/tests/test_slack_connector.py::test_slack_connector_collects_thread_replies_with_parent_context
backend/tests/test_connector_golden_dataset.py::test_connector_golden_dataset_preserves_agent_ready_metadata
```

### 관찰된 증상

테스트용 fake client에 `conversations_list()` 메서드가 없어 실패합니다.

대표 오류:

```text
AttributeError: 'FakeSlackClient' object has no attribute 'conversations_list'
```

또는:

```text
AttributeError: 'GoldenSlackClient' object has no attribute 'conversations_list'
```

### 확인 포인트

- `backend/app/connectors/slack.py`에서 `fetch_events_since()`가 항상 `self.client.conversations_list()`를 호출합니다.
- 기존 테스트 fake client들은 `conversation_history()`와 `conversation_replies()`만 구현한 상태입니다.
- 실제 의도가 “봇이 참여 중인 채널만 필터링”이라면, fake client 계약을 업데이트해야 합니다.
- 반대로 connector가 `conversations_list()` 없는 client도 지원해야 한다면, production 코드에서 fallback 처리가 필요합니다.

### 제안 우선순위

우선 fake client 계약을 production connector 요구사항에 맞추는 쪽이 안전해 보입니다. 다만 기존 테스트가 의도한 “최소 Slack client 인터페이스”가 있었다면, connector 코드에서 optional capability로 처리하는 방향도 검토가 필요합니다.

## Slack OAuth / PKCE 실패

### 실패 테스트

```text
backend/tests/test_oauth_pkce.py::test_slack_oauth_pkce_generation
backend/tests/test_oauth_pkce.py::test_slack_callback_with_custom_redirect_uri_and_pkce
backend/tests/test_oauth_pkce.py::test_api_endpoints_support_redirect_uri
backend/tests/test_slack_oauth.py::test_slack_oauth_install_url_contains_signed_state_and_hides_secret
```

### 관찰된 증상

Slack install URL에 PKCE 관련 query parameter가 없거나, install URL/state가 비어 있는 상태로 보입니다.

대표 오류:

```text
AssertionError: assert 'code_challenge' in params
```

또는:

```text
SlackApiError: Slack OAuth state is malformed
```

또 다른 실패:

```text
AssertionError: assert parsed.netloc == 'slack.com'
```

### 확인 포인트

- `build_slack_oauth_install_url()`가 정상적인 Slack URL을 만드는지 확인이 필요합니다.
- PKCE를 기본 활성화하기로 한 테스트 기대와 실제 구현이 어긋난 상태일 수 있습니다.
- custom `redirect_uri`를 넘겼을 때 state에 verifier/redirect 정보가 유지되는지 확인해야 합니다.
- install URL 생성 실패 시 빈 문자열을 반환하는 경로가 있는지 확인이 필요합니다.

### 제안 우선순위

OAuth는 실제 연동 흐름의 입구라 우선순위를 높게 두는 것이 좋습니다. 특히 `state`가 비어 있으면 callback 전체가 실패하므로 install URL 생성부터 먼저 재현하는 것이 좋습니다.

## Connector Ingestion 실패

### 실패 테스트

```text
backend/tests/test_connector_ingestion_contract.py::test_sync_connector_events_records_job_and_ingests_review_items
backend/tests/test_connector_ingestion_contract.py::test_sync_connector_events_passes_latest_slack_timestamp_cursor
backend/tests/test_connector_ingestion_contract.py::test_sync_connector_events_passes_latest_generic_sync_cursor
```

### 관찰된 증상

동기화 결과에서 생성된 review item 수가 기대값과 다릅니다.

대표 오류:

```text
AssertionError: assert 0 == 1
```

구체적으로:

```text
result.created_review_items == 0
```

테스트 기대값:

```text
result.created_review_items == 1
```

### 확인 포인트

- `sync_connector_events()`에서 source/document chunk는 생성되지만 review item 생성 단계가 skip되는지 확인이 필요합니다.
- review item 생성을 agent extraction 결과에 의존하도록 바뀌었는지 확인해야 합니다.
- deterministic fallback 또는 test connector payload가 현재 ingestion contract를 만족하는지 확인해야 합니다.
- parser status count가 비어 있는 것도 함께 봐야 합니다.

### 제안 우선순위

Slack 동기화 후 “검토사항 숫자 업데이트”와도 연결될 수 있으므로 우선순위가 높습니다. 동기화가 성공으로 보이지만 검토 큐에 아무것도 생기지 않는 상태라면 사용자 입장에서는 기능이 작동하지 않는 것처럼 보일 수 있습니다.

## Slack Agent Review Payload 실패

### 실패 테스트

```text
backend/tests/test_slack_agent_api.py::test_slack_agent_review_endpoint_creates_agent_review_item
```

### 관찰된 증상

생성된 `ReviewItem.payload`에 `prompt_version`이 없습니다.

대표 오류:

```text
KeyError: 'prompt_version'
```

### 확인 포인트

- Slack agent가 생성하는 review item payload 계약에 `prompt_version`을 유지해야 하는지 확인이 필요합니다.
- 최근 agent output schema 또는 payload 구조를 바꾸면서 누락됐을 가능성이 있습니다.
- `/api/v1/integrations/slack/agent-review` 응답은 complete로 보이지만, 저장된 payload가 테스트 기대와 다릅니다.

### 제안 우선순위

검토 큐에서 AI 산출물의 출처/프롬프트 버전을 추적해야 하므로 `prompt_version`은 유지하는 편이 좋습니다. agent run 추적, 비용 추적, 검토 이력과 연결될 수 있습니다.

## Connector Factory / Token Vault 실패

### 실패 테스트

```text
backend/tests/test_connector_factory.py::test_sync_connector_requires_slack_token_when_installed_token_is_not_in_vault
```

### 관찰된 증상

테스트는 token vault에 Slack token이 없으면 `ConnectorNotConfiguredError`가 발생하기를 기대하지만, 실제로는 예외가 발생하지 않았습니다.

대표 오류:

```text
Failed: DID NOT RAISE <class 'backend.app.connectors.factory.ConnectorNotConfiguredError'>
```

### 확인 포인트

- installed connection의 `token_ref`가 vault에 없을 때 설정값의 fallback token을 사용하도록 바뀌었는지 확인이 필요합니다.
- 실제 운영 정책이 “연결별 token_ref 필수”인지, “환경변수 fallback 허용”인지 결정해야 합니다.
- 보안상으로는 사용자가 설치한 connection이면 vault token 누락을 명확히 실패시키는 편이 안전합니다.

## 관련 있지만 Slack 담당 외 영역일 수 있는 실패

### Mail Document Agent 문구 불일치

실패 테스트:

```text
backend/tests/test_mail_document_agent.py::test_deterministic_mail_document_agent_marks_metadata_only_evidence_uncertain
backend/tests/test_mail_document_agent.py::test_deterministic_mail_document_agent_marks_unsupported_evidence_uncertain
```

증상:

테스트는 영어 문구를 기대하지만 실제 결과는 한국어입니다.

```text
Expected: Some document evidence is not body-parsed: ...
Actual: 일부 문서 증거가 본문 파싱되지 않았습니다: ...
```

이건 Slack 담당보다는 문서/지식 파이프라인 담당자가 보는 것이 자연스럽습니다.

## 재현 명령

Slack connector만 빠르게 확인:

```powershell
uv run pytest backend/tests/test_slack_connector.py backend/tests/test_connector_golden_dataset.py -q
```

Slack OAuth / PKCE 확인:

```powershell
uv run pytest backend/tests/test_oauth_pkce.py backend/tests/test_slack_oauth.py -q
```

Connector ingestion 확인:

```powershell
uv run pytest backend/tests/test_connector_ingestion_contract.py backend/tests/test_connector_factory.py -q
```

Slack agent review 확인:

```powershell
uv run pytest backend/tests/test_slack_agent_api.py::test_slack_agent_review_endpoint_creates_agent_review_item -q
```

전체 백엔드 확인:

```powershell
uv run pytest backend/tests -q
```

## 담당자에게 전달할 핵심 메시지

현재 Slack/OAuth/connector 영역은 테스트 fake client 계약, OAuth PKCE URL 생성, 동기화 후 review item 생성, agent review payload 계약이 서로 맞지 않는 상태로 보입니다.

특히 아래 세 가지를 먼저 보는 것을 추천합니다.

1. `SlackConnector.fetch_events_since()`가 요구하는 client interface와 테스트 fake client 계약 맞추기
2. `build_slack_oauth_install_url()`가 Slack install URL, signed state, PKCE parameter를 항상 생성하는지 확인하기
3. `sync_connector_events()` 이후 review item 생성 수가 0이 되는 이유 확인하기

이 세 가지가 정리되면 Slack 동기화, 검토 큐 반영, OAuth 설치 흐름의 신뢰도가 같이 올라갈 가능성이 큽니다.
