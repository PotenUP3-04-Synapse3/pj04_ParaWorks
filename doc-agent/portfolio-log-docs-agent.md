# Document Agent Portfolio Log

## 2026-05-14 Drive/Gmail Review Ingestion Fix

- Google Drive sync now reflects each changed Drive file as its own
  Mail/Document Agent Review Queue candidate, instead of collapsing all changed
  files into one broad candidate.
- Gmail sync keeps email bodies and changed attachments grouped by parent email,
  preserving context while avoiding unrelated email mixing.
- Live Gmail collection now applies a business-focused search query:
  `newer_than:90d -in:spam -in:trash -category:social -category:promotions -category:forums`.
  Delta sync combines the same exclusions with the latest `after:<cursor>`
  constraint.
- Gmail SourceEvents now include explicit `content_signature` metadata, giving
  ingestion a stable dedupe/update signal.
- Verification:

```powershell
uv run pytest backend/tests/test_mail_document_agent_api.py backend/tests/test_mail_document_agent_review_bridge.py backend/tests/test_google_connector.py backend/tests/test_connector_ingestion_contract.py backend/tests/test_connector_factory.py backend/tests/test_integration_runtime_status.py -q
uv run ruff check backend/app/agents/mail_document_agent/service.py backend/app/agents/mail_document_agent/__init__.py backend/app/api/v1/integrations.py backend/app/connectors/google.py backend/tests/test_mail_document_agent_api.py backend/tests/test_google_connector.py
```

Result: 63 targeted backend tests passed; ruff passed.
