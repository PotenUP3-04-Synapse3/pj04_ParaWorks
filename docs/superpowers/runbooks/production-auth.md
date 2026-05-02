# ParaWorks Production Auth Plan

Updated: 2026-05-02

## Current State

ParaWorks currently uses demo authentication:

- Frontend stores the selected demo user id in localStorage.
- API requests send `X-Demo-User`.
- Backend maps the header to static demo users in `backend/app/core/demo_auth.py`.
- Admin and employee permissions are already modeled at the demo-user level.

This is useful for MVP demos, but it must not be used as production auth.

## Target Architecture

Production auth should use:

- short-lived access session stored in an httpOnly, Secure, SameSite cookie;
- rotating refresh token stored server-side as a hashed token record;
- explicit logout that revokes the refresh token family;
- RBAC derived from ParaWorks user/team membership, not client-supplied headers;
- connector permissions enforced separately from ParaWorks app permissions;
- audit logs for login, refresh, logout, failed login, and admin role changes.

Recommended cookie policy:

- `paraworks_session`: httpOnly, Secure, SameSite=Lax, short TTL.
- `paraworks_refresh`: httpOnly, Secure, SameSite=Strict or Lax depending on deployment domain, longer TTL with rotation.

For local development, Secure can be disabled only behind an explicit
development setting.

## Backend Changes

Add persistent auth tables:

- `users`
  - id
  - email
  - display_name
  - role
  - department
  - status
  - created_at
  - updated_at
- `refresh_tokens`
  - id
  - user_id
  - token_hash
  - family_id
  - expires_at
  - revoked_at
  - replaced_by_token_id
  - created_at
  - last_used_at
- `user_permissions`
  - user_id
  - permission_level

Add or evolve auth endpoints:

- `POST /api/v1/auth/login`
  - verifies credential or OAuth identity;
  - sets session and refresh cookies;
  - returns serialized user only.
- `POST /api/v1/auth/refresh`
  - validates refresh cookie;
  - rotates refresh token;
  - sets new cookies.
- `POST /api/v1/auth/logout`
  - revokes refresh token family;
  - clears cookies.
- `GET /api/v1/auth/me`
  - reads server-side session cookie;
  - returns current user and permission levels.

Keep `X-Demo-User` support only when `PARAWORKS_DEMO_MODE=true`.

## Frontend Changes

- Remove localStorage as the authority for the current user.
- Use `credentials: "include"` on API requests.
- Read current identity from `/api/v1/auth/me`.
- Login page should submit credentials or initiate OAuth, then rely on cookies.
- Admin UI should show role and permission data from the backend session.
- Global search, Review Queue, RAG, and connector actions must not accept
  client-supplied user ids.

## Security Guardrails

- Never store access or refresh tokens in localStorage.
- Hash refresh tokens before storage.
- Rotate refresh tokens on every refresh.
- Detect refresh token reuse and revoke the token family.
- Apply CSRF protection for cookie-authenticated unsafe methods.
- Use audit logs for auth-sensitive actions.
- Rate-limit login and refresh endpoints.
- Fail closed if the session is missing or expired.

## Permission Model

Production authorization must combine:

1. ParaWorks RBAC:
   - admin
   - manager/reviewer
   - employee
2. ParaWorks knowledge permissions:
   - public
   - internal
   - restricted
3. Source-system permissions:
   - Slack channel membership
   - Gmail mailbox ownership/delegation
   - Drive ACLs
   - Calendar visibility

Restricted source evidence must not become broader approved knowledge unless a
reviewer with sufficient permission explicitly approves that boundary.

## Migration Order

1. Add database models and migrations while keeping demo auth enabled.
2. Introduce cookie session middleware/dependency beside `get_demo_user`.
3. Add `PARAWORKS_DEMO_MODE` branch:
   - demo mode: keep `X-Demo-User`;
   - production mode: require cookie session.
4. Update frontend API client to support `credentials: "include"`.
5. Convert login page to cookie-based login.
6. Add auth audit logs and admin role-management checks.
7. Add Playwright coverage:
   - unauthenticated redirect;
   - admin login;
   - employee restricted-content denial;
   - logout clears access.
8. Disable demo auth in deployment config.

## Cost Note

Auth should never trigger LLM calls, embedding calls, connector sync, or RAG
reindexing. User identity checks must be cheap database/session lookups.
