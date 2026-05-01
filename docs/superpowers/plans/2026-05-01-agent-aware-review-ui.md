# Agent-Aware Review UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `/review` so users can clearly distinguish AI Agent-generated candidates, inspect cost/evidence metadata, and act on Review Queue items like an Activity inbox.

**Architecture:** Keep existing Review APIs and client-side actions. Improve the frontend presentation in `frontend/src/app/review/page.tsx` and `SourceEvidenceDrawer` only, plus documentation updates. No backend schema changes in this step.

**Tech Stack:** Next.js 15, React 19, Tailwind CSS, lucide-react.

---

## File Structure

- Modify `frontend/src/app/review/page.tsx`
  - Replace corrupted Korean copy.
  - Add Agent metadata badges when `payload.agent_name` exists.
  - Add token/cost/prompt/cache metadata panel.
  - Improve confidence and permission visualization.
  - Keep approve/reject/edit/request-more-evidence behavior unchanged.
- Modify `frontend/src/components/shared/SourceEvidenceDrawer.tsx`
  - Replace corrupted copy.
  - Improve drawer layout and evidence link labels.
- Modify `docs/portfolio-log.md`
  - Record Review UI milestone and verification evidence.

## Task 1: Review Page

- [ ] Replace mojibake Korean strings.
- [ ] Add helpers for string/number/object payload fields.
- [ ] Detect Agent-generated items via `payload.agent_name`.
- [ ] Render Activity/Inbox-style item cards.
- [ ] Show prompt version, estimated cost, token usage, cache key, and permission when present.
- [ ] Preserve existing actions and editing behavior.

## Task 2: Evidence Drawer

- [ ] Replace corrupted Korean copy.
- [ ] Show snippet count and source links clearly.
- [ ] Keep external source links opening in a new tab.

## Task 3: Verification

- [ ] Run `npm.cmd run build` from `frontend`.
- [ ] Smoke `/review` over HTTP.
- [ ] Update portfolio log.
- [ ] Commit with `feat: improve agent-aware review UI`.

