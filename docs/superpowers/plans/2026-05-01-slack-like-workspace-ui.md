# Slack-Like Workspace UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade ParaWorks frontend into a Korean-first Slack-like workspace shell with improved Messages and Integrations surfaces.

**Architecture:** Keep the existing Next.js App Router structure and API calls. Improve `AppShell`, global CSS tokens, `/messages`, and `/integrations` in place without adding new backend dependencies.

**Tech Stack:** Next.js 15, React 19, Tailwind CSS, lucide-react.

---

## File Structure

- Modify `frontend/src/app/globals.css`
  - Add workspace color variables, scrollbar styling, and stronger focus states.
- Modify `frontend/src/components/layout/AppShell.tsx`
  - Add dark workspace rail, top command bar, agent status strip, and improved mobile nav.
- Modify `frontend/src/app/messages/page.tsx`
  - Improve channel list, channel header, message timeline, notices, and composer.
- Modify `frontend/src/app/integrations/page.tsx`
  - Replace mojibake copy, introduce Tools/Apps-style cards, and improve sync activity panel.
- Modify `docs/portfolio-log.md`
  - Record the Slack-like UI milestone.

## Task 1: Workspace Shell

- [ ] Update global background, panel, and focus styling in `globals.css`.
- [ ] Redesign `AppShell` with workspace rail and top command/search bar.
- [ ] Preserve language switching and route navigation.
- [ ] Verify mobile header remains compact and usable.

## Task 2: Messages Surface

- [ ] Keep existing data loading, posting, and send-to-review behavior.
- [ ] Improve channel list density, active states, unread badges, and metadata.
- [ ] Improve timeline layout with hover actions and message grouping feel.
- [ ] Improve composer with anchored panel, clearer placeholder, and action button.

## Task 3: Integrations Surface

- [ ] Replace corrupted Korean copy.
- [ ] Present integrations as Tools/Apps with readiness metadata.
- [ ] Make Slack visually prominent as the next connector path.
- [ ] Keep existing sync button and SSE job status behavior.

## Task 4: Verification

- [ ] Run `npm.cmd run build` from `frontend`.
- [ ] Start or reuse local smoke server.
- [ ] Browser smoke `/integrations`, `/messages`, `/dashboard`.
- [ ] Update portfolio log.
- [ ] Commit.

