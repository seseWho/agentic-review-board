# Data Model: Risk Reviewer v0.1

**Branch**: `004-risk-reviewer`  
**Date**: 2026-08-21  
**Spec**: `specs/004-risk-reviewer/spec.md`  
**Plan**: `specs/004-risk-reviewer/plan.md`  
**Status**: Approved — ready for task breakdown and implementation planning

## 1. Purpose

This document refines the exact Slice 4 contracts and invariants required to introduce Risk Reviewer v0.1 and extend the existing Review execution model through the third stage.

The design must:

1. represent material risk exposure explicitly;
2. preserve traceability to visible current-review artifacts;
3. distinguish generated-reference resolution from same-execution provenance;
4. preserve fact/assumption semantics;
5. remain minimal and specific to Risk Reviewer;
6. extend the existing explicit orchestrator without a generic workflow/reference framework.

Slice 4 remains in-memory, synchronous, provider-neutral, and persistence-free.

---

## 2. Existing Contracts Reused

The following existing contracts remain authoritative:

```text
ReviewInput
ReviewInputSource
ProblemAnalysis
FactFinding
AnalysisFinding
SolutionAlternatives
SolutionAlternative
ConstraintReference
ConstraintReferenceKind
ConstraintSource
QualitativeLevel
ReviewError
ReviewErrorKind
StageIdentity
StageStatus
ReviewStatus
```

`QualitativeLevel` remains exactly:

```text
LOW
MEDIUM
HIGH
```

for qualitative ordinal judgment only.

No probability, calibrated likelihood, risk score, expected loss, or confidence percentage is introduced.

---

## 3. Risk Domain Module

Add:

```text
src/agentic_review_board/domain/risks.py
```

All models in this module SHALL use:

```text
Pydantic v2
extra = forbid
frozen = true
```

Collections SHALL use tuples.

Required text SHALL be strict and non-blank.

---

## 4. Risk Scope

### 4.1 RiskScopeKind

```text
RiskScopeKind
- OVERALL
- ALTERNATIVES
```

Semantics:

- `OVERALL`: applies to the proposal/review as a whole;
- `ALTERNATIVES`: applies to one or more identified current candidate alternatives.

### 4.2 RiskScope

```text
RiskScope
- kind: RiskScopeKind
- alternative_ids: tuple[StrictStr, ...] = ()
```

Intrinsic invariants:

```text
OVERALL
→ alternative_ids == ()

ALTERNATIVES
→ len(alternative_ids) >= 1
→ every id non-blank
→ ids unique
```

Contextual invariant owned by `RiskReviewer`:

```text
for every alternative_id
→ exactly one current SolutionAlternative has that id
```

If `SolutionAlternatives.alternatives` is empty:

```text
OVERALL scope remains valid
ALTERNATIVES scope is contextually invalid
```

---

## 5. Optional Risk Category

The canonical documents provide representative categories, not an exhaustive ontology.

Therefore Slice 4 uses:

```text
category: StrictStr | None = None
```

Intrinsic rule:

```text
if category is not None
→ category must be non-blank
```

Representative prompt/display labels may include:

```text
technical
security
privacy
operational
maintainability
cost
external dependency
organizational
```

But the trusted contract does not restrict categories to that list.

This avoids both:

- inventing a taxonomy framework;
- incorrectly rejecting a grounded category such as `legal` or `compliance`.

Category never determines severity or ranking automatically.

---

## 6. Risk Basis References

Each material Risk must contain a non-empty structured `basis` explaining why it exists.

Slice 4 uses a Risk Reviewer-specific discriminated union:

```text
RiskBasisReference =
    ReviewInputBasisReference
    | ProblemAnalysisBasisReference
    | SolutionAlternativeBasisReference
```

This is deliberately not a generic cross-stage artifact-reference framework.

### 6.1 RiskBasisSource

```text
RiskBasisSource
- REVIEW_INPUT
- PROBLEM_ANALYSIS
- SOLUTION_ALTERNATIVE
```

### 6.2 Pydantic discriminator requirement

The union uses:

```python
Field(discriminator="source")
```

Therefore every variant SHALL expose `source` as a literal tag, not merely as the shared enum type.

Conceptually:

```python
source: Literal[RiskBasisSource.REVIEW_INPUT] = RiskBasisSource.REVIEW_INPUT
```

and equivalently for the other variants.

This is required for valid deterministic Pydantic v2 discriminated-union construction.

---

## 7. ReviewInputBasisReference

Reuse the existing `ReviewInputSource` enum rather than creating a second vocabulary.

```text
ReviewInputBasisReference
- source: Literal[REVIEW_INPUT]
- field: ReviewInputSource
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

CONSTRAINTS
→ value occurs exactly once in review_input.constraints

CONTEXT
→ value occurs exactly once in review_input.context

STATED_FACTS
→ value occurs exactly once in review_input.stated_facts
```

If a collection contains the same text more than once, a text-only generated reference is ambiguous and fails closed.

Successful resolution means only that the value resolves unambiguously inside the current `ReviewInput` supplied to the participant.

---

## 8. ProblemAnalysisBasisReference

### 8.1 ProblemAnalysisFindingKind

```text
ProblemAnalysisFindingKind
- FACT
- CONSTRAINT
- ASSUMPTION
- MISSING_INFORMATION
- UNCERTAINTY
```

This kind is explicit so assumption-derived basis remains structurally distinct from fact-derived basis.

### 8.2 Contract

```text
ProblemAnalysisBasisReference
- source: Literal[PROBLEM_ANALYSIS]
- kind: ProblemAnalysisFindingKind
- text: StrictStr
- id: StrictStr | None = None
```

Intrinsic invariants:

- `text` non-blank;
- `id`, when present, non-blank.

Contextual collection selection:

```text
FACT                → problem_analysis.facts
CONSTRAINT          → problem_analysis.constraints
ASSUMPTION          → problem_analysis.assumptions
MISSING_INFORMATION → problem_analysis.missing_information
UNCERTAINTY         → problem_analysis.uncertainties
```

Resolution:

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

`ASSUMPTION` never becomes `FACT` merely because Risk Reviewer references it.

---

## 9. SolutionAlternativeBasisReference

A plain alternative ID can identify affected scope, but it is insufficient as risk basis when the risk depends on a specific alternative characteristic.

### 9.1 SolutionAlternativeCharacteristicKind

```text
SolutionAlternativeCharacteristicKind
- DESCRIPTION
- ADVANTAGE
- DISADVANTAGE
- ASSUMPTION
- IMPLEMENTATION_COMPLEXITY
- RELEVANT_CONSTRAINT
```

`NAME` is intentionally excluded because a display label does not materially justify risk exposure.

### 9.2 Contract

```text
SolutionAlternativeBasisReference
- source: Literal[SOLUTION_ALTERNATIVE]
- alternative_id: StrictStr
- characteristic: SolutionAlternativeCharacteristicKind
- value: StrictStr | ConstraintReference
```

Intrinsic invariants:

- `alternative_id` non-blank;
- when `value` is text, it is non-blank;
- characteristic/value shape is compatible:

```text
RELEVANT_CONSTRAINT
→ value must be ConstraintReference

all other characteristics
→ value must be StrictStr
```

Contextual resolution first requires exactly one current alternative with:

```text
alternative.id == alternative_id
```

Then:

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
→ value equals exactly one current alternative.relevant_constraints item
```

No custom `<SOURCE>:<KIND>:<VALUE>` encoding is introduced.

Reusing the existing structured `ConstraintReference` keeps the generated contract closer to the already trusted Solution Architect output and removes unnecessary serialization rules.

---

## 10. RiskBasisReference Union

Conceptually:

```python
RiskBasisReference = Annotated[
    ReviewInputBasisReference
    | ProblemAnalysisBasisReference
    | SolutionAlternativeBasisReference,
    Field(discriminator="source"),
]
```

Every `Risk` SHALL contain at least one basis reference.

Exact duplicate basis references inside one Risk are rejected.

Generated basis references are resolved contextually against the trusted current inputs before `RiskAssessment` becomes trusted.

---

## 11. Risk

```text
Risk
- id: StrictStr
- category: StrictStr | None = None
- description: StrictStr
- affected_scope: RiskScope
- severity: QualitativeLevel
- basis: tuple[RiskBasisReference, ...]
- mitigation: StrictStr | None = None
- residual_uncertainty: StrictStr | None = None
```

Intrinsic invariants:

1. `id` non-blank.
2. `description` non-blank.
3. optional category non-blank when present.
4. basis contains at least one item.
5. exact duplicate basis references forbidden.
6. optional mitigation non-blank when present.
7. optional residual uncertainty non-blank when present.
8. severity uses existing `QualitativeLevel` only.
9. no probability, likelihood, score, rank, recommendation, winner, or preferred-alternative field exists.

Semantic role rules:

- mitigation does not remove the Risk;
- scope does not imply ranking;
- category remains descriptive only;
- basis must resolve before trusted propagation.

---

## 12. RiskAssessment

```text
RiskAssessment
- risks: tuple[Risk, ...]
- overall_observations: tuple[StrictStr, ...]
```

Intrinsic invariants:

1. risks may be empty;
2. risk IDs unique within the assessment;
3. every observation non-blank;
4. exact duplicate observations forbidden;
5. extra fields forbidden.

Therefore fields such as:

```text
ranking
preferred_alternative
recommendation
winner
probability
risk_score
```

are rejected structurally.

### 12.1 Zero-risk semantics

Valid:

```text
RiskAssessment(
    risks=(),
    overall_observations=(
        "Current information does not support a material specific risk.",
    ),
)
```

Also structurally valid:

```text
RiskAssessment(
    risks=(),
    overall_observations=(),
)
```

Zero risks does not imply safety, zero exposure, equivalence, or recommendation readiness.

---

## 13. Risk Reviewer Participant Contract

Add:

```text
src/agentic_review_board/participants/risk_reviewer.py
```

### 13.1 Public API

```text
RiskReviewer.assess(
    review_input: ReviewInput,
    problem_analysis: ProblemAnalysis,
    solution_alternatives: SolutionAlternatives,
) -> RiskAssessment
```

### 13.2 Provider-neutral payload

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

### 13.3 Validation sequence

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

Structural Pydantic failures:

```text
RiskReviewerOutputError("invalid Risk Reviewer output")
```

Contextual unresolved/ambiguous references also raise `RiskReviewerOutputError`.

No invalid/raw mapping enters Review state.

---

## 14. Contextual Validation Meaning

### 14.1 Scope

```text
OVERALL
→ no alternative lookup

ALTERNATIVES
→ every alternative id resolves exactly once
```

### 14.2 Basis

```text
REVIEW_INPUT
→ resolve current ReviewInput field/value

PROBLEM_ANALYSIS
→ resolve current Analyst collection item

SOLUTION_ALTERNATIVE
→ resolve current alternative
→ resolve exact characteristic/value
```

No semantic repair occurs.

### 14.3 What contextual references prove

Successful reference resolution means:

```text
this generated reference resolves unambiguously
inside the trusted artifacts supplied to this Risk Reviewer execution
```

It does not prove historical/global provenance across equal-valued reviews.

Same-execution provenance is handled separately by Review/StageExecution object identity.

---

## 15. Execution Model Extension

Update:

```text
src/agentic_review_board/domain/execution.py
```

### 15.1 RiskReviewerStageInput

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

### 15.2 StageInput

```text
StageInput =
    AnalystStageInput
    | SolutionArchitectStageInput
    | RiskReviewerStageInput
```

### 15.3 StageOutput

```text
StageOutput =
    ProblemAnalysis
    | SolutionAlternatives
    | RiskAssessment
```

### 15.4 StageExecution type matrix

Risk Reviewer:

```text
PENDING
→ inputs=None, output=None, error=None

RUNNING
→ inputs=RiskReviewerStageInput
→ output=None, error=None

COMPLETED
→ inputs=RiskReviewerStageInput
→ output=RiskAssessment
→ error=None

FAILED
→ inputs=RiskReviewerStageInput
→ output=None
→ error=ReviewError
```

Critic and Coordinator remain PENDING-only in Slice 4.

Any non-PENDING Critic/Coordinator stage remains invalid.

---

## 16. Same-Execution Provenance

All semantic stage lookup uses `StageIdentity`, never tuple position.

For Risk Reviewer when non-PENDING:

```text
risk.inputs.review_input is review.review_input
risk.inputs.problem_analysis is analyst.output
risk.inputs.solution_alternatives is architect.output
```

Preconditions for those identity checks:

```text
Analyst COMPLETED with ProblemAnalysis
Solution Architect COMPLETED with SolutionAlternatives
```

Equal-but-independent upstream objects are invalid as StageExecution provenance even when values are equal.

This identity rule applies to direct Review construction and transitions.

---

## 17. Stage Set and Ordering

Canonical identities remain exactly:

```text
ANALYST
SOLUTION_ARCHITECT
RISK_REVIEWER
CRITIC
COORDINATOR
```

Every Review contains exactly one StageExecution for each identity.

Validation remains identity/set based:

```text
len(identities) == 5
set(identities) == set(CANONICAL_STAGE_ORDER)
```

Tuple order equality is not a semantic invariant.

`Review.create()` emits canonical order.

`_replace_stage()` preserves the tuple order of an already valid Review.

All semantic lookup uses:

```text
review.stage(StageIdentity....)
```

not positional indexes.

---

## 18. Slice 4 Lifecycle Matrix

Let:

```text
A = Analyst
S = Solution Architect
R = Risk Reviewer
C = Critic
K = Coordinator
```

For Slice 4, C and K remain PENDING for all reachable states.

### 18.1 CREATED

Exactly:

```text
Review CREATED
A PENDING
S PENDING
R PENDING
C PENDING
K PENDING
```

### 18.2 RUNNING

Valid `(A, S, R)` prefixes exactly:

```text
(PENDING,   PENDING,   PENDING)
(RUNNING,   PENDING,   PENDING)
(COMPLETED, PENDING,   PENDING)
(COMPLETED, RUNNING,   PENDING)
(COMPLETED, COMPLETED, PENDING)
(COMPLETED, COMPLETED, RUNNING)
(COMPLETED, COMPLETED, COMPLETED)
```

Always:

```text
C PENDING
K PENDING
```

No other RUNNING combination is valid.

### 18.3 INCOMPLETE

Valid `(A, S, R)` shapes exactly:

```text
(FAILED,    PENDING,   PENDING)
(COMPLETED, FAILED,    PENDING)
(COMPLETED, COMPLETED, FAILED)
```

Always:

```text
C PENDING
K PENDING
```

Exactly one implemented stage is failed and every downstream stage remains PENDING.

### 18.4 COMPLETED

Global contractual rule remains:

```text
Review COMPLETED
→ all five stages COMPLETED
```

Slice 4 cannot produce this state because Critic/Coordinator remain unimplemented/PENDING-only.

---

## 19. Risk Reviewer Review Transitions

Existing Analyst and Solution Architect transitions remain unchanged.

Add exactly:

```text
start_risk_reviewer()
complete_risk_reviewer(risk_assessment)
fail_risk_reviewer(error)
```

### 19.1 start_risk_reviewer()

Preconditions:

```text
Review RUNNING
Analyst COMPLETED with ProblemAnalysis
Solution Architect COMPLETED with SolutionAlternatives
Risk Reviewer PENDING
Critic PENDING
Coordinator PENDING
```

Result:

```text
Risk Reviewer RUNNING
inputs = RiskReviewerStageInput(
    review_input=self.review_input,
    problem_analysis=analyst.output,
    solution_alternatives=architect.output,
)
output=None
error=None
Review remains RUNNING
```

Existing Analyst and Architect StageExecution objects remain unchanged.

### 19.2 complete_risk_reviewer(...)

Preconditions:

```text
Review RUNNING
Risk Reviewer RUNNING
Risk Reviewer.inputs is RiskReviewerStageInput
```

Result:

```text
Risk Reviewer COMPLETED
inputs = exact previous input object
output = exact supplied RiskAssessment object
error=None
Review remains RUNNING
Critic/Coordinator remain PENDING
```

### 19.3 fail_risk_reviewer(...)

Preconditions:

```text
Review RUNNING
Risk Reviewer RUNNING
Risk Reviewer.inputs is RiskReviewerStageInput
```

Atomic result:

```text
Review INCOMPLETE
Risk Reviewer FAILED
inputs = exact previous input object
output=None
error=supplied ReviewError
Critic PENDING
Coordinator PENDING
```

Analyst and Architect stages remain exactly preserved.

---

## 20. Orchestrator Typing and Boundary

Constructor conceptually becomes:

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

Retrieve upstream stages by identity:

```text
analyst_stage = review.stage(StageIdentity.ANALYST)
architect_stage = review.stage(StageIdentity.SOLUTION_ARCHITECT)
```

Internal invariant guards:

```text
if not isinstance(analyst_stage.output, ProblemAnalysis):
    raise ValueError(...)

if not isinstance(architect_stage.output, SolutionAlternatives):
    raise ValueError(...)
```

These guards remain outside participant try/except handling.

Participant boundary:

```text
try:
    risk_assessment = risk_reviewer.assess(
        review.review_input,
        analyst_stage.output,
        architect_stage.output,
    )
except RiskReviewerOutputError:
    ... OUTPUT_VALIDATION ...
except Exception:
    ... EXECUTION ...
```

Then:

```text
return review.complete_risk_reviewer(risk_assessment)
```

The Orchestrator never calls `LLMPort` directly.

---

## 21. Failure Mapping

Known generated-output validation failure:

```text
RiskReviewerOutputError
→ ReviewError(
    kind=OUTPUT_VALIDATION,
    message="Risk Reviewer output validation failed",
)
```

Other ordinary participant exception:

```text
Exception from RiskReviewer.assess(...)
→ ReviewError(
    kind=EXECUTION,
    message="Risk Reviewer execution failed",
)
```

No raw exception detail, provider name, prompt, response, stack trace, secret, endpoint, or private reasoning is stored.

Internal transition/stage/aggregate errors remain outside participant exception mapping and propagate.

`KeyboardInterrupt`, `SystemExit`, and other `BaseException` subclasses are not swallowed.

---

## 22. Validation Examples

### 22.1 Overall risk

```text
Risk(
    id="RISK-001",
    category="technical",
    description="The design may exceed the available offline compute budget.",
    affected_scope=RiskScope(kind=OVERALL, alternative_ids=()),
    severity=HIGH,
    basis=(
        ReviewInputBasisReference(
            source=REVIEW_INPUT,
            field=CONSTRAINTS,
            value="Must run offline",
        ),
    ),
    mitigation="Benchmark the target hardware before selection.",
    residual_uncertainty="Production workload size is unknown.",
)
```

### 22.2 Alternative-specific risk

```text
Risk(
    id="RISK-002",
    category="maintainability",
    description="ALT-001 has high implementation complexity.",
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
)
```

### 22.3 Relevant-constraint basis

```text
SolutionAlternativeBasisReference(
    source=SOLUTION_ALTERNATIVE,
    alternative_id="ALT-001",
    characteristic=RELEVANT_CONSTRAINT,
    value=ConstraintReference(
        source=PROBLEM_ANALYSIS,
        kind=ID,
        value="CON-001",
    ),
)
```

### 22.4 Assumption-derived basis

```text
ProblemAnalysisBasisReference(
    source=PROBLEM_ANALYSIS,
    kind=ASSUMPTION,
    text="Users will accept a local-only workflow",
    id="ASM-001",
)
```

The assumption remains visibly an assumption.

### 22.5 Invalid role leakage

```json
{
  "risks": [],
  "overall_observations": [],
  "preferred_alternative": "ALT-001"
}
```

Rejected because `extra="forbid"`.

---

## 23. Required Test Matrix

### Domain / Pydantic

- discriminated union constructs successfully using Literal source tags;
- all models frozen and extra-forbid;
- required strings reject blank;
- optional category rejects blank but accepts grounded arbitrary labels;
- OVERALL/ALTERNATIVES scope shape enforced;
- alternative IDs unique;
- Risk basis non-empty;
- exact duplicate basis rejected;
- Risk IDs unique within assessment;
- observations non-blank/unique;
- zero-risk assessment valid;
- ranking/recommendation/probability extra fields rejected.

### ReviewInput basis

- every existing `ReviewInputSource` value resolves correctly;
- scalar fields match exactly;
- collection item resolves only when unique;
- absent/ambiguous values rejected.

### ProblemAnalysis basis

For each kind:

- exact id+text resolves;
- text-only resolves when unique;
- unknown id/text rejected;
- mismatched id/text rejected;
- duplicate text without id rejected;
- assumptions remain distinct from facts.

### SolutionAlternative basis

- description resolves;
- unique advantage/disadvantage/assumption resolves;
- duplicate text is ambiguous;
- implementation complexity resolves by enum value;
- structured `ConstraintReference` resolves exactly;
- characteristic/value type mismatch rejected;
- unknown alternative rejected;
- zero alternatives cannot resolve alternative basis.

### Execution / provenance

- RiskReviewerStageInput accepted only for Risk Reviewer non-PENDING states;
- completed Risk Reviewer requires RiskAssessment;
- Critic/Coordinator non-PENDING rejected;
- exact ReviewInput identity required;
- exact Analyst ProblemAnalysis identity required;
- exact Architect SolutionAlternatives identity required;
- equal-but-independent upstream objects rejected;
- reordered valid stage tuple remains valid via StageIdentity lookup.

### Lifecycle / transitions

- all seven RUNNING prefixes accepted;
- all three INCOMPLETE shapes accepted;
- skipped-stage combinations rejected;
- Review COMPLETED unreachable in Slice 4;
- start/complete/fail Risk Reviewer paths;
- premature/repeated transitions rejected;
- upstream stage objects preserved;
- transitions operate correctly with valid noncanonical tuple order.

### Orchestrator

- exact role order Analyst → Solution Architect → Risk Reviewer;
- Risk Reviewer stage input recorded before call;
- exact trusted upstream objects passed;
- RiskReviewerOutputError → OUTPUT_VALIDATION;
- ordinary participant Exception → EXECUTION;
- internal invariant errors propagate;
- BaseException signals propagate;
- zero-risk completes successfully;
- zero-alternative upstream still invokes Risk Reviewer;
- sequential reviews isolated.

---

## 24. Explicit Non-Goals

This model does not introduce:

- Critic or Coordinator contracts;
- ranking/recommendation fields;
- numeric risk probability/scoring;
- impact matrices;
- persistent/global IDs;
- generic ArtifactReference abstractions;
- generic stage payload models;
- workflow registries;
- persistence/rehydration semantics;
- retries/timeouts;
- RAG/tools/browsing;
- provider-specific types;
- organization-specific taxonomy infrastructure.

---

## 25. Open Design Questions

None required before task breakdown.

The selected contracts are intentionally sufficient for Slice 4.

A reusable cross-stage reference abstraction should be considered only if later implementation evidence demonstrates repeated logic that materially harms maintainability.

---

## 26. Approval Gate

Before `tasks.md` is generated, confirm:

- discriminator uses Literal variant tags;
- existing `ReviewInputSource` is reused;
- risk category remains optional/open rather than an exhaustive enum;
- alternative characteristic basis is sufficiently precise;
- relevant constraints reuse structured `ConstraintReference`;
- fact/assumption distinction is preserved;
- contextual resolution and same-execution provenance remain separate;
- identity-based Review semantics from Slice 3 remain intact;
- lifecycle/failure matrices are complete;
- no ranking/recommendation leakage exists;
- no premature generic abstraction is introduced.

Only after explicit approval should implementation tasks be generated.
