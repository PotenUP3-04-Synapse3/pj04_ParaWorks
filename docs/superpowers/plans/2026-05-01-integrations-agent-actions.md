# Integrations Agent Actions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose multiple backend agents from the Integrations UI so users can run Slack Agent and Mail/Docs Agent from the same smoke surface.

**Architecture:** Generalize the existing Slack-only agent action state into a reusable action descriptor per integration card. Keep the API response type generic because all MVP agent-review endpoints return the same shape.

**Tech Stack:** Next.js 15, React 19, TypeScript, Tailwind, existing FastAPI agent-review endpoints.

---

## Task 1: Frontend Agent Action Wiring

- [x] Replace Slack-only response state with a generic `AgentReviewResponse`.
- [x] Add a Mail/Docs Agent action descriptor to Gmail and Drive cards.
- [x] Generalize `runSlackAgent` into `runAgent(agentKey, path)`.
- [x] Render completed agent names with Korean-friendly labels.

## Task 2: Verification

- [x] Run `npm.cmd run build` from `frontend`.
- [x] Restart smoke server after build.
- [x] Verify `/integrations`, `/dashboard`, and `/health` return HTTP 200.
- [x] Verify Gmail sync, Drive sync, and Mail/Docs Agent API create one agent Review candidate.

## Task 3: Commit

- [x] Update `docs/portfolio-log.md`.
- [x] Commit with `feat: expose mail docs agent in integrations`.
