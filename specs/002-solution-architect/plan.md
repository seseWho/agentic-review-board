# Implementation Plan: Solution Architect v0.1

**Branch**: `002-solution-architect`  
**Date**: 2026-08-20  
**Spec**: `specs/002-solution-architect/spec.md`  
**Status**: Draft — awaiting review

## 1. Summary

Implement the smallest executable Solution Architect slice that consumes the already-trusted `ReviewInput` and `ProblemAnalysis` produced by the previous increment and returns trusted `SolutionAlternatives` without introducing review orchestration or later participant responsibilities.

The increment introduces:

- `QualitativeLevel` as the shared qualitative scale required now by solution implementation complexity;
- `SolutionAlternative` as the structured representation of one candidate approach;
- `SolutionAlternatives` as the validated Solution Architect result;
- a `SolutionArchitect` participant that receives only the original `ReviewInput` and trusted `ProblemAnalysis`, requests provider-neutral structured generation through the existing `LLMPort`, validates generated data, enforces contextual upstream-reference invariants, and returns trusted `SolutionAlternatives`;
- deterministic tests covering normal alternatives, the explicit no-alternative case, fail-closed validation, upstream data propagation, reference validation, and post-validation immutability.

The increment reuses the existing Pydantic v2 contract policy, provider-neutral `LLMPort`, Python package structure, and CI quality gates established by Slice 1.

It does not implement the Review Orchestrator, stage lifecycle/status, Risk Reviewer, Critic, Coordinator, ranking, final recommendation, UI, persistence, RAG, tools, or a concrete model provider.

## 2. Technical Context

**Language/Version**: Python >=3.12  
**Production Dependency**: existing `pydantic>=2.13,<3`; no new production dependency  
**Development Dependencies**: existing pytest, Ruff, and mypy configuration  
**Storage**: none  
**Target Platform**: single local Python process and CI  
**Project Type**: existing single Python package using the `src/` layout  
**External Model Access**: reuse existing provider-neutral `LLMPort`; no concrete SDK or adapter  
**Performance Goals**: no new latency SLA; this slice adds one participant invocation only when called directly  
**Security Scope**: no credentials, persistence, external tools, autonomous actions, or confidential-data dependency  
**Scale/Scope**: one new participant output contract, one participant, one shared qualitative enum, deterministic unit/contract tests

### Existing implementation reused

This slice builds directly on the trusted contracts already present in `main`:

```text
ReviewInput
ProblemAnalysis
AnalysisFinding
FactFinding
LLMPort
```

No redesign of those contracts is required.

The existing `LLMPort.generate_structured(role, payload)` signature is already sufficiently generic for the Solution Architect and remains unchanged.

## 3. Constitution Check

### I. Genuine Agent Collaboration and Role Integrity — PASS

This is the first implemented downstream participant.

The Solution Architect:

- receives the original `ReviewInput`;
- consumes the validated `ProblemAnalysis` produced by the Analyst slice;
- produces only `SolutionAlternatives`;
- does not invoke another participant;
- does not control workflow progression;
- does not perform risk review, critique, ranking, or final recommendation.

This produces genuine explicit upstream-to-downstream information flow without introducing the full Orchestrator prematurely.

### II. Structured Contracts and Validation — PASS

Generated Solution Architect content remains untrusted until it passes:

1. Pydantic structural/model validation against the closed `SolutionAlternatives` contract;
2. contextual participant validation for references that must resolve against the actual trusted `ProblemAnalysis`.

Malformed or context-invalid output never becomes trusted `SolutionAlternatives` data.

### III. Traceability, Uncertainty, and Explicit Evidence — PASS

The contract keeps alternatives, trade-offs, assumptions, implementation complexity, and relevant constraints structurally explicit.

Solution-specific assumptions remain assumptions by construction and do not become facts.

Relevant constraint references must resolve to constraints present in the supplied trusted `ProblemAnalysis`.

The no-alternative case preserves explicit uncertainty through `generation_notes` rather than manufacturing candidate variants.

Trusted generated collections are immutable after validation so accepted stage output cannot be altered without crossing validation again.

### IV. Human Decision Authority — PASS

The Solution Architect explores the solution space only.

Its output contains no ranking, preferred alternative, final recommendation, external action, or autonomous decision behavior.

### V. Minimal Architecture and Evidence-Driven Complexity — PASS

No new framework, production dependency, adapter, database, orchestration framework, persistence layer, UI layer, RAG component, tool capability, broker, or distributed runtime is introduced.

The existing Pydantic v2 decision and `LLMPort` are reused.

A small shared qualitative enum is introduced only because the canonical Solution Architect contract requires qualitative implementation complexity now.

No new ADR is required by this plan.

### VI. Provider Independence and Boundary Discipline — PASS

The Solution Architect depends on the existing provider-neutral `LLMPort`.

Provider SDK request types, provider response envelopes, authentication objects, endpoint details, and provider-native schema types remain outside domain and participant code.

The participant supplies only provider-neutral structured data to the port.

### VII. Deterministic Testability and Visible Failure — PASS

All new behavior is testable with a deterministic `LLMPort` fake and no network access.

Tests cover valid alternatives, no-alternative behavior, structural failure, contextual reference failure, provider-failure separation, explicit upstream payload propagation, and immutability.

### VIII. Security by Minimization and Least Capability — PASS

The increment introduces no secrets, filesystem actions, external tools, persistence, browsing, collaboration integrations, or autonomous side effects.

Only the current `ReviewInput` and required trusted `ProblemAnalysis` are supplied to the participant/model boundary.

### IX. Incremental Delivery and Explicit Architectural Decisions — PASS

The increment adds one bounded product capability: Solution Architect output based on validated Analyst output.

ADR-0001 already governs the only material architectural dependency used here: Pydantic v2 for structured contracts and validation.

The remaining choices in this plan are local contract and package-organization decisions and do not introduce a new framework, runtime pattern, integration, persistence model, or security consequence.

**Constitution gate result**: PASS. No new ADR prerequisite is identified.

## 4. Architectural and Contract Decisions

### 4.1 Reuse Pydantic v2 and the existing fail-closed policy

`SolutionAlternative` and `SolutionAlternatives` use Pydantic v2 under ADR-0001.

Generated-output contracts follow the established policy:

- closed schemas where the contract is exhaustive (`extra="forbid"`);
- frozen trusted models;
- immutable validated collections;
- strict generated semantic text rather than permissive primitive-to-string coercion;
- non-empty validation for required generated text;
- no silent semantic repair of malformed model output.

No additional validation library is introduced.

### 4.2 Shared `QualitativeLevel`

Introduce the canonical qualitative scale:

```text
LOW
MEDIUM
HIGH
```

as one shared domain enum/value type.

It is used by `SolutionAlternative.implementation_complexity` in this slice and represents an ordinal engineering judgment, not a probability, duration estimate, effort estimate, or calibrated measurement.

A small shared domain module is justified because the Agent Model defines this as a shared concept and later canonical contracts also use the same semantic scale. This does not create a generic framework or new architectural layer.

### 4.3 `SolutionAlternative` contract

Conceptually:

```text
SolutionAlternative
- id
- name
- description
- advantages[]
- disadvantages[]
- assumptions[]
- implementation_complexity
- relevant_constraints[]
```

Contract intent:

- `id` is required, non-empty, and review-local; no global ID or persistent identity is introduced;
- `name` is required non-empty generated text;
- `description` is required non-empty generated text;
- `advantages`, `disadvantages`, and `assumptions` are explicit ordered collections of generated text;
- `implementation_complexity` accepts only the shared qualitative values;
- `relevant_constraints` is an ordered collection of references to constraints in the supplied `ProblemAnalysis`;
- validated collections are immutable after successful validation.

The plan does not impose an `ALT-001` formatting pattern because the canonical documents provide that as an example rather than a mandatory identifier syntax.

Exact minimum cardinality for the text collections beyond their required presence will be refined in `data-model.md` without inventing requirements not supported by the approved spec or canonical documents.

### 4.4 `SolutionAlternatives` contract and cardinality

Conceptually:

```text
SolutionAlternatives
- alternatives[]
- generation_notes?
```

The alternatives collection is always structurally present.

Valid cardinalities are:

```text
0 alternatives
or
2 alternatives
or
3 alternatives
```

A one-alternative result is invalid because the approved feature semantics are either a meaningful comparison set of two to three alternatives or an explicit statement that a useful alternative set cannot yet be formed.

More than three alternatives is invalid for the MVP slice.

When `alternatives` is empty:

- `generation_notes` becomes conditionally required;
- it must contain non-empty generated text explaining why meaningful alternatives cannot responsibly be formed;
- the text should preserve material missing information or uncertainty blocking comparison when applicable.

When alternatives are present, `generation_notes` remains optional and may provide concise generation context, but it does not replace required per-alternative fields.

Alternative IDs must be unique within one `SolutionAlternatives` result. Duplicate required IDs are a model-level structural invariant because the rule depends only on the candidate output.

### 4.5 Relevant-constraint reference representation

`ProblemAnalysis.constraints` items may have a review-local ID, but Slice 1 intentionally made those IDs optional.

Therefore this slice must not require every upstream constraint to gain an ID merely to support Solution Architect traceability.

The minimal reference policy is:

- each `relevant_constraints` entry is a non-empty provider-neutral textual reference;
- a reference is valid when it resolves to the supplied trusted `ProblemAnalysis.constraints` by an existing constraint ID when one is available, or by exact constraint text when no usable ID reference is supplied;
- the Solution Architect/application boundary performs this contextual resolution after structural validation;
- a reference that resolves to no current upstream constraint is invalid and fails the participant output;
- this is review-local structural traceability, not proof that the model interpreted the constraint correctly.

`data-model.md` will define the exact field/type representation while preserving this resolution policy.

This approach avoids retroactively making Analyst IDs mandatory, avoids index-based references that are opaque to users, and avoids introducing persistent/global identifiers.

### 4.6 Assumption preservation

Alternative assumptions remain under the explicit `assumptions[]` field.

They may restate or depend on an Analyst assumption or introduce a solution-specific assumption, but this slice does not provide any mechanism that promotes them into `facts`.

The implementation does not rewrite the upstream `ProblemAnalysis` and does not add facts to it.

No additional evidence-scoring or assumption-promotion mechanism is introduced.

### 4.7 Semantic distinctness boundary

The requirement that alternatives be meaningfully distinct is a participant-quality invariant, but arbitrary semantic distinctness cannot be proven reliably by Pydantic schema validation alone.

This slice therefore does **not** introduce:

- embedding similarity;
- fuzzy semantic heuristics;
- a second LLM call to judge the first LLM;
- a hidden Critic stage;
- hard-coded domain-specific alternative taxonomies.

The deterministic contract boundary enforces what can be established reliably, including valid cardinality, unique IDs, closed fields, required structure, qualitative complexity, and upstream constraint references.

Representative deterministic fixtures will contain genuinely different approaches, while canonical reference scenarios and later real-model evaluation remain the appropriate place to assess whether generated alternatives are materially distinct in meaning.

Obvious structural duplication such as duplicate alternative IDs is rejected, but the implementation must not claim that passing structural validation proves semantic originality or optimality.

### 4.8 Role-integrity boundary

`SolutionAlternatives` contains no fields for:

- ranking;
- preferred alternative;
- winner selection;
- final recommendation;
- final decision;
- risk assessment;
- critical review.

Because generated-output contracts are closed, unexpected fields representing those later-stage responsibilities fail structural validation rather than entering trusted output.

Semantic wording embedded inside an otherwise valid free-text field cannot be perfectly classified by schema validation. Role behavior in generated prose is therefore also covered by deterministic participant fixtures and later real-model evaluation rather than by pretending schema validation can understand arbitrary prose.

### 4.9 Provider-neutral upstream payload

The Solution Architect must demonstrate explicit consumption of both required upstream artifacts.

Conceptually the `LLMPort` request payload contains two explicit provider-neutral sections:

```text
review_input
problem_analysis
```

The participant may use the existing Pydantic serialization API to produce standard Python/JSON-compatible structures for those trusted models before passing them through `LLMPort`.

Provider-specific envelopes or SDK objects are prohibited.

The payload contains no Risk Reviewer, Critic, Coordinator, global Review state, hidden conversation memory, or unrelated application data.

### 4.10 Solution Architect validation boundary

Conceptual execution:

```text
ReviewInput + trusted ProblemAnalysis
              ↓
       Solution Architect
              ↓
           LLMPort
              ↓
  untrusted generated mapping
              ↓
 Pydantic structural validation
              ↓
 participant contextual validation
              ↓
   trusted SolutionAlternatives
```

Pydantic owns invariants that depend only on the candidate generated output, including:

- required fields and nested structure;
- strict/valid field types;
- closed-schema behavior;
- allowed qualitative values;
- alternative-count invariant;
- conditional requirement for non-empty `generation_notes` in the zero-alternative case;
- unique required alternative IDs;
- immutable validated collections.

The Solution Architect/application boundary owns invariants requiring actual trusted upstream context, specifically resolving `relevant_constraints` against the current `ProblemAnalysis.constraints`.

Generated structural or contextual validation failures are normalized into a Solution Architect output-validation error category.

Provider/transport errors remain distinguishable and propagate rather than being incorrectly converted into schema errors.

### 4.11 Input and trusted-output preservation

The participant does not mutate `ReviewInput` or `ProblemAnalysis`.

Both are already trusted frozen contracts from Slice 1.

`SolutionAlternative` and `SolutionAlternatives` are also immutable after validation, including their nested collections, so later stages cannot modify accepted Architect output in place without crossing validation again.

## 5. Project Structure

No new architectural layer is required.

Proposed additions are limited to the existing domain and participant boundaries:

```text
src/agentic_review_board/
├── application/
│   └── ports.py                  # unchanged LLMPort
├── domain/
│   ├── analysis.py               # existing ProblemAnalysis
│   ├── review.py                 # existing ReviewInput
│   ├── shared.py                 # new QualitativeLevel
│   └── solutions.py              # new SolutionAlternative / SolutionAlternatives
└── participants/
    ├── analyst.py                # unchanged
    └── solution_architect.py     # new participant

tests/
└── unit/
    ├── test_solution_alternatives.py
    └── test_solution_architect.py
```

Existing package `__init__.py` files may be updated only where required for normal package exposure; no facade or generic agent abstraction is introduced.

Responsibilities:

- `domain/shared.py`: shared qualitative level required by current canonical contracts;
- `domain/solutions.py`: Solution Architect output models and local structural invariants;
- `participants/solution_architect.py`: LLMPort interaction, explicit upstream payload construction, generated-output validation, contextual constraint-reference validation, and normalized participant output failure;
- `tests/unit/`: deterministic contract and participant tests.

No change to `application/ports.py` is expected because the current port already supports this participant.

## 6. Dependency Change

None.

The slice reuses:

```text
pydantic>=2.13,<3
```

under accepted ADR-0001.

No provider SDK, similarity library, orchestration framework, settings library, persistence dependency, or other production package is justified.

The project remains compatible with Python >=3.12 and the existing CI matrix.

## 7. Verification Strategy

### 7.1 `QualitativeLevel` and `SolutionAlternative` contract tests

Verify at minimum:

- `LOW`, `MEDIUM`, and `HIGH` are accepted implementation-complexity values;
- unsupported complexity values are rejected;
- required alternative ID, name, and description reject empty/whitespace-only generated text;
- required collection fields are structurally present;
- nested generated text rejects unrelated primitive coercion where strict text is required;
- unknown fields are rejected;
- externally list-shaped collections can be validated into ordered immutable representations;
- trusted alternative collections cannot be mutated after validation.

### 7.2 `SolutionAlternatives` cardinality and no-alternative tests

Verify at minimum:

- two valid alternatives are accepted;
- three valid alternatives are accepted;
- one alternative is rejected;
- more than three alternatives are rejected;
- zero alternatives with a valid non-empty explanation are accepted;
- zero alternatives without `generation_notes` are rejected;
- zero alternatives with blank `generation_notes` are rejected;
- `generation_notes` is optional when a valid alternative set exists;
- duplicate alternative IDs are rejected;
- top-level ranking, preferred-alternative, final-recommendation, or other unknown role-leakage fields are rejected;
- validated `SolutionAlternatives` and nested collections remain immutable.

### 7.3 Solution Architect happy-path tests

Using a deterministic fake `LLMPort`, verify at minimum:

- the participant supplies both `ReviewInput` and the trusted `ProblemAnalysis` to the model boundary;
- the payload contains no later-stage artifacts;
- a valid two- or three-alternative generated mapping becomes trusted `SolutionAlternatives`;
- an upstream constraint with an ID can be referenced and resolved;
- an upstream constraint without an ID can still be referenced through the approved exact-text fallback;
- valid input artifacts remain unchanged after participant execution.

### 7.4 No-alternative participant tests

Verify an underspecified deterministic scenario where:

- the returned alternatives collection is empty;
- `generation_notes` explicitly explains why useful alternatives cannot yet be formed;
- no artificial variants are manufactured by test fixtures;
- the result is accepted as trusted `SolutionAlternatives`.

A simplified version of the canonical underspecified/microservices scenario may be used as a fixture, but the test must validate behavioral properties rather than hard-code one prescribed answer.

### 7.5 Fail-closed and contextual-reference tests

Verify representative invalid generated output:

- missing required top-level or nested content;
- invalid qualitative complexity;
- duplicate required alternative IDs;
- invalid alternative cardinality;
- zero-alternative result without required explanatory notes;
- unknown role-leakage fields;
- `relevant_constraints` entry that resolves to no constraint in the actual current `ProblemAnalysis`;
- malformed nested alternative content.

Every such case must fail before trusted `SolutionAlternatives` is returned.

### 7.6 Error-separation tests

Verify that:

- Pydantic/contract failures are normalized into the Solution Architect output-validation error category;
- contextual invalid-reference failures use the same participant output-validation category;
- provider/transport exceptions raised by the fake `LLMPort` are not swallowed or misreported as schema failures.

### 7.7 Semantic-quality evaluation boundary

Deterministic fixtures should demonstrate materially different approaches and preserve visible trade-offs, but the unit test suite must not claim to prove arbitrary semantic distinctness from text alone.

Semantic properties such as:

- whether two natural-language alternatives are genuinely distinct;
- whether an alternative is truly compatible with the objective;
- whether all important constraints were recognized;
- whether prose subtly implies a winner;

belong to participant prompt/model evaluation against canonical reference scenarios once real-model integration is introduced, unless a deterministic rule can be justified later.

### 7.8 Existing regression and quality gates

The complete existing suite remains green together with the new deterministic tests:

```text
pytest
ruff check .
mypy
pip check
```

on the supported CI Python versions.

No live LLM endpoint is required.

## 8. Deliberately Deferred

This plan does not decide or implement:

- Review Orchestrator;
- `Review` / `StageExecution` lifecycle;
- stage status transitions;
- Risk Reviewer;
- Critic;
- Coordinator;
- ranking or preferred-alternative behavior;
- final recommendation;
- concrete LLM provider/model/endpoint protocol;
- concrete LLM adapter;
- prompt templates or prompt versioning;
- retry or timeout policy;
- embeddings or semantic-similarity validation;
- automatic semantic judging by a second model;
- UI framework;
- persistence or review history;
- RAG or document ingestion;
- external tools or autonomous actions;
- persistent/global identifiers;
- quantitative implementation estimates or probabilities.

## 9. ADR Status

### ADR-0001 — Pydantic v2 for Structured Contracts and Validation

**Status:** Accepted and directly applicable.

It already governs:

- use of Pydantic models for review contracts;
- closed generated-output validation;
- frozen trusted review data where traceability requires immutability;
- strictness/coercion policy;
- structural versus contextual invariant ownership;
- provider-neutral serialization boundaries;
- local validation remaining mandatory even if a future provider supports native structured output.

### New ADR assessment

No new ADR is required for this plan.

The slice introduces no new dependency, framework, persistence model, external integration, runtime/concurrency pattern, security capability, or model-provider choice.

The new decisions — qualitative enum placement, solution-contract cardinality, and review-local constraint-reference resolution — are direct refinements of already-approved canonical contracts and are sufficiently local to be documented in this plan and the subsequent `data-model.md`.

A new ADR should only be introduced if later planning or implementation evidence reveals a material architectural choice not covered by ADR-0001.

## 10. Planning Follow-up

After this plan is reviewed and approved, the next planning artifact should refine the exact structured data in:

```text
specs/002-solution-architect/data-model.md
```

That document should make the field-level contracts and validation ownership precise without changing the approved feature semantics.

Only after the plan/data-model gate is accepted should implementation tasks be generated.
