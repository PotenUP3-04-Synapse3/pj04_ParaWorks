# Document Agent Portfolio Log

Last updated: 2026-05-10

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
