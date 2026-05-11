# Document Agent Portfolio Log

Last updated: 2026-05-11

This file records Document Agent specific product, architecture, verification,
and demo evidence.

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

Portfolio angle:

- Makes parser quality auditable instead of leaving it only inside chunk
  metadata.
- Prepares the Document Agent track for future PDF, DOCX, Slides, and HWP/HWPX
  parser adapters while preserving evidence and permission provenance.

Verification:

```powershell
uv run pytest backend/tests/test_connector_ingestion_contract.py backend/tests/test_models.py -q
```

Result: 10 passed.

```powershell
uv run ruff check backend/app/models/source.py backend/app/models/__init__.py backend/app/ingestion/service.py backend/tests/test_connector_ingestion_contract.py
```

Result: all checks passed after one automatic formatting fix.

```powershell
uv run pytest backend/tests -q
```

Result: 253 passed, 1 skipped.
