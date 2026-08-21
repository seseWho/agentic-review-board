# Data Model: Risk Reviewer v0.1

**Branch**: `004-risk-reviewer`  
**Date**: 2026-08-21  
**Spec**: `specs/004-risk-reviewer/spec.md`  
**Plan**: `specs/004-risk-reviewer/plan.md`  
**Status**: Draft — awaiting review and approval

## 1. Purpose

This document refines the exact Slice 4 contracts and invariants required to introduce Risk Reviewer v0.1 and extend the existing Review execution model through the third stage.

The design must satisfy four simultaneous goals:

1. represent risk exposure explicitly and inspectably;
2. preserve traceability to visible current-review artifacts;
3. avoid overstating what local textual references can prove;
4. extend the existing explicit orchestration model without introducing a generic artifact or workflow framework.

Slice 4 remains in-memory, synchronous, provider-neutral, and persistence-free.

---

## 2. Existing Contracts Reused Unchanged

The following current contracts remain authoritative:

```text
ReviewInput
ProblemAnalysis
FactFinding
AnalysisFinding
SolutionAlternatives
SolutionAlternative
ConstraintReference
FindingReference
QualitativeLevel
ReviewError
ReviewErrorKind
StageIdentity
StageStatus
ReviewStatus
```

`QualitativeLevel` continues to mean:

```text
LOW
MEDIUM
HIGH
```

for ordinal qualitative judgment only.

No numeric probability or calibrated risk-score semantics are added.

---

## 3. Risk Domain Contracts

Add:

```text
src/agentic_review_board/domain/risks.py
```

All models in this module SHALL be:

```text
Pydantic v2
extra = forbid
frozen = true
```

Collection fields SHALL use tuples.

Required text SHALL be strict and non-blank.

### 3.1 RiskScopeKind

```text
RiskScopeKind
- OVERALL
- ALTERNATIVES
```

Semantics:

- `OVERALL`: the risk applies to the proposal/review as a whole;
- `ALTERNATIVES`: the risk applies to one or more identified candidate alternatives.

This enum does not encode severity, ranking, probability, or recommendation.

### 3.2 RiskScope

```text
RiskScope
- kind: RiskScopeKind
- alternative_ids: tuple[StrictStr, ...] = ()
```

Intrinsic invariants:

```text
kind == OVERALL
→ alternative_ids must be empty

kind == ALTERNATIVES
→ alternative_ids must contain >= 1 item
→ every id must be non-blank
→ ids must be unique within the scope
```

Contextual invariant owned by `RiskReviewer`:

```text
for every alternative_id
→ exactly one SolutionAlternative with that id exists
  in the current SolutionAlternatives input
```

If current `SolutionAlternatives.alternatives` is empty:

```text
ALTERNATIVES scope is invalid
OVERALL scope remains valid
```

### 3.3 RiskCategory

Use a small closed enum for the canonical MVP categories:

```text
RiskCategory
- TECHNICAL
- SECURITY
- PRIVACY
- OPERATIONAL
- MAINTAINABILITY
- COST
- EXTERNAL_DEPENDENCY
- ORGANIZATIONAL
```

`Risk.category` is optional.

Rationale:

- the canonical Agent Model supplies these categories explicitly;
- a closed enum gives deterministic validation;
- no requirement exists for arbitrary organization-specific category taxonomies in Slice 4;
- absence of category remains valid;
- no category is mandatory and the participant must not manufacture risks merely to populate the enum.

Adding or customizing categories later is a contract change, not a reason to introduce a taxonomy framework now.

---

## 4. Risk Basis References

A material risk must expose why it exists using visible review artifacts.

Slice 4 uses a **Risk Reviewer-specific tagged union**, not a generic cross-stage artifact-reference framework.

Conceptually:

```text
RiskBasisReference =
    ReviewInputBasisReference
    | ProblemAnalysisBasisReference
    | SolutionAlternativeBasisReference
```

Pydantic should use a deterministic discriminator such as `source`.

### 4.1 RiskBasisSource

```text
RiskBasisSource
- REVIEW_INPUT
- PROBLEM_ANALYSIS
- SOLUTION_ALTERNATIVE
```

### 4.2 ReviewInputField

A risk may be based on visible content from the original ReviewInput.

```text
ReviewInputField
- DESCRIPTION
- TITLE
- OBJECTIVE
- CONSTRAINT
- CONTEXT
- STATED_FACT
```

This enum is intentionally more precise than the existing Analyst `ReviewInputSource` where collection members need exact contextual resolution.

### 4.3 ReviewInputBasisReference

```text
ReviewInputBasisReference
- source: REVIEW_INPUT
- field: ReviewInputField
- value: StrictStr
```

Intrinsic invariants:

- `value` non-blank.

Contextual resolution:

```text
DESCRIPTION
→ value == review_input.description

TITLE
→ review_input.title is not None
→ value == review_input.title

OBJECTIVE
→ review_input.objective is not None
→ value == review_input.objective

CONSTRAINT
→ value occurs exactly once in review_input.constraints

CONTEXT
→ value occurs exactly once in review_input.context

STATED_FACT
→ value occurs exactly once in review_input.stated_facts
```

If repeated collection values make a text reference ambiguous, fail closed.

This contract proves that the referenced visible value resolves in the current ReviewInput. It does not prove historical origin across equal-valued review objects.

### 4.4 ProblemAnalysisFindingKind

```text
ProblemAnalysisFindingKind
- FACT
- CONSTRAINT
- ASSUMPTION
- MISSING_INFORMATION
- UNCERTAINTY
```

This explicit kind preserves the fact/assumption distinction required by the constitution.

### 4.5 ProblemAnalysisBasisReference

```text
ProblemAnalysisBasisReference
- source: PROBLEM_ANALYSIS
- kind: ProblemAnalysisFindingKind
- text: StrictStr
- id: StrictStr | None = None
```

Intrinsic invariants:

- `text` non-blank;
- `id`, when present, non-blank.

Contextual resolution selects exactly one current Analyst finding collection from `kind`:

```text
FACT                → problem_analysis.facts
CONSTRAINT          → problem_analysis.constraints
ASSUMPTION          → problem_analysis.assumptions
MISSING_INFORMATION → problem_analysis.missing_information
UNCERTAINTY         → problem_analysis.uncertainties
```

Resolution rule:

```text
id present
→ exactly one item has matching id AND matching text

id absent
→ exactly one item has matching text
```

No match or multiple matches:

```text
→ RiskReviewerOutputError
```

A `kind=ASSUMPTION` reference remains assumption-derived support. The Risk Reviewer must not relabel it as fact-derived support.

### 4.6 SolutionAlternativeCharacteristicKind

A reference to only an alternative ID is insufficient when the risk basis is a specific alternative characteristic.

Use:

```text
SolutionAlternativeCharacteristicKind
- DESCRIPTION
- ADVANTAGE
- DISADVANTAGE
- ASSUMPTION
- IMPLEMENTATION_COMPLEXITY
- RELEVANT_CONSTRAINT
```

No `NAME` characteristic is required because a display label alone does not materially justify risk exposure.

### 4.7 SolutionAlternativeBasisReference

```text
SolutionAlternativeBasisReference
- source: SOLUTION_ALTERNATIVE
- alternative_id: StrictStr
- characteristic: SolutionAlternativeCharacteristicKind
- value: StrictStr
```

Intrinsic invariants:

- `alternative_id` non-blank;
- `value` non-blank.

Contextual resolution first requires exactly one current alternative with:

```text
alternative.id == alternative_id
```

Then resolve characteristic:

```text
DESCRIPTION
→ value == alternative.description

ADVANTAGE
→ value occurs exactly once in alternative.advantages

DISADVANTAGE
→ value occurs exactly once in alternative.disadvantages

ASSUMPTION
→ value occurs exactly once in alternative.assumptions

IMPLEMENTATION_COMPLEXITY
→ value == alternative.implementation_complexity.value

RELEVANT_CONSTRAINT
→ value identifies exactly one serialized existing ConstraintReference
```

#### Relevant-constraint encoding

To avoid introducing a nested generic reference hierarchy, `RELEVANT_CONSTRAINT` basis uses one canonical deterministic text encoding of the existing `ConstraintReference`:

```text
<SOURCE>:<KIND>:<VALUE>
```

Examples:

```text
REVIEW_INPUT:TEXT:Must run offline
PROBLEM_ANALYSIS:ID:CON-001
```

The Risk Reviewer participant computes this encoding from current `alternative.relevant_constraints` and requires exactly one match.

This encoding is review-local and inspectable; it is not a persistent identifier.

### 4.8 RiskBasisReference union

Conceptual discriminated union:

```text
RiskBasisReference = Annotated[
    ReviewInputBasisReference
    | ProblemAnalysisBasisReference
    | SolutionAlternativeBasisReference,
    Field(discriminator="source"),
]
```

Every Risk must contain at least one basis reference.

Duplicate basis entries are not useful. `Risk` SHALL reject exact duplicate basis references within its basis tuple.

---

## 5. Risk

```text
Risk
- id: StrictStr
- category: RiskCategory | None
- description: StrictStr
- affected_scope: RiskScope
- severity: QualitativeLevel
- basis: tuple[RiskBasisReference, ...]
- mitigation: StrictStr | None
- residual_uncertainty: StrictStr | None
```

Intrinsic invariants:

1. `id` non-blank.
2. `description` non-blank.
3. `basis` contains >= 1 reference.
4. Exact duplicate basis references are forbidden.
5. `mitigation`, when present, non-blank.
6. `residual_uncertainty`, when present, non-blank.
7. `severity` is `LOW`, `MEDIUM`, or `HIGH` through existing `QualitativeLevel`.
8. No numeric probability, likelihood, score, rank, recommendation, or preferred-alternative field exists.

Semantic rules enforced by role/contract tests:

- mitigation does not remove the Risk object;
- category is optional;
- scope does not imply ranking;
- basis must resolve against current visible inputs before Risk becomes trusted.

---

## 6. RiskAssessment

```text
RiskAssessment
- risks: tuple[Risk, ...]
- overall_observations: tuple[StrictStr, ...]
```

Intrinsic invariants:

1. `risks` may be empty.
2. Risk IDs must be unique within the assessment.
3. Every observation must be non-blank.
4. Exact duplicate observations are forbidden.
5. Extra fields are forbidden, therefore generated fields such as:

```text
ranking
preferred_alternative
recommendation
winner
probability
risk_score
```

are rejected structurally.

### 6.1 Zero-risk semantics

This is valid:

```text
RiskAssessment(
    risks=(),
    overall_observations=(
        "Current information does not support a material specific risk.",
    ),
)
```

An empty `risks` tuple does not imply:

- the proposal is safe;
- risk is zero;
- alternatives are equivalent;
- a recommendation is justified.

`overall_observations` may describe limitations or remaining uncertainty but must not become a hidden ranking or recommendation channel.

No requirement forces `overall_observations` to be non-empty when `risks` is empty; an entirely empty assessment remains structurally valid. Whether a model chooses to explain limited evidence is prompt/quality behavior, not a domain invariant.

---

## 7. Risk Reviewer Participant Contract

Add:

```text
src/agentic_review_board/participants/risk_reviewer.py
```

### 7.1 Public API

```text
RiskReviewer.assess(
    review_input: ReviewInput,
    problem_analysis: ProblemAnalysis,
    solution_alternatives: SolutionAlternatives,
) -> RiskAssessment
```

### 7.2 Provider-neutral call

```text
raw = llm.generate_structured(
    role="risk_reviewer",
    payload={
        "review_input": review_input.model_dump(mode="json"),
        "problem_analysis": problem_analysis.model_dump(mode="json"),
        "solution_alternatives": solution_alternatives.model_dump(mode="json"),
    },
)
```

### 7.3 Validation sequence

```text
raw Mapping[str, object]
    ↓
RiskAssessment.model_validate(raw)
    ↓
_validate_scope_references(...)
    ↓
_validate_basis_references(...)
    ↓
trusted RiskAssessment
```

Structural Pydantic validation failures map to:

```text
RiskReviewerOutputError("invalid Risk Reviewer output")
```

Contextual unresolved/ambiguous references also map to `RiskReviewerOutputError`.

No raw generated mapping enters Review state.

### 7.4 Contextual scope validation

For each Risk:

```text
OVERALL
→ no alternative lookup

ALTERNATIVES
→ every id must resolve to exactly one current alternative
```

Unknown alternative id:

```text
→ RiskReviewerOutputError
```

### 7.5 Contextual basis validation

For every `Risk.basis` item:

```text
REVIEW_INPUT
→ resolve against current ReviewInput

PROBLEM_ANALYSIS
→ resolve against current ProblemAnalysis collection selected by kind

SOLUTION_ALTERNATIVE
→ resolve current alternative
→ resolve exact characteristic within that alternative
```

No semantic repair occurs.

### 7.6 Contextual reference meaning

Successful resolution means only:

```text
this generated reference resolves unambiguously
inside the trusted artifacts passed to this Risk Reviewer call
```

It does not mean:

```text
this local string carries historical provenance
or globally identifies an artifact across reviews
```

That distinction is intentional.

---

## 8. Execution Model Extension

Update:

```text
src/agentic_review_board/domain/execution.py
```

### 8.1 RiskReviewerStageInput

```text
RiskReviewerStageInput
- review_input: ReviewInput
- problem_analysis: ProblemAnalysis
- solution_alternatives: SolutionAlternatives
```

Configuration:

```text
extra = forbid
frozen = true
```

### 8.2 StageInput union

```text
StageInput =
    AnalystStageInput
    | SolutionArchitectStageInput
    | RiskReviewerStageInput
```

### 8.3 StageOutput union

```text
StageOutput =
    ProblemAnalysis
    | SolutionAlternatives
    | RiskAssessment
```

### 8.4 StageExecution identity/type matrix

#### ANALYST

Unchanged.

#### SOLUTION_ARCHITECT

Unchanged.

#### RISK_REVIEWER

```text
PENDING
inputs = None
output = None
error = None

RUNNING
inputs = RiskReviewerStageInput
output = None
error = None

COMPLETED
inputs = RiskReviewerStageInput
output = RiskAssessment
error = None

FAILED
inputs = RiskReviewerStageInput
output = None
error = ReviewError
```

#### CRITIC / COORDINATOR

Slice 4 rule:

```text
must remain PENDING
```

Any non-PENDING Critic or Coordinator stage is invalid in Slice 4.

---

## 9. Review Same-Execution Provenance

`Review` validation continues to use object identity for in-memory execution provenance.

All semantic lookups use `StageIdentity`, never stage tuple position.

For Risk Reviewer when non-PENDING:

```text
risk.inputs.review_input
    is review.review_input
```

and Analyst must be completed with:

```text
ProblemAnalysis
```

and Solution Architect must be completed with:

```text
SolutionAlternatives
```

Then:

```text
risk.inputs.problem_analysis
    is analyst.output

risk.inputs.solution_alternatives
    is architect.output
```

Equal-but-independent objects are invalid for StageExecution provenance.

This rule applies to direct Review construction as well as transitions.

---

## 10. Review Stage Set and Ordering

Canonical identities remain exactly:

```text
ANALYST
SOLUTION_ARCHITECT
RISK_REVIEWER
CRITIC
COORDINATOR
```

Every Review must contain exactly one StageExecution for each identity.

Validation remains set/identity based:

```text
len(identities) == 5
set(identities) == set(CANONICAL_STAGE_ORDER)
```

It must not require tuple order equality.

`Review.create()` still emits canonical order.

`_replace_stage()` preserves whatever tuple order is present in an already valid Review.

Semantic validation uses:

```text
review.stage(StageIdentity....)
```

not:

```text
review.stages[index]
```

---

## 11. Slice 4 Review Lifecycle Matrix

Let:

```text
A = Analyst
S = Solution Architect
R = Risk Reviewer
C = Critic
K = Coordinator
```

Critic and Coordinator must be PENDING for every non-COMPLETED Slice 4 state.

### 11.1 CREATED

Exactly:

```text
Review CREATED
A PENDING
S PENDING
R PENDING
C PENDING
K PENDING
```

### 11.2 RUNNING valid prefixes

Valid Slice 4 RUNNING stage triples `(A, S, R)` are exactly:

```text
(PENDING,   PENDING,   PENDING)
(RUNNING,   PENDING,   PENDING)
(COMPLETED, PENDING,   PENDING)
(COMPLETED, RUNNING,   PENDING)
(COMPLETED, COMPLETED, PENDING)
(COMPLETED, COMPLETED, RUNNING)
(COMPLETED, COMPLETED, COMPLETED)
```

For all seven:

```text
C PENDING
K PENDING
```

No other RUNNING combination is valid.

### 11.3 INCOMPLETE valid failure shapes

Exactly one implemented stage is failed and all downstream stages remain PENDING.

Valid `(A, S, R)` tuples:

```text
(FAILED,    PENDING, PENDING)
(COMPLETED, FAILED,  PENDING)
(COMPLETED, COMPLETED, FAILED)
```

And always:

```text
C PENDING
K PENDING
```

### 11.4 COMPLETED

Contractual global rule remains:

```text
Review COMPLETED
→ all five stages COMPLETED
```

Because Critic and Coordinator are PENDING-only in Slice 4, no Slice 4 transition can produce Review `COMPLETED`.

Direct construction of a fully completed five-stage Review is still rejected by StageExecution type rules because Critic/Coordinator outputs are not implemented yet.

---

## 12. Review Transitions

Existing Analyst and Solution Architect transitions remain unchanged.

Add exactly three Risk Reviewer transitions.

### 12.1 start_risk_reviewer()

Preconditions:

```text
Review.status == RUNNING
Analyst.status == COMPLETED
Analyst.output is ProblemAnalysis
Solution Architect.status == COMPLETED
Solution Architect.output is SolutionAlternatives
Risk Reviewer.status == PENDING
```

Transition result:

```text
Risk Reviewer.status = RUNNING
inputs = RiskReviewerStageInput(
    review_input=self.review_input,
    problem_analysis=analyst.output,
    solution_alternatives=architect.output,
)
output = None
error = None
```

Review status remains `RUNNING`.

The exact existing Analyst and Architect StageExecution objects are preserved.

### 12.2 complete_risk_reviewer(risk_assessment)

Preconditions:

```text
Review.status == RUNNING
Risk Reviewer.status == RUNNING
Risk Reviewer.inputs is RiskReviewerStageInput
risk_assessment is RiskAssessment by type boundary
```

Transition result:

```text
Risk Reviewer.status = COMPLETED
inputs = exact previous RiskReviewerStageInput object
output = exact supplied RiskAssessment object
error = None
```

Review remains `RUNNING`.

Critic and Coordinator remain PENDING.

### 12.3 fail_risk_reviewer(error)

Preconditions:

```text
Review.status == RUNNING
Risk Reviewer.status == RUNNING
Risk Reviewer.inputs is RiskReviewerStageInput
error is ReviewError by type boundary
```

Atomic transition result:

```text
Review.status = INCOMPLETE
Risk Reviewer.status = FAILED
inputs = exact previous RiskReviewerStageInput object
output = None
error = supplied ReviewError
Critic PENDING
Coordinator PENDING
```

Analyst and Architect stages are preserved exactly.

---

## 13. Orchestrator Typing and Narrowing

`ReviewOrchestrator` constructor conceptually becomes:

```text
ReviewOrchestrator(
    analyst: Analyst,
    solution_architect: SolutionArchitect,
    risk_reviewer: RiskReviewer,
)
```

After Solution Architect completion:

```text
review = review.start_risk_reviewer()
```

Retrieve by identity:

```text
analyst_stage = review.stage(StageIdentity.ANALYST)
architect_stage = review.stage(StageIdentity.SOLUTION_ARCHITECT)
```

Narrow explicitly:

```text
if not isinstance(analyst_stage.output, ProblemAnalysis):
    raise ValueError(...)

if not isinstance(architect_stage.output, SolutionAlternatives):
    raise ValueError(...)
```

These checks are internal invariant guards and remain **outside** the participant try/except boundary.

Participant call:

```text
try:
    risk_assessment = risk_reviewer.assess(
        review.review_input,
        analyst_stage.output,
        architect_stage.output,
    )
except RiskReviewerOutputError:
    ...
except Exception:
    ...
```

Then:

```text
return review.complete_risk_reviewer(risk_assessment)
```

The Orchestrator does not call `LLMPort` directly.

---

## 14. Failure Mapping

### 14.1 Known generated-output validation failure

```text
RiskReviewerOutputError
→ ReviewError(
    kind=OUTPUT_VALIDATION,
    message="Risk Reviewer output validation failed",
)
```

### 14.2 Other ordinary participant exception

```text
Exception raised by RiskReviewer.assess(...)
→ ReviewError(
    kind=EXECUTION,
    message="Risk Reviewer execution failed",
)
```

No raw exception text is stored.

No provider name, prompt, response, stack trace, secret, endpoint, or private reasoning is copied into ReviewError.

### 14.3 Internal invariant failure

Errors raised while:

- starting/completing/failing a Review transition;
- retrieving stages;
- narrowing trusted stage outputs;
- validating Review aggregate invariants;

remain outside the participant exception boundary and propagate to the caller.

`KeyboardInterrupt`, `SystemExit`, and other `BaseException` subclasses are not swallowed.

---

## 15. Required Validation Examples

### Valid overall risk

```text
Risk(
    id="RISK-001",
    category=TECHNICAL,
    description="The design may exceed the available offline compute budget.",
    affected_scope=RiskScope(
        kind=OVERALL,
        alternative_ids=(),
    ),
    severity=HIGH,
    basis=(
        ReviewInputBasisReference(
            source=REVIEW_INPUT,
            field=CONSTRAINT,
            value="Must run offline",
        ),
    ),
    mitigation="Benchmark the target hardware before selecting the implementation.",
    residual_uncertainty="Actual production workload size is not yet known.",
)
```

### Valid alternative-specific risk

```text
Risk(
    id="RISK-002",
    category=MAINTAINABILITY,
    description="ALT-001 depends on a high-complexity implementation.",
    affected_scope=RiskScope(
        kind=ALTERNATIVES,
        alternative_ids=("ALT-001",),
    ),
    severity=MEDIUM,
    basis=(
        SolutionAlternativeBasisReference(
            source=SOLUTION_ALTERNATIVE,
            alternative_id="ALT-001",
            characteristic=IMPLEMENTATION_COMPLEXITY,
            value="HIGH",
        ),
    ),
    mitigation=None,
    residual_uncertainty=None,
)
```

### Valid assumption-derived risk basis

```text
ProblemAnalysisBasisReference(
    source=PROBLEM_ANALYSIS,
    kind=ASSUMPTION,
    text="Users will accept a local-only workflow",
    id="ASM-001",
)
```

It remains visibly assumption-derived.

### Invalid scope

```text
kind=OVERALL
alternative_ids=("ALT-001",)
```

Rejected structurally.

### Invalid alternative reference

```text
kind=ALTERNATIVES
alternative_ids=("ALT-999",)
```

Structurally valid but rejected contextually if `ALT-999` is not in current SolutionAlternatives.

### Invalid weak alternative basis

A generated object containing only:

```text
source=SOLUTION_ALTERNATIVE
alternative_id=ALT-001
```

is rejected because the discriminated model also requires `characteristic` and `value`.

### Invalid role leakage

```text
{
  "risks": [],
  "overall_observations": [],
  "preferred_alternative": "ALT-001"
}
```

Rejected because `extra="forbid"`.

---

## 16. Test Matrix Derived from the Model

### Risk-domain intrinsic tests

- all contracts frozen / extra-forbid;
- required strings reject blank;
- scope OVERALL/ALTERNATIVES compatibility;
- alternative IDs unique within scope;
- category optional and enum-restricted;
- Risk basis non-empty;
- duplicate exact basis rejected;
- Risk IDs unique within assessment;
- observations reject blank/duplicate;
- zero-risk assessment valid;
- unsupported ranking/recommendation/probability fields rejected.

### Contextual ReviewInput basis tests

- description resolves;
- optional title/objective resolve only when present;
- current constraint/context/stated_fact resolves;
- absent value rejected;
- duplicate collection text is ambiguous and rejected.

### Contextual ProblemAnalysis basis tests

For every finding kind:

- exact id+text resolves;
- text-only resolves when unique;
- unknown id/text rejected;
- mismatched id+text rejected;
- duplicate text without id rejected;
- assumption kind remains separate from fact kind.

### Contextual SolutionAlternative basis tests

- description resolves;
- unique advantage/disadvantage/assumption resolves;
- duplicate text is ambiguous and rejected;
- implementation complexity resolves from enum value;
- relevant constraint canonical encoding resolves;
- unknown alternative rejected;
- characteristic/value mismatch rejected;
- zero-alternative result cannot resolve any alternative basis.

### Execution/provenance tests

- RiskReviewerStageInput accepted only for Risk Reviewer non-PENDING states;
- completed Risk Reviewer requires RiskAssessment;
- Critic/Coordinator non-PENDING rejected;
- Risk Reviewer exact ReviewInput identity required;
- exact Analyst ProblemAnalysis identity required;
- exact Architect SolutionAlternatives identity required;
- equal-but-independent copies rejected;
- reordered valid stage tuple remains semantically valid through identity lookup.

### Lifecycle tests

- all seven RUNNING prefixes accepted;
- all three INCOMPLETE failure shapes accepted;
- invalid skipped-stage combinations rejected;
- `COMPLETED` unreachable in Slice 4.

### Transition tests

- Risk Reviewer start/complete/fail happy paths;
- start before Architect completion rejected;
- repeated start rejected;
- completion/failure before start rejected;
- upstream stages preserved exactly;
- Critic/Coordinator remain PENDING;
- transitions work with noncanonical but valid tuple order.

### Orchestrator tests

- exact role order Analyst → Solution Architect → Risk Reviewer;
- inputs recorded before Risk Reviewer call;
- exact trusted upstream objects passed;
- RiskReviewerOutputError maps to OUTPUT_VALIDATION;
- ordinary participant Exception maps to EXECUTION;
- internal invariant error not converted;
- BaseException signals propagate;
- zero-risk output completes Risk Reviewer;
- zero-alternative upstream still invokes Risk Reviewer;
- sequential reviews remain isolated.

---

## 17. Explicit Non-Goals

This data model does not introduce:

- Critic or Coordinator contracts;
- ranking or recommendation fields;
- risk probability/likelihood scores;
- impact matrices;
- persistent/global IDs;
- generic ArtifactReference abstractions;
- generic stage payload models;
- workflow registries;
- persistence or rehydration semantics;
- retries/timeouts;
- RAG/tools/browsing;
- provider-specific types;
- organization-custom risk taxonomy infrastructure.

---

## 18. Open Design Questions

None required before task breakdown.

The selected contracts are intentionally sufficient for Slice 4 and deliberately avoid solving future Critic/Coordinator reference needs in advance.

If implementation evidence later shows that duplicated reference-resolution logic across multiple future participants becomes a real maintenance problem, a reusable reference abstraction can be proposed separately with tests and architectural review.

---

## 19. Approval Gate

Before generating `tasks.md`, review this data model for:

- compatibility with canonical Risk Reviewer semantics;
- basis-reference sufficiency without overengineering;
- correct fact/assumption preservation;
- correct separation of contextual references vs same-execution provenance;
- consistency with existing Slice 3 identity-based Review semantics;
- complete lifecycle matrix;
- fail-closed output handling;
- absence of ranking/recommendation leakage;
- absence of premature generic abstractions.

Only after explicit approval should implementation tasks be generated.
