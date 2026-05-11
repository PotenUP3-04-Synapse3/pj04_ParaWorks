# Document Agent Portfolio Log

Last updated: 2026-05-11

This file records Document Agent specific product, architecture, verification,
and demo evidence. Do not store Document Agent progress entries in
`docs/portfolio-log.md`.

## Working Rules

- `doc-agent/` is the owned asset folder for the Document Agent track, not a
  temporary scratch folder.
- Document Agent plans, logs, evaluation sets, prompts, demo assets, and design
  notes belong under `./doc-agent/`.
- Real ParaWorks runtime code and tests belong in the existing project
  structure, such as `backend/app/...` and `backend/tests/...`.
- Existing ParaWorks runtime, connector, model, API, or test files should be
  modified in place when the Document Agent work needs to integrate with them.
- Document Agent portfolio and project records belong in this file.
- Target git branch: `/agent_docs`.

## Document Parser Contract and Google Docs Export

Recorded on 2026-05-10.

- Added a small document parsing contract for `DocumentParser`,
  `ParsedDocument`, `ParsedDocumentChunk`, and `ParserRun`.
- Enforced evidence-first parsed chunks: chunks require source id, source URL,
  snippet, permission, version, revision, parser status, and content signature
  metadata.
- Extended the Google Drive connector so Google Docs files can be exported as
  `text/plain` through a fakeable client boundary, while preserving restricted
  permissions and parser provenance.

Portfolio angle:

- Turns Drive from metadata-only sync toward evidence-backed document RAG.
- Establishes the Track B contract that future PDF, DOCX, HWPX, and Gmail
  attachment parsers can share without calling live provider APIs in tests.

Verification:

```powershell
uv run pytest backend/tests/test_document_parser_contracts.py backend/tests/test_google_connector.py backend/tests/test_connector_golden_dataset.py backend/tests/test_connector_ingestion_contract.py -q
```

Result: 25 passed.

```powershell
uv run pytest backend/tests -q
```

Result: 256 passed, 1 skipped.

```powershell
uv run ruff check backend/app/documents backend/app/connectors/google.py backend/tests/test_document_parser_contracts.py backend/tests/test_google_connector.py
```

Result: all checks passed.

## Parsed Document Ingestion Persistence

Recorded on 2026-05-10.

- Added a document ingestion service that converts `SourceEvent` into
  `ParsedDocument` and persists it as `Document`, `DocumentVersion`, and
  `DocumentChunk`.
- Wired connector ingestion through the parsed document path so Google Docs
  export metadata reaches stored chunks.
- Preserved parser provenance on chunks, including parser name/status,
  document version, revision id, content signature, source evidence, permission
  level, participants, and deterministic chunk content hash.
- Kept existing connector ingestion behavior compatible for Slack/Gmail/mock
  sources by defaulting non-parser events to a single parsed source-event chunk.

Portfolio angle:

- Connects the new parser contract to the real ParaWorks storage path instead
  of leaving it as an isolated type definition.
- Makes future revision-based skip logic and RAG metadata enrichment possible
  from persisted chunk metadata.

Verification:

```powershell
uv run pytest backend/tests/test_document_ingestion_service.py backend/tests/test_document_parser_contracts.py backend/tests/test_google_connector.py backend/tests/test_connector_golden_dataset.py backend/tests/test_connector_ingestion_contract.py backend/tests/test_mail_document_agent_review_bridge.py -q
```

Result: 27 passed.

```powershell
uv run pytest backend/tests -q
```

Result: 257 passed, 1 skipped.

```powershell
uv run ruff check backend/app/documents backend/app/ingestion/service.py backend/tests/test_document_ingestion_service.py backend/tests/test_document_parser_contracts.py backend/tests/test_google_connector.py
```

Result: one formatting issue fixed automatically, no remaining errors.

## Content Signature Skip and Version Updates

Recorded on 2026-05-10.

- Changed connector ingestion so an existing `source_id` is skipped only when
  the incoming `content_signature` matches the stored source metadata.
- Added changed-signature handling for Drive documents: the existing `Source`
  is updated, the existing `Document.current_version` advances, and a new
  `DocumentVersion` plus `DocumentChunk` is stored.
- Preserved cost-control behavior for duplicate source events without
  preventing new Drive revisions from entering the document pipeline.
- Verified that changed chunks get different deterministic `content_hash`
  values, which keeps downstream vector indexing incremental.

Portfolio angle:

- Demonstrates document-version awareness instead of treating Drive files as
  one-time immutable source events.
- Makes parser and embedding cost savings observable: unchanged signatures skip
  before new chunks are created, while changed signatures produce only the new
  version/chunk needed for later indexing.

Verification:

```powershell
uv run pytest backend/tests/test_document_ingestion_service.py backend/tests/test_connector_ingestion_contract.py backend/tests/test_rag_indexing.py backend/tests/test_google_connector.py backend/tests/test_mail_document_agent_review_bridge.py -q
```

Result: 50 passed.

```powershell
uv run ruff check backend/app/documents backend/app/ingestion backend/tests/test_document_ingestion_service.py backend/tests/test_connector_ingestion_contract.py
```

Result: all checks passed.

```powershell
uv run pytest backend/tests -q
```

Result: 261 passed, 1 skipped.

## RAG Vector Metadata Enrichment

Recorded on 2026-05-10.

- Updated RAG index document construction so stored document chunk parser
  metadata flows into `VectorDocument.metadata`.
- Preserved parser name/status, MIME type, document version, revision id,
  content signature, chunk content hash, section path, and page number for RAG
  serving documents.
- Added regression coverage proving restricted Drive document chunks carry
  parser/version metadata into the vector indexing boundary.

Portfolio angle:

- Keeps document provenance available after chunk storage, so future search and
  answer generation can cite not just a source URL but the parser, revision,
  and content signature that produced the indexed evidence.
- Strengthens incremental indexing because vector documents now carry the same
  parser/content identity that the ingestion path uses for skip decisions.

Verification:

```powershell
uv run pytest backend/tests/test_rag_indexing.py backend/tests/test_document_ingestion_service.py backend/tests/test_connector_ingestion_contract.py backend/tests/test_google_connector.py -q
```

Result: 50 passed.

```powershell
uv run ruff check backend/app/rag/indexing.py backend/tests/test_rag_indexing.py
```

Result: all checks passed.

```powershell
uv run pytest backend/tests -q
```

Result: 262 passed, 1 skipped.

## Drive MIME Parser Status Policy

Recorded on 2026-05-10.

- Added explicit Google Drive MIME type parser status policy.
- Google Docs still exports through `google_drive_text_export` and records
  `parser_status="parsed"`.
- Google Sheets, Slides, PDF, and DOCX now remain `metadata_only` with
  type-specific status reasons.
- HWP/HWPX MIME types now record `parser_status="unsupported"` with
  `parser_status_reason="hwp_parser_not_decided"`.
- Verified that unsupported or metadata-only Drive file types do not attempt
  Google Docs text export.

Portfolio angle:

- Prevents unsupported files from looking like successfully parsed evidence.
- Gives Review Queue, RAG, and future parser adapters a clear status contract
  for why a Drive file does or does not have body-backed evidence.

Verification:

```powershell
uv run pytest backend/tests/test_google_connector.py backend/tests/test_document_ingestion_service.py backend/tests/test_connector_ingestion_contract.py backend/tests/test_rag_indexing.py -q
```

Result: 57 passed.

```powershell
uv run ruff check backend/app/connectors/google.py backend/tests/test_google_connector.py
```

Result: all checks passed.

```powershell
uv run pytest backend/tests -q
```

Result: 269 passed, 1 skipped.

## Mail/Document Agent Parser Status Awareness

Recorded on 2026-05-11.

- Propagated document parser metadata into Mail/Document Agent
  `EvidenceMessage.metadata`.
- Updated the deterministic Mail/Document Agent model so Drive evidence with
  `parser_status != "parsed"` is treated as uncertain instead of normal
  body-backed evidence.
- Metadata-only Drive evidence now produces lower confidence and an
  uncertainty reason naming the source id, parser status, and parser reason.
- Unsupported Drive evidence receives an even lower confidence score so HWP/HWPX
  and similar files do not appear as fully supported AI evidence.

Portfolio angle:

- Connects parser quality to human review quality: Review Queue candidates can
  now show when a document candidate is based on metadata-only or unsupported
  evidence.
- Prevents the agent from overstating confidence when Drive content could not
  be body-parsed.

Verification:

```powershell
uv run pytest backend/tests/test_mail_document_agent.py backend/tests/test_mail_document_agent_review_bridge.py backend/tests/test_mail_document_agent_api.py backend/tests/test_company_memory_orchestration_service.py backend/tests/test_document_ingestion_service.py backend/tests/test_google_connector.py -q
```

Result: 37 passed.

```powershell
uv run ruff check backend/app/agents/mail_document_agent backend/tests/test_mail_document_agent.py backend/tests/test_mail_document_agent_review_bridge.py
```

Result: one formatting issue fixed automatically, no remaining errors.

```powershell
uv run pytest backend/tests -q
```

Result: 272 passed, 1 skipped.

## Parser Status Count Observability

Recorded on 2026-05-11.

- Added `parser_status_counts` to RAG reindex responses so operators can see
  how many indexed serving documents are `parsed`, `metadata_only`, or
  `unsupported`.
- Added `parser_status_counts` to connector sync results and integration sync
  API responses, with backward-compatible handling for existing test doubles.
- Recorded parser status counts in integration sync audit metadata.

Portfolio angle:

- Makes document parser quality visible in API responses instead of hiding it
  inside chunk metadata.
- Helps demos show cost and evidence quality: unchanged or unsupported files
  can be counted separately from fully parsed Google Docs evidence.

Verification:

```powershell
uv run pytest backend/tests/test_connector_ingestion_contract.py backend/tests/test_integration_runtime_status.py backend/tests/test_rag_indexing.py backend/tests/test_rag_indexing_tasks.py backend/tests/test_audit_logs.py -q
```

Result: 49 passed.

```powershell
uv run pytest backend/tests -q
```

Result: 274 passed, 1 skipped.

```powershell
uv run ruff check backend/app/rag/reindexing.py backend/app/ingestion/sync.py backend/app/api/v1/integrations.py backend/tests/test_rag_indexing.py backend/tests/test_connector_ingestion_contract.py
```

Result: all checks passed.

## ParserRun Persistence

Recorded on 2026-05-11.

- Added `DocumentParserRun` as a persisted audit table for document parser
  execution metadata.
- Connector ingestion now records one parser run for each newly persisted
  `DocumentVersion`.
- Parser runs preserve parser name, parser status, status reason, MIME type,
  document version label, revision id, content signature, chunk count, source
  URL, source id, permission level, and source snippet.
- Duplicate source events remain skipped and do not create duplicate parser
  run records.
- During merge conflict resolution, ParserRun persistence was aligned with the
  newer `backend/app/documents/service.py` persistence boundary instead of the
  older direct ingestion path.

Portfolio angle:

- Makes parser quality auditable instead of leaving it only inside chunk
  metadata.
- Prepares the Document Agent track for future PDF, DOCX, Slides, and HWP/HWPX
  parser adapters while preserving evidence and permission provenance.

Verification:

```powershell
uv run pytest backend/tests/test_connector_ingestion_contract.py backend/tests/test_document_ingestion_service.py backend/tests/test_document_parser_contracts.py -q
```

Result: 15 passed.

```powershell
uv run pytest backend/tests/test_connector_ingestion_contract.py backend/tests/test_document_ingestion_service.py backend/tests/test_document_parser_contracts.py backend/tests/test_google_connector.py backend/tests/test_mail_document_agent.py backend/tests/test_mail_document_agent_review_bridge.py backend/tests/test_rag_indexing.py -q
```

Result: 68 passed.

```powershell
uv run pytest backend/tests -q
```

Result: 275 passed, 1 skipped.

## Stable Document Chunking

Recorded on 2026-05-11.

- Added deterministic paragraph and section-aware chunking for parsed
  `SourceEvent` document bodies.
- Short heading-like paragraphs now start a new chunk section, and each stored
  `DocumentChunk` keeps a stable `chunk_index`, `section_path`, source snippet,
  permission level, parser metadata, and content hash.
- Long paragraphs are split within the configured chunk size instead of being
  stored as one oversized RAG document.
- ParserRun `chunk_count` now reflects the actual number of chunks persisted
  for the document version.

Portfolio angle:

- Improves RAG evidence quality by keeping document structure visible after
  ingestion.
- Prepares Drive Docs/Sheets and future PDF/DOCX/HWPX parsers to share the
  same versioned chunking path.

Verification:

```powershell
uv run pytest backend/tests/test_document_ingestion_service.py backend/tests/test_document_parser_contracts.py backend/tests/test_connector_ingestion_contract.py backend/tests/test_rag_indexing.py backend/tests/test_mail_document_agent_review_bridge.py -q
```

Result: 42 passed.

```powershell
uv run ruff check backend/app/documents/service.py backend/tests/test_document_ingestion_service.py
```

Result: all checks passed.

```powershell
uv run pytest backend/tests -q
```

Result: 276 passed, 1 skipped.

## PDF and DOCX Parser Adapter Decisions

Recorded on 2026-05-11.

- Added a document-layer parser adapter decision contract for MIME types that
  are not yet parsed through Google Drive export.
- PDF now records the planned candidate package as `pypdf` while staying
  `metadata_only` with `parser_status_reason="pdf_parser_not_enabled"`.
- DOCX now records the planned candidate package as `python-docx` while
  staying `metadata_only` with `parser_status_reason="docx_parser_not_enabled"`.
- HWP/HWPX remain `unsupported` with
  `parser_status_reason="hwp_parser_not_decided"`.
- Google Drive parser status fallback now uses the same document-layer
  decision contract, keeping connector metadata and parser planning aligned.

Portfolio angle:

- Documents parser roadmap decisions in code without adding new runtime
  dependencies or live parsing risk.
- Gives future PDF/DOCX parser workers a stable contract for tests, parser
  status, candidate package, and enablement state.

Verification:

```powershell
uv run pytest backend/tests/test_document_parser_contracts.py backend/tests/test_google_connector.py backend/tests/test_document_ingestion_service.py backend/tests/test_connector_ingestion_contract.py backend/tests/test_mail_document_agent.py backend/tests/test_mail_document_agent_review_bridge.py backend/tests/test_rag_indexing.py -q
```

Result: 71 passed.

```powershell
uv run ruff check backend/app/documents/parsers.py backend/app/connectors/google.py backend/tests/test_document_parser_contracts.py backend/tests/test_google_connector.py
```

Result: all checks passed.

```powershell
uv run pytest backend/tests -q
```

Result: 278 passed, 1 skipped.

## Gmail Attachment Boundary

Recorded on 2026-05-11.

- Added a Gmail attachment metadata boundary without downloading or parsing
  attachment bodies.
- Gmail messages with attachment parts now emit additional `SourceEvent`
  records using stable source ids:
  `gmail_attachment:{message_id}:{attachment_id}`.
- Attachment events preserve parent Gmail source id, message id, thread id,
  attachment id, filename, MIME type, size, parser status, document version,
  revision id, content signature, source snippet, and Gmail readonly scope.
- PDF attachments currently stay `metadata_only` through the shared parser
  adapter decision contract.
- Mail/Document Agent evidence packets now include `gmail_attachment` chunks
  alongside Gmail body and Drive evidence.

Portfolio angle:

- Makes the Gmail document boundary explicit before any live attachment
  download or paid parsing path exists.
- Gives future PDF/DOCX attachment parsers stable source ids and provenance
  metadata to plug into the existing document ingestion, Review Queue, and RAG
  paths.

Verification:

```powershell
uv run pytest backend/tests/test_google_connector.py backend/tests/test_connector_ingestion_contract.py backend/tests/test_document_ingestion_service.py backend/tests/test_mail_document_agent.py backend/tests/test_mail_document_agent_review_bridge.py backend/tests/test_rag_indexing.py -q
```

Result: 69 passed.

```powershell
uv run ruff check backend/app/connectors/google.py backend/app/agents/mail_document_agent/service.py backend/tests/test_google_connector.py backend/tests/test_mail_document_agent_review_bridge.py
```

Result: all checks passed.

```powershell
uv run pytest backend/tests -q
```

Result: 280 passed, 1 skipped.

## Google Slides Text Export

Recorded on 2026-05-11.

- Expanded the Google Drive parser coverage to include Google Slides.
- Slides files now export through Drive `files.export` using `text/plain`.
- Slides evidence is stored with `parser_name="google_drive_slides_text_export"`
  and `parser_status="parsed"` instead of remaining metadata-only.
- PDF, DOCX, HWP, and HWPX remain on explicit metadata-only or unsupported
  parser policies until their parser adapter decisions are made.

Portfolio angle:

- Broadens Track B evidence coverage from documents and spreadsheets into
  presentation decks, which commonly hold planning, proposal, and review
  decisions.
- Reuses the same fakeable Google client boundary, version metadata,
  content-signature skip behavior, and downstream chunk/RAG path.

Verification:

```powershell
uv run pytest backend/tests/test_google_connector.py backend/tests/test_document_ingestion_service.py backend/tests/test_connector_ingestion_contract.py backend/tests/test_rag_indexing.py backend/tests/test_mail_document_agent.py backend/tests/test_mail_document_agent_review_bridge.py -q
```

Result: 67 passed.

```powershell
uv run ruff check backend/app/connectors/google.py backend/tests/test_google_connector.py backend/app/documents/service.py backend/tests/test_document_ingestion_service.py
```

Result: all checks passed.

```powershell
uv run pytest backend/tests -q
```

Result: 276 passed, 1 skipped.

## Google Sheets CSV Export

Recorded on 2026-05-11.

- Added Google Sheets export through Drive `files.export` using `text/csv`.
- Google Sheets files now produce body-backed Drive `SourceEvent` records with
  `parser_name="google_drive_sheets_csv_export"` and
  `parser_status="parsed"`.
- Kept Slides/PDF/DOCX/HWP/HWPX on explicit metadata-only or unsupported
  policies, so only Google Docs and Google Sheets currently become parsed
  Drive evidence.

Portfolio angle:

- Expands the Document Agent track from prose documents into spreadsheet-backed
  company evidence such as budgets, expense tables, and planning trackers.
- Keeps the same evidence/version/content-signature path, so Sheets evidence
  benefits from the existing skip, RAG metadata, and agent confidence logic.

Verification:

```powershell
uv run pytest backend/tests/test_google_connector.py backend/tests/test_document_ingestion_service.py backend/tests/test_connector_ingestion_contract.py backend/tests/test_rag_indexing.py backend/tests/test_mail_document_agent.py backend/tests/test_mail_document_agent_review_bridge.py -q
```

Result: 65 passed.

```powershell
uv run ruff check backend/app/connectors/google.py backend/tests/test_google_connector.py
```

Result: all checks passed.

```powershell
uv run pytest backend/tests -q
```

Result: 274 passed, 1 skipped.
