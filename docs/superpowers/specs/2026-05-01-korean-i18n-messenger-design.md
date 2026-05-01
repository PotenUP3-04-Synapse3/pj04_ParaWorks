# Korean I18n and Messenger Design

Date: 2026-05-01

## Goal

Make ParaWorks feel natural for Korean business users while adding the first Slack-like messenger surface to the existing demo harness.

## Scope

This pass adds:

- Korean as the default frontend language.
- A Korean/English language switch persisted in `localStorage`.
- A new Messenger navigation item and `/messages` screen.
- Mock message channels and message posting APIs.

This pass does not add production real-time transport, file uploads, mentions, Slack import, or persistent production chat storage. Those remain follow-up work after the MVP messenger surface is validated.

## Approach

Frontend i18n starts as a small local dictionary and React provider. This keeps the harness dependency-light and makes Korean the default without introducing a routing framework or locale middleware.

Messenger APIs are adapter-style mock endpoints under `/api/v1/messages`. They return deterministic business-oriented channels and messages, and allow posting a message during the running backend session. The frontend renders a Slack-like three-part layout: channel list, message timeline, and composer.

## API

- `GET /api/v1/messages/channels`
- `GET /api/v1/messages/channels/{channel_id}/messages`
- `POST /api/v1/messages/channels/{channel_id}/messages`

## Frontend

- Add `frontend/src/lib/i18n/*` for locale state and dictionaries.
- Update `AppShell` to show Korean labels by default, add a language switch, and link to Messenger.
- Add `frontend/src/app/messages/page.tsx` as a client page using the messages APIs.

## Verification

- Backend tests cover channel listing, message listing, posting, and not-found validation.
- Frontend build verifies i18n and Messenger TypeScript integration.
- Browser smoke verifies language switch and message posting flow.
