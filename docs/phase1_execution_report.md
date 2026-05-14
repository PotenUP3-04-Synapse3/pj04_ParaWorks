# Phase 1: DB 스키마 보강 (project_key 추가) 실행 보고서

본 문서는 **프로젝트 중심 지식 자동화 계획서**의 첫 번째 단계인 'DB 스키마 보강' 작업의 실행 및 검증 결과를 기록합니다.

---

## 1. 작업 내용 (Action)

- **목표**: `DecisionRecord`, `Todo`, `HistoryEvent`, `TimelineEvent` 등 핵심 지식 모델에 `project_key` 컬럼을 추가하여 데이터가 어떤 프로젝트에 속하는지 추적할 수 있는 기반 마련.
- **변경 파일**: `backend/app/models/knowledge.py`
  - 위 4개의 클래스에 `project_key: Mapped[str | None] = mapped_column(String(64), index=True)` 코드를 추가했습니다.
- **Alembic 마이그레이션**: `uv run alembic revision --autogenerate -m "add project_key to knowledge models"` 명령어를 통해 DB 마이그레이션 스크립트를 생성했습니다.

---

## 2. 시행착오 및 해결 과정 (Mistakes & Troubleshooting)

작업 도중 다음과 같은 에러가 발생하였고, 이를 해결하며 진행했습니다.

### 2.1 데이터베이스 연결 오류 (Port Mismatch)

- **상황**: Alembic 스크립트 생성 시 `FATAL: password authentication failed for user "paraworks"`라는 오류와 함께 5432 포트 연결 실패 발생.
- **원인**: Docker 컨테이너 확인 결과, Postgres 서버가 로컬에서 `5432` 포트로 포트포워딩되어 돌아가고 있었으나, `.env` 및 `alembic.ini` 파일에는 기본값인 `5432`로 설정되어 있어 비밀번호 불일치(다른 로컬 DB 연결) 현상이 발생.
- **해결 1**: 파이썬 스크립트를 이용해 `.env` 파일의 `DATABASE_URL`과 `PARAWORKS_POSTGRES_PORT` 값을 `5432`로 수정.
- **해결 2**: `alembic.ini` 파일 내의 `sqlalchemy.url` 값 역시 `5432`로 수정(`replace` 도구 사용).
- **해결 3**: 환경 변수 `$env:DATABASE_URL`을 명시적으로 설정하여 Alembic 명령어가 안전하게 올바른 DB를 바라보도록 유도.

### 2.2 Alembic Auto-generate 과잉 삭제 방지

- **상황**: 마이그레이션 스크립트 생성 시, `rag_vector_documents` 테이블과 인덱스를 삭제하려는 쿼리가 자동 생성됨.
- **원인**: `pgvector`를 사용하는 테이블 구조가 Alembic의 `Base.metadata` 로딩 과정에서 완벽히 호환되지 않아 테이블이 없어진 것으로 잘못 인식함.
- **해결**: 생성된 마이그레이션 파일(`5f8d874023d7_add_project_key_to_knowledge_models.py`)을 열어 `rag_vector_documents` 삭제 관련 `upgrade()`, `downgrade()` 코드를 수동으로 제거(수술)하여 기존 벡터 데이터가 소실되지 않도록 보호함.

---

## 3. 검증 결과 (Validation)

수정된 마이그레이션 스크립트를 `uv run alembic upgrade head`로 적용한 후, 관련된 테스트를 진행하여 모든 코드가 구조 변경 위에서도 정상 작동함을 확인했습니다.

- **실행 명령어**: `uv run pytest backend/tests/test_db_schema_operations.py backend/tests/test_models.py backend/tests/test_knowledge_api.py -v`
- **테스트 결과**: 10개 항목 모두 통과 (100% Passed)
  - 스키마 체커(`test_schema_checker...`): 정상
  - 모델 상태 검증(`test_models.py`): 정상
  - 지식 API (`test_knowledge_api.py`): 정상

---

**진행 상태**: Phase 1 완료. 이제 다음 단계인 'Phase 2: AI 자동 분류 및 검토 UI 연동'으로 넘어갈 준비가 되었습니다.
