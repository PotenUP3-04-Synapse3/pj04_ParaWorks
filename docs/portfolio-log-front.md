# ParaWorks Frontend Portfolio Log

Updated: 2026-05-11

## Frontend Positioning

ParaWorks frontend is now moving from a demo harness UI into a portfolio-ready
Korean-first product surface. The recent pass focused on consistency,
operational clarity, and visual confidence across the whole app rather than
adding new feature breadth.

The frontend story is:

- Korean-first SaaS workspace for company memory operations.
- Slack-like navigation and messaging surfaces.
- Human review workflows with visible evidence and permission context.
- Agent observability, cost controls, and RAG/search surfaces that feel like
  product tools instead of debug screens.
- A restrained Liquid Glass visual system with consistent panels, controls,
  status states, and spacing.

## Recent Work

### Lint Warning Cleanup

Cleaned the remaining frontend lint warnings.

- Removed an unused `LogIn` import from the login page.
- Replaced raw `<img>` usage with Next `Image` in:
  - login brand logo;
  - account profile avatar;
  - app shell brand logos;
  - app shell user avatar.

Portfolio value:

- Shows attention to production frontend quality.
- Keeps the Next.js codebase aligned with framework guidance.
- Reduces noise before final demo and screenshot capture.

Verification:

```bash
cd frontend
npm run lint
npm run build
```

Result: both passed with no lint warnings.

### Global Liquid Glass Consistency Pass

Aligned the visual tone, spacing, card radius, and status surfaces across the
main product pages.

Updated patterns:

- Replaced scattered hard-coded warm surfaces such as `#fbfaf8` with shared
  glass tokens.
- Replaced fixed blue `#173a96` product accents with `--primary` and
  `--primary-dark`.
- Standardized oversized `rounded-[30px]` and `rounded-[32px]` panels to the
  app's tighter `rounded-lg` system.
- Added a reusable `shadow-panel` utility for elevated glass surfaces.
- Moved more panels and controls to:
  - `--glass-elevated`;
  - `--glass-strong`;
  - `--line-soft`;
  - `--shadow-panel`.
- Preserved compact operational density instead of making the product feel like
  a marketing landing page.

Touched surfaces:

- Dashboard
- Messages
- Review Queue
- Search / Ask Workspace
- Integrations and OAuth callback pages
- Agent Runs and Agent Run detail
- Knowledge Map
- Account
- Admin
- Login and Google login callback
- Shared AppShell

Portfolio value:

- Demonstrates a coherent product design system across many real screens.
- Makes Review Queue, RAG, integrations, and agent observability feel like one
  workspace.
- Improves screenshot-readiness for final case-study material.

### Review Queue and Page Health Polish

Aligned Review Queue with the same heading and layout rhythm used by the rest
of the app.

- Changed Review Queue top section to use the shared `page-heading` pattern.
- Kept reviewer actions compact and operational.
- Preserved evidence-first workflow without changing backend behavior.

Also fixed small page-health gaps found during visual regression:

- Added `/account` to the Playwright route inventory.
- Added a `main` wrapper to `/login/google/callback`.
- Updated the page regression glass-surface detector to recognize the newer
  token-based surface classes.
- Ignored expected unauthenticated `403` console noise in the Search page
  regression check.

Portfolio value:

- Shows that the UI is tested as a whole application, not only as isolated
  components.
- Keeps future route additions visible through route inventory coverage.

### Dashboard Runtime Warning Fix

Fixed a dashboard count calculation that could produce a React `NaN` warning
when a source count key was missing.

Change:

- Source totals now coalesce missing counts to `0` before summing.

Portfolio value:

- Small but important polish: final demos should not emit noisy console
  warnings.

### Profile Avatar Verification

Checked demo-user profile image behavior after AppShell avatar rendering was
updated.

Findings:

- Admin accounts intentionally have no avatar image.
- Employee/reviewer accounts expose these avatar URLs:
  - `hanvv3@koreacu.ac.kr` -> `/profile/hanvv3.png`
  - `mina@paraworks.com` -> `/profile/mina.png`
  - `jun@paraworks.com` -> `/profile/jun.png`
  - `soyeon@paraworks.com` -> `/profile/soyeon.png`
- The Next dev server serves all profile image files with `200 OK`.

Operational note:

- The existing Next dev server was restarted and `http://localhost:3000` is
  serving the refreshed app.

### UX Polish: Profile and Sidebar Identity Restoration

Recorded on 2026-05-11.

Following user feedback that the recent "Clean Light Theme" pass felt too plain
or less unified, restored and improved the premium identity of the sidebar and
account profile.

- **Profile Picture Resizing**: Increased the diameter on the Account page by
  1.5x (96px -> 144px) for better visual balance and presence.
- **Sidebar Background Alignment**: Reverted the sidebar background to match
  the app's light-grey background (`#f8f9fa`), creating a unified "Rail" look.
- **Elevated Interactive Elements**: Applied a pure white (`#ffffff`) background
  with a soft shadow and fine-line border to active menu items and the bottom
  profile box, making them appear "elevated" above the grey sidebar.

Portfolio value:

- Shows responsiveness to user feedback regarding "premium feel" and "unity."
- Demonstrates how to balance a "clean" aesthetic with visual depth and
  interactive affordance.
- Aligns the sidebar identity with the "Elevated White" design pattern used
  elsewhere in the app.

Verification:

- Manually verified the layout on the Account and Dashboard pages.
- Confirmed that the sidebar and profile box now share the same "elevated"
  visual language.
- Next dev server refreshed with the new styles.

## Verification Evidence

Commands run in the current session:

```bash
cd frontend
npm run lint
npm run build
npm run test:visual -- --project=chromium-desktop e2e/page-regression.spec.ts
```

Results:

- Frontend lint: passed.
- Frontend build: passed.
- Desktop page regression: `41 passed`.

Additional checks:

```bash
curl -I http://127.0.0.1:3000/profile/jun.png
curl -I http://127.0.0.1:3000/profile/mina.png
curl -I http://127.0.0.1:3000/profile/soyeon.png
curl -I http://127.0.0.1:3000/profile/hanvv3.png
```

Result: all returned `200 OK`.

## Files Changed

Primary frontend files:

- `frontend/src/app/globals.css`
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/app/dashboard/page.tsx`
- `frontend/src/app/messages/page.tsx`
- `frontend/src/app/review/page.tsx`
- `frontend/src/app/search/page.tsx`
- `frontend/src/app/account/page.tsx`
- `frontend/src/app/login/page.tsx`
- `frontend/src/app/login/google/callback/page.tsx`
- `frontend/src/app/integrations/page.tsx`
- `frontend/src/app/agent-runs/page.tsx`
- `frontend/src/app/agent-runs/[id]/page.tsx`
- `frontend/src/app/knowledge-map/page.tsx`
- OAuth callback client/page files
- `frontend/e2e/page-regression.spec.ts`

Related local state:

- Playwright Chromium was installed locally so page regression can run.
- Next dev server was restarted.

## Remaining Frontend Follow-Ups

Recommended next frontend tasks:

1. Run mobile Playwright regression and capture final mobile screenshots.
2. Do a manual screenshot pass for:
   - dashboard;
   - messages;
   - review queue;
   - integrations;
   - agent runs;
   - knowledge map;
   - search / ask workspace.
3. Add final screenshots and short captions to `docs/portfolio-case-study.md`.
4. Decide whether the `docker` dependency changes in `pyproject.toml` and
   `uv.lock` belong in the same commit or should be separated.

## 2026-05-12 Account Menu Simplification

- Removed the sidebar account menu's `다른 계정으로 전환` item because it only
  routed to `/login` and did not differ meaningfully from logout in the current
  cookie-session flow.
- Kept `내 계정 정보` and `로그아웃` as the two clear account actions.

Verification:

- `npm.cmd run build` passed.

## 2026-05-12 Enterprise UI Polish Pass

- Applied a restrained production SaaS polish pass without changing navigation,
  layout structure, information architecture, or interaction flow.
- Added missing shared UI tokens for soft primary states, hover borders,
  stronger secondary text, focus rings, and panel-hover elevation.
- Tightened typography hierarchy by making page titles and operational row
  titles slightly stronger while keeping compact Korean-first density.
- Improved enterprise interaction feedback across shared shell/search/buttons,
  selected sidebar items, metric cards, review rows, activity rows, filter
  pills, and primary actions.
- Strengthened evidence/review scanability with calmer panel separation,
  clearer disabled states, and subtle hover feedback suitable for daily
  internal operations work.

Verification:

- `npm.cmd run build` passed from `frontend`.
- Local HTTP smoke returned `200` for `/dashboard`, `/review`, and `/search`.
- Desktop Playwright page regression was attempted, but did not complete:
  route inventory is stale for `/documents` and `/projects`, and the local
  Playwright Chromium binary is missing from the expected cache path.

## 2026-05-12 Admin Console Alignment Pass

- Reworked `/admin` to match the current enterprise console visual system used
  by Dashboard, Review, and Agent Operations.
- Replaced older `liquid-*` surfaces with the shared `reference-dashboard`,
  `page-heading`, `panel`, `source-metric-card`, `activity-toolbar`, and
  dense table styling.
- Added admin-specific table, select, permission pill, and status pill styles
  that preserve the existing user/role/permission workflow while making the
  page feel like the rest of the operational product.
- Kept the information architecture unchanged: permission gate, account
  metrics, user permission management, and audit log remain in the same order.

Verification:

- `npm.cmd run build` passed from `frontend`.
- Local HTTP smoke returned `200` for `/admin`.

## 2026-05-12 Agent Runs And Integrations Header Alignment

- Aligned `/agent-runs` and `/integrations` page headers with the same
  `reference-dashboard`, `page-heading`, and `reference-heading` typography
  pattern used by Dashboard.
- Replaced page-local `text-sm`/`text-2xl` heading classes with shared `h1`,
  metadata, and helper text rules so title weight, Korean text sizing, and
  secondary copy contrast match the rest of the console.
- Kept page content, cards, operations panels, and workflows unchanged.

Verification:

- `npm.cmd run build` passed from `frontend`.
- Local HTTP smoke returned `200` for `/agent-runs` and `/integrations`.

## 2026-05-12 Header Eyebrow Consistency

- Changed the Dashboard eyebrow from Korean copy to `My Work Home` so it
  matches the English eyebrow convention used by the other product pages.
- Added a shared rule for the first small text above page titles in
  `page-heading`/`reference-heading` so all menu headers use the same blue
  eyebrow color without changing body helper text.

Verification:

- `npm.cmd run build` passed from `frontend`.

## 2026-05-12 Premium Enterprise Visual Token Pass

- Refined the global visual tokens toward a quieter premium enterprise SaaS
  aesthetic without changing page layout, navigation, card composition, or
  interaction flow.
- Set the hierarchy to `#ECEEF2` app background, `#F5F6F8` section/control
  background, and `#FFFFFF` card surfaces.
- Standardized card depth with the requested low-elevation shadow:
  `0 1px 2px rgba(16,24,40,0.04), 0 1px 1px rgba(16,24,40,0.02)`.
- Updated typography contrast tokens to `#101828` primary text, `#667085`
  supporting text, and `#98A2B3` metadata/subtle labels.
- Reduced decorative blue usage by moving secondary badges, icons, hover rows,
  and helper labels back to neutral surfaces while preserving blue for active
  navigation, primary actions, and important interactive states.
- Reconnected legacy `liquid-*`, `glass-row`, and `integration-glass-card`
  classes to the current surface/shadow tokens so older pages share the same
  enterprise depth system.

Verification:

- `npm.cmd run build` passed from `frontend`.
- Local HTTP smoke returned `200` for `/dashboard`, `/review`,
  `/integrations`, and `/agent-runs`.
