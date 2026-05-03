# Google Identity Login and RBAC Design

Date: 2026-05-03

## Goal

Replace the current demo account selector with a product-like identity and
authorization model for ParaWorks.

The target behavior is:

- users sign in with Google;
- ParaWorks maps the verified Google email to an internal `AuthUser`;
- the app issues ParaWorks httpOnly session and refresh cookies;
- roles and permission levels are controlled inside ParaWorks, not inferred from
  Google scopes;
- admin-only pages and cost-sensitive workflows are protected;
- Review Queue approval becomes a role-aware workflow similar to a payment
  approval system.

Google login and Google data integrations must remain separate. Login uses
identity scopes only. Gmail, Drive, and Calendar integrations keep their own
OAuth consent flows and data scopes.

## User Seed Policy

Initial seeded users:

| Email | Role | Permission levels | Notes |
| --- | --- | --- | --- |
| `hanvv3@gmail.com` | `admin` | `public`, `internal`, `restricted` | Workspace owner/admin. |
| `hanvv3@koreacu.ac.kr` | `employee` | `public`, `internal` | Google login employee account. |
| `mina@paraworks.com` | `reviewer` | `public`, `internal` | Demo reviewer. |
| `jun@paraworks.com` | `employee` | `public`, `internal` | Demo engineer. |
| `soyeon@paraworks.com` | `employee` | `public` | Demo operations user. |

Unknown Google accounts are rejected with an "invite required" response. This is
safer for an enterprise product than auto-provisioning every Google account.

## Authentication Flow

### Google Identity Login

New login-specific endpoints:

- `GET /api/v1/auth/google/login-url`
- `GET /api/v1/auth/google/callback`

The login URL uses Google OpenID Connect identity scopes:

- `openid`
- `email`
- `profile`

The login URL should include `prompt=select_account` so a user can log out and
choose another Google account on the next login attempt.

The callback flow:

1. Validate signed login state.
2. Exchange the authorization code for tokens.
3. Read Google user info.
4. Require a verified email.
5. Look up `AuthUser` by normalized email.
6. Reject unknown or inactive users.
7. Issue ParaWorks session and refresh cookies.
8. Redirect back to the app.

### Demo Login

Demo login remains available only when `PARAWORKS_DEMO_MODE=true`.

In production-like mode:

- `/api/v1/auth/login-options` must not expose all demo users.
- `/api/v1/auth/login` must reject demo account switching.
- API access must require valid ParaWorks cookies.

## Data Model

The existing `auth_users` table remains the identity source of truth.

Required fields already present:

- `external_id`
- `email`
- `display_name`
- `role`
- `department`
- `title`
- `status`
- `permission_levels`

Recommended additions for a later migration:

- `identity_provider`: `google`, `demo`, `manual`
- `provider_subject`: Google `sub` when available
- `last_login_at`
- `manager_user_id`

The first implementation can avoid a migration by encoding Google provider
metadata through `external_id` and using the existing fields.

## Role Model

Initial roles:

- `employee`
- `reviewer`
- `manager`
- `admin`

Role capabilities:

| Capability | employee | reviewer | manager | admin |
| --- | --- | --- | --- | --- |
| Search accessible knowledge | yes | yes | yes | yes |
| View accessible timelines/history/decisions | yes | yes | yes | yes |
| Create evidence or review requests | yes | yes | yes | yes |
| Review public/internal candidates | no | yes | yes | yes |
| Review restricted candidates | no | no | yes | yes |
| Final restricted approval | no | no | no | yes |
| View cost/admin observability | no | no | limited | yes |
| Manage users and roles | no | no | no | yes |
| Manage integrations globally | no | no | limited | yes |

Permission levels remain source-content access levels:

- `public`
- `internal`
- `restricted`

Roles answer "what can this user do?" Permission levels answer "what content can
this user see?"

## Page Access

Admin-only:

- `/admin`
- future `/costs`
- cost-sensitive global AgentRun observability controls
- user management
- global OAuth/integration administration

Reviewer and above:

- `/review`

Employee and above:

- `/dashboard`
- `/messages`
- `/search`
- `/knowledge`
- `/knowledge-map`
- `/timeline`
- `/history`
- `/decisions`
- `/notifications`

Frontend route guards should hide unavailable navigation items and also handle
direct URL access. Backend API guards are the source of truth.

## Admin UX

The admin page should evolve from a read-only demo console into a user
management workspace.

MVP admin actions:

- view users;
- change role;
- change status between `active` and `suspended`;
- change title and department;
- change permission levels;
- see audit logs for every admin action.

Every role, status, and permission change must create an audit log with:

- actor user id and email;
- target user id and email;
- previous values;
- new values;
- timestamp.

## Review Queue Approval Model

Knowledge review should behave like an approval system.

MVP states:

- `pending_review`
- `needs_more_evidence`
- `approved`
- `rejected`

Role rules:

- `reviewer` can approve `public` and `internal` candidates.
- `manager` can approve `public`, `internal`, and department-level restricted
  candidates in a later phase.
- `admin` is required for restricted final approval.

Future states:

- `reviewer_approved`
- `manager_approved`
- `admin_approved`
- `promoted_to_knowledge`

The first implementation should keep the existing simple Review Queue states but
add role checks around approval actions. Full multi-step approval should be a
second implementation slice after the route guards and admin management UI are
stable.

## API Guards

Add reusable dependency helpers:

- `require_authenticated_user`
- `require_role(*roles)`
- `require_admin_user`
- `require_reviewer_user`
- `require_permission_level(level)`

The existing demo dependency can wrap the same `AuthUser`-like shape, but new
code should move toward authenticated user records as the canonical input.

## Frontend Behavior

Login page:

- primary action: "Continue with Google";
- secondary demo account selector only in demo mode;
- after logout, login again should route through Google account selection;
- show an invite-required message for unknown emails.

App shell:

- fetch `/api/v1/auth/me`;
- show current user identity and role;
- hide admin-only navigation from non-admin users;
- hide Review Queue from users below `reviewer`;
- show a clear 403 state if direct URL access fails.

## Cost and Security Notes

- Login and role checks must never call paid LLM or embedding APIs.
- Admin user management must not expose OAuth tokens or provider secrets.
- Google identity tokens must not be stored as raw secrets.
- Refresh tokens remain hashed in the database.
- Unknown Google accounts must be rejected instead of auto-created.
- Role changes must be audited because they can expand access to restricted
  knowledge and cost controls.

## Implementation Slices

1. Seed users and RBAC contract.
2. Google Identity login endpoints.
3. Frontend login page and logout/account switching.
4. Backend API guards for admin/reviewer/cost-sensitive routes.
5. Frontend route guards and navigation filtering.
6. Admin user management APIs and UI.
7. Review Queue role checks.
8. Optional multi-step approval states.

## Verification Plan

Backend tests:

- Google login rejects unknown email.
- Google login accepts seeded admin email.
- Google login accepts seeded employee email.
- inactive users cannot log in.
- non-admin users cannot call admin APIs.
- reviewer can approve internal review items.
- employee cannot approve review items.
- admin can approve restricted review items.
- role changes create audit logs.

Frontend tests:

- login page shows Google login as primary action;
- demo selector appears only in demo mode;
- admin sees `/admin` navigation;
- employee does not see admin/cost navigation;
- direct admin page access as employee shows a 403 state;
- logout allows another Google account selection.

Manual OAuth smoke:

- verify Google OAuth redirect URI is configured;
- login as `hanvv3@gmail.com`;
- logout;
- login as `hanvv3@koreacu.ac.kr`;
- confirm navigation and page access differ.
