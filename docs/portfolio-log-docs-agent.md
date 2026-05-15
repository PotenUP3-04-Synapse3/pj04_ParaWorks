# Document Agent Portfolio Log

Last updated: 2026-05-15

## Google Calendar All-Calendars Operating MVP

Recorded on 2026-05-15.

- Expanded the Mail/Document Agent operating scope to Mail/Docs/Calendar
  without creating a separate Calendar Agent.
- Changed Google Calendar sync from `primary` only to all accessible calendars
  through `calendarList`, with bounded initial collection and per-calendar
  `updatedMin` delta cursors.
- Made Calendar source ids collision-safe with
  `calendar:{calendar_id}:{event_id}` and preserved calendar/event metadata
  through Source, DocumentChunk, AgentRun evidence summary, ReviewItem payload,
  Review source evidence, and Project/Timeline display timing.
- Added Calendar candidate behavior: confirmed meetings and milestones become
  `timeline_event`, preparation/deadline/follow-up events become `todo`, and
  personal/low-signal events produce no ReviewItem.
- Kept the existing Review Queue trust boundary: Calendar output remains a
  pending ReviewItem until approved, and approved source ids continue to gate
  RAG indexing.

Verification:

```powershell
uv run pytest backend/tests/test_google_connector.py backend/tests/test_connector_golden_dataset.py backend/tests/test_mail_document_agent.py backend/tests/test_mail_document_agent_review_bridge.py backend/tests/test_mail_document_agent_api.py backend/tests/test_review.py backend/tests/test_review_knowledge_promotion.py backend/tests/test_project_memory_api.py backend/tests/test_rag_indexing.py -q
uv run ruff check backend/app/connectors/google.py backend/app/agents/mail_document_agent/agent.py backend/app/agents/mail_document_agent/llm.py backend/app/agents/mail_document_agent/service.py backend/app/agent_runtime/evidence_summary.py backend/app/api/v1/review.py backend/app/projects/service.py
cd frontend
npm.cmd run lint
npm.cmd run build
```

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

## Mail/Document Agent LLM Review Queue Quality

Recorded on 2026-05-14.

- Changed the shared agent LLM default model to `gpt-5.4-mini` and aligned
  Mail/Document LLM preflight metadata with that default.
- Hardened Mail/Document LLM output parsing so string `"false"` does not become
  business-related truth, and LLM `structured_data` cannot overwrite reserved
  ReviewItem fields such as title, summary, source ids, AgentRun id, or cost.
- Upgraded Mail/Document ReviewItems to preserve action-oriented payload fields
  such as `business_context`, `task_summary`, `recommended_next_step`,
  `assignee`, `due_date`, `counterparty`, `source_subject`, and
  `summary_quality`.
- Changed Mail/Docs paid LLM review generation to create source-grouped
  ReviewItems: Gmail with attachments stays grouped, while Drive and Calendar
  evidence stays source-local.
- Improved Review Queue approval so the API returns promotion results with
  created knowledge record ids, created timeline ids, project key, and next
  routes. The frontend now surfaces a post-approval navigation CTA.
- Updated the Review Queue frontend to show Mail/Docs 업무 판단 before the raw
  summary and keep original mail/document text inside source evidence.
- Strengthened permission filtering so both Source and DocumentChunk permission
  levels must be allowed before evidence enters the Mail/Docs agent.

Verification:

```powershell
uv run pytest backend/tests/test_mail_document_agent.py backend/tests/test_mail_document_agent_review_bridge.py backend/tests/test_mail_document_agent_api.py backend/tests/test_review.py backend/tests/test_review_knowledge_promotion.py backend/tests/test_project_memory_api.py -q
uv run ruff check backend/app/agents/mail_document_agent backend/app/agents/slack_agent/llm.py backend/app/api/v1/integrations.py backend/app/api/v1/review.py backend/app/knowledge/promotion.py backend/app/core/config.py
cd frontend
npm.cmd exec tsc -- --noEmit
npm.cmd run build
```

Result: backend targeted suite passed with 51 tests, ruff passed, TypeScript
check passed, and frontend production build passed.

## Google Connector and Ingestion Foundation

### Google Web API Client and Multi-Source Sync

Recorded on 2026-05-11.

Implemented a unified Google connector supporting Gmail, Drive, and Calendar.

- **Unified Client**: Built `GoogleWebApiClient` in `backend/app/connectors/google.py` with support for OAuth, retries, and pagination across multiple Google services.
- **Gmail Sync**: Implemented message and thread extraction with automatic text/plain and text/html body parsing and participant domain analysis.
- **Calendar Sync**: Added calendar event ingestion with attendee status tracking and duration calculation.
- **Incremental Sync Service**: Implemented `sync_connector_events` in `backend/app/ingestion/sync.py` with cursor-based partitioning and content-signature deduplication.

Portfolio angle:

- Shows the ability to build complex, reliable integrations with major SaaS providers.
- Establishes the "Evidence-First" ingestion pipeline used by all downstream agents.

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

## Gmail Attachment Ingestion Smoke

Recorded on 2026-05-11.

- Strengthened the local Gmail mock sync so it now includes a
  `gmail_attachment` source event alongside the parent Gmail body event.
- Kept the attachment boundary metadata-only: PDF attachment bodies are not
  downloaded or parsed, and the event records
  `parser_name="gmail_attachment_metadata"`,
  `parser_status="metadata_only"`, and
  `parser_status_reason="pdf_parser_not_enabled"`.
- Added API-level smoke coverage proving `POST /api/v1/integrations/gmail/sync`
  persists the attachment as `Source`, `DocumentChunk`, and
  `DocumentParserRun` records with parent source id, participants, MIME type,
  content signature, parser status, document version, and revision id.
- Verified the sync response reports `parser_status_counts` for attachment
  metadata, making the demo path show parsed vs metadata-only evidence quality.

Portfolio angle:

- Makes the existing Gmail attachment boundary visible in the normal SQLite
  smoke workflow instead of only in connector unit tests.
- Shows that attachment evidence enters the same versioned document ingestion,
  parser audit, Review Queue, and Mail/Document Agent evidence pipeline without
  live Gmail API calls or paid parsing.

Verification:

```powershell
uv run pytest backend/tests/test_mock_connectors.py backend/tests/test_mail_document_agent_api.py -q
```

Result: 8 passed.

```powershell
uv run ruff check backend/app/connectors/mock.py backend/app/seeds/mock_sources.py backend/tests/test_mock_connectors.py backend/tests/test_mail_document_agent_api.py
```

Result: all checks passed.

```powershell
uv run pytest backend/tests/test_mock_connectors.py backend/tests/test_mail_document_agent_api.py backend/tests/test_connector_ingestion_contract.py backend/tests/test_document_ingestion_service.py backend/tests/test_mail_document_agent_review_bridge.py backend/tests/test_rag_indexing.py -q
```

Result: 49 passed.

## Parser Quality UI Visibility

Recorded on 2026-05-11.

- Added frontend `parser_status_counts` typing for connector sync and RAG
  reindex responses.
- Integrations sync results now show a Parser quality breakdown when a
  connector reports parsed, metadata-only, or unsupported source counts.
- RAG reindex dry-run preview now shows parser quality counts next to the
  embedding budget estimate, so operators can see whether indexed evidence is
  body-parsed or metadata-only before approving a write job.
- Added Playwright coverage for Gmail parser quality sync results and RAG
  parser quality preview rendering.

Portfolio angle:

- Moves parser quality from backend-only metadata into visible operator UX.
- Helps demonstrate that attachment and document evidence can be reviewable
  without overstating unsupported or metadata-only files as fully parsed
  company knowledge.

Verification:

```powershell
npm.cmd exec tsc -- --noEmit
```

Result: passed.

```powershell
npm.cmd run build
```

Result: passed.

## Document Golden Dataset Expansion

Recorded on 2026-05-11.

- Expanded connector golden payloads to cover three distinct Google Drive file types:
  - Google Docs (pplication/vnd.google-apps.document) with a mocked text export, successfully reporting \parser_status=\parsed\.
  - Google Sheets (pplication/vnd.google-apps.spreadsheet), demonstrating \parser_status=\metadata_only\.
  - HWP (pplication/haansofthwp), demonstrating \parser_status=\unsupported\.
- Updated GoldenGoogleClient to simulate \drive_file_text_export\ when testing textual body exports from Google Drive.
- Adjusted \_google_event\ helpers to expect a collection of events correctly matching test fixtures.

Portfolio angle:

- Demonstrates robust end-to-end evidence parsing scenarios from raw Connector JSON into robust parser boundaries without risking false positives.
- Provides immediate regression coverage against Google Drive MIME mapping decisions explicitly added in prior checkpoints.

Verification:

\\\powershell
uv run pytest backend/tests/test_connector_golden_dataset.py -q
\\\

Result: 1 passed.

\\\powershell
uv run pytest backend/tests -q
\\\

Result: all passed, 1 skipped.

