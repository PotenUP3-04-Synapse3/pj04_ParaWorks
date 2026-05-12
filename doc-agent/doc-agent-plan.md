# Document & Knowledge Agent (Track B) Plan

이 문서는 Developer B(문서 및 지식 파이프라인)의 전체 작업 계획입니다.
목표: "우리 회사 매뉴얼이나 기획서, 업무 메일에 어떤 내용이 들어있는가?"를 ParaWorks가 Google Drive/Gmail 문서 내용을 근거, 버전, 권한, 출처와 함께 정확히 찾아 답할 수 있게 합니다.

## 작업 운영 규칙
- `doc-agent/`는 임시 폴더가 아니라 Document Agent 트랙의 소유 자산 폴더입니다.
- 관련된 작업 로그는 `doc-agent/portfolio-log-docs-agent.md`에 저장합니다.
- 공용 제품 방향은 루트 `plan.md`를 따릅니다.

## 단계별 작업 계획 (Tasks)

### Step 1. 기반 아키텍처 및 파이프라인 (완료)
- [x] Google Gmail/Drive/Calendar sync skeleton (`backend/app/connectors/google.py`) 구현
- [x] 기본 문서 모델(`Source`, `Document`, `DocumentVersion`, `DocumentChunk`) 구축
- [x] 문서 파서 및 버전 관리 계약(Contracts)의 기초 정의 (문서 메타데이터, 리비전 추적 등)
- [x] pgvector 임베딩 어댑터 세팅 및 비용 절감을 위한 점진적 벡터 인덱싱(Incremental Indexing) 기초
- [x] Mail/Document Agent 세로 슬라이스 뼈대 및 SQLite smoke 모드 적용

### Step 2. 수집 및 파싱 고도화 (Ingestion & Parsing) (완료)
- [x] **Google Drive 본문 export 구현**
  - Google Docs (text/plain 또는 HTML), Sheets (text/csv) 파싱
  - PDF, DOCX 로컬 파서 연동, HWP/HWPX 등은 우선 `metadata_only` 또는 `unsupported`로 처리
- [x] **Gmail 본문/첨부 경계 강화**
  - Multipart body 품질 개선, 스레드 단위 메타데이터 보존
  - 메일 본문과 첨부 파일 간의 Source ID 체계 정립
- [x] **Chunking (청킹) 품질 개선**
  - 내용 기반(제목/섹션/페이지/문단 단위) 청킹 및 청크 메타데이터 보존
- [x] **파서 실행 기록(Parser Run Record) 및 상태 추적**
  - 파싱 성공/실패 여부를 나타내는 `parser_status`, `parser_status_reason` 필드 적용

### Step 3. 메일/문서 에이전트 인텔리전스 (AI Agent) (완료)
- [x] **업무 연관성 판단 프롬프트 작성**
  - 수집된 메일/문서가 실제 업무와 관련된 내용인지 판단 (사적인 메일 필터링)
- [x] **프로젝트별 분류 로직 개발**
  - 문서/메일의 내용을 기반으로 소속 프로젝트 자동 태깅
- [x] **구조화된 정보 추출 (Structured Output)**
  - Gmail: `To`, `From`, `Subject`, `CC`, `Date`, `Summary`, `Link` 추출
  - Drive: `Uploader`, `Title`, `Upload Date`, `Summary`, `Link` 추출

### Step 4. 검토 큐(Review Queue) 연동 및 임시 저장 테이블 렌더링 (완료)
- [x] **에이전트 산출물 Review Queue 전달**
  - 추출된 구조화 데이터(요약 + 메타데이터)를 `ReviewItem(status="pending_review")`로 저장
- [x] **Source Evidence Drawer UI 업데이트**
  - 검토/승인/수정 화면(Frontend)에 구조화된 이메일/문서 포맷이 잘 보이도록 UI 연동

### Step 5. 검색 및 문서 관측성 (Observability) 연동 (완료)
- [x] **Document Observability API 개발 (Backend)**
  - `GET /api/v1/documents`, `GET /api/v1/documents/{document_id}/versions`, `GET /api/v1/documents/parser-stats` 엔드포인트 추가
- [x] **Search API 메타데이터 증강 (Backend)**
  - `/api/v1/search` 응답에 문서의 `parser_status`, `parser_status_reason`, `revision_id` 추가
- [x] **Document Observability UI 개발 (Frontend)**
  - `/documents` 페이지를 만들어 동기화된 문서, 버전, 파싱 상태 뱃지 렌더링
- [x] **Search Results UI 업데이트 (Frontend)**
  - 텍스트 추출이 불가한 항목(`metadata_only`, `unsupported`)에 대한 경고 배지 표시

### Step 6. 테스트 및 검증 (Testing & Demo) (완료)
- [x] **문서 Golden Dataset 구축**
  - 파싱 가능한 문서와 메타데이터 전용 문서를 테스트하는 데이터셋 추가 (`backend/tests/test_connector_golden_dataset.py`)
- [x] **테스트 코드 작성 (TDD)**
  - Drive export 변환 테스트, 동일 content signature에 대한 재임베딩 스킵 테스트 등
- [x] **End-to-End 데모 시나리오 실행**
  - 파싱 -> 에이전트 검토 -> RAG 재색인(changed/skipped 확인) -> 질문 시 근거 제공 확인
