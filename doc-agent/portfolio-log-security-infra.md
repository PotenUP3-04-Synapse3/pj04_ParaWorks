# ParaWorks Security and Infrastructure Portfolio Log

Last updated: 2026-05-11

This file records security hardening, infrastructure setup, and backend operational milestones for the ParaWorks project.

## Security Hardening

### Auth Hardening: CSRF and Rate Limiting

Recorded on 2026-05-11.

Implemented production-ready security layers for authentication and API protection.

- **CSRF Protection**: Added global CSRF validation middleware in `backend/app/core/session_auth.py`. 
  - Uses `httpOnly` cookies for token storage and requires `X-CSRF-Token` header for state-changing requests.
  - Applied as a global dependency to all `api/v1` routes.
- **Rate Limiting**: Implemented an IP-based rate limiter in `backend/app/core/rate_limit.py`.
  - Specifically protects `/login` and `/refresh` endpoints to prevent brute-force attacks.
  - Currently uses in-memory storage (prepared for Redis migration).

Portfolio angle:

- Shows commitment to production security standards beyond simple MVP functionality.
- Demonstrates knowledge of session security (CSRF) and infrastructure protection (Rate limiting).

Verification:

- Backend security suite with 12 test cases covering token validation and limit triggers passed.
- Manual verification of 429 Too Many Requests response on throttled auth attempts.

### RBAC: Role-Based Access Control

Recorded on 2026-05-11.

Established a multi-tier permission system to ensure "Equal Agent Ownership" and permission-aware RAG.

- **Role Hierarchy**: Defined `employee`, `reviewer`, `manager`, and `admin` roles in `backend/app/core/rbac.py`.
- **Permission Levels**: Implemented `public`, `internal`, and `restricted` visibility levels for all company memory evidence.
- **Access Guards**: Added `require_role_at_least` and `ensure_can_review_permission` helpers to protect sensitive operational paths (Review Queue, Admin APIs).

Portfolio angle:

- Demonstrates enterprise-ready access control architecture.
- Ensures that agents never broaden the visibility of restricted source material.

### Sensitive Data Redaction

Recorded on 2026-05-11.

Implemented an automated redaction layer to protect secrets and PII from being leaked into logs or LLM prompts.

- **Pattern-Based Redaction**: Added `backend/app/core/redaction.py` to mask Slack tokens (`xoxb-`), OAuth secrets, and refresh tokens using regex.
- **Global Safety**: Used across connectors and logging to ensure no raw secrets are stored or transmitted.

Portfolio angle:

- Shows attention to data privacy and security compliance in LLM applications.

## Infrastructure and Tooling

### PowerShell Execution Policy Resolution

Recorded on 2026-05-11.

Resolved environment-specific restrictions preventing the execution of project scripts on Windows.

- **Execution Policy Bypass**: Added a runbook entry and logic to bypass restricted PowerShell execution policies for the smoke test script (`scripts/start-smoke.ps1`).
- Ensures seamless onboarding and demo execution for developers and stakeholders in restricted Windows environments.

Portfolio angle:

- Shows practical troubleshooting for environment friction and developer experience (DX).
- Ensures reliability of the "Smoke Mode" demo path.

Verification:

- Successfully initiated `start-smoke.ps1` on a restricted Windows shell without `PSSecurityException`.
