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
