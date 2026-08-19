# Implementation Plan: Review Input + Analyst v0.1

**Branch**: `001-review-input-analyst`  
**Date**: 2026-08-19  
**Spec**: `specs/001-review-input-analyst/spec.md`  
**Status**: Draft — awaiting review

## 1. Summary

Implement the smallest executable Analyst slice while preserving the architectural boundary between untrusted model output and trusted review contracts.

The increment will introduce:

- `ReviewInput` as the validated representation of the current user-provided problem and optional context;
- `ProblemAnalysis` as the validated Analyst result;
- Pydantic v2 as the common structured-contract and validation mechanism;
- a provider-neutral `LLMPort` boundary;
- an `Analyst` participant that requests structured content, validates the returned data, enforces Analyst-specific invariants, and returns a trusted `ProblemAnalysis`;
- deterministic tests that require neither network access nor a live LLM.

The increment will not implement orchestration, UI, a concrete model provider, persistence, or downstream participants.

## 2. Technical Context

**Language/Version**: Python >=3.12  
**Production Dependency**: `pydantic>=2.13,<3`  
**Development Dependencies**: pytest, Ruff, mypy as already defined by the project bootstrap  
**Storage**: none  
**Target Platform**: single local Python process and CI  
**Project Type**: single Python package using the existing `src/` layout  
**External Model Access**: provider-neutral port only; no concrete SDK in this increment  
**Performance Goals**: no hard latency target; representative model/provider measurements do not yet exist  
**Security Scope**: no credentials, external tools, persistence, autonomous actions, or confidential-data dependency  
**Scale/Scope**: one review input contract, one Analyst output contract, one participant, one provider-neutral boundary

### Pydantic version policy

Use stable Pydantic v2 rather than a pre-release line. The implementation dependency will use the compatible range:

```text
pydantic>=2.13,<3
```

The plan intentionally avoids pinning to one patch release. Patch-level reproducibility may later be handled through dependency locking if the project demonstrates a need for it.

No `pydantic-settings` dependency is required by this increment.

## 3. Constitution Check

### I. Genuine Agent Collaboration and Role Integrity — PASS

Only the Analyst responsibility is implemented in this increment.

The Analyst:

- consumes only the current `ReviewInput` plus the technical model-access boundary required to perform its role;
- produces only `ProblemAnalysis`;
- does not generate or rank solution alternatives;
- does not recommend an architecture or implementation option;
- does not make the final decision;
- does not control workflow progression.

No attempt is made to simulate the remaining four participants.

### II. Structured Contracts and Validation — PASS

Pydantic v2 will provide the standard mechanism for declaring and validating structured review contracts.

Generated Analyst content remains untrusted until it passes:

1. Pydantic structural validation against the expected contract;
2. Analyst-specific invariant checks that require comparison with the current `ReviewInput`.

Invalid generated content does not become trusted `ProblemAnalysis` data.

### III. Traceability, Uncertainty, and Explicit Evidence — PASS

`ProblemAnalysis` keeps facts, constraints, assumptions, missing information, and uncertainties structurally distinct.

Items represented as user-provided facts must remain traceable to the current `ReviewInput`.

Review-local identifiers remain optional where useful for traceability; the implementation must not turn the canonical SHOULD into a universal mandatory-ID rule.

### IV. Human Decision Authority — PASS

This increment produces problem analysis only. It contains no recommendation execution, external side effect, or autonomous decision capability.

### V. Minimal Architecture and Evidence-Driven Complexity — PASS WITH ADR

Pydantic introduces one production dependency, but it directly addresses an already-defined architectural need: structured contract declaration, parsing, validation, error reporting, and future schema generation across multiple agent outputs.

Because the canonical architecture explicitly deferred selection of the structured-output validation library, adoption of Pydantic requires an ADR before implementation is considered approved.

No agent framework, persistence layer, RAG system, UI framework, broker, database, or distributed component is introduced.

### VI. Provider Independence and Boundary Discipline — PASS

The Analyst depends on a provider-neutral `LLMPort`, not on a concrete model SDK.

Pydantic is a contract/validation dependency, not a model-provider dependency.

Provider SDK objects must not appear in domain contracts, participant interfaces, or tests.

### VII. Deterministic Testability and Visible Failure — PASS

All behavior introduced by this feature must be testable with a deterministic `LLMPort` fake.

Tests cover valid output and representative invalid generated content. A real model endpoint is not required for the core suite.

### VIII. Security by Minimization and Least Capability — PASS

The increment introduces no secret, persistence, tool, network action, filesystem mutation, or autonomous execution capability.

### IX. Incremental Delivery and Explicit Architectural Decisions — PASS WITH ADR

The increment is deliberately limited to Review Input + Analyst.

Before implementation proceeds, a new ADR under `docs/adr/` must record the choice of Pydantic v2 as the structured-contract and validation library, including alternatives, consequences, and reconsideration conditions.

**Constitution gate result**: PASS, conditional only on approval of the Pydantic ADR before implementation.

## 4. Architectural Decisions in This Plan

### 4.1 Pydantic v2 for structured contracts

Use Pydantic `BaseModel` models for the structured contracts introduced by this feature.

Primary reasons:

- centralized field and model validation;
- structured validation errors;
- declarative nested contracts;
- reduced handwritten parsing and shape-validation code;
- support for immutable/frozen model configuration where appropriate;
- deterministic handling of unknown fields;
- JSON Schema generation that can later support provider-neutral structured-output integration without changing the semantic contracts.

Pydantic validation does not make generated content trusted by itself. Trust is established only after both structural validation and feature-specific invariants succeed.

### 4.2 Fail-closed contract configuration

Models receiving generated content should use explicit configuration rather than permissive defaults.

The baseline is:

- reject unknown fields where the contract is closed (`extra="forbid"`);
- preserve original textual values rather than trimming or rewriting them silently;
- use strict textual field types for generated textual content so unrelated primitive types are not silently accepted as text;
- use explicit validators only for real domain invariants rather than duplicating validation already provided by Pydantic.

The implementation should favor built-in Pydantic v2 constructs over custom schema internals.

### 4.3 ReviewInput preservation

`ReviewInput` will be represented as a Pydantic model configured to prevent reassignment after creation.

Conceptual fields remain aligned with the Agent Model:

```text
ReviewInput
- title?          optional text
- description     required text
- objective?      optional text
- constraints[]   optional collection
- context[]       optional collection
- stated_facts[]  optional collection
```

Validation must reject a description that is empty or whitespace-only without modifying the original non-empty text.

Optional user-provided values remain optional.

### 4.4 ProblemAnalysis contract

`ProblemAnalysis` will be a Pydantic model with the canonical semantic categories:

```text
ProblemAnalysis
- objective
- facts[]
- constraints[]
- assumptions[]
- missing_information[]
- uncertainties[]
```

The model must not contain solution alternatives, solution ranking, architecture recommendations, or a final recommendation.

### 4.5 Fact provenance

A fact must include enough structural information to identify the `ReviewInput` field that supports it.

The allowed source-reference vocabulary is limited to the conceptual `ReviewInput` fields:

```text
description
title
objective
constraints
context
stated_facts
```

Pydantic validates that the source-reference value belongs to the allowed vocabulary.

The Analyst boundary then verifies that the referenced field is actually present/applicable in the current `ReviewInput` before accepting the fact into trusted output.

This is structural provenance, not independent external fact verification.

### 4.6 Review-local identifiers

Finding identifiers are useful for later cross-stage traceability but are not mandatory for every Analyst finding in the canonical Agent Model.

Therefore:

- an identifier may be present on structured findings;
- if present, it must be non-empty and unambiguous within the current `ProblemAnalysis`;
- duplicate provided identifiers must be rejected;
- absence of an identifier alone must not invalidate an otherwise valid finding in this increment.

This preserves the canonical SHOULD semantics.

### 4.7 Provider-neutral LLM boundary

Define a minimal Python `Protocol` representing the model capability required by the Analyst.

For this increment the port should:

- accept provider-neutral Analyst input data;
- return an untrusted mapping/object representation suitable for local validation;
- expose no concrete SDK types, authentication objects, endpoint-specific envelopes, or provider-specific tool definitions.

The port does not need to know about OpenAI, Anthropic, Ollama, vLLM, or any other concrete provider.

A later adapter may use Pydantic-generated JSON Schema when integrating provider-native structured output, but provider-side schema enforcement must never replace local validation before trusted Review state.

### 4.8 Analyst validation boundary

Conceptual execution:

```text
ReviewInput
    ↓
Analyst
    ↓
LLMPort
    ↓
untrusted generated mapping
    ↓
Pydantic structural validation
    ↓
Analyst-specific invariant validation
    ↓
trusted ProblemAnalysis
```

Pydantic handles shape/type/closed-schema validation.

The Analyst/application boundary retains only invariants that depend on review context, such as checking fact provenance against the actual current `ReviewInput` and checking ambiguity of optional local identifiers.

Validation errors from generated content should be normalized into an Analyst/output-validation error category rather than leaking provider-specific failures or being repaired silently.

## 5. Proposed Project Structure

No new architectural layer is required.

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

tests/
└── unit/
    ├── test_review_input.py
    └── test_analyst.py
```

Responsibilities:

- `domain/review.py`: Pydantic `ReviewInput` and review-input-specific validation.
- `domain/analysis.py`: Pydantic Analyst output contracts and structural domain validation.
- `application/ports.py`: provider-neutral `LLMPort` Protocol.
- `participants/analyst.py`: Analyst interaction with `LLMPort`, conversion from untrusted output, review-context invariants, and normalized Analyst output failure.
- `tests/unit/`: deterministic domain and participant behavior.

The exact package structure remains revisitable through ADR if later increments provide evidence that another layout is clearer.

## 6. Dependency Change

After the plan and ADR are approved, `pyproject.toml` should change from no production dependency to:

```toml
[project]
dependencies = [
    "pydantic>=2.13,<3",
]
```

No other production dependency is justified by this feature.

The project remains compatible with Python >=3.12 and the existing CI matrix.

## 7. Verification Strategy

### 7.1 ReviewInput tests

Verify at minimum:

- minimal valid description is accepted;
- blank/whitespace-only description is rejected;
- all optional fields may be absent;
- supplied text is not silently trimmed or rewritten;
- model reassignment is rejected once constructed.

### 7.2 ProblemAnalysis / Analyst happy-path tests

Verify at minimum:

- a valid deterministic generated mapping becomes `ProblemAnalysis`;
- all six semantic categories are present;
- facts and assumptions remain distinct;
- valid fact provenance points to applicable current `ReviewInput` data;
- Analyst output contains no solution alternatives, ranking, or final recommendation fields.

### 7.3 Fail-closed tests

Verify representative invalid generated content:

- missing mandatory `ProblemAnalysis` field;
- unknown top-level generated field when the contract forbids extras;
- wrong primitive type for a strict textual field;
- invalid fact source-reference value;
- fact reference to a ReviewInput field that is absent/not applicable;
- duplicate provided review-local identifiers;
- malformed nested finding.

Every such case must fail before a trusted `ProblemAnalysis` is returned.

### 7.4 Provider-boundary tests

Use a deterministic fake implementing `LLMPort`.

Core tests must not import or require any concrete provider SDK and must run without network access.

### 7.5 Existing quality gates

The completed increment must pass:

```text
pytest
ruff check .
mypy
pip check
```

on the supported CI Python versions.

## 8. Deliberately Deferred

This plan does not decide or implement:

- concrete LLM provider/model/endpoint protocol;
- concrete LLM adapter;
- prompts, prompt templates, or prompt versioning;
- retries or timeouts;
- full `Review` / `StageExecution` lifecycle;
- Review Orchestrator;
- stage status transitions;
- UI framework;
- persistence;
- downstream participants;
- RAG, document ingestion, external tools, or autonomous actions;
- dependency locking strategy unless reproducibility evidence requires it;
- use of Pydantic Settings.

## 9. Required ADR Before Implementation

Before implementation of this revised plan, create and review one ADR for:

**Decision**: adopt Pydantic v2 as the structured-contract, validation, and serialization foundation for review-domain and participant-output contracts.

The ADR should compare at least:

- Python dataclasses plus handwritten validation;
- Pydantic v2;
- retaining a generic/no-library approach until later.

It should document:

- why Pydantic is justified now rather than deferred further;
- where Pydantic is allowed to appear in the architecture;
- validation and `extra` policy;
- consequences of making it a core production dependency;
- how provider independence is preserved;
- conditions under which the decision should be revisited.

The ADR is a planning gate, not a new feature requirement.

## 10. Existing Branch Reconciliation

The current branch already contains an earlier provisional implementation based on standard-library dataclasses and handwritten validation.

That code must not be treated as authoritative for this revised plan and must not be merged in its current form.

After this plan and the required ADR are approved, the later implementation phase will reconcile the branch by:

- replacing provisional structured contracts with the approved Pydantic models;
- removing handwritten structural validation that Pydantic makes redundant;
- retaining only review-context/domain invariants not covered by ordinary schema validation;
- updating tests to match the approved specification and plan;
- re-running the complete deterministic and CI quality gates.

No code change is part of the current planning phase.
