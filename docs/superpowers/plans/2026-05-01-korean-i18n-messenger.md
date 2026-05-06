# Korean I18n and Messenger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Korean-first language switching and a Slack-like mock messenger MVP to ParaWorks.

**Architecture:** Backend exposes deterministic mock message APIs under `/api/v1/messages`. Frontend adds a small client-side i18n provider and a `/messages` screen linked from the shell.

**Tech Stack:** FastAPI, Pydantic v2, pytest, Next.js 15 App Router, React 19, TypeScript, Tailwind CSS, lucide-react.

---

## Tasks

- [ ] Add failing backend tests for message channels, message listing, posting, and 404 handling.
- [ ] Implement message schemas, in-memory mock service, router, and route registration.
- [ ] Add frontend i18n dictionary/provider with Korean default and English switch.
- [ ] Update AppShell navigation and labels to use i18n and include Messenger.
- [ ] Add `/messages` page with channel list, timeline, and composer.
- [ ] Verify with backend tests, frontend build, and browser smoke test.
