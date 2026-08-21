# Implementation Plan: Risk Reviewer v0.1

**Branch**: `004-risk-reviewer`  
**Date**: 2026-08-21  
**Spec**: `specs/004-risk-reviewer/spec.md`  
**Status**: Revised — awaiting review and approval

## 1. Summary

Implement the smallest fourth executable slice that introduces the Risk Reviewer as a real participant and extends the existing Review Orchestrator from two implemented stages to three:

```text
ReviewInput
    ↓
Analyst
    ↓ ProblemAnalysis
Solution Architect
    ↓ SolutionAlternatives
Risk Reviewer
    ↓ RiskAssessment
```

The slice adds:

- structured immutable risk-domain contracts;
- a provider-neutral `RiskReviewer` participant using the existing `LLMPort`;
- fail-closed structural and contextual validation;
- Risk Reviewer execution-input provenance in `StageExecution`;
- Review lifecycle transitions for Risk Reviewer start/complete/fail;
- explicit Orchestrator execution through the third stage;
- deterministic tests for contract integrity, contextual references, zero-risk behavior, failure handling, sequencing, and review isolation/regression.

Successful Slice 4 state remains deliberately incomplete as a five-stage review:

```text
Review                RUNNING
Analyst               COMPLETED
Solution Architect    COMPLETED
Risk Reviewer         COMPLETED
Critic                PENDING
Coordinator           PENDING
```

A Risk Reviewer failure produces:

```text
Review                INCOMPLETE
Analyst               COMPLETED
Solution Architect    COMPLETED
Risk Reviewer         FAILED
Critic                PENDING
Coordinator           PENDING
```

The Risk Reviewer identifies downside exposure. It does not rank alternatives or recommend a winner.

---

## 2. Technical Context

**Language/Version**: Python >=3.12  
**Production Dependency**: existing `pydantic>=2.13,<3`; no new production dependency  
**Development Dependencies**: existing pytest, Ruff, and mypy  
**Execution Model**: synchronous, sequential, single process  
**Storage**: none; review state remains in-memory only  
**Model Boundary**: existing provider-neutral `LLMPort`  
**Network in Core Tests**: none

Existing contracts reused:

```text
ReviewInput
ProblemAnalysis
SolutionAlternatives
SolutionAlternative
QualitativeLevel
Review
StageExecution
ReviewError
ReviewErrorKind
StageIdentity
StageStatus
ReviewStatus
LLMPort
```

Existing implemented participants reused unchanged unless a narrowly justified regression fix is required:

```text
Analyst
SolutionArchitect
```

No new orchestration framework or provider SDK is introduced.

---

## 3. Constitution Check

### I. Genuine Agent Collaboration and Role Integrity — PASS

Risk Reviewer receives explicit current-review outputs from Analyst and Solution Architect and performs a distinct semantic role: downside exposure analysis.

It SHALL NOT generate alternatives, rank options, issue final recommendations, or control workflow progression.

### II. Structured Contracts and Validation — PASS

Generated Risk Reviewer output is untrusted until:

```text
raw mapping
→ Pydantic structural validation
→ contextual reference validation
→ trusted RiskAssessment
```

Invalid output fails closed and does not enter `StageExecution.output`.

### III. Traceability, Uncertainty, and Explicit Evidence — PASS

Each risk has explicit scope and structured basis. Alternative references and upstream finding references are validated against the current review artifacts.

Assumptions remain assumptions. Missing information and residual uncertainty remain visible.

Execution provenance and generated-output references remain distinct concepts: execution provenance proves same-review handoff through object identity, while generated references prove only that a reference resolves unambiguously within the current trusted review artifacts.

### IV. Human Decision Authority — PASS

Risk Reviewer does not select a winner or create a final recommendation.

### V. Minimal Architecture and Evidence-Driven Complexity — PASS

The increment adds only one risk-domain module, one participant, narrow execution-state extensions, Orchestrator extension, and deterministic tests.

No generic artifact framework, risk engine, taxonomy service, stage registry, or workflow framework is introduced.

### VI. Provider Independence and Boundary Discipline — PASS

Risk Reviewer depends on `LLMPort`; the Orchestrator continues to depend only on participant objects and domain contracts.

### VII. Deterministic Testability and Visible Failure — PASS

A deterministic fake `LLMPort` drives successful, zero-risk, malformed-output, contextual-reference, and execution-failure scenarios.

### VIII. Security by Minimization and Least Capability — PASS

No browsing, RAG, external tools, credentials, raw generated-output storage, private reasoning, or provider-specific diagnostics enter trusted domain state.

### IX. Incremental Delivery and Explicit Architectural Decisions — PASS

The slice extends existing Pydantic contracts and explicit synchronous orchestration without changing runtime architecture. ADR-0001 remains sufficient unless data-model refinement uncovers a materially new architectural choice.

**Constitution gate result**: PASS.

---

## 4. Architectural and Contract Decisions

### 4.1 Introduce a dedicated risk-domain module

Add:

```text
src/agentic_review_board/domain/risks.py
```

This module owns Risk Reviewer output contracts only.

It must not become a generic findings/artifact framework.

Expected concepts:

```text
RiskAssessment
Risk
RiskScope
RiskBasisReference
```

Exact field representation is refined in `data-model.md`.

### 4.2 Reuse QualitativeLevel for severity

Risk severity reuses:

```text
QualitativeLevel.LOW
QualitativeLevel.MEDIUM
QualitativeLevel.HIGH
```

Do not introduce:

- numeric probability;
- likelihood × impact matrices;
- risk scores;
- confidence percentages;
- expected-loss calculations.

Those would add unsupported quantitative semantics.

### 4.3 Keep risk category optional and lightweight

The canonical model describes category as optional and gives representative examples rather than requiring a complete controlled taxonomy.

Therefore Slice 4 should not introduce a global category service or require every category.

`data-model.md` shall choose the smallest closed or strict-text representation consistent with canonical requirements and deterministic validation.

The key invariant is semantic:

- category is optional;
- no exhaustive category coverage is required;
- category does not determine risk existence or severity automatically.

### 4.4 Explicit affected scope

A risk must distinguish:

```text
overall proposal
one alternative
multiple alternatives
```

The representation must be structurally unambiguous.

Recommended direction for data-model refinement:

```text
RiskScope
- kind: OVERALL | ALTERNATIVES
- alternative_ids: tuple[str, ...]
```

with invariants:

```text
OVERALL
→ alternative_ids == ()

ALTERNATIVES
→ one or more unique alternative_ids
→ every id resolves in current SolutionAlternatives
```

This avoids ambiguous free-form `affected_scope` text while remaining much smaller than a generic entity-reference system.

### 4.5 Structured risk basis must identify why the risk exists

Each material risk needs non-empty structured support grounded in visible current-review artifacts.

Risk basis must be able to refer minimally to:

```text
ReviewInput content
ProblemAnalysis finding
specific SolutionAlternative characteristic
```

For a solution alternative, referencing only `ALT-001` is insufficient when the material basis is a particular characteristic of that alternative. The future data model must preserve enough detail to identify the relevant property, for example:

```text
alternative id
+ characteristic kind
+ characteristic value/reference
```

Representative characteristic kinds may include:

```text
ASSUMPTION
ADVANTAGE
DISADVANTAGE
IMPLEMENTATION_COMPLEXITY
RELEVANT_CONSTRAINT
DESCRIPTION
```

The exact enum/field structure belongs to `data-model.md`; this plan requires only that downstream readers can determine not merely which alternative is implicated, but which visible characteristic supports the risk.

The exact basis representation will be defined after examining existing reference patterns in:

```text
FactFinding
AnalysisFinding
ConstraintReference
FindingReference
SolutionAlternative
```

Design constraints:

- current-review local only;
- provider-neutral;
- immutable;
- no global IDs;
- no generic `ArtifactReference` hierarchy;
- references validated contextually by the Risk Reviewer participant;
- text fallback permitted only where current upstream contracts lack mandatory IDs and ambiguity is handled fail-closed;
- assumption-derived basis must remain distinguishable from fact-derived basis;
- a generated textual/local reference proves resolution within the current review context, not historical provenance across reviews.

### 4.6 RiskAssessment may contain zero risks

Contract shape:

```text
RiskAssessment
- risks: tuple[Risk, ...]
- overall_observations: tuple[str, ...]
```

A zero-risk result is valid.

`overall_observations` allows concise explanation of limited evidence, cross-cutting exposure, or remaining uncertainty without fabricating a `Risk`.

It must not contain ranking/recommendation semantics.

### 4.7 Risk identifiers are local and unique

Every `Risk` should have a required local identifier such as:

```text
RISK-001
```

The domain validates uniqueness inside one `RiskAssessment`.

No global/persistent identifier is introduced.

### 4.8 Risk Reviewer participant boundary

Add:

```text
src/agentic_review_board/participants/risk_reviewer.py
```

Conceptual API:

```text
RiskReviewer.assess(
    review_input: ReviewInput,
    problem_analysis: ProblemAnalysis,
    solution_alternatives: SolutionAlternatives,
) -> RiskAssessment
```

Execution follows the existing participant serialization pattern:

```text
LLMPort.generate_structured(
    role="risk_reviewer",
    payload={
        "review_input": review_input.model_dump(mode="json"),
        "problem_analysis": problem_analysis.model_dump(mode="json"),
        "solution_alternatives": solution_alternatives.model_dump(mode="json"),
    },
)
```

Then:

```text
_validate_structure(raw)
_validate_scope_references(...)
_validate_basis_references(...)
return trusted RiskAssessment
```

Known generated-output validation errors map to a dedicated participant exception:

```text
RiskReviewerOutputError
```

This follows the existing Analyst/Solution Architect pattern.

### 4.9 Contextual validation ownership

Pydantic/domain contracts validate intrinsic structure:

- closed/frozen models;
- non-empty required text;
- severity enum;
- scope structural compatibility;
- unique risk IDs;
- non-empty basis per risk;
- collection immutability.

The participant validates references that require current upstream context:

- alternative IDs exist in current `SolutionAlternatives`;
- alternative-characteristic references resolve against that current alternative;
- ProblemAnalysis references resolve uniquely against the current artifact;
- ReviewInput references correspond to visible current input;
- zero-alternative input contains no alternative-specific risk scope/reference.

Contextual reference validation answers:

> Does this generated reference resolve unambiguously inside the trusted artifacts supplied to this Risk Reviewer execution?

It does not answer:

> Did this string historically originate in this Review rather than another equal-looking Review?

That stronger same-execution provenance guarantee belongs to `StageExecution` and is enforced through exact object identity, not textual/local generated identifiers.

Do not embed one entire Review context inside `RiskAssessment` just to perform validation.

### 4.10 Extend StageInput and StageOutput explicitly

Add a third concrete stage-input contract:

```text
RiskReviewerStageInput
- review_input: ReviewInput
- problem_analysis: ProblemAnalysis
- solution_alternatives: SolutionAlternatives
```

Extend unions:

```text
StageInput =
    AnalystStageInput
    | SolutionArchitectStageInput
    | RiskReviewerStageInput

StageOutput =
    ProblemAnalysis
    | SolutionAlternatives
    | RiskAssessment
```

No generic stage payload envelope is introduced.

### 4.11 StageExecution Risk Reviewer typing

Slice 4 permits Risk Reviewer lifecycle shapes:

```text
PENDING
→ no inputs/output/error

RUNNING
→ RiskReviewerStageInput
→ no output/error

COMPLETED
→ RiskReviewerStageInput
→ RiskAssessment
→ no error

FAILED
→ RiskReviewerStageInput
→ ReviewError
→ no output
```

Critic and Coordinator remain PENDING-only.

### 4.12 Same-execution provenance extends through third stage

For any started Risk Reviewer stage:

```text
risk.inputs.review_input
    is review.review_input

risk.inputs.problem_analysis
    is analyst.output

risk.inputs.solution_alternatives
    is solution_architect.output
```

The current in-memory identity rule remains appropriate because Slice 4 still has no persistence/rehydration.

No equal-but-independent upstream object is accepted as `StageExecution` provenance, even if its value is identical.

This object-identity rule is deliberately separate from contextual validation of generated local references inside `RiskAssessment`.

### 4.13 Preserve identity-based Review semantics from Slice 3

Canonical stage order remains useful for deterministic creation and presentation, but Review semantics must continue to use `StageIdentity` rather than tuple position.

Slice 4 extensions to:

- aggregate validators;
- lifecycle coherence checks;
- provenance checks;
- transition preconditions;
- stage retrieval;

must resolve stages through identity-based lookup such as:

```text
review.stage(StageIdentity.RISK_REVIEWER)
```

and must not reintroduce positional assumptions such as:

```text
review.stages[2]
```

for semantic validation.

`Review.create(...)` continues to emit canonical stage order; transitions continue to preserve the existing tuple order.

### 4.14 Extend valid Review lifecycle shapes minimally

Successful Slice 4 adds two new RUNNING prefixes after Solution Architect completion:

```text
Analyst COMPLETED
Architect COMPLETED
Risk Reviewer RUNNING
Critic PENDING
Coordinator PENDING
```

and:

```text
Analyst COMPLETED
Architect COMPLETED
Risk Reviewer COMPLETED
Critic PENDING
Coordinator PENDING
```

Existing earlier Slice 3 RUNNING prefixes remain valid.

Slice 4 INCOMPLETE adds:

```text
Analyst COMPLETED
Architect COMPLETED
Risk Reviewer FAILED
Critic PENDING
Coordinator PENDING
```

Existing Analyst/Architect failure shapes remain valid.

`COMPLETED` remains unreachable because Critic and Coordinator are PENDING-only.

### 4.15 Explicit Risk Reviewer transitions

Extend `Review` with narrow stage-specific transitions:

```text
start_risk_reviewer()
complete_risk_reviewer(risk_assessment)
fail_risk_reviewer(error)
```

Preconditions:

```text
Review RUNNING
Analyst COMPLETED with ProblemAnalysis
Solution Architect COMPLETED with SolutionAlternatives
Risk Reviewer PENDING/RUNNING as appropriate
Critic + Coordinator PENDING
```

Failure transition atomically builds:

```text
Review INCOMPLETE
Risk Reviewer FAILED
```

while preserving Analyst and Architect stages exactly.

No generic transition engine is introduced.

### 4.16 Extend explicit Orchestrator sequence, not architecture

`ReviewOrchestrator` constructor becomes conceptually:

```text
ReviewOrchestrator(
    analyst,
    solution_architect,
    risk_reviewer,
)
```

After Solution Architect completion:

```text
start Risk Reviewer
retrieve trusted Analyst + Architect outputs from current Review
invoke RiskReviewer.assess(...)
complete or fail Risk Reviewer
return Review
```

Invocation order must be exactly:

```text
analyst
solution_architect
risk_reviewer
```

No stage loop, handler registry, graph engine, or plugin mechanism yet.

Three stages are still small enough that explicit code is easier to inspect and safer to evolve.

### 4.17 Risk Reviewer failure boundary

Catch exceptions only around:

```text
RiskReviewer.assess(...)
```

Mapping:

```text
RiskReviewerOutputError
→ ReviewErrorKind.OUTPUT_VALIDATION
→ "Risk Reviewer output validation failed"

other ordinary Exception from participant call
→ ReviewErrorKind.EXECUTION
→ "Risk Reviewer execution failed"
```

Do not copy raw exception text into trusted Review state.

Domain/lifecycle defects outside this participant call continue to propagate.

### 4.18 Preserve review isolation

The Orchestrator remains stateless regarding Review execution.

Adding Risk Reviewer must not introduce:

- current review field;
- previous assessment cache;
- cross-review risk memory;
- global assumptions;
- active-review repository.

Sequential Review executions through the same participants remain isolated.

---

## 5. Proposed Project Structure

```text
src/agentic_review_board/
├── application/
│   ├── orchestrator.py             # extend explicit sequence through Risk Reviewer
│   └── ports.py                    # unchanged
├── domain/
│   ├── analysis.py                 # existing
│   ├── execution.py                # extend Risk Reviewer execution state
│   ├── review.py                   # existing
│   ├── risks.py                    # new Risk/RiskAssessment contracts
│   ├── shared.py                   # existing QualitativeLevel
│   └── solutions.py                # existing
└── participants/
    ├── analyst.py                  # existing
    ├── solution_architect.py       # existing
    └── risk_reviewer.py            # new

tests/unit/
├── test_risks.py                   # new intrinsic risk-domain tests
├── test_risk_reviewer.py           # new participant/context-validation tests
├── test_review_execution.py        # extend aggregate state/provenance
├── test_review_transitions.py      # extend Risk Reviewer transitions
└── test_review_orchestrator.py     # extend 3-stage execution/failure/isolation
```

No new infrastructure, persistence, adapters, UI, generic workflow, or generic artifact package.

---

## 6. Dependency Change

None.

Reuse existing:

```text
pydantic>=2.13,<3
```

No risk library, probability package, workflow framework, or provider SDK is required.

---

## 7. Verification Strategy

### 7.1 Risk domain contract tests

Verify:

- models closed/frozen;
- tuple-backed collections;
- strict non-empty required text;
- severity accepts only `QualitativeLevel`;
- risk IDs unique within assessment;
- scope structural invariants;
- each risk has non-empty basis;
- optional mitigation/residual uncertainty/category semantics;
- zero risks accepted;
- no numeric probability field exists.

### 7.2 Participant structural-validation and role-integrity tests

Drive deterministic raw mappings and verify:

- valid assessment accepted;
- malformed risk rejected;
- invalid severity rejected;
- duplicate risk IDs rejected;
- invalid scope shape rejected;
- empty basis rejected;
- extra/unexpected fields rejected;
- generated `ranking`, `preferred_alternative`, `recommendation`, final-decision fields, or unsupported numeric probability fields are rejected rather than trusted;
- Risk Reviewer output remains limited to risk analysis and does not silently absorb Coordinator responsibilities.

### 7.3 Contextual scope validation tests

Verify:

- overall scope needs no alternative IDs;
- one/multiple current alternative IDs resolve;
- unknown alternative ID rejected;
- duplicate affected alternative IDs rejected structurally or contextually;
- alternative-specific scope rejected when upstream alternatives are empty.

### 7.4 Contextual basis validation tests

Verify references resolve only against the trusted artifacts supplied to the current Risk Reviewer execution:

- ReviewInput content;
- ProblemAnalysis findings;
- specific characteristics of current SolutionAlternative items.

For SolutionAlternative basis, verify enough detail is present to identify the characteristic supporting the risk rather than accepting an alternative ID alone as complete basis when a particular characteristic is claimed.

Reject:

- unknown references;
- ambiguous text fallback;
- mismatched ID/text where both are supplied;
- unknown or mismatched alternative characteristic references;
- unsupported claims of source provenance.

Do not assert that textual/local identifiers can distinguish two historically separate reviews containing equal values. Their contract is contextual resolution within the current trusted inputs only.

### 7.5 Zero-risk and zero-alternative tests

Verify:

- zero-risk `RiskAssessment` accepted;
- zero alternatives do not prevent Risk Reviewer invocation;
- no alternative-specific scope/reference is accepted if there are no alternatives;
- overall observations may explain limited evidence without fabricating risk.

### 7.6 Execution aggregate tests

Extend existing tests for:

- RiskReviewerStageInput typing;
- RiskAssessment output typing;
- Critic/Coordinator still PENDING-only;
- new valid RUNNING prefixes;
- new valid INCOMPLETE Risk Reviewer failure shape;
- same-instance Risk Reviewer provenance for ReviewInput, ProblemAnalysis, and SolutionAlternatives;
- rejection of equal-but-independent upstream objects as StageExecution provenance;
- identity-based Review validation/lookup remains valid even if a directly constructed stage tuple is not in canonical order;
- `Review.create(...)` still emits canonical order and transitions preserve it.

### 7.7 Transition tests

Verify:

```text
Risk Reviewer PENDING → RUNNING
RUNNING → COMPLETED
RUNNING → FAILED
```

and:

- only after Analyst + Architect completed;
- transitions find stages by `StageIdentity`, not semantic tuple position;
- preserved exact upstream stage objects;
- exact trusted RiskAssessment output reuse;
- atomic Review INCOMPLETE on Risk Reviewer failure;
- illegal/repeated transitions rejected;
- Critic/Coordinator unchanged.

### 7.8 Successful orchestration test

Using one recording fake `LLMPort`, verify exact role invocation order:

```text
analyst
solution_architect
risk_reviewer
```

Verify:

- each stage input recorded before invocation;
- Risk Reviewer receives exact current ReviewInput;
- exact Analyst output;
- exact Architect output;
- all three implemented stages complete;
- Critic/Coordinator remain PENDING;
- final Review remains RUNNING;
- no ranking/recommendation introduced.

### 7.9 Risk Reviewer failure tests

Drive separately:

```text
RiskReviewerOutputError
ordinary participant Exception
```

Verify:

- Risk Reviewer FAILED;
- Review INCOMPLETE;
- exact recorded stage inputs retained;
- no RiskAssessment output;
- Analyst/Architect completed state preserved;
- Critic/Coordinator PENDING;
- safe error kind/message;
- raw exception detail absent.

### 7.10 Regression and isolation tests

Verify:

- existing Analyst failure semantics unchanged;
- existing Architect failure semantics unchanged;
- zero-alternative behavior unchanged;
- two sequential three-stage reviews remain isolated;
- incomplete prior review does not contaminate a fresh review;
- Orchestrator still catches only participant-call exceptions.

### 7.11 Quality gates

Run full repository gates:

```text
python -m pytest
python -m ruff check .
python -m mypy
python -m pip check
```

Then inspect production source to confirm Slice 4 adds no:

- provider SDK;
- direct Orchestrator → `LLMPort` dependency;
- Critic/Coordinator implementation;
- ranking/final-decision logic;
- numeric probability/risk-scoring model;
- persistence/RAG/UI/tools;
- generic workflow/stage registry;
- generic artifact/reference repository.

---

## 8. Deliberately Deferred

This plan does not implement or decide:

- Critic / CriticalReview;
- Coordinator / FinalReview;
- ranking, recommendation, preferred alternative, final confidence;
- likelihood/impact matrices or quantitative risk scoring;
- automated mitigation execution;
- external policy/security scanners;
- browsing, RAG, document ingestion, embeddings, MCP, or tools;
- provider-specific transport taxonomy;
- retries, backoff, timeout, cancellation, pause/resume;
- persistence, review history, serialization/rehydration, durable IDs;
- async/concurrent stages;
- UI/view models;
- generic workflow engine;
- generic participant registry;
- generic artifact/reference repository;
- organization-wide risk taxonomy service.

---

## 9. ADR Status

ADR-0001 — **Use Pydantic v2 for Structured Contracts and Validation** — remains applicable.

No new ADR is currently required because Slice 4:

- introduces no new dependency;
- preserves synchronous local execution;
- preserves provider boundaries;
- extends existing explicit union/contracts rather than introducing a new generic runtime pattern;
- keeps provenance in-memory and review-local;
- adds no persistence, concurrency, integration, or security capability.

If data-model refinement shows that a reusable cross-stage artifact-reference architecture is genuinely necessary, that would require separate architectural review rather than being smuggled into Risk Reviewer v0.1.

---

## 10. Data-Model Follow-up

Before tasks are generated, `data-model.md` must refine exactly:

- `Risk` fields;
- `RiskAssessment` fields;
- affected-scope representation and invariants;
- risk-basis reference representation, including alternative-characteristic granularity;
- contextual resolution rules for ReviewInput, ProblemAnalysis, and SolutionAlternatives;
- the explicit distinction between generated-reference contextual resolution and StageExecution same-instance provenance;
- category representation;
- zero-risk semantics;
- uniqueness rules;
- `RiskReviewerStageInput`;
- StageInput/StageOutput union extension;
- exact valid Slice 4 Review RUNNING/INCOMPLETE shapes;
- identity-based stage lookup/validation requirements;
- same-instance provenance rules;
- Risk Reviewer transitions;
- stable participant failure messages;
- typing/narrowing required by Orchestrator.

Only after `data-model.md` is reviewed and approved should implementation tasks be generated.
