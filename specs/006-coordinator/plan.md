# Implementation Plan: Coordinator v0.1

**Branch**: `006-coordinator`  
**Specification**: `specs/006-coordinator/spec.md` — Approved  
**Status**: Approved — reviewed against specification and existing architecture; ready for data-model design

## 1. Objective

Implement Slice 6 as the minimum fifth-stage extension of the existing Agentic Review Board pipeline:

```text
ReviewInput
  → Analyst / ProblemAnalysis
  → Solution Architect / SolutionAlternatives
  → Risk Reviewer / RiskAssessment
  → Critic / CriticalReview
  → Coordinator / FinalReview
  → Review COMPLETED
```

Coordinator SHALL consolidate the exact five trusted current-review artifacts, produce transparent alternative ordering, distinguish justified recommendation from insufficient evidence, and complete the Review only after the entire `FinalReview` passes structural and contextual validation.

No autonomous action, UI, persistence, scoring model, provider integration, generic workflow engine, or generic reference framework is introduced.

---

## 2. Design Principles

### 2.1 Coordinator decides; upstream participants remain unchanged

Coordinator owns final synthesis, ranking, and recommendation status. It SHALL consume upstream artifacts as immutable review evidence and SHALL NOT rewrite:

- `ReviewInput`;
- `ProblemAnalysis`;
- `SolutionAlternatives`;
- `RiskAssessment`;
- `CriticalReview`.

Critic remains advisory input. Material criticism must be reflected in the final result or explicitly dismissed as not decision-relevant with justification.

### 2.2 Final output remains advisory

`FinalReview` SHALL contain an explicit decision-support notice. A completed Review represents completed advisory analysis, not an executed or automatically accepted decision.

### 2.3 Preserve the established trust boundary

The participant boundary remains:

```text
LLMPort structured response
        ↓ untrusted
Pydantic structural validation
        ↓
Coordinator-specific contextual validation
        ↓ trusted
FinalReview
```

No partial `FinalReview` enters Review state.

### 2.4 Separate generated references from execution provenance

Two concepts remain independent:

- contextual validation determines whether generated IDs/references resolve exactly against current upstream artifacts;
- same-execution provenance determines whether `CoordinatorStageInput` contains the exact current Python objects using identity (`is`).

No abstraction SHALL combine them.

### 2.5 Explicit ranking without scoring

Ranking SHALL use explicit positions and exact alternative identity. Slice 6 SHALL NOT introduce:

- numeric scores;
- weights;
- hidden formulas;
- probability estimates;
- tie-breaking infrastructure.

The model proposes an order; deterministic validation checks the order is complete and internally consistent.

### 2.6 Preserve the accepted alternative cardinality

`SolutionAlternatives` already permits exactly 0, 2, or 3 alternatives. Slice 6 SHALL preserve that upstream contract.

Zero alternatives SHALL produce an empty ranking and `INSUFFICIENT_EVIDENCE`. Two or three alternatives SHALL use one complete ranking structure. A one-alternative state is invalid upstream and SHALL NOT be added as a Coordinator case.

### 2.7 Extend explicitly, not generically

Add Coordinator directly to the existing explicit contracts, lifecycle, transitions, and orchestrator. Do not replace the current implementation with a loop, stage registry, graph, plugin mechanism, or workflow framework.

---

## 3. Proposed Repository Changes

Expected production changes are limited to:

```text
src/agentic_review_board/
├── domain/
│   ├── final_reviews.py          # new FinalReview contracts
│   └── execution.py              # Coordinator input/output, lifecycle, provenance, transitions
├── participants/
│   └── coordinator.py            # participant + contextual validation
└── application/
    └── orchestrator.py           # explicit fifth-stage execution/failure mapping
```

Expected test changes:

```text
tests/unit/
├── test_final_reviews.py         # intrinsic FinalReview contracts
├── test_coordinator.py           # participant/contextual validation
├── test_review_execution.py      # final stage and aggregate invariants
├── test_review_transitions.py    # explicit Coordinator transitions
└── test_review_orchestrator.py   # five-stage success/failure/isolation
```

Expected specification artifacts:

```text
specs/006-coordinator/
├── spec.md
├── plan.md
├── data-model.md
└── tasks.md
```

No new runtime dependency is expected.

Final filenames may be adjusted during data-model review, but responsibility boundaries SHALL remain unchanged.

---

## 4. FinalReview Domain Design Direction

The approved specification requires a trusted final artifact containing conceptually:

```text
FinalReview
├── situation_summary
├── ranked_alternatives[]
├── recommendation_outcome
├── preferred_alternative?
├── conclusion_rationale
├── principal_risks[]
├── unresolved_questions[]
├── next_validation_step
├── confidence
└── decision_support_notice
```

Exact classes and fields are deferred to `data-model.md`.

All trusted domain models SHALL follow the existing conventions:

- Pydantic v2;
- immutable/frozen;
- extra fields forbidden;
- required text non-blank after approved whitespace stripping;
- immutable tuple collections;
- provider-neutral types.

### 4.1 Ranked alternatives

Each ranking entry must be sufficient to represent:

- exact existing alternative identity;
- explicit contiguous position;
- justification;
- final considerations;
- conditions that could change ranking.

The complete ranking rules depend on upstream alternative count:

| Upstream alternatives | Required ranking |
|---:|---|
| 0 | empty |
| 2–3 | every alternative exactly once at positions 1…N |

A count of 1 remains invalid under the accepted `SolutionAlternatives` contract and is not widened by Slice 6.

No ties, gaps, duplicates, omissions, or unknown alternatives are valid.

### 4.2 Recommendation outcome

The model SHALL use exactly:

```text
RECOMMENDED
INSUFFICIENT_EVIDENCE
```

For `RECOMMENDED`:

- preferred alternative required;
- preferred alternative equals the position-1 alternative;
- conclusion rationale required.

For `INSUFFICIENT_EVIDENCE`:

- preferred alternative absent;
- conclusion rationale required;
- zero alternatives necessarily use this outcome.

Position 1 alone does not imply `RECOMMENDED`.

### 4.3 Principal risks

Principal risks SHALL select exact existing `Risk.id` values. The data model should use the smallest representation that supports:

- exact identity;
- no unknown risks;
- no duplicates;
- no invented replacement risk descriptions.

It SHALL not introduce a generic cross-artifact reference framework.

### 4.4 Unresolved questions

Unresolved questions may originate from:

- Analyst missing information or uncertainty;
- Solution Architect generation blockers;
- Risk residual uncertainty;
- Critic contradictions or unresolved issues;
- another visible upstream value without a stable ID.

The data-model phase SHALL define bounded Coordinator-specific shapes. Stable IDs SHALL be used where available; exact visible text may be used only where no stable ID exists.

No fuzzy resolution or silent repair is allowed.

### 4.5 Material criticism disposition

Every entry present in `CriticalReview.criticisms` SHALL be treated as a criticism that Coordinator must address. Each exact `Criticism.id` SHALL appear once as either:

- `REFLECTED`, with an inspectable explanation of its effect on the final result; or
- `DISMISSED`, with a non-empty justification explaining why it is not decision-relevant.

Slice 6 SHALL NOT infer materiality from `CriticismImportance` or introduce a new threshold. The data model SHALL avoid a generic finding-processing framework and SHALL not require mechanical disposition of validated points.

### 4.6 Decision-support notice

The notice is mandatory. The data-model review SHALL decide whether it is:

- a fixed trusted application value; or
- a generated field constrained to an exact approved value.

The simpler option should be preferred while preserving the requirement that `FinalReview` visibly contains the notice.

---

## 5. Coordinator Participant Boundary

Add a participant with the approved five-argument semantic contract:

```python
Coordinator.coordinate(
    review_input,
    problem_analysis,
    solution_alternatives,
    risk_assessment,
    critical_review,
) -> FinalReview
```

The precise method name remains subject to review before plan approval; `coordinate(...)` is proposed because it matches the participant identity and avoids conflating coordination with autonomous decision execution.

The participant SHALL:

1. call `LLMPort.generate_structured(role="coordinator", payload=...)`;
2. serialize exactly the five explicit upstream artifacts into JSON-compatible data;
3. structurally parse a complete `FinalReview`;
4. contextually validate all ranking IDs, preferred alternative, principal risk IDs, unresolved-question references, and material-criticism dispositions;
5. validate cross-field recommendation invariants;
6. return the exact parsed `FinalReview` only after all validation succeeds;
7. raise a dedicated `CoordinatorOutputError` for any structural or contextual output failure.

No provider SDK is added to participant, domain, or application code.

---

## 6. Contextual Validation Strategy

Validation SHALL be explicit and Coordinator-specific.

### 6.1 Alternative resolution

Alternative references resolve by exact existing `SolutionAlternative.id`.

Validate atomically:

- ranking cardinality against upstream alternatives;
- every upstream alternative appears exactly once when required;
- no unknown or duplicate IDs;
- positions equal the exact contiguous set `1..N`;
- preferred ID, when present, resolves exactly;
- preferred ID equals position 1 for `RECOMMENDED`.

### 6.2 Risk resolution

Principal risks resolve by exact `Risk.id`.

Reject:

- unknown IDs;
- duplicates;
- generated replacement risk content;
- IDs absent from the current `RiskAssessment`.

### 6.3 Unresolved-question resolution

The data model SHALL provide a closed set of Coordinator-specific source/kind combinations based only on fields that actually exist in accepted Slice 1–5 models.

Resolution rules:

- exact ID and compatible visible value where a stable ID exists;
- unique exact visible value where no ID exists;
- zero matches fail;
- multiple matches fail;
- absent optional values fail;
- no case folding, fuzzy matching, repair, or semantic normalization.

### 6.4 Criticism disposition validation

Disposition entries SHALL reference exact existing Criticism IDs. Every material criticism present in `CriticalReview.criticisms` SHALL be accounted for exactly once.

The data-model phase SHALL define how “reflected” locations are represented without requiring a generic artifact graph.

### 6.5 Atomicity

One invalid nested ID/reference or one inconsistent recommendation/ranking rule rejects the complete output as `CoordinatorOutputError`. No valid subset is returned or stored.

---

## 7. Execution Model Extension

### 7.1 CoordinatorStageInput

Add an immutable closed input object containing:

```text
CoordinatorStageInput
- review_input: ReviewInput
- problem_analysis: ProblemAnalysis
- solution_alternatives: SolutionAlternatives
- risk_assessment: RiskAssessment
- critical_review: CriticalReview
```

### 7.2 Stage unions

Extend explicitly:

```text
StageInput  += CoordinatorStageInput
StageOutput += FinalReview
```

### 7.3 Local Coordinator states

Permit exactly:

```text
PENDING
inputs=None
output=None
error=None

RUNNING
inputs=CoordinatorStageInput
output=None
error=None

COMPLETED
inputs=CoordinatorStageInput
output=FinalReview
error=None

FAILED
inputs=CoordinatorStageInput
output=None
error=ReviewError
```

### 7.4 Same-execution provenance

For Coordinator RUNNING, COMPLETED, and FAILED:

```python
coordinator.inputs.review_input is review.review_input
coordinator.inputs.problem_analysis is analyst.output
coordinator.inputs.solution_alternatives is solution_architect.output
coordinator.inputs.risk_assessment is risk_reviewer.output
coordinator.inputs.critical_review is critic.output
```

Equality is insufficient.

### 7.5 Review lifecycle

Validate by `StageIdentity`, not tuple position.

Slice 6 permits exactly:

- 10 `RUNNING` shapes;
- 5 `INCOMPLETE` shapes;
- 1 `COMPLETED` shape.

The first nine RUNNING and first four INCOMPLETE shapes remain unchanged from Slice 5. Slice 6 adds:

```text
RUNNING:
A COMPLETED
S COMPLETED
R COMPLETED
C COMPLETED
COORDINATOR RUNNING

INCOMPLETE:
A COMPLETED
S COMPLETED
R COMPLETED
C COMPLETED
COORDINATOR FAILED

COMPLETED:
A COMPLETED
S COMPLETED
R COMPLETED
C COMPLETED
COORDINATOR COMPLETED
```

Noncanonical valid stage tuple order remains supported; lookup and replacement remain identity-based.

---

## 8. Explicit Review Transitions

Add only:

```python
Review.start_coordinator()
Review.complete_coordinator(final_review)
Review.fail_coordinator(error)
```

### start_coordinator

Requires:

- Review RUNNING;
- Analyst, Solution Architect, Risk Reviewer, and Critic COMPLETED;
- exact trusted upstream output types;
- Coordinator PENDING.

Produces Coordinator RUNNING with exact five-object `CoordinatorStageInput`.

### complete_coordinator

Requires Coordinator RUNNING.

Produces:

- Coordinator COMPLETED;
- exact recorded input object preserved;
- exact supplied trusted `FinalReview` object stored;
- Review COMPLETED.

### fail_coordinator

Requires Review RUNNING and Coordinator RUNNING.

Produces atomically:

- Coordinator FAILED;
- exact recorded input preserved;
- no output;
- supplied safe error;
- Review INCOMPLETE.

No generic transition engine is introduced.

---

## 9. Orchestrator Extension

Append one explicit synchronous sequence after Critic completion:

```text
start Coordinator
    ↓
retrieve exact five upstream artifacts by StageIdentity
    ↓
narrow trusted types outside participant try/except
    ↓
Coordinator.coordinate(...)
    ↓ success
complete Coordinator → Review COMPLETED
```

The participant-call failure boundary SHALL catch:

- `CoordinatorOutputError` → `OUTPUT_VALIDATION` with exact message `Coordinator output validation failed`;
- other ordinary `Exception` from the participant call → `EXECUTION` with exact message `Coordinator execution failed`.

Then call `fail_coordinator(...)` and return immediately.

The boundary SHALL NOT swallow:

- transition errors;
- type-narrowing errors;
- aggregate/provenance invariant failures;
- `BaseException` control signals.

No loop, registry, graph, framework, retry, timeout, or concurrency is added.

---

## 10. Test Strategy

Implementation SHALL proceed tests-first in small blocks.

### 10.1 Intrinsic FinalReview contracts

Test independently:

- enums and immutable closed models;
- blank and wrong-type rejection;
- tuple normalization and duplicate rules;
- ranking positions and local invariants;
- recommendation outcome/preferred alternative consistency;
- mandatory conclusion rationale, next validation step, confidence, and decision-support notice;
- zero-, two-, and three-alternative structurally representable states;
- no numeric scoring/probability fields;
- no replacement alternative or risk structures.

### 10.2 Participant and contextual validation

Use deterministic recording/fake `LLMPort` tests for:

- exact role and five-artifact serialization;
- valid multi-alternative recommendation;
- valid insufficient-evidence outcomes;
- zero, two, and three alternatives;
- exact ranking completeness;
- alternative and risk ID resolution;
- unresolved-question references;
- Critic criticism disposition;
- empty and validation-only `CriticalReview`;
- malformed/extra fields;
- unknown, duplicate, omitted, ambiguous, mismatched, or cross-review references;
- preferred alternative/ranking inconsistencies;
- atomic failure with no repair or partial output;
- upstream artifacts unchanged.

### 10.3 Execution aggregate

Directly construct:

- Coordinator PENDING/RUNNING/COMPLETED/FAILED;
- all exact 10 RUNNING shapes;
- all exact 5 INCOMPLETE shapes;
- exact single COMPLETED shape;
- invalid skipped/multiple-failure shapes;
- exact five-object provenance for every non-PENDING Coordinator state;
- equal-but-independent copy rejection;
- identity-based noncanonical tuple behavior.

### 10.4 Transitions

Test:

- start preconditions and exact recorded inputs;
- completion preserves exact input/output objects and yields Review COMPLETED;
- failure is atomic and preserves upstream work;
- repeated, premature, and terminal transitions rejected;
- noncanonical tuple order preserved.

### 10.5 Orchestration

Test:

- exact five-role order;
- exact five-artifact handoff;
- final Review COMPLETED;
- all earlier failure regressions keep Coordinator PENDING and uninvoked;
- Coordinator structural/contextual output failure;
- ordinary Coordinator execution failure;
- exact safe messages and no raw provider detail;
- internal invariant propagation;
- `BaseException` control signals;
- sequential success and failure→fresh-review isolation.

### 10.6 Cross-cutting verification

Run:

```text
python -m pytest
python -m ruff check .
python -m mypy
python -m pip check
```

Inspect production and dependencies for prohibited scope.

No live LLM or network is required by core tests.

---

## 11. Implementation Sequence

1. Define and test intrinsic `FinalReview` contracts.
2. Define and test Coordinator-specific contextual validation.
3. Extend `StageExecution` and Review aggregate invariants.
4. Add explicit Coordinator transitions.
5. Extend `ReviewOrchestrator` through the fifth stage.
6. Run full regression, isolation, quality, dependency, and architecture checks.

Each block SHALL be independently green before the next block begins.

---

## 12. Failure and Security Boundaries

### 12.1 Untrusted model output

All generated Coordinator data remains untrusted until complete structural and contextual validation succeeds.

### 12.2 Safe errors

Trusted Review state stores only:

```text
Coordinator output validation failed
Coordinator execution failed
```

Raw provider exceptions, validation traces, credentials, endpoints, and prompt details are not stored.

### 12.3 Least capability

Coordinator receives only the five explicit current-review artifacts and provider-neutral structured generation capability.

It receives no:

- tools;
- filesystem access;
- network/browsing capability;
- persistence;
- external action authority;
- previous-review memory.

### 12.4 Human authority

`FinalReview` contains an explicit decision-support notice and a next validation step, but the system does not execute or approve any action.

---

## 13. Constitution Check

### I. Genuine collaboration and role integrity — PASS

Coordinator alone ranks and recommends. It consumes every validated upstream artifact and does not absorb or rewrite upstream roles.

### II. Structured contracts and validation — PASS

`FinalReview` and all critical nested information use explicit closed contracts and fail-closed contextual validation.

### III. Traceability, uncertainty, and explicit evidence — PASS

Ranking justification, considerations, risk selection, unresolved questions, Critic disposition, conclusion rationale, and next validation step remain inspectable.

### IV. Human decision authority — PASS

The output is explicitly advisory and no external action capability is introduced.

### V. Minimal architecture — PASS

Only one participant, one output family, one input provenance model, three transitions, and one explicit orchestration step are added.

### VI. Provider independence — PASS

Coordinator depends only on `LLMPort`; no provider SDK reaches domain/application.

### VII. Deterministic testability and visible failure — PASS

All domain, participant, lifecycle, transition, orchestration, and isolation behavior is testable with deterministic substitutes.

### VIII. Security by minimization — PASS

No secrets, persistence, tools, external actions, hidden memory, or additional runtime capability are introduced.

### IX. Incremental delivery — PASS

Work remains ordered by approved artifacts and tests-first implementation blocks.

No constitutional violation or new ADR trigger is identified.

---

## 14. Risks and Mitigations

### Risk 1 — FinalReview becomes a generic evidence graph

**Mitigation:** use Coordinator-specific alternative, risk, unresolved-question, and criticism-disposition references only where required.

### Risk 2 — Ranking validation becomes a scoring engine

**Mitigation:** validate explicit ordering and consistency only; do not calculate, score, weight, or override model judgment.

### Risk 3 — Recommendation is forced by position 1

**Mitigation:** keep recommendation outcome independent and require explicit `RECOMMENDED` plus a matching preferred alternative.

### Risk 4 — Critic mechanically controls Coordinator

**Mitigation:** require visible consideration or justified dismissal, while Coordinator retains final synthesis responsibility.

### Risk 5 — Contextual reference surface grows excessively

**Mitigation:** restrict reference kinds to stable IDs and exact visible values needed by approved `FinalReview`; defer anything not justified by current requirements.

### Risk 6 — Lifecycle completion weakens earlier invariants

**Mitigation:** enumerate and test the exact 10/5/1 lifecycle matrix and preserve identity-based validation.

---

## 15. Completion Criteria

The implementation is ready for final review when:

1. approved `FinalReview` and Coordinator contracts are implemented;
2. contextual validation resolves every required generated reference exactly;
3. ranking and recommendation invariants hold for zero, two, and three alternatives while one alternative remains invalid upstream;
4. every material Critic criticism is reflected or explicitly dismissed;
5. Coordinator transitions enforce exact five-object provenance;
6. successful orchestration yields the sole valid Review COMPLETED shape;
7. failures preserve all upstream artifacts and yield Review INCOMPLETE;
8. deterministic tests cover success, failure, sparse inputs, and isolation;
9. pytest, Ruff, mypy strict, and dependency checks pass;
10. architectural inspection confirms no prohibited scope.

---

## 16. Review Decisions Required Before Approval

Review shall confirm:

1. production filenames and responsibility boundaries;
2. proposed participant method `Coordinator.coordinate(...)`;
3. preservation of the accepted 0/2/3 alternative cardinality and one ranking structure for two or three alternatives;
4. exact two-value recommendation outcome;
5. Coordinator-specific reference direction for risks, unresolved questions, and Critic disposition;
6. mandatory decision-support notice as a fixed trusted application value represented in `FinalReview`;
7. exact 10/5/1 lifecycle matrix;
8. no ADR is required.

No `data-model.md` or implementation work SHALL begin until this plan is reviewed and explicitly approved.
