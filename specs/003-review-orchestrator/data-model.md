# Data Model: Review Orchestrator v0.1

**Feature:** `specs/003-review-orchestrator/spec.md`  
**Plan:** `specs/003-review-orchestrator/plan.md`  
**ADR:** `docs/adr/ADR-0001-pydantic-v2-for-structured-contracts.md`  
**Status:** Draft — awaiting internal review

## 1. Purpose

This document defines the structured review-execution state introduced by **Review Orchestrator v0.1**.

It refines the approved feature specification and implementation plan without adding later participant behavior or a generic workflow framework.

The increment introduces:

- `StageIdentity`;
- `StageStatus`;
- `ReviewStatus`;
- `ReviewErrorKind`;
- `ReviewError`;
- `AnalystStageInput`;
- `SolutionArchitectStageInput`;
- `StageExecution`;
- `Review`.

It also defines the valid immutable state transitions required by Slice 3.

Pydantic v2 remains the approved structured-contract implementation mechanism under ADR-0001.

---

## 2. Shared Modeling Rules

The following rules apply to Slice 3 execution-state contracts:

- trusted review state is represented explicitly rather than inferred from logs or hidden conversational memory;
- execution-state models are closed and reject unexpected structured fields;
- trusted state models are frozen;
- collections retained in trusted state are immutable;
- every constructed `StageExecution` must satisfy its lifecycle and identity/type invariants;
- every constructed `Review` must satisfy both per-stage invariants and cross-stage/global lifecycle invariants;
- transitions create new validated snapshots rather than mutating existing trusted state;
- transition code must not use unchecked `model_copy(update=...)` semantics that bypass validation;
- participant-generated outputs become eligible for stage completion only after the existing participant validation boundary returns a trusted domain model;
- review/domain state contains no provider SDK types, raw provider envelopes, credentials, private chain-of-thought, or full raw model responses;
- Slice 3 introduces no persistent identifiers, timestamps, retry metadata, persistence schema, workflow registry, or generic artifact abstraction.

Conceptually, execution-state models follow:

```text
frozen = true
extra = forbid
```

Exact Python syntax belongs to implementation, but the field shapes and invariants below are normative for this slice.

---

## 3. Existing Trusted Models Reused

Slice 3 consumes these existing contracts unchanged:

```text
ReviewInput
ProblemAnalysis
SolutionAlternatives
```

Their existing immutability and validation remain authoritative.

The existing participants also remain unchanged semantically:

```text
Analyst.analyze(ReviewInput) -> ProblemAnalysis

SolutionArchitect.propose(
    ReviewInput,
    ProblemAnalysis,
) -> SolutionAlternatives
```

The Orchestrator receives only trusted return values from those participant methods.

---

## 4. StageIdentity

Represents one canonical review-stage identity.

### Values

```text
ANALYST
SOLUTION_ARCHITECT
RISK_REVIEWER
CRITIC
COORDINATOR
```

These five values are the complete canonical MVP stage set.

Slice 3 executes only:

```text
ANALYST
SOLUTION_ARCHITECT
```

The remaining identities are present in review state but remain `PENDING` throughout Slice 3.

A module-level canonical order may be defined for deterministic review creation and display:

```text
ANALYST
SOLUTION_ARCHITECT
RISK_REVIEWER
CRITIC
COORDINATOR
```

Storage position is not the semantic identity of a stage; validation and lookup must use `StageIdentity` rather than tuple index meaning.

---

## 5. StageStatus

Represents the lifecycle state of one stage execution.

### Values

```text
PENDING
RUNNING
COMPLETED
FAILED
```

Allowed Slice 3 transitions are exactly:

```text
PENDING → RUNNING
RUNNING → COMPLETED
RUNNING → FAILED
```

No transition from `COMPLETED` or `FAILED` back to `RUNNING` exists in this increment.

No `BLOCKED`, `PAUSED`, `CANCELLED`, `RETRYING`, or timeout status is introduced.

---

## 6. ReviewStatus

Represents the overall lifecycle state of one review execution.

### Values

```text
CREATED
RUNNING
INCOMPLETE
COMPLETED
```

Slice 3 uses:

```text
CREATED → RUNNING
RUNNING → INCOMPLETE
```

`COMPLETED` remains part of the canonical lifecycle contract but cannot be reached by a valid Slice 3 review because Risk Reviewer, Critic, and Coordinator cannot leave `PENDING` in this increment.

A successful Slice 3 execution therefore ends as:

```text
ReviewStatus = RUNNING

ANALYST             = COMPLETED
SOLUTION_ARCHITECT  = COMPLETED
RISK_REVIEWER       = PENDING
CRITIC              = PENDING
COORDINATOR         = PENDING
```

Here `RUNNING` means the review has started and has not reached a terminal review outcome; it does not require a participant to be actively executing at the instant of inspection.

---

## 7. Stage-Local Input Provenance

Slice 3 records the trusted inputs supplied to each executed participant using two small stage-specific value objects.

These are not provider request payloads. They are in-memory review-traceability contracts.

### 7.1 AnalystStageInput

```text
AnalystStageInput
- review_input: ReviewInput
```

Rules:

- closed and frozen;
- `review_input` is the current review's original trusted `ReviewInput`;
- no serialized copy or provider-specific representation is required;
- no other upstream artifact is valid for Analyst execution.

### 7.2 SolutionArchitectStageInput

```text
SolutionArchitectStageInput
- review_input: ReviewInput
- problem_analysis: ProblemAnalysis
```

Rules:

- closed and frozen;
- `review_input` is the current review's original trusted `ReviewInput`;
- `problem_analysis` is the trusted result owned by the completed Analyst stage of the same current review;
- no regenerated, repaired, independently inferred, or cross-review `ProblemAnalysis` is valid;
- no later-stage artifact is included.

### 7.3 StageInput type

For Slice 3:

```text
StageInput = AnalystStageInput | SolutionArchitectStageInput
```

No generic `Artifact`, `StagePayload`, arbitrary mapping, reference registry, or plugin-defined input envelope is introduced.

Future slices may extend this union only when their participant contracts are approved.

---

## 8. ReviewErrorKind

Represents the failure classification that Slice 3 can reliably determine at the participant invocation boundary.

### Values

```text
OUTPUT_VALIDATION
EXECUTION
```

### OUTPUT_VALIDATION

Used when an existing participant raises its known generated-output validation exception:

```text
AnalystOutputError
SolutionArchitectOutputError
```

This means model-generated content failed the participant's trusted-output boundary.

### EXECUTION

Used when another ordinary exception is raised from inside the invoked participant call and Slice 3 has no more reliable provider-neutral classification.

`EXECUTION` does not claim that the failure was specifically a provider, transport, authentication, timeout, or internal model-service error.

Slice 3 does not introduce a finer provider-error taxonomy before a provider-neutral adapter/error contract exists.

Internal lifecycle/orchestrator defects outside the participant call boundary are not represented as ordinary `ReviewError` stage failures; they propagate to the caller.

---

## 9. ReviewError

Represents concise trusted failure information for a failed stage.

### Fields

```text
ReviewError
- kind: ReviewErrorKind
- message: str
```

### `kind`

Required and restricted to the Slice 3 values defined above.

### `message`

Rules:

- required strict text;
- non-empty and not whitespace-only;
- concise and suitable for later user-visible presentation;
- produced by trusted application/orchestration code, not copied from arbitrary generated model content;
- must not contain private chain-of-thought, full prompts, full raw model responses, credentials, secrets, or stack traces.

The Orchestrator should use stable messages such as:

```text
Analyst output validation failed
Analyst execution failed
Solution Architect output validation failed
Solution Architect execution failed
```

The raw source exception text is not part of trusted `ReviewError` state in Slice 3.

Stage identity is not duplicated inside `ReviewError`; it is already owned by the surrounding `StageExecution`.

---

## 10. Stage Output Type

For Slice 3:

```text
StageOutput = ProblemAnalysis | SolutionAlternatives
```

Identity/type compatibility is mandatory:

```text
ANALYST + COMPLETED
    → output must be ProblemAnalysis

SOLUTION_ARCHITECT + COMPLETED
    → output must be SolutionAlternatives
```

Risk Reviewer, Critic, and Coordinator cannot have outputs in Slice 3 because their stages remain `PENDING`.

No untyped generated mapping can be stored as trusted stage output.

---

## 11. StageExecution

Represents the complete inspectable in-memory execution record for one canonical stage.

### Fields

```text
StageExecution
- identity: StageIdentity
- status: StageStatus
- inputs: StageInput | None
- output: StageOutput | None
- error: ReviewError | None
```

The model is closed and frozen.

### 11.1 Generic status-shape invariant

Every stage must satisfy:

```text
PENDING
- inputs = None
- output = None
- error = None

RUNNING
- inputs != None
- output = None
- error = None

COMPLETED
- inputs != None
- output != None
- error = None

FAILED
- inputs != None
- output = None
- error != None
```

A trusted output and terminal error can never coexist.

### 11.2 Analyst identity/type invariant

For `identity = ANALYST`:

```text
PENDING
    inputs = None
    output = None
    error = None

RUNNING
    inputs = AnalystStageInput
    output = None
    error = None

COMPLETED
    inputs = AnalystStageInput
    output = ProblemAnalysis
    error = None

FAILED
    inputs = AnalystStageInput
    output = None
    error = ReviewError
```

`SolutionArchitectStageInput` and `SolutionAlternatives` are invalid on the Analyst stage.

### 11.3 Solution Architect identity/type invariant

For `identity = SOLUTION_ARCHITECT`:

```text
PENDING
    inputs = None
    output = None
    error = None

RUNNING
    inputs = SolutionArchitectStageInput
    output = None
    error = None

COMPLETED
    inputs = SolutionArchitectStageInput
    output = SolutionAlternatives
    error = None

FAILED
    inputs = SolutionArchitectStageInput
    output = None
    error = ReviewError
```

`AnalystStageInput` and `ProblemAnalysis` are invalid as Solution Architect stage-specific input/output types.

### 11.4 Unimplemented-stage invariant

For Slice 3:

```text
RISK_REVIEWER
CRITIC
COORDINATOR
```

must always satisfy:

```text
status = PENDING
inputs = None
output = None
error = None
```

This is an intentional Slice 3 restriction, not a permanent canonical rule. Each later participant slice must extend the trusted input/output union and relax only the corresponding stage restriction when its contract is approved.

### 11.5 StageExecution validation ownership

`StageExecution` owns invariants that depend only on:

- its own identity;
- its own status;
- its own input type;
- its own output type;
- presence/absence of its own error.

It does not independently prove that its upstream artifacts belong to the same `Review`; that cross-artifact provenance belongs to the `Review` aggregate.

---

## 12. Review

Represents one isolated in-memory review execution.

### Fields

```text
Review
- review_input: ReviewInput
- status: ReviewStatus
- stages: tuple[StageExecution, ...]
```

The model is closed and frozen.

There are no stored duplicate fields such as:

```text
Review.problem_analysis
Review.solution_alternatives
```

Trusted outputs are logically owned by their completed stage records.

### 12.1 Stage set invariant

Every `Review` contains exactly five stage records.

Each canonical `StageIdentity` appears exactly once:

```text
ANALYST
SOLUTION_ARCHITECT
RISK_REVIEWER
CRITIC
COORDINATOR
```

Duplicate identities, missing identities, or extra stages are invalid.

The canonical creation helper emits the stages in canonical sequence, and transitions preserve that order. Validation must not rely on positional index as stage identity.

### 12.2 Original-input invariant

`Review.review_input` is the original validated `ReviewInput` for the lifetime of this review snapshot lineage.

Transitions preserve it unchanged.

### 12.3 Cross-stage input provenance invariant

When Analyst has started:

```text
AnalystStageInput.review_input
    == Review.review_input
```

When Solution Architect has started:

```text
SolutionArchitectStageInput.review_input
    == Review.review_input
```

and:

```text
SolutionArchitectStageInput.problem_analysis
    == completed Analyst StageExecution.output
```

The runtime transition path must reuse the trusted upstream immutable objects directly rather than serialize/reparse or regenerate them.

The aggregate-level validation guarantee uses semantic model equality rather than Python object identity, because object identity is not a stable serializable domain invariant. The canonical transition implementation nevertheless passes the exact current trusted object instances.

This means the Solution Architect input record references the Analyst-owned immutable result for provenance; it does not become a second logical owner of an independently mutable copy.

### 12.4 CREATED invariant

For:

```text
Review.status = CREATED
```

all five stages must be:

```text
PENDING
```

with no inputs, outputs, or errors.

### 12.5 RUNNING invariant

For:

```text
Review.status = RUNNING
```

all of the following must hold:

- no stage is `FAILED`;
- Risk Reviewer, Critic, and Coordinator are `PENDING`;
- Solution Architect can be non-`PENDING` only when Analyst is `COMPLETED`;
- the state must represent a valid sequential prefix of the implemented workflow.

Valid Slice 3 `RUNNING` shapes include:

```text
A) execution started, Analyst not started yet
ANALYST             PENDING
SOLUTION_ARCHITECT  PENDING
later stages        PENDING

B) Analyst executing
ANALYST             RUNNING
SOLUTION_ARCHITECT  PENDING
later stages        PENDING

C) Analyst completed, handoff not started
ANALYST             COMPLETED
SOLUTION_ARCHITECT  PENDING
later stages        PENDING

D) Solution Architect executing
ANALYST             COMPLETED
SOLUTION_ARCHITECT  RUNNING
later stages        PENDING

E) implemented Slice 3 work completed
ANALYST             COMPLETED
SOLUTION_ARCHITECT  COMPLETED
later stages        PENDING
```

No other `RUNNING` combination is valid in Slice 3.

### 12.6 INCOMPLETE invariant

For:

```text
Review.status = INCOMPLETE
```

exactly one implemented mandatory stage has failed and all dependent later stages remain `PENDING`.

Valid Slice 3 shapes are exactly:

```text
A) Analyst failure
ANALYST             FAILED
SOLUTION_ARCHITECT  PENDING
RISK_REVIEWER       PENDING
CRITIC              PENDING
COORDINATOR         PENDING

B) Solution Architect failure
ANALYST             COMPLETED
SOLUTION_ARCHITECT  FAILED
RISK_REVIEWER       PENDING
CRITIC              PENDING
COORDINATOR         PENDING
```

An `INCOMPLETE` review with no failed stage is invalid.

A review with both Analyst and Solution Architect failed is invalid because dependent execution must stop after the first mandatory failure.

### 12.7 COMPLETED invariant

For:

```text
Review.status = COMPLETED
```

all five mandatory canonical stages must be `COMPLETED`.

Because Slice 3 restricts Risk Reviewer, Critic, and Coordinator to `PENDING`, no valid Slice 3 `Review` can currently satisfy this invariant.

The enum value exists now so the domain lifecycle remains aligned with the canonical architecture; future participant slices will extend valid stage states incrementally.

---

## 13. Review Creation

The domain provides one canonical creation operation conceptually equivalent to:

```text
Review.create(review_input)
```

Result:

```text
Review
- review_input = supplied trusted ReviewInput
- status = CREATED
- stages = five canonical StageExecution records
    - each status = PENDING
    - each inputs = None
    - each output = None
    - each error = None
```

Creation must produce fresh stage objects for every new Review.

No prior review state, output, error, assumption, or stage-input record is reused.

No persistent review identifier is introduced.

---

## 14. Review Transition Operations

Slice 3 uses explicit stage-specific transitions rather than a generic workflow engine or dynamic stage registry.

The exact implementation may use instance methods or small domain functions, but the operations and preconditions below are normative.

### 14.1 Start review

Conceptually:

```text
Review.start()
```

Precondition:

```text
status == CREATED
```

Result:

```text
status = RUNNING
all stages remain PENDING
```

Calling start on any non-`CREATED` review fails explicitly.

### 14.2 Start Analyst

Conceptually:

```text
Review.start_analyst()
```

Preconditions:

```text
Review.status == RUNNING
Analyst.status == PENDING
Solution Architect and later stages == PENDING
```

Result:

```text
Analyst.status = RUNNING
Analyst.inputs = AnalystStageInput(
    review_input = Review.review_input
)
```

No other stage changes.

### 14.3 Complete Analyst

Conceptually:

```text
Review.complete_analyst(problem_analysis)
```

Preconditions:

```text
Review.status == RUNNING
Analyst.status == RUNNING
problem_analysis is trusted ProblemAnalysis
```

Result:

```text
Analyst.status = COMPLETED
Analyst.inputs = preserved existing AnalystStageInput
Analyst.output = supplied trusted ProblemAnalysis
Analyst.error = None
```

Review remains `RUNNING`.

### 14.4 Fail Analyst

Conceptually:

```text
Review.fail_analyst(error)
```

Preconditions:

```text
Review.status == RUNNING
Analyst.status == RUNNING
error is trusted ReviewError
```

One validated target `Review` snapshot is produced atomically:

```text
Review.status = INCOMPLETE
Analyst.status = FAILED
Analyst.inputs = preserved existing AnalystStageInput
Analyst.output = None
Analyst.error = supplied ReviewError
all downstream stages remain PENDING
```

No externally observable intermediate `RUNNING + Analyst FAILED` Review snapshot is valid.

### 14.5 Start Solution Architect

Conceptually:

```text
Review.start_solution_architect()
```

Preconditions:

```text
Review.status == RUNNING
Analyst.status == COMPLETED
Analyst.output is ProblemAnalysis
Solution Architect.status == PENDING
later stages == PENDING
```

Result:

```text
Solution Architect.status = RUNNING
Solution Architect.inputs = SolutionArchitectStageInput(
    review_input = Review.review_input,
    problem_analysis = exact trusted Analyst output
)
```

The transition does not regenerate, copy semantically, or revalidate a new analysis through the LLM boundary.

### 14.6 Complete Solution Architect

Conceptually:

```text
Review.complete_solution_architect(solution_alternatives)
```

Preconditions:

```text
Review.status == RUNNING
Analyst.status == COMPLETED
Solution Architect.status == RUNNING
solution_alternatives is trusted SolutionAlternatives
```

Result:

```text
Solution Architect.status = COMPLETED
Solution Architect.inputs = preserved existing SolutionArchitectStageInput
Solution Architect.output = supplied trusted SolutionAlternatives
Solution Architect.error = None
Review.status remains RUNNING
```

A valid zero-alternative `SolutionAlternatives` object is treated exactly like any other trusted successful Solution Architect output.

### 14.7 Fail Solution Architect

Conceptually:

```text
Review.fail_solution_architect(error)
```

Preconditions:

```text
Review.status == RUNNING
Analyst.status == COMPLETED
Solution Architect.status == RUNNING
error is trusted ReviewError
```

One validated target Review snapshot is produced atomically:

```text
Review.status = INCOMPLETE
Analyst remains COMPLETED with its trusted output
Solution Architect.status = FAILED
Solution Architect.inputs = preserved existing inputs
Solution Architect.output = None
Solution Architect.error = supplied ReviewError
later stages remain PENDING
```

No externally observable intermediate `RUNNING + Solution Architect FAILED` Review snapshot is valid.

---

## 15. Validated Snapshot Replacement Mechanism

Every transition reconstructs a complete validated target `Review` using:

- the unchanged original `ReviewInput`;
- a new immutable stage tuple containing four preserved stage objects and one validated replacement stage where applicable;
- the target `ReviewStatus`.

Conceptually:

```text
new_stages = tuple(
    replacement if stage.identity == target_identity else stage
    for stage in current_review.stages
)

new_review = Review(
    review_input = current_review.review_input,
    status = target_status,
    stages = new_stages,
)
```

This reconstruction must pass normal `Review` validation.

Do not use unchecked Pydantic model-copy updates that skip model validators.

The tuple remains tiny and fixed at five stages, so rebuilding the snapshot is intentionally preferred over adding mutable state machinery or a transactional abstraction.

---

## 16. Stage Lookup and Type Narrowing

The Review domain may provide a small identity-based lookup helper conceptually equivalent to:

```text
Review.stage(identity: StageIdentity) -> StageExecution
```

It performs a five-element lookup by `StageIdentity`; it does not use stage position as semantic identity.

The Orchestrator retrieves the Analyst result through explicit type narrowing rather than a generic artifact accessor.

Conceptually:

```text
analyst_stage = review.stage(ANALYST)

if analyst_stage.status != COMPLETED:
    internal lifecycle error

if not isinstance(analyst_stage.output, ProblemAnalysis):
    internal lifecycle error

problem_analysis = analyst_stage.output
```

Because a valid `Review` already enforces the Analyst output invariant, these checks primarily satisfy static typing and defend against internal misuse.

Any such invariant failure occurs outside the participant invocation boundary and must propagate rather than become an ordinary participant `ReviewError`.

No generic typed artifact repository or reflection-based output registry is introduced.

---

## 17. Validation Ownership

### 17.1 Existing participant boundary

Existing participants remain responsible for converting untrusted generated mappings into trusted outputs:

```text
Analyst
    raw generated mapping
    → structural/context validation
    → ProblemAnalysis

SolutionArchitect
    raw generated mapping
    → structural/context validation
    → SolutionAlternatives
```

Slice 3 does not duplicate those generated-output checks inside `Review` or `StageExecution`.

### 17.2 StageExecution responsibility

`StageExecution` validates:

- status/input/output/error shape;
- stage identity versus stage-input type;
- stage identity versus trusted-output type;
- unimplemented-stage pending-only restriction.

### 17.3 Review responsibility

`Review` validates:

- exactly five canonical stage identities;
- original-input coherence;
- cross-stage input provenance;
- implemented dependency order;
- ReviewStatus versus stage-status consistency;
- valid incomplete-review patterns;
- complete-review precondition.

### 17.4 Orchestrator responsibility

The Orchestrator:

- invokes transitions in legal order;
- invokes participants only between the corresponding `RUNNING` and terminal stage transitions;
- catches known participant output-validation errors only at the participant call boundary;
- maps other participant-call exceptions to `EXECUTION` without claiming a more specific cause;
- creates safe `ReviewError` values;
- stops after mandatory failure;
- never calls `LLMPort` directly.

---

## 18. Error Mapping Relationship

Conceptually:

```text
AnalystOutputError
    → ReviewError(
        kind = OUTPUT_VALIDATION,
        message = "Analyst output validation failed"
      )

other Exception from Analyst.analyze(...)
    → ReviewError(
        kind = EXECUTION,
        message = "Analyst execution failed"
      )

SolutionArchitectOutputError
    → ReviewError(
        kind = OUTPUT_VALIDATION,
        message = "Solution Architect output validation failed"
      )

other Exception from SolutionArchitect.propose(...)
    → ReviewError(
        kind = EXECUTION,
        message = "Solution Architect execution failed"
      )
```

The original arbitrary exception message is not copied into trusted Review state.

`KeyboardInterrupt`, `SystemExit`, and other non-`Exception` control-flow signals are not converted into stage failures.

Errors thrown by Review transition/validation logic outside the participant invocation call are not swallowed by the participant failure mapping.

---

## 19. Immutability and Ownership

The following trusted objects are immutable in Slice 3:

```text
ReviewInput
ProblemAnalysis
SolutionAlternatives
AnalystStageInput
SolutionArchitectStageInput
ReviewError
StageExecution
Review
```

Logical ownership is:

```text
Review
└── StageExecution
    ├── execution-input provenance
    ├── trusted participant output when completed
    └── ReviewError when failed
```

`ReviewInput` is owned by the Review and referenced by executed stage-input records.

`ProblemAnalysis` is logically owned by the completed Analyst stage and referenced by the Solution Architect input record when that downstream stage starts.

`SolutionAlternatives` is logically owned by the completed Solution Architect stage.

These references do not establish independently mutable duplicate sources of truth.

---

## 20. Review Isolation

Every call to `Review.create(review_input)` creates a new stage tuple and new stage records.

The `ReviewOrchestrator` stores only participant dependencies and no previous Review state.

Therefore a new Review cannot inherit:

- prior statuses;
- prior stage inputs;
- prior trusted outputs;
- prior errors;
- prior assumptions;
- prior generated artifacts.

Two reviews may happen to contain equal immutable values, but neither review owns or looks up state through a shared active-review repository in Slice 3.

---

## 21. Representative Invalid States

The following must fail deterministic validation or transition preconditions:

```text
StageExecution(PENDING, inputs != None)
StageExecution(RUNNING, inputs = None)
StageExecution(RUNNING, output != None)
StageExecution(COMPLETED, output = None)
StageExecution(COMPLETED, error != None)
StageExecution(FAILED, error = None)
StageExecution(FAILED, output != None)

ANALYST + SolutionArchitectStageInput
ANALYST + SolutionAlternatives output
SOLUTION_ARCHITECT + AnalystStageInput
SOLUTION_ARCHITECT + ProblemAnalysis output
RISK_REVIEWER non-PENDING in Slice 3
CRITIC non-PENDING in Slice 3
COORDINATOR non-PENDING in Slice 3

Review(CREATED + any non-PENDING stage)
Review(RUNNING + any FAILED stage)
Review(RUNNING + Solution Architect started before Analyst COMPLETED)
Review(INCOMPLETE + no failed implemented stage)
Review(INCOMPLETE + both implemented stages FAILED)
Review(COMPLETED + any non-COMPLETED stage)

AnalystStageInput.review_input != Review.review_input
SolutionArchitectStageInput.review_input != Review.review_input
SolutionArchitectStageInput.problem_analysis != current completed Analyst output
```

---

## 22. Deliberately Deferred Data

Slice 3 intentionally does not model:

- `RiskAssessment`;
- Risk Reviewer stage inputs or outputs;
- `CriticalReview`;
- Critic stage inputs or outputs;
- `FinalReview`;
- Coordinator stage inputs or outputs;
- ranking or preferred alternative;
- final recommendation or final confidence;
- persistent/global review IDs;
- timestamps or duration;
- retry counters or retry history;
- timeout/cancellation state;
- pause/resume/checkpoint state;
- persistent review history;
- database entities;
- provider request/response envelopes;
- provider-specific error classes;
- raw exception details in trusted review state;
- UI view models;
- event streams;
- async/concurrent stage state;
- generic stage registry;
- generic participant plugin system;
- generic artifact repository/reference registry;
- RAG, embeddings, document ingestion, MCP, tools, or autonomous actions.

---

## 23. Verification Mapping

The implementation tests derived from this data model must cover at minimum:

### Contract/enums

- exact enum values;
- closed/frozen models;
- immutable stage collection;
- non-empty `ReviewError.message`.

### StageExecution

- every valid state shape;
- representative invalid status/input/output/error combinations;
- Analyst input/output typing;
- Solution Architect input/output typing;
- later-stage pending-only restriction.

### Review aggregate

- fresh canonical creation;
- exactly five unique canonical identities;
- canonical creation ordering without positional semantic dependence;
- valid CREATED state;
- every valid Slice 3 RUNNING prefix state;
- both valid INCOMPLETE patterns;
- Slice 3 COMPLETED impossibility;
- mismatched ReviewInput provenance rejected;
- mismatched Solution Architect ProblemAnalysis provenance rejected.

### Transitions

- legal transition sequence;
- invalid transition preconditions fail explicitly;
- failure produces one valid `INCOMPLETE + FAILED` target snapshot;
- successful completion preserves previous immutable outputs;
- zero-alternative Solution Architect result completes successfully;
- transitions preserve original ReviewInput and unaffected stage records.

### Isolation

- two sequential reviews start from fresh stage state;
- no error/output/input provenance leaks across reviews.

### Orchestrator integration

- exact participant call order;
- Solution Architect receives the trusted Analyst result from the same Review;
- known output errors map to `OUTPUT_VALIDATION`;
- arbitrary participant-call exceptions map to `EXECUTION`;
- internal lifecycle errors are not converted to participant failures;
- later participants remain unimplemented and uninvoked.

---

## 24. Traceability to Approved Sources

This data model remains subordinate to and consistent with:

- `specs/003-review-orchestrator/spec.md`;
- `specs/003-review-orchestrator/plan.md`;
- `docs/02-requirements.md` — stage visibility, incomplete review semantics, structured validation, failure handling, execution record, deterministic behavior, and review isolation;
- `docs/03-architecture.md` — Review Orchestrator responsibility, Review/StageExecution domain concepts, five-stage dependency order, review lifecycle, stage lifecycle, and trusted-output propagation;
- `docs/04-agent-model.md` — explicit participant inputs/outputs, no hidden state, and no participant workflow control;
- `docs/05-quality-security.md` — fail-closed validation, deterministic orchestration testing, safe visible failure, and preservation of upstream artifacts;
- `.specify/memory/constitution.md` — structured contracts, traceability, role integrity, visible failure, provider independence, minimal architecture, and incremental delivery;
- `docs/adr/ADR-0001-pydantic-v2-for-structured-contracts.md` — Pydantic v2 structured-contract and validation policy.
