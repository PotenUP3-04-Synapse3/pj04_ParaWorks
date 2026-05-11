좋아요. 개발자 B의 역할은 이미 있는 Mail/Document Agent, Google OAuth/sync skeleton, pgvector 기반 위에 “문서 본문을 믿을 수 있게 가져와서, 버전별로 추적하고, RAG가 정확히 찾게 만드는” 트랙으로 잡으면 됩니다.

**작업 운영 규칙**

- `doc-agent/`는 임시 폴더가 아니라 Document Agent 트랙의 소유 자산 폴더다.
- Document Agent 트랙의 계획, 로그, 평가셋, 프롬프트, 데모 자산, 설계 메모는 `./doc-agent/` 아래에 둔다.
- 실제 ParaWorks 런타임에 포함되는 백엔드 코드와 테스트는 기존 프로젝트 구조에 맞춰
  `backend/app/...`, `backend/tests/...`에 생성하거나 수정한다.
- 기존 ParaWorks 런타임/커넥터/테스트 코드를 바꿔야 할 때는 해당 기존 파일을 직접 수정한다.
- Document Agent 관련 작업 로그와 포트폴리오 기록은 `docs/portfolio-log.md`가 아니라
  `doc-agent/portfolio-log-docs-agent.md`에 저장한다.
- git 작업 브랜치는 `/agent_docs`를 기준으로 한다.
- 공용 제품 방향은 루트 `plan.md`를 따르되, Document Agent 트랙의 세부 실행 기록과 의사결정은 이 계획 파일과
  `doc-agent/portfolio-log-docs-agent.md`를 우선 확인한다.

**현재 출발점**  
plan.md 기준 Track B는 이미 “Document and Knowledge Pipeline”입니다. 코드상으로도 다음 기반이 있습니다.

- Google Gmail/Drive/Calendar sync skeleton: backend/app/connectors/google.py
- Gmail 본문 추출 일부 구현됨
- Drive는 현재 메타데이터 중심, 본문 export/parsing은 아직 본격 구현 전
- 문서 모델: Source, Document, DocumentVersion, DocumentChunk
- Mail/Document Agent 세로 슬라이스 존재
- pgvector adapter, incremental indexing, cost skip logic 존재
- SQLite smoke mode 유지 필요

**목표 문장**  
“우리 회사 매뉴얼이나 기획서에 어떤 내용이 들어있는가?”라는 질문에 대해, ParaWorks가 Google Drive/Gmail 문서 내용을 근거, 버전, 권한, 출처와 함께 정확히 찾아 답할 수 있게 한다.

**개발 플랜**

1. **문서 파서/버전 계약 고정**
    
    먼저 Track B의 핵심 계약을 작게 확정합니다.
    
    구현 대상:
    
    - DocumentParser
    - ParsedDocument
    - ParsedDocumentChunk
    - ParserRun
    - DocumentVersion 메타데이터 확장
    - Drive/Gmail attachment/source metadata 표준화
    
    필수 필드:
    
    - source_id
    - source_url
    - source_snippet
    - permission_level
    - mime_type
    - document_version
    - revision_id
    - content_signature
    - parser_name
    - parser_status
    - parser_status_reason
    - page_number 또는 section_path
    - chunk_index
    - content_hash
    
    완료 기준:
    
    - 파서 결과에 source/evidence가 없으면 chunk 생성 실패
    - restricted Drive 문서는 restricted chunk로 유지
    - 같은 content_signature는 재파싱/재임베딩 스킵 가능
2. **Google Drive 본문 export 구현**
    
    현재 Drive는 metadata-only 상태이므로 가장 큰 제품 가치가 여기서 나옵니다.
    
    우선순위:
    
    - Google Docs: files.export로 text/plain 또는 HTML export
    - Google Sheets: text/csv 또는 간단한 cell text 추출
    - Google Slides: text export 가능 범위 확인
    - PDF: 일단 metadata-only 또는 fake parser로 시작, 이후 pypdf 검토
    - DOCX: 이후 python-docx 계열 검토
    - HWP/HWPX: 결정 보류, adapter 인터페이스만 준비
    
    테스트 정책:
    
    - live Google API 호출 금지
    - fake Google client로 export payload 테스트
    - mime type별 parser status 테스트
    
    완료 기준:
    
    - Drive file metadata가 아니라 실제 본문으로 DocumentVersion과 DocumentChunk가 생성됨
    - export 불가 파일은 명확히 parser_status=unsupported 또는 metadata_only
    - 실패해도 sync 전체가 죽지 않고 parser run에 이유가 남음
3. **Gmail 본문/첨부 경계 강화**
    
    Gmail 본문 추출은 이미 일부 있으므로, 여기서는 “문서 파이프라인으로 들어갈 만한 메일/첨부”를 정리합니다.
    
    구현 대상:
    
    - Gmail multipart body 품질 개선
    - thread-level metadata 보존
    - 첨부 metadata 수집
    - 첨부 본문 파싱은 Drive parser와 같은 인터페이스 재사용
    - 외부 도메인, 발신자/수신자, thread context metadata 유지
    
    완료 기준:
    
    - 메일 본문 chunk가 gmail:{message_id} evidence를 보존
    - 첨부가 있으면 gmail_attachment:{message_id}:{attachment_id} 같은 안정적 source id 사용
    - 외부 참여자가 있는 메일은 metadata에 남고 권한 확장 없음
4. **Chunking 품질 개선**
    
    RAG 정확도는 결국 chunk 품질에서 갈립니다. 단순 길이 자르기보다 문서 구조를 보존합니다.
    
    정책:
    
    - 제목/섹션/페이지/문단 단위 우선
    - chunk text는 검색에 충분히 길게, evidence snippet은 짧게
    - chunk metadata에 section_path, page_number, heading, parser_name, revision_id 저장
    - 너무 긴 문서는 deterministic windowing
    - 중복 chunk는 content hash로 제거
    
    완료 기준:
    
    - “휴가 정책”, “비용 정산”, “프로젝트 일정” 같은 질문이 관련 chunk를 안정적으로 찾음
    - chunk마다 출처 링크와 snippet이 있음
    - 문서 버전이 바뀌면 바뀐 chunk만 재색인 가능
5. **pgvector 인덱싱 연결 강화**
    
    pgvector와 incremental indexing은 이미 있으므로, Track B는 문서 메타데이터 품질과 skip 정확도를 책임집니다.
    
    구현 대상:
    
    - build_rag_index_documents가 문서 parser metadata를 vector metadata에 포함
    - document_id를 안정적으로 설계  
        예: chunk:{document_id}:{version}:{chunk_index}
    - content_hash가 text, source, permission, parser metadata를 반영
    - reindex 결과에 문서 기준 통계 추가
    
    응답/로그에 보여줄 것:
    
    - indexed_count
    - skipped_count
    - saved_embedding_calls
    - parser_status_counts
    - changed_document_count
    - unsupported_document_count
    
    완료 기준:
    
    - 같은 문서 재동기화 시 embedding call이 발생하지 않음
    - 버전이 바뀐 문서만 재색인됨
    - SQLite smoke는 deterministic search 유지
    - pgvector search는 feature flag 뒤에서만 동작
6. **문서 버전 관리**
    
    “기획서에 어떤 내용이 들어있는가?” 다음 질문은 보통 “언제 바뀌었나?”입니다. 버전 추적을 Track B의 강점으로 잡습니다.
    
    구현 대상:
    
    - Drive version, headRevisionId, modifiedTime 기반 DocumentVersion 생성/갱신
    - content_signature 비교로 unchanged skip
    - 이전 버전과 현재 버전의 chunk count, hash 변화 기록
    - parser run 기록으로 “왜 본문이 비어 있는지” 설명 가능하게 만들기
    
    MVP 범위:
    
    - full diff UI는 나중
    - backend metadata와 테스트 먼저
    - 문서별 최신 버전, revision id, parser status를 API에서 확인 가능하게
7. **Mail/Document Agent 개선**
    
    기존 Mail/Document Agent는 review candidate 생성 쪽이므로, 문서 파이프라인이 안정된 뒤 붙입니다.
    
    개선 방향:
    
    - Drive/Gmail chunk만 evidence packet으로 사용
    - source-less output 금지
    - 문서 기반 history/decision/todo candidate 생성
    - low confidence일 때 uncertainty reason 필수
    - cost metadata 유지
    - parser status가 metadata-only인 문서는 “본문 근거 부족”으로 낮은 confidence 처리
    
    완료 기준:
    
    - Drive 문서 본문에서 Review Queue item 생성
    - source link/snippet/permission/confidence가 리뷰 UI에 보존
    - LLM 없이 deterministic test로 검증 가능
8. **테스트 순서**
    
    이 순서로 TDD를 추천합니다.
    
    1. Drive export payload를 SourceEvent/document parse input으로 변환하는 테스트
    2. mime type별 parser status 테스트
    3. DocumentVersion이 revision 변경 시 새 버전을 만드는 테스트
    4. 동일 content signature는 재파싱/재색인 skip하는 테스트
    5. restricted 문서가 restricted chunk/vector metadata로 유지되는 테스트
    6. pgvector reindex가 changed chunk만 embedding하는 테스트
    7. Mail/Document Agent가 Gmail/Drive evidence만 Review Queue로 보내는 테스트
    8. /api/v1/ask 또는 /api/v1/search가 문서 chunk를 근거로 찾는 smoke 테스트
9. **작업 브랜치 제안**
    
    Track B 단독 브랜치:
    
    `/agent_docs`
    
    세부 PR 또는 커밋 단위:
    
    `feat: add document parser contracts feat: export google drive document content feat: track document parser runs and versions feat: chunk parsed documents for rag feat: enrich vector documents with parser metadata feat: improve mail document agent evidence quality`
    

10. **데모 시나리오**
    

최종 데모는 이렇게 잡으면 좋습니다.

1. Google Drive mock 또는 fake live sync 실행
2. “사내 휴가 매뉴얼” 문서가 파싱됨
3. parser status, revision id, chunk count 표시
4. RAG reindex dry-run에서 changed/skipped/saved calls 확인
5. 질문: “우리 회사 휴가 신청 절차는?”
6. 답변이 문서 chunk, source link, snippet, permission과 함께 반환
7. 문서 revision 변경 후 재동기화
8. 변경된 chunk만 재색인되는 것 확인

**첫 번째 구현 추천**  
가장 먼저 할 일은 DocumentParser 계약과 Drive Google Docs text export 테스트입니다. 이게 잡히면 이후 PDF/DOCX/HWPX, Gmail attachment, pgvector indexing이 전부 같은 파이프라인 위에 얹힙니다.
