# Route Audit And Next 16 Upgrade Plan

## Goal

Make the current frontend reliable across all MVP routes after adding Slack OAuth status UI, and remove the outdated Next.js warning without changing the backend contract.

## Scope

- Upgrade the frontend to Next.js 16.2.4 with the matching ESLint config package.
- Convert linting to ESLint 9 flat config.
- Harden `/integrations` so core connector manifests load even when optional OAuth connection-status endpoints are absent on a stale backend.
- Expand Playwright visual smoke coverage beyond the dashboard to all current user-facing routes.
- Keep the Slack card layout stable by showing the OAuth install button only when Slack OAuth is configured and not yet connected.

## Cost And Reliability Notes

- Optional Slack OAuth metadata should fail soft. A missing status endpoint must not trigger retries that hide Gmail, Drive, or Calendar cards.
- The UI should continue to operate in mock/demo mode without making live Slack or embedding calls.
- Full route smoke coverage catches broken pages early, reducing time wasted debugging late-stage integration failures.

## Verification

- `npm.cmd run lint`
- `npm.cmd run build`
- `uv run pytest backend/tests -v`
- `.\scripts\run-visual-smoke.ps1 -BackendPort 8013 -FrontendPort 3013 -DatabasePath '.tmp\paraworks-route-audit-final.db'`
