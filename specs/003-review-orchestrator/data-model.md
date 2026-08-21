# Data Model: Review Orchestrator v0.1

**Feature:** `specs/003-review-orchestrator/spec.md`  
**Plan:** `specs/003-review-orchestrator/plan.md`  
**ADR:** `docs/adr/ADR-0001-pydantic-v2-for-structured-contracts.md`  
**Status:** Approved — ready for task breakdown

## 1. Purpose

This document defines the structured in-memory execution state introduced by **Review Orchestrator v0.1**.

It refines the approved spec and plan without adding later participant behavior, persistence, or a generic workflow framework.

Slice 3 introduces:

- `StageIdentity`;
- `StageStatus`;
- `ReviewStatus`;
- `ReviewErrorKind`;
- `ReviewError`;
- `AnalystStageInput`;
- `SolutionArchitectStageInput`;
- `StageExecution`;
- `Review`;
- explicit validated snapshot transitions.

Pydantic v2 remains governed by ADR-0001.

---

## 2. Shared Modeling Rules

Execution-state contracts are:

```text
frozen = true
extra = forbid
```

Normative rules:

- trusted review state is explicit and inspectable;
- collections retained in trusted state are immutable;
- each `StageExecution` validates its own lifecycle and identity/type invariants;
- each `Review` validates the canonical five-stage set, dependency order, provenance, and overall lifecycle coherence;
- transitions build a new validated `Review` snapshot rather than mutating trusted state;
- unchecked `model_copy(update=...)` operations that bypass validation are not used for transitions;
- generated participant output is stored only after the existing participant boundary returns a trusted `ProblemAnalysis` or `SolutionAlternatives`;
- review state contains no raw generated mappings, provider SDK types, credentials, full prompts, full raw model responses, stack traces, or private chain-of-thought;
- no persistent IDs, timestamps, retries, persistence schema, artifact repository, or workflow framework are introduced.

---

## 3. Existing Trusted Models Reused

Slice 3 reuses unchanged:

```text
ReviewInput
ProblemAnalysis
SolutionAlternatives
```

Existing participant contracts remain:

```text
Analyst.analyze(ReviewInput) -> ProblemAnalysis

SolutionArchitect.propose(
    ReviewInput,
    ProblemAnalysis,
) -> SolutionAlternatives
```

The Orchestrator does not validate raw LLM output itself; it receives only trusted participant return values or participant exceptions.

---

## 4. Lifecycle Enums

### 4.1 StageIdentity

Closed values:

```text
ANALYST
SOLUTION_ARCHITECT
RISK_REVIEWER
CRITIC
COORDINATOR
```

Canonical order is the same sequence above.

The tuple order is useful for deterministic creation/display, but stage identity and lookup are always based on `StageIdentity`, never on positional index semantics.

### 4.2 StageStatus

Closed values:

```text
PENDING
RUNNING
COMPLETED
FAILED
```

Slice 3 stage transitions:

```text
PENDING → RUNNING
RUNNING → COMPLETED
RUNNING → FAILED
```

No retry/reset transition is introduced.

### 4.3 ReviewStatus

Closed values:

```text
CREATED
RUNNING
INCOMPLETE
COMPLETED
```

Slice 3 transitions:

```text
CREATED → RUNNING
RUNNING → INCOMPLETE
```

`COMPLETED` remains part of the canonical lifecycle but is unreachable in Slice 3 because Risk Reviewer, Critic, and Coordinator remain `PENDING`.

A successful Slice 3 state is therefore:

```text
Review       RUNNING
Analyst      COMPLETED
Architect    COMPLETED
Risk         PENDING
Critic       PENDING
Coordinator  PENDING
```

`RUNNING` means started and not terminal; it does not require an agent to be active at inspection time.

---

## 5. Stage Input Provenance

Stage input records are trusted in-memory execution records, not provider payloads.

### 5.1 AnalystStageInput

```text
AnalystStageInput
- review_input: ReviewInput
```

The field must reference the current `Review.review_input` instance.

### 5.2 SolutionArchitectStageInput

```text
SolutionArchitectStageInput
- review_input: ReviewInput
- problem_analysis: ProblemAnalysis
```

Both references belong to the current Review execution:

- `review_input` is the same instance as `Review.review_input`;
- `problem_analysis` is the same trusted instance owned by the current completed Analyst stage.

No regenerated, reparsed, repaired, equal-but-independent, or cross-review artifact is accepted as canonical stage provenance.

### 5.3 Runtime identity rationale

Slice 3 is explicitly in-memory and has no persistence, serialization round-trip, resume, or rehydration requirement.

Therefore runtime provenance validation MAY and SHOULD use Python object identity for these relationships:

```text
analyst.inputs.review_input
    is review.review_input

architect.inputs.review_input
    is review.review_input

architect.inputs.problem_analysis
    is analyst.output
```

This is stronger than value equality: two independently constructed but equal objects do not prove that the downstream stage consumed the artifact accepted in this Review execution.

This identity requirement is local to the current in-memory MVP. If persistence/rehydration is introduced later, provenance will require a reviewed persistent identity/reference model rather than silently weakening this invariant.

### 5.4 StageInput union

For Slice 3:

```text
StageInput = AnalystStageInput | SolutionArchitectStageInput
```

No generic `Artifact`, arbitrary mapping, payload registry, or plugin envelope is introduced.

---

## 6. ReviewError

### 6.1 ReviewErrorKind

Closed Slice 3 values:

```text
OUTPUT_VALIDATION
EXECUTION
```

`OUTPUT_VALIDATION` maps known existing participant output errors:

```text
AnalystOutputError
SolutionArchitectOutputError
```

`EXECUTION` represents any other ordinary `Exception` raised from inside the participant invocation when no finer provider-neutral classification exists.

It does not claim a specific provider/transport cause.

### 6.2 ReviewError fields

```text
ReviewError
- kind: ReviewErrorKind
- message: str
```

Rules:

- closed and frozen;
- `message` is strict non-empty text;
- message is created by trusted orchestration code;
- arbitrary source exception text is not copied into trusted Review state;
- stage identity is not duplicated because the surrounding `StageExecution` already owns it.

Stable messages:

```text
Analyst output validation failed
Analyst execution failed
Solution Architect output validation failed
Solution Architect execution failed
```

Internal lifecycle/domain defects outside the participant invocation boundary are not converted to `ReviewError`; they propagate.

---

## 7. StageOutput

Slice 3 output union:

```text
StageOutput = ProblemAnalysis | SolutionAlternatives
```

Identity compatibility:

```text
ANALYST + COMPLETED
    → ProblemAnalysis

SOLUTION_ARCHITECT + COMPLETED
    → SolutionAlternatives
```

No raw mapping can be stored as trusted stage output.

---

## 8. StageExecution

```text
StageExecution
- identity: StageIdentity
- status: StageStatus
- inputs: StageInput | None
- output: StageOutput | None
- error: ReviewError | None
```

The model is closed and frozen.

### 8.1 Generic lifecycle invariant

```text
PENDING
inputs = None
output = None
error = None

RUNNING
inputs != None
output = None
error = None

COMPLETED
inputs != None
output != None
error = None

FAILED
inputs != None
output = None
error != None
```

Trusted output and terminal error can never coexist.

### 8.2 Analyst type invariant

```text
ANALYST / PENDING
    inputs=None, output=None, error=None

ANALYST / RUNNING
    inputs=AnalystStageInput

ANALYST / COMPLETED
    inputs=AnalystStageInput
    output=ProblemAnalysis

ANALYST / FAILED
    inputs=AnalystStageInput
    error=ReviewError
```

`SolutionArchitectStageInput` and `SolutionAlternatives` are invalid for Analyst.

### 8.3 Solution Architect type invariant

```text
SOLUTION_ARCHITECT / PENDING
    inputs=None, output=None, error=None

SOLUTION_ARCHITECT / RUNNING
    inputs=SolutionArchitectStageInput

SOLUTION_ARCHITECT / COMPLETED
    inputs=SolutionArchitectStageInput
    output=SolutionAlternatives

SOLUTION_ARCHITECT / FAILED
    inputs=SolutionArchitectStageInput
    error=ReviewError
```

`AnalystStageInput` and `ProblemAnalysis` are invalid for Solution Architect.

### 8.4 Later-stage Slice 3 restriction

For:

```text
RISK_REVIEWER
CRITIC
COORDINATOR
```

Slice 3 permits only:

```text
status = PENDING
inputs = None
output = None
error = None
```

Future approved slices extend the unions and relax only the corresponding stage restriction.

`StageExecution` validates only local identity/status/input/output/error consistency. Same-review provenance is validated by the `Review` aggregate.

---

## 9. Review

```text
Review
- review_input: ReviewInput
- status: ReviewStatus
- stages: tuple[StageExecution, ...]
```

The model is closed and frozen.

Trusted outputs have a single logical owner in their completed stage records. The Review does not store duplicate fields such as:

```text
problem_analysis
solution_alternatives
```

### 9.1 Canonical stage-set invariant

Every Review contains exactly five stage records, one for each `StageIdentity`.

Invalid:

- duplicate identity;
- missing identity;
- extra stage.

Creation emits canonical order and transitions preserve it, but validators/lookups use identity rather than index.

### 9.2 ReviewInput provenance

For any started Analyst stage:

```text
analyst.inputs.review_input is review.review_input
```

For any started Solution Architect stage:

```text
architect.inputs.review_input is review.review_input
```

### 9.3 Analyst → Architect provenance

For any started Solution Architect stage:

```text
analyst.status == COMPLETED
analyst.output is ProblemAnalysis
architect.inputs.problem_analysis is analyst.output
```

This directly records which trusted Analyst result was handed downstream.

---

## 10. Valid Review Shapes

### 10.1 CREATED

Exactly:

```text
Review = CREATED
all five stages = PENDING
```

No stage has inputs/output/error.

### 10.2 RUNNING

No stage may be `FAILED`. Later three stages remain `PENDING`.

Valid implemented prefixes are exactly:

```text
A)
Analyst      PENDING
Architect    PENDING

B)
Analyst      RUNNING
Architect    PENDING

C)
Analyst      COMPLETED
Architect    PENDING

D)
Analyst      COMPLETED
Architect    RUNNING

E)
Analyst      COMPLETED
Architect    COMPLETED
```

In all cases Risk Reviewer, Critic, and Coordinator are `PENDING`.

No other `RUNNING` combination is valid.

### 10.3 INCOMPLETE

Valid Slice 3 terminal failure shapes are exactly:

```text
A) Analyst failure
Analyst      FAILED
Architect    PENDING
later        PENDING

B) Architect failure
Analyst      COMPLETED
Architect    FAILED
later        PENDING
```

Therefore:

- exactly one implemented mandatory stage is failed;
- an incomplete Review with no failed stage is invalid;
- both implemented stages failed is invalid because dependent execution stops after the first mandatory failure.

### 10.4 COMPLETED

`ReviewStatus.COMPLETED` requires all five mandatory stages to be `COMPLETED`.

Since Slice 3 restricts the later three stages to `PENDING`, no valid Slice 3 Review can satisfy this state.

---

## 11. Canonical Creation

Conceptual API:

```text
Review.create(review_input)
```

Produces a fresh Review:

```text
status = CREATED
review_input = supplied trusted instance
stages = five fresh StageExecution(PENDING)
```

No state from a previous Review is reused.

No review ID is introduced.

---

## 12. Explicit Review Transitions

Slice 3 uses stage-specific operations rather than a generic workflow engine.

Exact method/function syntax may vary; preconditions and target states are normative.

### 12.1 start

```text
pre:
Review.status == CREATED

post:
Review.status = RUNNING
all stages remain PENDING
```

### 12.2 start_analyst

```text
pre:
Review.status == RUNNING
Analyst == PENDING
Architect/later == PENDING

post:
Analyst = RUNNING
Analyst.inputs = AnalystStageInput(
    review_input = Review.review_input  # same instance
)
```

### 12.3 complete_analyst(problem_analysis)

```text
pre:
Review.status == RUNNING
Analyst == RUNNING
problem_analysis is trusted ProblemAnalysis

post:
Analyst = COMPLETED
inputs preserved
output = supplied trusted problem_analysis instance
error = None
Review remains RUNNING
```

### 12.4 fail_analyst(error)

```text
pre:
Review.status == RUNNING
Analyst == RUNNING
error is ReviewError

post atomically:
Review = INCOMPLETE
Analyst = FAILED
Analyst inputs preserved
Analyst output = None
Analyst error = error
all downstream = PENDING
```

No valid intermediate `RUNNING + FAILED` Review snapshot is constructed.

### 12.5 start_solution_architect

```text
pre:
Review.status == RUNNING
Analyst == COMPLETED
Analyst.output is ProblemAnalysis
Architect == PENDING
later == PENDING

post:
Architect = RUNNING
Architect.inputs.review_input is Review.review_input
Architect.inputs.problem_analysis is Analyst.output
```

### 12.6 complete_solution_architect(solution_alternatives)

```text
pre:
Review.status == RUNNING
Analyst == COMPLETED
Architect == RUNNING
solution_alternatives is trusted SolutionAlternatives

post:
Architect = COMPLETED
inputs preserved
output = supplied trusted solution_alternatives instance
error = None
Review remains RUNNING
```

A valid zero-alternative `SolutionAlternatives` is successful and follows the same transition.

### 12.7 fail_solution_architect(error)

```text
pre:
Review.status == RUNNING
Analyst == COMPLETED
Architect == RUNNING
error is ReviewError

post atomically:
Review = INCOMPLETE
Analyst remains COMPLETED with its output
Architect = FAILED
Architect inputs preserved
Architect output = None
Architect error = error
later stages = PENDING
```

---

## 13. Validated Snapshot Reconstruction

Each transition builds a new complete Review from validated components.

Conceptually:

```text
new_stages = tuple(
    replacement if stage.identity == target else stage
    for stage in review.stages
)

new_review = Review(
    review_input=review.review_input,
    status=target_status,
    stages=new_stages,
)
```

Normal `Review` validation must execute on the target snapshot.

The stage tuple always contains five items, so rebuilding it is preferred to mutable state machinery, event sourcing, or transaction infrastructure.

---

## 14. Lookup and Type Narrowing

A small identity-based helper may be provided:

```text
Review.stage(identity: StageIdentity) -> StageExecution
```

The Orchestrator retrieves Analyst output through explicit narrowing:

```text
stage = review.stage(ANALYST)
require stage.status == COMPLETED
require isinstance(stage.output, ProblemAnalysis)
problem_analysis = stage.output
```

A valid Review already guarantees these conditions; the checks make static typing explicit and defend against internal misuse.

Failure of such domain/lifecycle invariants occurs outside the participant invocation boundary and propagates rather than becoming a participant failure.

---

## 15. Validation Ownership

### Existing participants

Own untrusted generated-output validation:

```text
raw mapping → participant validation → trusted domain output
```

### StageExecution

Owns:

- status/input/output/error shape;
- identity/input type compatibility;
- identity/output type compatibility;
- Slice 3 later-stage pending-only restriction.

### Review

Owns:

- exactly five unique canonical stages;
- same-instance ReviewInput provenance;
- same-instance Analyst → Architect provenance;
- dependency order;
- `ReviewStatus` versus stage-state coherence;
- valid incomplete patterns;
- complete-review precondition.

### ReviewOrchestrator

Owns:

- legal sequencing;
- participant invocation;
- error mapping at participant boundaries;
- safe `ReviewError` creation;
- stopping after mandatory failure;
- no direct `LLMPort` access.

---

## 16. Error Mapping

```text
AnalystOutputError
→ OUTPUT_VALIDATION / "Analyst output validation failed"

other Exception from Analyst.analyze(...)
→ EXECUTION / "Analyst execution failed"

SolutionArchitectOutputError
→ OUTPUT_VALIDATION / "Solution Architect output validation failed"

other Exception from SolutionArchitect.propose(...)
→ EXECUTION / "Solution Architect execution failed"
```

Raw exception messages are not copied into trusted Review state.

`KeyboardInterrupt`, `SystemExit`, and other non-`Exception` control-flow signals are not converted to stage failures.

Domain/orchestrator errors outside participant calls are not swallowed by this mapping.

---

## 17. Ownership

Logical ownership:

```text
Review
├── ReviewInput
└── StageExecution × 5
    ├── stage-input provenance when started
    ├── trusted output when completed
    └── ReviewError when failed
```

`ProblemAnalysis` is logically owned by Analyst stage output and referenced by the Architect stage input.

`SolutionAlternatives` is logically owned by Architect stage output.

The same immutable object may appear as an upstream output reference and downstream input reference; this is intentional traceability, not duplicated mutable ownership.

---

## 18. Review Isolation

Every `Review.create(...)` builds a fresh stage tuple and fresh stage records.

`ReviewOrchestrator` stores participant dependencies only, not prior Review state.

A new review cannot inherit prior:

- stage status;
- stage input provenance;
- trusted output;
- error;
- assumptions or generated artifacts.

---

## 19. Representative Invalid States

Must fail deterministic validation or transition preconditions:

```text
PENDING + inputs
RUNNING without inputs
RUNNING + output
COMPLETED without output
COMPLETED + error
FAILED without error
FAILED + output

ANALYST + SolutionArchitectStageInput
ANALYST + SolutionAlternatives
SOLUTION_ARCHITECT + AnalystStageInput
SOLUTION_ARCHITECT + ProblemAnalysis output
later stage non-PENDING in Slice 3

CREATED + non-PENDING stage
RUNNING + FAILED stage
RUNNING + Architect started before Analyst COMPLETED
INCOMPLETE + no failed implemented stage
INCOMPLETE + both implemented stages failed
COMPLETED + any non-COMPLETED stage

AnalystStageInput.review_input is not Review.review_input
ArchitectStageInput.review_input is not Review.review_input
ArchitectStageInput.problem_analysis is not current Analyst.output
```

---

## 20. Verification Mapping

Tests derived from this model must cover:

- exact closed enum values;
- frozen/closed models and immutable stage tuple;
- all valid/invalid `StageExecution` shapes;
- input/output identity typing per stage;
- fresh five-stage `CREATED` Review;
- every valid Slice 3 `RUNNING` prefix;
- both valid `INCOMPLETE` patterns;
- inability to construct a valid Slice 3 `COMPLETED` Review;
- same-instance ReviewInput provenance;
- same-instance Analyst → Architect provenance;
- rejection of equal-but-independent provenance objects;
- legal transition sequence;
- explicit failure on illegal transitions;
- atomic failure target snapshots;
- preservation of prior trusted outputs on later failure;
- zero-alternative Architect success;
- sequential review isolation;
- output-validation versus execution error mapping;
- internal lifecycle errors not converted to participant failures;
- later roles never invoked.

Core verification remains deterministic and network-free.

---

## 21. Deliberately Deferred

Slice 3 does not model:

- Risk Reviewer/RiskAssessment contracts;
- Critic/CriticalReview contracts;
- Coordinator/FinalReview contracts;
- ranking, preferred alternative, recommendation, final confidence;
- persistent/global IDs;
- persistence, history, resume, serialization/rehydration provenance;
- timestamps/durations;
- retries/timeouts/cancellation;
- async/concurrency;
- provider-specific errors or envelopes;
- raw exception diagnostics in trusted Review state;
- UI view models;
- generic workflow/stage registry;
- generic artifact/reference repository;
- RAG, embeddings, MCP, tools, or autonomous actions.

---

## 22. Traceability to Approved Sources

This data model is subordinate to and consistent with:

- `specs/003-review-orchestrator/spec.md`;
- `specs/003-review-orchestrator/plan.md`;
- `docs/02-requirements.md` — stage visibility, validation, failure handling, NFR-006 execution records, deterministic workflow behavior, and isolation;
- `docs/03-architecture.md` — Orchestrator responsibility, Review/StageExecution concepts, dependency order, lifecycle, and trusted-output propagation;
- `docs/04-agent-model.md` — explicit inputs/outputs, original ReviewInput preservation, no hidden state, and no participant workflow control;
- `docs/05-quality-security.md` — correct orchestration, contract integrity, traceability, visible failure, deterministic testing, and data minimization;
- `.specify/memory/constitution.md` — structured contracts, traceability, role integrity, visible failure, provider independence, minimal architecture, and incremental delivery;
- `docs/adr/ADR-0001-pydantic-v2-for-structured-contracts.md` — Pydantic v2 validation policy.