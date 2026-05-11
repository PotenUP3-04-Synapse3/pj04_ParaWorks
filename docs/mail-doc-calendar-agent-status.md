# Mail/Document/Calendar Agent 진행상황

Updated: 2026-05-12

## 목표

Google Drive 문서, Gmail, Calendar 데이터를 수집하고, evidence metadata를 보존한 뒤,
프로젝트 단위로 분류/요약해서 ParaWorks 화면에서 확인할 수 있게 만든다.

이 트랙은 Developer B의 Mail and Document Agent 책임 영역이다. 다만 Calendar는 일정
맥락이 프로젝트 묶음에 꼭 필요하므로, Gmail/Drive evidence window와 같은 수집/분류
경계에서 함께 다룬다.

## 현재 구현된 것

- Google OAuth 설치 경계가 Gmail, Drive, Calendar에 대해 존재한다.
- `GoogleConnector`가 Gmail, Drive, Calendar를 `SourceEvent`로 변환한다.
- Gmail은 본문 payload, thread id, participant/domain metadata, external participant
  여부를 보존한다.
- Gmail attachment는 별도 `gmail_attachment` source로 들어오며 parser status,
  parent message id, attachment id, mime type, content signature를 보존한다.
- Drive는 Google Docs/Sheets/Slides export를 통해 본문 text/csv/plain text를
  수집한다.
- Drive PDF/DOCX/HWP/HWPX는 metadata-only 또는 unsupported 상태로 표시하고,
  parser status reason을 남긴다.
- Calendar는 event status, organizer/creator, attendee response counts,
  external attendee domains, duration metadata를 보존한다.
- `ingest_events`가 모든 connector event를 Source, Document, DocumentVersion,
  DocumentParserRun, DocumentChunk로 저장한다.
- Mail/Document Agent는 Gmail, Gmail attachment, Drive evidence를 Review Queue
  후보로 만들고 AgentRun 비용/토큰/증거 요약을 기록한다.
- 이번 세션에서 Mail/Document Agent evidence packet에 Calendar source를 포함했다.
- 이번 세션에서 `GET /api/v1/projects`를 추가해 Gmail/Drive/Calendar evidence를
  `project_key` 또는 `scenario` 기준으로 묶어 반환한다.
- 프로젝트 API는 strictest permission을 적용하고, 현재 사용자가 볼 수 없는 restricted
  프로젝트는 숨긴 뒤 hidden count를 반환한다.

## 현재 한계

- 프로젝트 분류는 deterministic heuristic이다. `project_key`, `scenario`, URL/title/source id
  패턴을 사용하며, 아직 LLM 기반 프로젝트 분류 모델은 없다.
- `/projects` 프론트엔드 화면은 현재 정적 데모 데이터 중심이다. 새 backend API와 완전히
  연결하려면 다음 프론트엔드 슬라이스가 필요하다.
- Drive binary PDF/DOCX/HWP/HWPX 본문 parser는 아직 실제 파일 다운로드/파싱까지 가지
  않는다. Google-native Docs/Sheets/Slides export가 먼저 구현된 상태다.
- Gmail attachment도 metadata source로 저장되며, attachment body download/parser는
  아직 없다.
- Calendar는 Mail/Document Agent evidence window에 들어오지만, agent name과 manifest는
  아직 `mail_document_agent`로 남아 있다. 제품 용어를 바꿀지는 팀 결정이 필요하다.

## 남은 작업

1. `/projects` frontend를 `GET /api/v1/projects`에 연결한다.
2. Project detail view에서 evidence link, source snippet, permission, source type을
   reviewer가 바로 확인할 수 있게 한다.
3. 프로젝트 분류 규칙을 명시적인 `project_key` 우선, URL/title fallback, reviewer 수정
   가능 상태로 확장한다.
4. Drive PDF/DOCX parser adapter를 실제 parser로 승격할지 결정하고, parser run record
   테스트를 먼저 추가한다.
5. HWP/HWPX parser는 후보 라이브러리와 운영 리스크를 비교한 뒤 adapter decision을
   문서화한다.
6. Gmail attachment download/parser를 추가하되, live Google API 호출은 fake client
   테스트 뒤에만 연결한다.
7. Calendar event를 프로젝트 일정/마일스톤 후보로 변환하는 deterministic agent slice를
   추가한다.
8. 프로젝트 grouping 결과를 Review Queue 후보와 approved knowledge promotion 흐름에
   연결한다.
9. 프로젝트별 token/cost summary와 skipped duplicate evidence count를 UI에 노출한다.
10. Gmail/Drive/Calendar golden dataset을 프로젝트 grouping 케이스까지 확장한다.

## 이번 세션에서 진행한 작업

- Calendar source를 Mail/Document Agent evidence packet에 포함했다.
- Calendar metadata 중 event context/status/organizer/duration/attendee metadata를
  agent metadata로 보존했다.
- `backend/app/projects/service.py`에 프로젝트 메모리 집계 서비스를 추가했다.
- `backend/app/api/v1/projects.py`에 프로젝트 목록 API를 추가했다.
- `backend/tests/test_project_memory_api.py`로 Gmail/Drive/Calendar grouping과 restricted
  project hiding을 검증했다.
- `backend/tests/test_mail_document_agent_review_bridge.py`에 Calendar evidence packet
  회귀 테스트를 추가했다.

## 검증

```bash
uv run pytest backend/tests -v
```

Result: 287 passed, 1 skipped.
