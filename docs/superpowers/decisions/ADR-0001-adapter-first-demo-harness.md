# ADR-0001: Adapter-First Demo Harness

## Status

Accepted

## Context

ParaWorks needs to validate company-wide knowledge workflows before production integrations are ready. The core risk is whether source-backed review, permission-filtered search, and evidence inspection work as one coherent service.

## Decision

The first harness uses mock connectors that implement the same source-event contract future real connectors will implement. The backend normalizes source events, creates deterministic review candidates, enforces permission filtering, and exposes demo UI APIs.

## Consequences

- Real connectors can be added without rewriting ingestion and review logic.
- Tests can run without external SaaS credentials.
- Permission leakage checks are part of the baseline harness.
- LangGraph integration can be added after deterministic behavior is covered.
