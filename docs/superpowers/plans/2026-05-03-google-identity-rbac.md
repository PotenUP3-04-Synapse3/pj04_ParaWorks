# Google Identity Login and RBAC Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the demo-only login experience with Google identity login, seeded ParaWorks users, RBAC guards, admin user management, and role-aware Review Queue approvals.

**Architecture:** Keep `AuthUser` as the ParaWorks identity source of truth. Google login verifies an email and maps it to an existing active user, then issues the existing httpOnly session and refresh cookies. Role checks live in reusable backend dependencies, while the frontend hides unavailable navigation and shows clear forbidden states.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic settings, httpOnly cookies, Google OAuth/OpenID Connect, Next.js App Router, TypeScript, Tailwind, pytest, Playwright later.

---

### Task 1: Seed Users and RBAC Helpers

**Files:**
- Modify: `backend/app/core/demo_auth.py`
- Create: `backend/app/core/rbac.py`
- Modify: `backend/app/core/session_auth.py`
- Test: `backend/tests/test_auth_api.py`

- [ ] **Step 1: Write failing tests**

Add tests that assert:

```python
def test_login_options_include_requested_google_seed_accounts(client) -> None:
    response = client.get('/api/v1/auth/login-options')
    assert response.status_code == 200
    emails = {user['email']: user for user in response.json()['users']}
    assert emails['hanvv3@gmail.com']['role'] == 'admin'
    assert 'restricted' in emails['hanvv3@gmail.com']['permission_levels']
    assert emails['hanvv3@koreacu.ac.kr']['role'] == 'employee'


def test_login_accepts_requested_admin_google_seed_account(client) -> None:
    response = client.post('/api/v1/auth/login', json={'email': 'hanvv3@gmail.com'})
    assert response.status_code == 200
    assert response.json()['user']['role'] == 'admin'


def test_login_accepts_requested_employee_google_seed_account(client) -> None:
    response = client.post('/api/v1/auth/login', json={'email': 'hanvv3@koreacu.ac.kr'})
    assert response.status_code == 200
    assert response.json()['user']['role'] == 'employee'
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
$env:PARAWORKS_DEMO_MODE='true'; .\.venv\Scripts\python.exe -m pytest backend\tests\test_auth_api.py -q
```

Expected: tests fail because the requested seed accounts are not present.

- [ ] **Step 3: Implement seeds and helpers**

Update `USERS` to include:

```python
'hanvv-admin': DemoUser(
    'google-hanvv-admin',
    'hanvv3@gmail.com',
    'admin',
    {'public', 'internal', 'restricted'},
    'Hanvv Admin',
    'Workspace Administrator',
    'Platform',
),
'hanvv-employee': DemoUser(
    'google-hanvv-employee',
    'hanvv3@koreacu.ac.kr',
    'employee',
    {'public', 'internal'},
    'Hanvv Employee',
    'AI Agent Developer',
    'Engineering',
),
```

Create `backend/app/core/rbac.py` with role order, permission helpers, and reusable role checks.

- [ ] **Step 4: Verify tests pass**

Run the same auth test command and expect all tests in `test_auth_api.py` to pass.

### Task 2: Google Identity Login Backend

**Files:**
- Create: `backend/app/auth/google_identity.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/api/v1/auth.py`
- Test: `backend/tests/test_google_identity_auth.py`

- [ ] **Step 1: Write failing tests**

Test login URL contains identity scopes and account picker:

```python
def test_google_identity_login_url_uses_identity_scopes_and_account_picker(client) -> None:
    response = client.get('/api/v1/auth/google/login-url')
    assert response.status_code == 200
    payload = response.json()
    assert payload['configured'] is True
    assert 'openid' in payload['required_scopes']
    assert 'prompt=select_account' in payload['login_url']
```

Test callback accepts a seeded user through injected access payload:

```python
def test_google_identity_callback_accepts_seeded_admin_user(client) -> None:
    # Implement by directly testing the service with GoogleIdentityAccess,
    # not by making a real Google network call.
```

Test unknown email is rejected.

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
$env:PARAWORKS_DEMO_MODE='true'; .\.venv\Scripts\python.exe -m pytest backend\tests\test_google_identity_auth.py -q
```

Expected: module or endpoint is missing.

- [ ] **Step 3: Implement Google identity service**

Create a login-specific state signer and client. Reuse the existing Google OAuth implementation style, but keep connector scopes out of the login flow.

Environment defaults:

```python
google_identity_redirect_uri: str = 'http://localhost:3000/login/google/callback'
google_identity_state_secret: str = 'local-development-google-identity-state-secret'
```

Login URL response shape:

```python
{
    'configured': True,
    'login_url': 'https://accounts.google.com/o/oauth2/v2/auth?...',
    'state': 'signed-state',
    'required_scopes': ['openid', 'email', 'profile'],
}
```

- [ ] **Step 4: Add auth API endpoints**

Add:

```python
@router.get('/google/login-url')
def get_google_login_url(settings: Settings = Depends(get_settings)) -> dict: ...

@router.get('/google/callback')
def google_login_callback(code: str, state: str, response: Response, db: DbSession) -> dict: ...
```

The callback issues cookies and returns `{'user': serialize_auth_user(auth_user)}`.

- [ ] **Step 5: Verify targeted tests pass**

Run the new Google identity auth tests.

### Task 3: Backend API Guards and Admin User Management

**Files:**
- Modify: `backend/app/api/v1/admin.py`
- Modify: `backend/app/api/v1/auth.py`
- Create: `backend/schemas/admin.py` if needed
- Test: `backend/tests/test_admin_users.py`

- [ ] **Step 1: Write failing tests**

Tests:

```python
def test_employee_cannot_patch_user_role(client) -> None:
    response = client.patch('/api/v1/admin/users/google-hanvv-employee', headers={'X-Demo-User': 'viewer'}, json={'role': 'reviewer'})
    assert response.status_code == 403


def test_admin_can_patch_user_role_and_audit_log_is_created(client) -> None:
    response = client.patch('/api/v1/admin/users/google-hanvv-employee', headers={'X-Demo-User': 'hanvv-admin'}, json={'role': 'reviewer'})
    assert response.status_code == 200
    assert response.json()['user']['role'] == 'reviewer'
    audit_response = client.get('/api/v1/admin/audit-logs', headers={'X-Demo-User': 'hanvv-admin'})
    assert any(log['action'] == 'admin.user.update' for log in audit_response.json()['logs'])
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
$env:PARAWORKS_DEMO_MODE='true'; .\.venv\Scripts\python.exe -m pytest backend\tests\test_admin_users.py -q
```

- [ ] **Step 3: Implement admin APIs**

Add:

- `GET /api/v1/admin/users`
- `PATCH /api/v1/admin/users/{external_id}`

Allowed fields:

- `role`
- `status`
- `department`
- `title`
- `permission_levels`

Record audit metadata with previous and next values.

- [ ] **Step 4: Verify tests pass**

Run admin tests.

### Task 4: Review Queue Role Checks

**Files:**
- Modify: `backend/app/api/v1/review.py`
- Test: `backend/tests/test_review_rbac.py`

- [ ] **Step 1: Write failing tests**

Tests:

```python
def test_employee_cannot_approve_review_item(client, db_session) -> None:
    # Insert pending internal ReviewItem with evidence.
    response = client.post(f'/api/v1/review/{item.id}/approve', headers={'X-Demo-User': 'viewer'})
    assert response.status_code == 403


def test_reviewer_can_approve_internal_review_item(client, db_session) -> None:
    response = client.post(f'/api/v1/review/{item.id}/approve', headers={'X-Demo-User': 'mina@paraworks.com'})
    assert response.status_code == 200


def test_reviewer_cannot_approve_restricted_review_item(client, db_session) -> None:
    response = client.post(f'/api/v1/review/{item.id}/approve', headers={'X-Demo-User': 'mina@paraworks.com'})
    assert response.status_code == 403
```

- [ ] **Step 2: Implement permission checks**

Before approval:

```python
ensure_can_review_permission(user, item.permission_level)
```

Rules:

- `reviewer`: public/internal
- `manager`: public/internal/restricted for this MVP
- `admin`: all

- [ ] **Step 3: Verify review RBAC tests pass**

Run:

```powershell
$env:PARAWORKS_DEMO_MODE='true'; .\.venv\Scripts\python.exe -m pytest backend\tests\test_review_rbac.py -q
```

### Task 5: Frontend Login and Route Guards

**Files:**
- Modify: `frontend/src/lib/api/types.ts`
- Modify: `frontend/src/app/login/page.tsx`
- Modify: `frontend/src/components/layout/AppShell.tsx`
- Create: `frontend/src/app/login/google/callback/page.tsx`
- Test: existing lint/build, Playwright later.

- [ ] **Step 1: Add user-aware frontend types**

Ensure user type supports:

```ts
role: "employee" | "reviewer" | "manager" | "admin" | string;
status?: string;
permission_levels: string[];
```

- [ ] **Step 2: Update login page**

Primary action:

- fetch `/api/v1/auth/google/login-url`;
- show Google login button when configured;
- keep demo selector under a "Demo accounts" section only when options are returned.

- [ ] **Step 3: Add Google callback page**

The page reads `code`, `state`, calls `/api/v1/auth/google/callback`, then redirects to `/dashboard`.

- [ ] **Step 4: Add navigation filtering**

Fetch `/api/v1/auth/me` in `AppShell`.

Hide:

- `/admin` unless role is `admin`;
- `/review` unless role is `reviewer`, `manager`, or `admin`.

Keep `/login` visible.

- [ ] **Step 5: Verify frontend**

Run:

```powershell
cd frontend
npm.cmd run lint
npm.cmd run build
```

### Task 6: Documentation and Final Verification

**Files:**
- Modify: `plan.md`
- Modify: `docs/portfolio-log.md`
- Modify: `docs/superpowers/runbooks/session-handoff.md`

- [ ] **Step 1: Document the completed auth/RBAC slice**

Record:

- Google identity login boundary;
- seeded accounts;
- RBAC page/API restrictions;
- Review Queue approval role rules;
- no paid LLM calls.

- [ ] **Step 2: Run full verification**

Run:

```powershell
$env:PARAWORKS_DEMO_MODE='true'; .\.venv\Scripts\python.exe -m pytest backend\tests -q
cd frontend
npm.cmd run lint
npm.cmd run build
```

- [ ] **Step 3: Commit**

Commit message:

```bash
git commit -m "feat: add google identity rbac"
```

