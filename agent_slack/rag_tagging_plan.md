# [작업 계획서] 슬랙 데이터 RAG 고도화를 위한 메타데이터 태그 시스템 구축

## 1. 개요 (Background & Objective)
ParaWorks AI 비서가 슬랙 데이터를 활용하여 답변할 때, 단순한 텍스트 검색을 넘어 **맥락(Context)**을 이해하고 **명확한 근거(Citation)**를 제시할 수 있도록 메타데이터 태그 시스템을 구축합니다. 또한, 승인된 고품질 지식만을 RAG에 활용하여 답변의 정확성을 보장합니다.

- **목표**: RAG 검색 품질 향상 및 답변 신뢰성 강화
- **담당**: 개발자 A (Communication Intelligence)

## 2. 메타데이터 태그 설계 (Metadata Schema)

### A. 정적 태그 (Static Tags - 수집 시점 생성)
슬랙 API로부터 직접 얻을 수 있는 기본 정보입니다.
| Key | 설명 | 예시 |
| :--- | :--- | :--- |
| `channel_name` | 메시지가 발생한 채널명 | `#pjt-ai-memory`, `#general` |
| `author_name` | 작성자의 실명 (ID 변환 완료된 이름) | `김철수`, `이영희` |
| `is_thread_reply` | 쓰레드 댓글 여부 (Boolean) | `true` / `false` |
| `parent_ts` | 쓰레드인 경우 부모 메시지의 타임스탬프 | `1715000000.0001` |
| `created_at_date` | 메시지 생성 날짜 (YYYY-MM-DD) | `2024-05-13` |

### B. 동적 태그 (Dynamic Tags - 분석 시점 생성)
Slack Agent가 대화 내용을 분석하여 부여하는 지능형 태그입니다.
| Key | 설명 | 예시 |
| :--- | :--- | :--- |
| `category` | 업무 분류 | `Project`, `Operations`, `Admin` |
| `topic_tag` | 구체적 토픽/프로젝트명 | `RAG 고도화`, `인사정책` |
| `importance` | 중요도 (Low/Medium/High) | `High` |

## 3. 상세 구현 단계 (Implementation Steps)

### Phase 1: 커넥터 레벨 수정 (정적 태그 강화)
- **대상**: `backend/app/connectors/slack.py`
- **작업 내용**:
    1. `conversations_list` 결과를 캐싱하여 채널 ID를 채널명으로 변환하는 로직 추가.
    2. `SourceEvent` 생성 시 위 표에 정의된 정적 태그들을 `raw_metadata`에 포함.
    3. 메시지 본문 해시를 통한 `content_signature` 추가 (중복 임베딩 방지).

### Phase 2: 동적 태그 전파 (Agent Back-propagation)
- **대상**: `backend/app/agents/slack_agent/sync_service.py`
- **작업 내용**:
    1. `Slack Agent`가 분석을 마친 후, 추출된 `ReviewCandidate`의 카테고리와 토픽 정보를 원본 `DocumentChunk` 테이블에 업데이트.
    2. 원본 메시지와 분석 결과 간의 매핑을 위해 `source_id`를 활용.

### Phase 3: RAG 검색 및 답변 근거 UI 연동
- **대상**: `backend/app/rag/indexing.py` 및 프롬프트
- **작업 내용**:
    1. 강화된 메타데이터가 `pgvector` 인덱스에 포함되도록 인덱싱 로직 확인.
    2. AI 비서 답변 시 하단에 `[근거: #채널명, 작성자, 날짜]` 형태의 출처 표기가 가능하도록 데이터 제공.

## 4. 데이터 보안 및 품질 정책 (Data Security & Quality Policy)

- **승인 기반 RAG (Approval-only RAG)**:
    - AI Agent가 추출한 후보 중 사람이 **'승인(Approve)'**한 데이터만 RAG 엔진(pgvector)에 전송하여 임베딩을 수행합니다.
    - 원본 데이터(`DocumentChunk`)는 승인된 지식의 증거로 보존하되, 승인되지 않은 정보가 답변에 활용되는 것을 원천 차단합니다.

- **반려 데이터 즉각 폐기 (Delete on Rejection)**:
    - 검토 큐에서 **'반려(Reject)'** 처리된 데이터는 DB에서 물리적으로 삭제합니다.
    - 불필요한 노이즈 데이터를 제거하여 검색 품질을 유지하고 DB 용량을 최적화합니다.

## 5. 예상 결과 (Expected Output Format)

> **사용자 질문**: "지난주 RAG 고도화 프로젝트에서 결정된 사항이 뭐야?"
> 
> **AI 답변**: "지난 5월 8일, RAG 고도화 프로젝트와 관련하여 **벡터 DB를 pgvector로 전환**하기로 결정되었습니다. [근거: #pjt-ai-memory, 김철수, 2024-05-08]"

## 6. 향후 일정 (Timeline)
- **Day 1**: Phase 1 (커넥터 수정 및 정적 태그 반영)
- **Day 2**: Phase 2 (에이전트 분석 결과 역전파 로직 구현)
- **Day 3**: Phase 3 (RAG 검색 테스트 및 최종 검증)
