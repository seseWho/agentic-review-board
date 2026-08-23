# Implementation Plan: Critic v0.1

**Branch**: `005-critic`  
**Specification**: `specs/005-critic/spec.md` — Approved  
**Status**: Approved — reviewed against spec and existing architecture; ready for data-model design

## 1. Objective

Implement Slice 5 as the minimum fourth-stage extension of the existing Agentic Review Board pipeline:

```text
ReviewInput
  → Analyst / ProblemAnalysis
  → Solution Architect / SolutionAlternatives
  → Risk Reviewer / RiskAssessment
  → Critic / CriticalReview
  → Coordinator remains PENDING
```

The implementation SHALL add a trusted, inspectable Critic artifact and execute Critic only after all three upstream mandatory stages have completed successfully.

No final ranking, recommendation, Coordinator implementation, generic workflow engine, or generic cross-stage reference framework is introduced.

---

## 2. Design Principles

### 2.1 Preserve the established trust boundary

The existing pattern remains:

```text
LLMPort structured response
        ↓ untrusted
Pydantic structural validation
        ↓
Critic-specific contextual reference validation
        ↓ trusted
CriticalReview
```

Structural validity alone is insufficient when generated Critic findings claim to reference current review artifacts.

### 2.2 Keep generated references separate from execution provenance

Two different concepts remain intentionally separate:

- **generated-reference validation** asks whether Critic output meaningfully resolves to current review artifacts;
- **same-execution provenance** asks whether the Critic StageExecution holds the exact upstream Python object instances from the current Review execution.

The implementation SHALL NOT merge these into one abstraction.

### 2.3 Critic challenges; Coordinator decides

Critic may criticize, validate, identify omissions, contradictions, and unresolved issues. It SHALL NOT rank alternatives, select a preferred alternative, or recommend a winner.

### 2.4 Do not force artificial activity

A fully empty `CriticalReview` is valid. The domain contract SHALL not require one criticism, one validated point, or any other generated finding merely to prove that Critic ran.

### 2.5 Extend explicitly, not generically

Slice 5 adds one participant and one stage. Existing explicit lifecycle/orchestration code SHALL be extended directly rather than replaced by a stage registry, graph, plugin architecture, or workflow framework.

---

## 3. Proposed Repository Changes

Expected production changes are limited to:

```text
src/agentic_review_board/
├── domain/
│   ├── criticism.py              # new Critic output contracts
│   └── execution.py              # extend StageInput/StageOutput and Review lifecycle
├── participants/
│   └── critic.py                 # new participant + contextual validation boundary
└── application/
    └── orchestrator.py           # explicit fourth-stage invocation/failure handling
```

Expected tests:

```text
tests/unit/
├── test_criticism.py             # new intrinsic Critic-domain tests
├── test_critic.py                # new participant/contextual-reference tests
├── test_review_execution.py      # extend stage/aggregate invariants
├── test_review_transitions.py    # extend explicit Critic transitions
└── test_review_orchestrator.py   # extend sequence/failure/isolation tests
```

No new production dependency is expected.

The final exact filenames remain subject to data-model review, but responsibilities SHALL remain separated along these boundaries.

---

## 4. CriticalReview Domain Design Direction

The approved spec requires these conceptual collections:

```text
CriticalReview
├── criticisms[]
├── validated_points[]
├── missing_alternatives[]
├── contradictions[]
└── unresolved_issues[]
```

The data-model phase SHALL define explicit immutable Pydantic models rather than free-form dictionaries.

### 4.1 Criticism

`Criticism` SHALL represent at least the canonical semantics:

- stable ID;
- target type;
- target reference when required/resolvable;
- issue;
- qualitative importance;
- rationale;
- optional correction or question.

The model SHALL make generic unsupported prose harder to accept than an explicit inspectable finding.

### 4.2 Validated points

Validated points SHOULD be structured rather than bare strings if doing so is necessary to preserve upstream traceability.

The data-model phase SHALL choose the smallest structure that can:

- identify what upstream point survived review where practical;
- explain why it remains supported;
- preserve assumption/fact semantics;
- avoid turning validation into recommendation.

### 4.3 Missing alternatives

A missing-alternative finding SHALL describe:

- the omitted category/class;
- why it matters;
- whether the omission weakens the later ability to justify a recommendation.

When the omission is inferred from explicit current-review artifacts, the finding SHALL preserve an inspectable basis that can be contextually validated against those artifacts. A missing-alternative finding SHALL NOT be accepted as generic unsupported prose such as “more options are needed” without visible current-review grounding.

It SHALL NOT embed a replacement `SolutionAlternative`.

### 4.4 Contradictions

Contradictions SHOULD be explicit structured objects, not bare strings, because the approved spec requires both sides to remain inspectable and traceable when referencable.

The data-model phase SHALL define the minimum representation needed to identify side A, side B, and why they conflict without creating a generic artifact graph.

### 4.5 Unresolved issues

Unresolved issues SHALL remain explicit and inspectable. When an unresolved issue derives from one or more current-review artifacts, the data model SHALL preserve a bounded explicit basis that can be contextually validated. A purely textual unresolved issue is acceptable only where no explicit referencable current artifact exists and the issue's rationale still exposes its visible current-review basis.

The data model SHALL not require a generic artifact graph merely to express such basis.

### 4.6 Empty review

All five top-level collections SHALL permit zero items simultaneously.

---

## 5. Critic Reference Strategy

Critic has the broadest upstream view so far, but Slice 5 SHALL still avoid a generic artifact-reference framework.

### 5.1 Referenceable source families

The data model SHALL support only reference families justified by approved Critic behavior, expected to include targeted references into:

- `ReviewInput`;
- `ProblemAnalysis`;
- `SolutionAlternatives`;
- `RiskAssessment`.

Within those families, only fields/items that Critic can legitimately challenge or validate SHALL be exposed as reference targets.

### 5.2 Explicit-target rule

When a Critic finding targets one explicit current artifact/item and that target is unambiguously resolvable, the generated output SHALL include the reference required by the approved data model.

A missing reference SHALL not be accepted merely because the prose happens to mention the target.

### 5.3 Cross-artifact findings

Some criticisms genuinely span multiple artifacts. These SHALL not be forced into a false single-target representation.

The data model SHALL support a bounded way to express their visible basis without turning Slice 5 into a generic evidence graph.

This same principle applies to `MissingAlternative` and `UnresolvedIssue`: where their rationale depends on explicit upstream artifacts, the approved data model SHALL preserve enough Critic-specific basis information for contextual validation without requiring a single false target.

### 5.4 Ambiguity policy

Reference resolution SHALL be fail-closed:

- exact explicit IDs where available;
- exact ID + value/text compatibility where required;
- unique textual fallback only where an existing artifact lacks a stable ID and the match is unambiguous;
- zero matches → validation failure;
- multiple matches → validation failure;
- no silent normalization, fuzzy matching, nearest-match selection, or generated repair.

This follows the established Risk Reviewer trust-boundary discipline.

---

## 6. Critic Participant

Add a provider-neutral `Critic` participant with the Slice 5 application-facing method:

```text
review(
    review_input,
    problem_analysis,
    solution_alternatives,
    risk_assessment,
) -> CriticalReview
```

The method name `review` is fixed by this plan. Data-model design SHALL define only the data contracts consumed and returned by this API, not rename participant behavior.

The participant SHALL:

1. serialize the four explicit inputs into JSON-compatible structured payloads;
2. call `LLMPort.generate_structured(...)` using role `critic`;
3. structurally parse the returned object as `CriticalReview`;
4. contextually validate all generated references and required bases against the four exact input artifacts;
5. return the trusted `CriticalReview` only after every required validation succeeds.

A dedicated `CriticOutputError` SHALL distinguish generated-output validation failure from ordinary execution failure.

The participant SHALL hold no mutable per-review state.

---

## 7. Execution Aggregate Extension

### 7.1 CriticStageInput

Add an explicit Critic stage input containing the exact current:

```text
ReviewInput
ProblemAnalysis
SolutionAlternatives
RiskAssessment
```

### 7.2 StageInput / StageOutput

Extend existing explicit unions so:

- Critic can carry `CriticStageInput`;
- completed Critic can carry `CriticalReview`;
- Coordinator remains PENDING-only in Slice 5.

Do not introduce generic payload envelopes.

### 7.3 Same-execution provenance

For Critic in RUNNING, COMPLETED, or FAILED state, the aggregate SHALL require identity with:

- current Review `review_input`;
- Analyst completed output;
- Solution Architect completed output;
- Risk Reviewer completed output.

Equal-but-independent model copies SHALL be rejected.

### 7.4 Exact Slice 5 lifecycle matrix

Lifecycle validation SHALL be explicit over the four implemented stages, resolved by `StageIdentity` in this order for matrix reasoning only:

```text
Analyst / Solution Architect / Risk Reviewer / Critic
```

For `ReviewStatus.RUNNING`, exactly these nine prefixes are valid:

```text
PENDING    PENDING    PENDING    PENDING
RUNNING    PENDING    PENDING    PENDING
COMPLETED  PENDING    PENDING    PENDING
COMPLETED  RUNNING    PENDING    PENDING
COMPLETED  COMPLETED  PENDING    PENDING
COMPLETED  COMPLETED  RUNNING    PENDING
COMPLETED  COMPLETED  COMPLETED  PENDING
COMPLETED  COMPLETED  COMPLETED  RUNNING
COMPLETED  COMPLETED  COMPLETED  COMPLETED
```

Coordinator SHALL be `PENDING` in every valid Slice 5 RUNNING state.

For `ReviewStatus.INCOMPLETE`, exactly these four mandatory-stage failure shapes are valid:

```text
FAILED     PENDING    PENDING    PENDING
COMPLETED  FAILED     PENDING    PENDING
COMPLETED  COMPLETED  FAILED     PENDING
COMPLETED  COMPLETED  COMPLETED  FAILED
```

Coordinator SHALL be `PENDING` in every Slice 5 INCOMPLETE state.

This encodes one and only one failed mandatory implemented stage; all earlier implemented stages must be COMPLETED and all later stages must remain PENDING.

Successful Slice 5 terminal-for-this-slice shape is therefore:

```text
Review RUNNING
Analyst COMPLETED
Solution Architect COMPLETED
Risk Reviewer COMPLETED
Critic COMPLETED
Coordinator PENDING
```

Critic failure shape is:

```text
Review INCOMPLETE
Analyst COMPLETED
Solution Architect COMPLETED
Risk Reviewer COMPLETED
Critic FAILED
Coordinator PENDING
```

`ReviewStatus.COMPLETED` remains unreachable in Slice 5.

### 7.5 StageIdentity, not tuple position

All validation, lookup, and replacement SHALL continue using `StageIdentity`. The matrices above define semantic stage order, not tuple indexing. Existing support for semantically valid noncanonical tuple ordering SHALL not regress.

---

## 8. Explicit Review Transitions

Add only the Critic transitions required by this slice:

```text
start_critic()
complete_critic(critical_review)
fail_critic(error)
```

They SHALL follow the existing immutable reconstruction pattern.

### start_critic

Preconditions:

- Review is RUNNING;
- Analyst COMPLETED;
- Solution Architect COMPLETED;
- Risk Reviewer COMPLETED;
- Critic PENDING;
- Coordinator PENDING.

Result:

- Critic RUNNING;
- exact four upstream objects captured in `CriticStageInput`;
- all other stages unchanged.

### complete_critic

Precondition: Critic RUNNING.

Result:

- Critic COMPLETED;
- exact previous CriticStageInput preserved;
- supplied trusted `CriticalReview` reused as output;
- Review remains RUNNING;
- Coordinator remains PENDING.

### fail_critic

Precondition: Critic RUNNING.

Result atomically:

- Critic FAILED;
- Review INCOMPLETE;
- exact recorded Critic inputs preserved;
- no Critic output stored;
- completed upstream stages unchanged;
- Coordinator remains PENDING.

No generic transition engine is introduced.

---

## 9. Orchestrator Extension

Extend the existing explicit synchronous sequence after Risk Reviewer success:

```text
...
review = review.start_critic()
critical_review = critic.review(exact upstream artifacts)
review = review.complete_critic(critical_review)
return review
```

The orchestrator SHALL retrieve upstream outputs by `StageIdentity` and narrow them to the exact trusted types before entering the Critic participant-call failure boundary.

### 9.1 Output-validation failure

Catch `CriticOutputError` only around the Critic participant invocation.

Map it to `ReviewErrorKind.OUTPUT_VALIDATION` with the exact stable safe message:

```text
Critic output validation failed
```

Then call `fail_critic(...)` and return the INCOMPLETE Review immediately.

### 9.2 Ordinary execution failure

Catch ordinary `Exception` only around the Critic participant invocation.

Map it to `ReviewErrorKind.EXECUTION` with the exact stable safe message:

```text
Critic execution failed
```

Raw provider exception text SHALL not enter trusted Review state.

### 9.3 Internal failures

Domain/invariant/programming errors outside the Critic participant invocation SHALL propagate. `BaseException` control signals such as `KeyboardInterrupt` and `SystemExit` SHALL not be swallowed.

---

## 10. Test Strategy

Implementation SHALL remain tests-first.

### 10.1 Intrinsic domain tests

Test Critic-domain contracts independently of Review and LLMPort:

- frozen/extra-forbid behavior;
- non-blank required fields;
- unique IDs where IDs exist;
- qualitative importance values;
- reference shape invariants;
- contradiction shape invariants;
- missing-alternative semantics and basis shape;
- unresolved-issue semantics and basis shape where applicable;
- duplicate handling where material;
- all-empty CriticalReview validity;
- rejection of ranking/recommendation/replacement fields by closed schemas.

### 10.2 Participant/context validation tests

Using deterministic fake/recording `LLMPort`:

- exact role `critic`;
- all four inputs serialized;
- valid criticism target resolution;
- valid validated-point target resolution;
- contradiction side resolution;
- risk/mitigation references;
- cross-artifact criticism basis;
- missing-alternative basis resolution;
- unresolved-issue basis resolution where explicit current artifacts are supplied;
- unknown reference failure;
- ambiguous reference failure;
- explicit required target omitted failure;
- zero-alternative and zero-risk upstream cases;
- fully empty CriticalReview success;
- malformed structured output;
- no partial trusted output.

### 10.3 Execution aggregate tests

Extend existing tests for:

- Critic stage local shapes;
- all nine exact Slice 5 RUNNING prefixes;
- all four exact Slice 5 INCOMPLETE failure shapes;
- rejection of skipped stages, multiple failures, and later-stage execution after failure;
- Coordinator PENDING-only;
- `ReviewStatus.COMPLETED` unreachable;
- same-execution identity provenance across all four Critic inputs;
- rejection of equal-but-independent copies;
- noncanonical tuple ordering regression.

### 10.4 Transition tests

Test start/complete/fail Critic transitions, including premature/repeated/terminal misuse and tuple-order preservation.

### 10.5 Orchestrator tests

Test:

- exact role order `analyst → solution_architect → risk_reviewer → critic`;
- exact artifact handoff;
- successful Slice 5 end state;
- fully empty CriticalReview success;
- zero-alternative/zero-risk success;
- Critic output-validation failure with exact safe message `Critic output validation failed`;
- Critic ordinary execution failure with exact safe message `Critic execution failed`;
- preservation of upstream completed outputs;
- Coordinator never invoked;
- internal errors not swallowed;
- sequential Review isolation with reused orchestrator/participants;
- regression coverage for Analyst, Solution Architect, and Risk Reviewer failure behavior.

### 10.6 Cross-cutting verification

Before merge:

```text
python -m pytest
python -m ruff check .
python -m mypy
python -m pip check
```

Also inspect production dependencies/imports and final diff for scope creep.

---

## 11. Implementation Order

The recommended order is intentionally dependency-driven:

```text
1. Critic intrinsic domain contracts
        ↓
2. Critic participant structural + contextual trust boundary
        ↓
3. StageExecution / Review invariant extension
        ↓
4. Explicit Critic Review transitions
        ↓
5. Explicit orchestrator fourth-stage extension
        ↓
6. Regression, isolation, architecture and quality verification
```

Tests SHALL precede corresponding production changes in each increment.

---

## 12. Scope-Control Checks

Before implementation and again before merge, verify Slice 5 has NOT introduced:

- Coordinator behavior;
- final recommendation/ranking;
- FinalReview;
- automatic alternative replacement;
- numeric criticism/risk probability scoring;
- provider SDKs in domain/application;
- direct orchestrator-to-provider calls;
- generic workflow/stage registry;
- generic artifact graph/reference framework;
- persistence/RAG/tools/UI;
- retries/timeouts/concurrency;
- hidden mutable participant state;
- private chain-of-thought storage/exposure.

---

## 13. Planning Decisions Deferred to Data Model

The following SHALL be decided explicitly in `data-model.md`, not implicitly during coding:

1. exact `CriticismTargetType` vocabulary;
2. exact shape of Critic target references across the four upstream artifact families;
3. whether cross-artifact criticisms use multiple explicit basis references, a bounded dedicated structure, or another Critic-specific representation;
4. exact `ValidatedPoint` structure and whether its target reference is optional by shape or by target kind;
5. exact `MissingAlternative` structure, its Critic-specific basis representation, and representation of recommendation-impact severity/boolean/qualitative meaning;
6. exact `Contradiction` side structure and reference requirements;
7. exact `UnresolvedIssue` structure and bounded basis representation where it derives from current artifacts;
8. duplicate/uniqueness invariants for each collection;
9. whether existing qualitative enums can be reused semantically or a Critic-specific enum is clearer.

Participant API naming and failure-message naming are not data-model decisions: `Critic.review(...)`, `CriticOutputError`, `Critic output validation failed`, and `Critic execution failed` are fixed by this approved plan.

No implementation should guess the remaining data-shape decisions before data-model approval.

---

## 14. Plan Acceptance Gate

This plan has been reviewed and approved. `data-model.md` may be created because review confirmed that:

1. implementation boundaries remain minimal and Slice-5-specific;
2. the trust boundary is structural validation followed by explicit current-review contextual validation;
3. generated references and same-execution provenance remain separate;
4. Critic cannot assume Coordinator responsibilities;
5. empty CriticalReview remains valid;
6. all four exact upstream artifacts are carried into Critic execution;
7. lifecycle/failure states are fixed to the exact 9 RUNNING / 4 INCOMPLETE Slice 5 matrix while preserving Slice 1–4 semantics;
8. StageIdentity remains authoritative over tuple position;
9. no generic workflow/reference architecture is introduced prematurely;
10. MissingAlternative and UnresolvedIssue preserve explicit contextual basis when grounded in current artifacts;
11. Critic failure boundaries use exact stable safe messages;
12. remaining unresolved representation decisions are explicitly deferred to data-model rather than hidden in implementation.
