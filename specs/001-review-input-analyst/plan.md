# Implementation Plan: Review Input + Analyst v0.1

**Branch**: `001-review-input-analyst` | **Date**: 2026-08-19 | **Spec**: `specs/001-review-input-analyst/spec.md`

## Summary

Implement the smallest executable product increment: immutable `ReviewInput`, validated `ProblemAnalysis`, a provider-neutral `LLMPort`, and an `Analyst` participant that converts untrusted structured model output into trusted domain data. Use only the Python standard library in production code and deterministic fakes in tests.

## Technical Context

**Language/Version**: Python >=3.12  
**Primary Dependencies**: Python standard library only  
**Storage**: N/A  
**Testing**: pytest  
**Target Platform**: local Python process / CI  
**Project Type**: single Python package  
**Performance Goals**: no hard latency target; no live model in this increment  
**Constraints**: provider-independent core, no persistence, no UI, no real LLM SDK, deterministic tests  
**Scale/Scope**: one participant and two core domain contracts

## Constitution Check

### Pre-design gate

- **Genuine collaboration / role integrity**: PASS. Only Analyst is implemented; no attempt is made to simulate later participants.
- **Structured contracts and validation**: PASS. `ProblemAnalysis` is explicit and generated output is validated before conversion.
- **Traceability / uncertainty**: PASS. Facts include source references; assumptions, missing information, and uncertainties remain distinct.
- **Human decision authority**: PASS. No recommendation or external action exists in this increment.
- **Minimal architecture**: PASS. No framework, persistence, UI, RAG, agent framework, or provider SDK is introduced.
- **Provider independence**: PASS. Analyst depends on a minimal `LLMPort` Protocol.
- **Deterministic testability**: PASS. Fake structured-generation responses are sufficient for all feature tests.
- **Security minimization**: PASS. No credentials or external capabilities are introduced.
- **Incremental delivery**: PASS. The feature is independently verifiable and does not implement future orchestration prematurely.

### Post-design gate

PASS. Research and data-model decisions preserve all pre-design conclusions. No constitutional exception is required.

## Project Structure

### Documentation

```text
specs/001-review-input-analyst/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
└── tasks.md
```

### Source

```text
src/agentic_review_board/
├── application/
│   ├── __init__.py
│   └── ports.py
├── domain/
│   ├── __init__.py
│   ├── analysis.py
│   └── review.py
└── participants/
    ├── __init__.py
    └── analyst.py

tests/unit/
├── test_analyst.py
└── test_review_input.py
```

## Design

### Domain

Use frozen, slotted dataclasses for immutable contracts.

`ReviewInput` validates only the required description while preserving supplied text.

`ProblemAnalysis` separates facts, constraints, assumptions, missing information, and uncertainty. `FactFinding` carries an explicit source reference to a field on the current `ReviewInput`.

### Provider boundary

`LLMPort` is a Python `Protocol` with a minimal structured-generation operation. No provider-specific types are allowed in this interface.

### Analyst boundary

`Analyst.analyze(review_input)`:

1. builds a provider-neutral payload from the current `ReviewInput`;
2. requests one structured generation using role `analyst`;
3. treats the returned mapping as untrusted;
4. validates required fields, collection shapes, source references, and identifier uniqueness;
5. returns a trusted `ProblemAnalysis` or raises `AnalystOutputError`.

### Deliberately deferred

- full `Review` / `StageExecution` lifecycle;
- orchestrator;
- status transitions;
- UI;
- real LLM adapter;
- prompt templates/versioning;
- retry/timeout behavior;
- Pydantic or another schema library;
- downstream participants.

## Verification

Required deterministic tests:

- minimal valid `ReviewInput` accepted;
- blank description rejected;
- valid Analyst response produces `ProblemAnalysis`;
- missing required Analyst collection rejected;
- invalid fact source reference rejected;
- duplicate finding identifiers rejected.

CI quality gates remain pytest, Ruff, and mypy as defined by the bootstrap.
