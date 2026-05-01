# Slack-Like Workspace UI Design

Date: 2026-05-01
Project: ParaWorks

## Purpose

This spec defines the first ParaWorks frontend UX upgrade. The goal is to move
from a plain harness UI to a Korean-first, Slack-like business workspace that
can later hold AI agents, review queues, RAG answers, and integration tools
without another layout rewrite.

## Design Direction

Use a Slack-like workspace shell, not a marketing dashboard.

ParaWorks should feel like an everyday operational tool:

- dense but readable;
- channel and activity oriented;
- Korean-first;
- familiar to Slack users;
- ready for AI agent entry points and review workflows.

Slack's current product direction emphasizes consolidated desktop tabs, Activity
as a place to manage messages and actions, Files/Tools as grouped work surfaces,
and AI assistance reachable from the main workspace. ParaWorks should borrow
these UX patterns without copying Slack branding.

References checked on 2026-05-01:

- https://slack.com/intl/en-gb/help/articles/16764236868755-An-overview-of-Slacks-new-design
- https://slack.com/help/articles/46751260742035-Introducing-the-new-Activity-view-in-Slack/
- https://slack.com/help/articles/115004846068-Slack-updates-and-changes

## Scope

In scope for this first pass:

- Redesign `AppShell` with a darker workspace rail, clearer nav, and top search
  bar.
- Add visible AI/Review affordances in the shell without implementing new agent
  functionality.
- Upgrade `/messages` to feel closer to a real Slack-like channel surface.
- Upgrade `/integrations` from plain cards to a Tools/Apps-style work surface.
- Improve global colors, spacing, focus states, and panel styling.
- Preserve existing API calls and business logic.

Out of scope:

- New backend APIs.
- Real Slack OAuth.
- Full Review/Search redesign.
- New frontend test framework.
- Pixel-perfect Slack clone or Slack branding.

## UX Requirements

### Workspace Shell

The shell should provide:

- persistent desktop sidebar;
- compact mobile top navigation;
- workspace identity and Korean-first copy;
- navigation items with icons and active states;
- top command/search bar for future RAG/agent entry;
- small status strip showing local MVP/agent readiness.

### Messages

The messages page should:

- feel like a channel view rather than a generic card;
- show a channel list with unread badges and descriptions;
- show a channel header with summary metadata;
- display messages in a scannable timeline;
- keep "send to Review Queue" visible but not visually noisy;
- keep the composer anchored and easy to use.

### Integrations

The integrations page should:

- feel like Slack Tools/Apps;
- explain connector readiness with operational metadata;
- make Slack the most prominent near-term connector;
- show sync status in a compact activity panel;
- avoid corrupted copy and replace it with polished Korean-first text.

## Visual System

Use a restrained operational palette:

- dark plum/navy workspace rail;
- warm off-white app background;
- white panels;
- soft neutral borders;
- green/blue accents for status and actions;
- no decorative gradient blobs or marketing hero layout.

Cards should remain practical panels with 8px or smaller radius. The design
should prioritize scanning, comparison, repeated use, and information density.

## Implementation Notes

Current frontend structure is small:

- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/app/globals.css`
- `frontend/src/app/messages/page.tsx`
- `frontend/src/app/integrations/page.tsx`

This pass should modify only those files unless a small shared helper becomes
obviously necessary.

## Verification

Required checks:

- `npm.cmd run build` from `frontend`.
- Browser smoke on:
  - `/messages`
  - `/integrations`
  - `/dashboard`
- Confirm Korean text is readable and not mojibake.
- Confirm desktop and mobile layouts do not overlap.
- Confirm existing message posting and send-to-review controls remain present.

## Portfolio Angle

This work shows that ParaWorks is not only an AI backend prototype. It is being
shaped into a credible Korean business workspace that can host multi-agent
knowledge workflows in a familiar collaboration UI.

