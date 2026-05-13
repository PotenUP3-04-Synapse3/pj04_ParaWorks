# ParaWorks 데이터베이스 테이블 명세서

본 문서는 ParaWorks 프로젝트의 데이터베이스 테이블 구조와 필드 정보를 상세히 설명합니다.

## 1. 개요
ParaWorks는 에이전트 기반의 협업 시스템으로, 사용자 인증, 슬랙/드라이브 통합, 지식 베이스 구축 등을 위한 테이블을 포함하고 있습니다.

## 2. 데이터베이스 스키마 구조
ParaWorks는 PostgreSQL을 사용하며, 데이터베이스 내에는 다음과 같은 스키마들이 존재합니다.

| 스키마명 | 성격 | 설명 |
| :--- | :--- | :--- |
| `public` | 사용자 스키마 | **ParaWorks 애플리케이션의 모든 테이블이 저장되는 기본 공간**입니다. 별도의 스키마 지정 없이 생성된 모든 오브젝트는 이곳에 위치합니다. |
| `information_schema` | 시스템 스키마 | SQL 표준에 정의된 정보 스키마입니다. 데이터베이스 내의 테이블, 컬럼, 권한 등 모든 메타데이터 정보를 뷰(View) 형태로 제공합니다. |
| `pg_catalog` | 시스템 스키마 | PostgreSQL의 시스템 카탈로그 테이블들이 위치합니다. 인덱스, 함수, 연산자 등 데이터베이스 운영에 필요한 내부 정보를 저장합니다. |
| `pg_toast` | 시스템 스키마 | TOAST(The Oversized-Attribute Storage Technique) 스키마입니다. 한 페이지(8KB)를 초과하는 큰 가변 길이 데이터(Large Text, JSON 등)를 압축하여 별도로 저장하는 공간입니다. |

## 3. 테이블 목록
(모든 ParaWorks 애플리케이션 테이블은 `public` 스키마 내에 위치합니다.)

| 테이블명 | 클래스명 | 설명 |
| :--- | :--- | :--- |
| `auth_users` | `AuthUser` | 사용자 계정 정보 |
| `refresh_tokens` | `RefreshToken` | OAuth2 리프레시 토큰 정보 |
| `integration_connections` | `IntegrationConnection` | 외부 서비스(Slack, Drive 등) 연결 정보 |
| `sync_jobs` | `SyncJob` | 데이터 동기화 작업 상태 |
| `sources` | `Source` | 원본 데이터 소스 정보 (메시지, 문서 등) |
| `documents` | `Document` | 소스에서 추출된 문서 정보 |
| `document_versions` | `DocumentVersion` | 문서 버전별 내용 |
| `document_chunks` | `DocumentChunk` | 문서를 분할한 텍스트 조각 |
| `document_parser_runs` | `DocumentParserRun` | 문서 파싱 실행 이력 |
| `message_channels` | `MessageChannel` | 메시지 채널(Slack 채널 등) 정보 |
| `messages` | `Message` | 개별 메시지 내용 |
| `decision_records` | `DecisionRecord` | 의사 결정 지식 데이터 |
| `history_events` | `HistoryEvent` | 역사적 사건 지식 데이터 |
| `timeline_events` | `TimelineEvent` | 타임라인 이벤트 지식 데이터 |
| `todos` | `Todo` | 할 일(Action Items) 지식 데이터 |
| `review_items` | `ReviewItem` | 지식 베이스 등록 전 검토 항목 |
| `agent_runs` | `AgentRun` | AI 에이전트 실행 기록 및 비용 |
| `audit_logs` | `AuditLog` | 시스템 활동 감사 로그 |
| `vector_index_states` | `VectorIndexState` | 벡터 데이터베이스 인덱싱 상태 |
| `rag_vector_documents` | (Native SQL) | 벡터 임베딩 저장 테이블 (pgvector) |

---

## 3. 상세 명세

### 3.1 사용자 및 인증

#### auth_users (AuthUser)
| 컬럼명 | 타입 | 제약사항 | 설명 |
| :--- | :--- | :--- | :--- |
| `id` | Integer | PK | 고유 식별자 |
| `external_id` | String(128) | Unique, Index | 외부 인증 시스템 ID (Google ID 등) |
| `email` | String(320) | Unique, Index | 이메일 주소 |
| `display_name` | String(200) | | 표시 이름 |
| `role` | String(32) | Index | 사용자 역할 (admin, user 등) |
| `department` | String(120) | | 부서명 |
| `title` | String(160) | | 직함 |
| `status` | String(32) | Index | 계정 상태 (active 등) |
| `permission_levels`| JSON | | 접근 가능한 권한 레벨 리스트 |
| `created_at` | DateTime | | 생성 일시 |
| `updated_at` | DateTime | | 수정 일시 |

#### refresh_tokens (RefreshToken)
| 컬럼명 | 타입 | 제약사항 | 설명 |
| :--- | :--- | :--- | :--- |
| `id` | Integer | PK | 고유 식별자 |
| `user_id` | Integer | FK (auth_users.id), Index | 사용자 식별자 |
| `token_hash` | String(96) | Unique, Index | 토큰 해시값 |
| `family_id` | String(64) | Index | 토큰 패밀리 ID (Rotational Reuse 방지용) |
| `expires_at` | DateTime | Index | 만료 일시 |
| `revoked_at` | DateTime | Nullable, Index | 취소 일시 |
| `replaced_by_token_id`| Integer | Nullable | 갱신된 새 토큰 ID |
| `created_at` | DateTime | | 생성 일시 |
| `last_used_at` | DateTime | Nullable | 마지막 사용 일시 |

---

### 3.2 서비스 통합

#### integration_connections (IntegrationConnection)
| 컬럼명 | 타입 | 제약사항 | 설명 |
| :--- | :--- | :--- | :--- |
| `id` | Integer | PK | 고유 식별자 |
| `connector_type`| String(32) | Index | 연결 타입 (slack, drive 등) |
| `workspace_id` | String(128) | Index | 외부 서비스 워크스페이스 ID |
| `workspace_name`| String(200) | | 워크스페이스 이름 |
| `workspace_url` | String(500) | | 워크스페이스 URL |
| `bot_user_id` | String(128) | Nullable | 봇 사용자 ID |
| `scopes` | JSON | | 부여된 권한 범위 리스트 |
| `token_ref` | String(300) | | 토큰 참조 정보 |
| `masked_bot_token`| String(64) | | 마스킹된 토큰 정보 |
| `status` | String(32) | Index | 연결 상태 |
| `raw_metadata` | JSON | | 원본 메타데이터 |
| `created_at` | DateTime | | 생성 일시 |
| `updated_at` | DateTime | | 수정 일시 |

#### sync_jobs (SyncJob)
| 컬럼명 | 타입 | 제약사항 | 설명 |
| :--- | :--- | :--- | :--- |
| `id` | Integer | PK | 고유 식별자 |
| `job_id` | String(64) | Unique, Index | 작업 고유 ID |
| `connector_type`| String(32) | Index | 연결 타입 |
| `status` | String(32) | | 작업 상태 (queued, running, complete 등) |
| `message` | String(300) | | 작업 상태 메시지 |
| `progress_pct` | Integer | | 진행률(%) |
| `created_at` | DateTime | | 생성 일시 |
| `updated_at` | DateTime | | 수정 일시 |

---

### 3.3 데이터 소스 및 문서

#### sources (Source)
| 컬럼명 | 타입 | 제약사항 | 설명 |
| :--- | :--- | :--- | :--- |
| `id` | Integer | PK | 고유 식별자 |
| `source_type` | String(32) | Index | 소스 타입 (slack, gmail, drive 등) |
| `source_id` | String(128) | Unique, Index | 원본 서비스의 고유 ID |
| `source_url` | String(500) | | 원본 데이터 URL |
| `title` | String(300) | | 제목 |
| `author` | String(200) | Nullable | 작성자 |
| `permission_level`| String(32) | Index | 권한 레벨 (internal, public 등) |
| `raw_metadata` | JSON | | 원본 메타데이터 |
| `created_at` | DateTime | | 생성 일시 |

#### documents (Document)
| 컬럼명 | 타입 | 제약사항 | 설명 |
| :--- | :--- | :--- | :--- |
| `id` | Integer | PK | 고유 식별자 |
| `source_id` | Integer | FK (sources.id), Index | 상위 소스 식별자 |
| `title` | String(300) | | 문서 제목 |
| `current_version`| String(64) | | 현재 버전 정보 |

#### document_versions (DocumentVersion)
| 컬럼명 | 타입 | 제약사항 | 설명 |
| :--- | :--- | :--- | :--- |
| `id` | Integer | PK | 고유 식별자 |
| `document_id` | Integer | FK (documents.id), Index | 상위 문서 식별자 |
| `version` | String(64) | | 버전 레이블 |
| `body` | Text | | 문서 내용 본문 |

#### document_chunks (DocumentChunk)
| 컬럼명 | 타입 | 제약사항 | 설명 |
| :--- | :--- | :--- | :--- |
| `id` | Integer | PK | 고유 식별자 |
| `version_id` | Integer | FK (document_versions.id), Index | 상위 버전 식별자 |
| `source_id` | Integer | FK (sources.id), Index | 소스 식별자 (조인 효율성용) |
| `chunk_index` | Integer | | 청크 순서 |
| `text` | Text | | 분할된 텍스트 내용 |
| `source_snippet`| Text | | 원본 텍스트 스니펫 |
| `permission_level`| String(32) | Index | 권한 레벨 |
| `metadata` | JSON | | 청크 메타데이터 |

---

### 3.4 지식 베이스

#### decision_records (DecisionRecord)
| 컬럼명 | 타입 | 제약사항 | 설명 |
| :--- | :--- | :--- | :--- |
| `id` | Integer | PK | 고유 식별자 |
| `title` | String(300) | | 결정 사항 제목 |
| `decision_summary`| Text | | 결정 요약 |
| `source_links` | JSON | | 출처 링크 목록 |
| `source_snippets`| JSON | | 출처 텍스트 목록 |
| `confidence_score`| Float | | 데이터 신뢰도 점수 |
| `permission_level`| String(32) | Index | 권한 레벨 |
| `review_status` | String(32) | | 검토 상태 (pending, approved 등) |
| `created_at` | DateTime | | 생성 일시 |

---

### 3.5 시스템 로그 및 에이전트

#### agent_runs (AgentRun)
| 컬럼명 | 타입 | 제약사항 | 설명 |
| :--- | :--- | :--- | :--- |
| `id` | Integer | PK | 고유 식별자 |
| `agent_name` | String(64) | Index | 에이전트 이름 |
| `prompt_version` | String(128) | Index | 프롬프트 버전 |
| `status` | String(32) | Index | 실행 상태 |
| `source_window` | String(200) | Index | 참조 소스 범위 |
| `cache_key` | String(128) | Index | 캐시 키 |
| `model_name` | String(128) | | 사용된 AI 모델 명 |
| `input_tokens` | Integer | | 입력 토큰 수 |
| `output_tokens` | Integer | | 출력 토큰 수 |
| `total_tokens` | Integer | | 총 토큰 수 |
| `estimated_cost_usd`| Float | | 예상 비용 (USD) |
| `permission_level`| String(32) | Index | 권한 레벨 |
| `metadata` | JSON | | 실행 메타데이터 |
| `started_at` | DateTime | | 시작 일시 |
| `completed_at` | DateTime | Nullable | 완료 일시 |

#### audit_logs (AuditLog)
| 컬럼명 | 타입 | 제약사항 | 설명 |
| :--- | :--- | :--- | :--- |
| `id` | Integer | PK | 고유 식별자 |
| `actor_id` | String(64) | Index | 행위자 ID |
| `actor_email` | String(200) | Index | 행위자 이메일 |
| `actor_role` | String(32) | Index | 행위자 역할 |
| `action` | String(100) | Index | 수행한 작업 |
| `target_type` | String(64) | Index | 작업 대상 타입 |
| `target_id` | String(200) | Index | 작업 대상 식별자 |
| `status` | String(32) | Index | 성공 여부 |
| `metadata` | JSON | | 추가 메타데이터 |
| `created_at` | DateTime | Index | 로그 생성 일시 |
