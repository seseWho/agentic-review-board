# Implementation Plan: Solution Architect v0.1

**Branch**: `002-solution-architect`  
**Date**: 2026-08-20  
**Spec**: `specs/002-solution-architect/spec.md`  
**Status**: Approved — data-model refinement in progress

## 1. Summary

Implement the smallest executable Solution Architect slice that consumes the trusted `ReviewInput` and `ProblemAnalysis` from Slice 1 and returns trusted `SolutionAlternatives` without introducing review orchestration or later participant responsibilities.

The increment introduces:

- `QualitativeLevel` as the shared `LOW` / `MEDIUM` / `HIGH` scale;
- `ConstraintReference` for explicit references to known upstream constraints;
- `GenerationNotes` for structured generation context and explicit no-alternative blockers;
- `SolutionAlternative` as one candidate approach;
- `SolutionAlternatives` as the validated Solution Architect result;
- a `SolutionArchitect` participant that uses the existing provider-neutral `LLMPort`, performs local structural validation, performs contextual upstream-reference validation, and returns trusted output;
- deterministic tests for normal alternatives, the no-alternative case, fail-closed behavior, reference validation, provider-failure separation, and immutability.

The increment reuses Pydantic v2, the existing Python package structure, and the current `LLMPort` unchanged.

It does not implement the Review Orchestrator, stage lifecycle/status, Risk Reviewer, Critic, Coordinator, ranking, final recommendation, UI, persistence, RAG, tools, or a concrete model provider.

## 2. Technical Context

**Language/Version**: Python >=3.12  
**Production Dependency**: existing `pydantic>=2.13,<3`; no new production dependency  
**Development Dependencies**: existing pytest, Ruff, and mypy configuration  
**Storage**: none  
**Target Platform**: single local Python process and CI  
**External Model Access**: existing provider-neutral `LLMPort`; no concrete SDK or adapter  
**Security Scope**: no credentials, persistence, external tools, autonomous actions, or confidential-data dependency

Existing trusted contracts reused unchanged:

```text
ReviewInput
ProblemAnalysis
AnalysisFinding
FactFinding
LLMPort
```

## 3. Constitution Check

### I. Genuine Agent Collaboration and Role Integrity — PASS

The Solution Architect:

- consumes the original `ReviewInput`;
- consumes validated `ProblemAnalysis`;
- produces only `SolutionAlternatives`;
- does not invoke another participant;
- does not control workflow progression;
- does not perform risk review, critique, ranking, or final recommendation.

This is the first direct downstream consumption of the Analyst result and therefore demonstrates genuine structured collaboration without introducing the full Orchestrator prematurely.

### II. Structured Contracts and Validation — PASS

Generated Solution Architect content remains untrusted until it passes:

1. Pydantic structural/model validation;
2. contextual validation for references that require the actual trusted upstream artifacts.

Critical downstream information in the no-alternative path is not left only in free-form prose: blockers are represented explicitly in `GenerationNotes`.

Invalid generated content never becomes trusted `SolutionAlternatives`.

### III. Traceability, Uncertainty, and Explicit Evidence — PASS

- assumptions remain assumptions;
- relevant constraints are explicit `ConstraintReference` values;
- no-alternative blockers are explicit structured references to `ProblemAnalysis.missing_information` and `ProblemAnalysis.uncertainties`;
- accepted generated collections are immutable after validation;
- upstream outputs remain evidence rather than unquestioned truth.

### IV. Human Decision Authority — PASS

The Solution Architect explores solution space only. It does not select, rank, recommend, or execute a solution.

### V. Minimal Architecture and Evidence-Driven Complexity — PASS

No new dependency, framework, database, orchestration framework, adapter, persistence layer, UI layer, semantic-similarity component, or tool capability is introduced.

`ConstraintReference` and `GenerationNotes` are small local value objects that replace ambiguous string conventions and make required cross-stage information explicit. They do not introduce a generic reference framework.

### VI. Provider Independence and Boundary Discipline — PASS

The existing `LLMPort.generate_structured(role, payload)` remains unchanged. Provider SDK types and transport envelopes stay outside domain and participant contracts.

### VII. Deterministic Testability and Visible Failure — PASS

All behavior is testable with a deterministic `LLMPort` fake and no network access.

### VIII. Security by Minimization and Least Capability — PASS

No new secrets, persistence, filesystem actions, browsing, collaboration integration, tools, or autonomous side effects are introduced.

### IX. Incremental Delivery and Explicit Architectural Decisions — PASS

ADR-0001 already governs the relevant Pydantic and validation-boundary decisions. The new value objects are local refinements of approved contracts and do not justify a new ADR.

**Constitution gate result**: PASS.

## 4. Architectural and Contract Decisions

### 4.1 Reuse Pydantic v2 and fail closed

Generated-output contracts use the established ADR-0001 policy:

- `extra="forbid"` where the contract is closed;
- frozen trusted models;
- immutable validated collections;
- strict generated semantic text;
- required text rejects empty/whitespace-only values;
- no silent semantic repair.

Structural validity does not imply factual correctness or semantic quality.

### 4.2 Shared `QualitativeLevel`

Use the canonical shared values:

```text
LOW
MEDIUM
HIGH
```

`SolutionAlternative.implementation_complexity` uses this scale as a relative engineering judgment, not as probability, duration, cost, or calibrated effort.

### 4.3 Explicit `ConstraintReference`

A relevant constraint reference must state what it refers to instead of overloading one string with source and interpretation semantics.

Conceptually:

```text
ConstraintReference
- source: REVIEW_INPUT | PROBLEM_ANALYSIS
- kind: TEXT | ID
- value: str
```

Rules:

```text
source = REVIEW_INPUT
    → kind MUST be TEXT
    → value MUST exactly match one ReviewInput.constraints textual value

source = PROBLEM_ANALYSIS, kind = ID
    → value MUST exactly match one supplied AnalysisFinding.id

source = PROBLEM_ANALYSIS, kind = TEXT
    → value MUST exactly match one ProblemAnalysis.constraints finding.text
```

Structural validation owns the allowed enum values, non-empty `value`, and the rule that `REVIEW_INPUT` cannot use `ID`.

The `SolutionArchitect` contextual boundary owns resolution against the actual current upstream artifacts.

No fuzzy matching, trimming, lowercasing, indexing convention, semantic similarity, or LLM-assisted repair is introduced.

If a typed reference matches no current target it fails closed. If a typed reference is genuinely ambiguous inside its declared source/kind, it also fails closed.

Repeated identical text in `ReviewInput.constraints` may be treated as the same textual target because the original contract provides no local identity for those strings. Distinct `ProblemAnalysis` findings with the same text make a `PROBLEM_ANALYSIS + TEXT` reference ambiguous; an available unique ID should be used instead.

This design removes cross-source ambiguity and removes the need for special logic to decide whether a bare string is an ID or text.

### 4.4 `GenerationNotes` as structured generation context

Keep the canonical top-level shape:

```text
SolutionAlternatives
- alternatives[]
- generation_notes?
```

but refine `generation_notes` into a small structured value object:

```text
GenerationNotes
- explanation: str
- blocking_missing_information[]
- blocking_uncertainties[]
```

The blocker collections contain explicit references to the corresponding `ProblemAnalysis` categories. Their exact reference representation is defined in `data-model.md` and remains local to this feature; no generic repository-wide reference framework is introduced.

When alternatives are present, `generation_notes` remains optional.

When `alternatives` is empty:

- `generation_notes` is mandatory;
- `explanation` is mandatory and non-empty;
- material blocking missing information and uncertainties must be preserved through the corresponding structured blocker collections when applicable;
- no artificial alternatives are manufactured to satisfy a count.

This preserves the canonical no-alternative behavior while ensuring critical blockers remain structurally inspectable by later stages.

### 4.5 `SolutionAlternative` contract

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

Rules:

- `id` required, non-empty, review-local, with no mandatory prefix convention;
- `name` required non-empty strict text;
- `description` required non-empty strict text;
- `advantages`, `disadvantages`, and `assumptions` are required ordered collections but may be empty when there is genuinely no corresponding material item;
- `implementation_complexity` uses `QualitativeLevel`;
- `relevant_constraints` contains `ConstraintReference` values;
- validated collections are immutable.

The data model must not invent minimum item counts that the approved spec and canonical Agent Model do not require.

### 4.6 `SolutionAlternatives` cardinality

Valid alternative counts are exactly:

```text
0
2
3
```

Therefore:

- 2 or 3 alternatives → normal comparison path;
- 0 alternatives → valid only with required `GenerationNotes`;
- 1 alternative → invalid;
- >3 alternatives → invalid.

Alternative IDs must be unique within the result.

### 4.7 Assumption preservation

Alternative assumptions remain under `assumptions[]`. They may repeat an Analyst assumption or introduce a solution-specific assumption, but this slice provides no mechanism to promote an assumption into a fact or rewrite `ProblemAnalysis`.

### 4.8 Semantic distinctness boundary

The requirement that alternatives be meaningfully distinct is a semantic-quality invariant and cannot be proven reliably by Pydantic alone.

This slice deliberately does not introduce:

- embeddings;
- fuzzy similarity thresholds;
- a second LLM judge;
- a hidden Critic stage;
- domain-specific alternative taxonomies.

Deterministic validation enforces what is reliably structural. Canonical reference scenarios and later real-model evaluation assess semantic distinctness.

### 4.9 Role-integrity boundary

`SolutionAlternatives` contains no structured fields for ranking, preferred alternative, winner selection, final recommendation, final decision, risk assessment, or critical review.

Closed schemas reject those unexpected structured fields. Schema validation does not pretend to classify every possible role violation embedded in arbitrary prose.

### 4.10 Provider-neutral upstream payload

The model boundary receives two explicit provider-neutral sections:

```text
review_input
problem_analysis
```

Trusted Pydantic contracts may be serialized to standard Python/JSON-compatible structures before passing them to `LLMPort`.

No later-stage artifacts or provider-specific objects are included.

### 4.11 Validation boundary

Conceptual execution:

```text
ReviewInput + trusted ProblemAnalysis
              ↓
       SolutionArchitect
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

Pydantic/model validation owns candidate-output-only invariants, including:

- required fields and nested structure;
- strict text;
- closed schemas;
- qualitative enum values;
- valid alternative cardinality;
- required generation notes in the zero-alternative case;
- alternative ID uniqueness;
- local `ConstraintReference` source/kind compatibility;
- immutable collections.

The participant/application boundary owns invariants requiring trusted upstream context, including:

- resolving `ConstraintReference` values;
- resolving no-alternative blocker references against the current `ProblemAnalysis`;
- rejecting unresolved or ambiguous contextual references.

Generated structural/contextual validation failures are normalized into a Solution Architect output-validation error category. Provider/transport errors remain distinguishable and propagate separately.

## 5. Project Structure

No new architectural layer is required.

```text
src/agentic_review_board/
├── application/
│   └── ports.py                   # unchanged
├── domain/
│   ├── analysis.py                # existing
│   ├── review.py                  # existing
│   ├── shared.py                  # QualitativeLevel
│   └── solutions.py               # references + GenerationNotes + solution contracts
└── participants/
    ├── analyst.py                 # unchanged
    └── solution_architect.py      # new participant

tests/
└── unit/
    ├── test_solution_alternatives.py
    └── test_solution_architect.py
```

No generic `references.py`, agent superclass, orchestration abstraction, or extra layer is introduced.

## 6. Dependency Change

None.

The slice reuses:

```text
pydantic>=2.13,<3
```

under ADR-0001.

## 7. Verification Strategy

### 7.1 Shared and alternative contract tests

Verify at minimum:

- `LOW`, `MEDIUM`, `HIGH` accepted and unsupported values rejected;
- required alternative ID/name/description reject blank text;
- required collection fields are present;
- list-shaped external collections validate into immutable ordered representations;
- unknown generated fields are rejected;
- trusted output cannot be mutated after validation.

### 7.2 `ConstraintReference` tests

Verify:

- `REVIEW_INPUT + TEXT` is structurally valid;
- `REVIEW_INPUT + ID` is structurally invalid;
- `PROBLEM_ANALYSIS + ID` and `PROBLEM_ANALYSIS + TEXT` are structurally valid;
- blank reference value is invalid;
- contextual resolution succeeds for exact valid targets;
- unresolved references fail;
- genuinely ambiguous references inside the declared source/kind fail;
- a ReviewInput constraint remains referenceable even if omitted by the Analyst;
- no fuzzy or normalized matching is performed.

### 7.3 `GenerationNotes` and no-alternative tests

Verify:

- 0 alternatives requires `GenerationNotes`;
- explanation is non-empty;
- blocker collections are structurally explicit;
- valid blockers resolve to the corresponding current `ProblemAnalysis` findings;
- unresolved or ambiguous blockers fail context validation;
- representative underspecified fixtures preserve material blockers;
- no artificial alternatives are manufactured.

### 7.4 `SolutionAlternatives` tests

Verify:

- 2 alternatives accepted;
- 3 alternatives accepted;
- 1 rejected;
- >3 rejected;
- 0 accepted only with valid generation notes;
- duplicate alternative IDs rejected;
- structured role-leakage fields rejected;
- nested collections remain immutable.

### 7.5 Participant happy-path tests

Using a deterministic fake `LLMPort`, verify:

- both `ReviewInput` and `ProblemAnalysis` are supplied explicitly;
- no later-stage artifacts are supplied;
- valid generated output becomes trusted `SolutionAlternatives`;
- upstream artifacts remain unchanged;
- context references resolve before output is returned.

### 7.6 Error separation

Verify:

- structural/model failures become Solution Architect output-validation failures;
- contextual reference failures use the same generated-output validation category;
- provider/transport exceptions are not swallowed or relabeled as schema failures.

### 7.7 Semantic-quality evaluation boundary

Unit tests must not claim to prove arbitrary semantic properties such as true alternative distinctness, objective compatibility, complete constraint recognition, or subtle ranking language in prose.

Those belong to representative scenario evaluation and later real-model integration unless a deterministic rule is separately justified.

### 7.8 Regression quality gates

The complete deterministic suite must pass:

```text
pytest
ruff check .
mypy
pip check
```

with no live LLM endpoint.

## 8. Deliberately Deferred

This plan does not implement or decide:

- Review Orchestrator or stage lifecycle;
- Risk Reviewer, Critic, Coordinator;
- ranking or final recommendation;
- concrete LLM provider/adapter;
- prompt templates/versioning;
- retries/timeouts;
- embeddings or semantic judging;
- UI;
- persistence/history;
- RAG/document ingestion;
- external tools/autonomous actions;
- persistent/global IDs;
- generic cross-domain reference infrastructure;
- quantitative complexity estimates.

## 9. ADR Status

ADR-0001 — **Use Pydantic v2 for Structured Contracts and Validation** — remains accepted and directly applicable.

No new ADR is required. `ConstraintReference` and `GenerationNotes` are local contract refinements that make approved semantics explicit without changing architecture, dependencies, runtime, security capability, or provider strategy.

## 10. Planning Follow-up

`data-model.md` must define the exact field-level representation and validation ownership for the value objects above. Only after that model is reviewed and approved should implementation tasks be generated.
