# Document Agent Finalization (Backend & Frontend)

The Document Agent track (Track B) has successfully built the ingestion pipeline, versioning, parser contracts, and vector enrichment on the backend. To complete the `doc-agent-plan.md`, we need to expose the document observability API, surface the parser status in existing search/review flows, and implement the frontend UI to display document versions and extraction states.

## Steps

1. **Document Observability API (Backend)**
   - Implement `GET /api/v1/documents` and `GET /api/v1/documents/{document_id}/versions` endpoints.
   - Return the latest version, `revision_id`, `parser_name`, `parser_status`, and chunk counts (Satisfying `doc-agent-plan.md` item 6 MVP requirement).

2. **Search API Metadata Augmentation (Backend)**
   - Update `SearchRequest` response in `backend/app/api/v1/search.py` to include `parser_status`, `parser_status_reason`, and `revision_id` from candidate metadata.

3. **Document Golden Dataset Cases (Backend)**
   - Add Track B golden dataset cases in `backend/tests/test_connector_golden_dataset.py` for Google Docs (parsed) and PDF/HWP (metadata_only/unsupported).

4. **Document Observability UI (Frontend)**
   - Create a Document List/Detail page (e.g., `frontend/src/app/documents/page.tsx` or under `admin/documents`) to view synced documents, versions, and chunk counts.
   - Display `parser_status` badges (Parsed, Metadata Only, Unsupported) and `parser_status_reason`.

5. **Search Results UI Update (Frontend)**
   - Update Search results components to display `metadata_only` or `unsupported` warnings on items that lack full text extraction.

6. **End-to-End Demo Scenario Test/Run**
   - Execute the demo scenario (Step 10 of `doc-agent-plan.md`) ensuring backend indexing logs and frontend renders reflect changes accurately.

## Relevant files

- `backend/app/api/v1/documents.py` (신규) — Document metadata API 라우터.
- `backend/app/api/v1/search.py` — 검색 결과 반환 스키마에 Document 메타데이터 추가.
- `backend/tests/test_connector_golden_dataset.py` — Document golden test suite.
- `frontend/src/app/documents/page.tsx` (신규) — Document 상태 확인 목적의 프론트엔드 라우트.
- `frontend/src/app/search/page.tsx` 및 관련 UI — 검색 결과에 parser 상태 표시 렌더링.

## Verification

1. 백엔드 테스트: 신규 `test_documents_api.py` 작성 후 구동 및 Golden Dataset 케이스 통과 확인.
2. 프론트엔드 빌드: 린트 및 `npm run build` 스크립트 점검.
3. 데모 리뷰: Drive 파싱 결과를 UI에서 확인하고, RAG 색인 시 changed/skipped 정보가 표시되는지 End-to-end 환경에서 육안 점검.

## Decisions

- PDF, DOCX, HWP/HWPX의 본문 추출(Parser Adatper 도입)은 현재 로그에 문서화된 대로 일단은 `metadata_only`나 `unsupported` 로 둔 상태를 유지합니다. 지금은 해당 추출 상태를 API와 UI로 가시화하는 데 집중합니다.