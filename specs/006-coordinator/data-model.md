# Data Model: Coordinator v0.1

**Branch**: `006-coordinator`  
**Specification**: Approved  
**Plan**: Approved  
**Status**: Approved — reviewed against real Slice 1–5 contracts; ready for task breakdown

## 1. Purpose

This document defines the minimum trusted domain and execution model for Coordinator v0.1.

It covers:

- transparent complete ranking of the existing alternatives;
- justified recommendation or explicit insufficient evidence;
- exact selection of principal upstream risks;
- bounded unresolved-question references into real Slice 1–5 fields;
- explicit disposition of every Critic criticism;
- qualitative confidence and human decision authority;
- `FinalReview`;
- `CoordinatorStageInput`;
- the final 10/5/1 Review lifecycle.

The design preserves the accepted `SolutionAlternatives` cardinality of exactly 0, 2, or 3 alternatives. It does not introduce one-alternative state, scoring, replacement alternatives, generic workflow infrastructure, or a generic artifact-reference framework.

---

## 2. Modeling Conventions

All new trusted Coordinator models SHALL use:

```python
ConfigDict(
    frozen=True,
    extra="forbid",
    str_strip_whitespace=True,
)
```

Rules shared by the new models:

- required text rejects blank-after-strip values;
- optional text rejects blank-after-strip when present;
- collections use immutable tuples;
- collection text items reject blanks;
- exact duplicates are rejected where deterministically meaningful;
- generated IDs are explicit non-blank strings;
- no provider-specific metadata is allowed;
- no numeric score, weight, or probability is allowed;
- integer ranking position is the only numeric Coordinator field;
- upstream objects remain immutable and are never copied into `FinalReview`.

Reuse the existing `QualitativeLevel` enum for confidence:

```text
LOW
MEDIUM
HIGH
```

A second confidence enum would duplicate an accepted project concept without adding semantics.

---

## 3. RecommendationOutcome

```text
RecommendationOutcome
- RECOMMENDED
- INSUFFICIENT_EVIDENCE
```

This enum distinguishes an evidence-supported preference from an explicit decision not to recommend yet.

No additional states such as `REJECTED`, `CONDITIONAL`, or `DEFERRED` are introduced in v0.1.

---

## 4. RankedAlternative

```text
RankedAlternative
- alternative_id: str
- position: int
- justification: str
- considerations: tuple[str, ...]
- conditions_that_could_change_ranking: tuple[str, ...] = ()
```

### Intrinsic rules

- `alternative_id` required/non-blank;
- `position` is a strict positive integer;
- `justification` required/non-blank;
- `considerations` contains at least one non-blank unique item;
- `conditions_that_could_change_ranking` may be empty;
- condition items are non-blank and unique;
- no alternative name, description, advantages, disadvantages, assumptions, complexity, or replacement content is embedded.

### Aggregate rules within FinalReview

- alternative IDs are unique;
- positions are unique;
- positions form exactly the contiguous sequence `1..N`;
- tuple order is not semantically authoritative; explicit `position` is;
- contextual validation later requires `N == len(current SolutionAlternatives.alternatives)`;
- every current alternative ID appears exactly once.

Because trusted upstream alternatives contain exactly 0, 2, or 3 items:

| Current alternatives | Valid ranking |
|---:|---|
| 0 | empty |
| 2 | both IDs once at positions 1 and 2 |
| 3 | all IDs once at positions 1, 2, and 3 |

A one-item ranking is not valid current-review output because one upstream alternative is not a valid `SolutionAlternatives` state.

---

## 5. PrincipalRisk

```text
PrincipalRisk
- risk_id: str
- rationale: str
```

The object selects an existing upstream `Risk` without copying or rewriting it.

Rules:

- both fields required/non-blank;
- `risk_id` resolves exactly against current `RiskAssessment.risks[].id`;
- duplicate selected risk IDs are invalid;
- zero principal risks is valid when the current assessment contains no decision-relevant risks;
- selection does not alter severity, mitigation, scope, basis, or residual uncertainty;
- unknown IDs reject the complete Coordinator output.

The rationale explains why the selected existing risk is principal to the final decision. It is not a replacement risk description.

---

## 6. Coordinator-Specific Unresolved-Question References

Coordinator needs a bounded reference vocabulary for unresolved information that actually exists in accepted upstream models.

It SHALL NOT reuse or generalize `CriticReference`. Critic references target a broader criticism vocabulary; Coordinator unresolved-question references serve a narrower final-review purpose.

Use a discriminated union of four source-specific models.

### 6.1 UnresolvedQuestionSource

```text
PROBLEM_ANALYSIS
SOLUTION_ALTERNATIVES
RISK_ASSESSMENT
CRITICAL_REVIEW
```

`ReviewInput` is intentionally excluded. The accepted unresolved sources are structured downstream findings derived from the input, not arbitrary reinterpretations of raw input text.

### 6.2 ProblemUnresolvedKind

```text
PROBLEM_ASSUMPTION
MISSING_INFORMATION
UNCERTAINTY
```

These map exactly to:

- `ProblemAnalysis.assumptions`;
- `ProblemAnalysis.missing_information`;
- `ProblemAnalysis.uncertainties`.

### 6.3 ProblemUnresolvedReference

```text
ProblemUnresolvedReference
- source: literal PROBLEM_ANALYSIS
- kind: ProblemUnresolvedKind
- value: str
- item_id: str | None = None
```

Rules:

- `value` required/non-blank;
- optional `item_id` non-blank when present;
- with ID: exactly one current finding must match both ID and text;
- without ID: exactly one current finding must match text;
- zero or multiple matches fail.

This matches the real `AnalysisFinding` contract, whose ID is optional.

### 6.4 SolutionUnresolvedKind

```text
ALTERNATIVE_ASSUMPTION
BLOCKING_MISSING_INFORMATION
BLOCKING_UNCERTAINTY
```

These map exactly to:

- `SolutionAlternative.assumptions`;
- `GenerationNotes.blocking_missing_information`;
- `GenerationNotes.blocking_uncertainties`.

### 6.5 SolutionUnresolvedReference

```text
SolutionUnresolvedReference
- source: literal SOLUTION_ALTERNATIVES
- kind: SolutionUnresolvedKind
- value: str
- alternative_id: str | None = None
- item_id: str | None = None
```

Rules:

- `value` required/non-blank;
- optional identifiers are non-blank when present;
- `ALTERNATIVE_ASSUMPTION` requires `alternative_id`, forbids `item_id`, and resolves `value` uniquely within exactly that current alternative's `assumptions`;
- blocker kinds require current `generation_notes`, forbid `alternative_id`, and resolve using exact ID+text when `item_id` exists or unique exact text otherwise;
- no assumption fallback or search is allowed across multiple alternatives;
- unknown alternative IDs, absent generation notes, zero matches, or multiple matches fail.

This matches the real string-based `SolutionAlternative.assumptions` and optional-ID `FindingReference` contracts.

### 6.6 RiskUnresolvedReference

```text
RiskUnresolvedReference
- source: literal RISK_ASSESSMENT
- risk_id: str
- value: str
```

This reference targets exactly `Risk.residual_uncertainty`.

Rules:

- both fields required/non-blank;
- exactly one current risk must match `risk_id`;
- that risk must have non-null residual uncertainty exactly equal to `value`;
- mitigation, description, category, severity, basis, affected scope, and overall observations are not unresolved-question targets through this model.

### 6.7 CriticUnresolvedKind

```text
MISSING_ALTERNATIVE
CONTRADICTION
UNRESOLVED_ISSUE
```

These map exactly to:

- `CriticalReview.missing_alternatives`;
- `CriticalReview.contradictions`;
- `CriticalReview.unresolved_issues`.

Criticisms use the separate mandatory disposition model below. Validated points are not unresolved questions.

### 6.8 CriticUnresolvedReference

```text
CriticUnresolvedReference
- source: literal CRITICAL_REVIEW
- kind: CriticUnresolvedKind
- item_id: str
- value: str
```

Compatibility value by kind:

| Kind | Exact visible value |
|---|---|
| MISSING_ALTERNATIVE | `MissingAlternative.category` |
| CONTRADICTION | `Contradiction.rationale` |
| UNRESOLVED_ISSUE | `UnresolvedIssue.issue` |

Rules:

- `item_id` and `value` required/non-blank;
- exactly one current item must match both;
- no fallback by text because all three Critic finding types require IDs;
- unknown ID, wrong kind, or mismatched value fails.

### 6.9 Union

```text
UnresolvedQuestionReference =
    ProblemUnresolvedReference
  | SolutionUnresolvedReference
  | RiskUnresolvedReference
  | CriticUnresolvedReference
```

Use `source` as the discriminator.

No generic `ArtifactReference`, arbitrary path, JSON pointer, string serialization, or cross-stage graph is introduced.

---

## 7. UnresolvedQuestion

```text
UnresolvedQuestion
- id: str
- reference: UnresolvedQuestionReference
- question: str
- rationale: str
```

Rules:

- all textual fields required/non-blank;
- `reference` required;
- `question` is concise human-readable decision-support text, not an upstream replacement;
- `rationale` explains why the referenced unresolved item remains material;
- IDs are unique within `FinalReview.unresolved_questions`;
- the same resolved upstream target cannot appear twice;
- every nested reference resolves atomically against current inputs.

A final review may contain zero unresolved questions when none remain material. Insufficient evidence ordinarily requires at least one visible unresolved question unless zero alternatives already provides an explicit upstream generation blocker through `GenerationNotes`; the exact cross-field rule is defined in Section 11.

---

## 8. CriticismDisposition

### 8.1 CriticismDispositionOutcome

```text
REFLECTED
DISMISSED
```

Every entry in current `CriticalReview.criticisms` must be addressed exactly once. No importance threshold is inferred.

### 8.2 FinalReviewSection

```text
SITUATION_SUMMARY
RANKING
CONCLUSION
PRINCIPAL_RISKS
UNRESOLVED_QUESTIONS
NEXT_VALIDATION_STEP
CONFIDENCE
```

This enum identifies a bounded visible section of `FinalReview`; it is not a generic artifact path.

### 8.3 CriticismDisposition

```text
CriticismDisposition
- criticism_id: str
- outcome: CriticismDispositionOutcome
- rationale: str
- reflected_in: tuple[FinalReviewSection, ...] = ()
```

Rules:

- `criticism_id` and `rationale` required/non-blank;
- `reflected_in` contains unique values;
- `REFLECTED` requires at least one `reflected_in` section;
- `DISMISSED` requires empty `reflected_in`;
- each disposition resolves by exact current `Criticism.id`;
- disposition IDs are unique;
- contextual validation requires the exact set of disposition IDs to equal the exact set of current criticism IDs;
- outcome does not mutate, delete, or reclassify the Criticism;
- `rationale` explains the visible effect or justified non-relevance.

An empty `CriticalReview.criticisms` requires an empty dispositions collection.

---

## 9. Fixed Decision-Support Notice

Use one application-owned constant:

```text
This review supports, but does not replace, human decision-making.
```

Represent it in `FinalReview` as a fixed literal/default:

```text
decision_support_notice:
  Literal["This review supports, but does not replace, human decision-making."]
```

Design consequences:

- the notice is always present in trusted `FinalReview`;
- the LLM does not author legal or authority wording;
- no alternative generated wording is accepted;
- the constant is immutable and provider-neutral;
- the application does not rely on prompt compliance to preserve human authority.

The participant may omit this application-owned field from the model-requested generated schema and add/validate it through the trusted contract boundary, provided the final returned `FinalReview` contains the exact literal. The implementation choice must remain deterministic and tested.

---

## 10. FinalReview

```text
FinalReview
- situation_summary: str
- ranked_alternatives: tuple[RankedAlternative, ...]
- recommendation_outcome: RecommendationOutcome
- preferred_alternative_id: str | None
- conclusion_rationale: str
- principal_risks: tuple[PrincipalRisk, ...]
- unresolved_questions: tuple[UnresolvedQuestion, ...]
- criticism_dispositions: tuple[CriticismDisposition, ...]
- next_validation_step: str
- confidence: QualitativeLevel
- decision_support_notice: fixed literal
```

### Required text

The following are required/non-blank:

- `situation_summary`;
- `conclusion_rationale`;
- `next_validation_step`;
- optional `preferred_alternative_id` when present.

### Collection uniqueness

Reject:

- duplicate ranked alternative IDs;
- duplicate ranking positions;
- duplicate principal risk IDs;
- duplicate unresolved-question IDs;
- duplicate resolved unresolved-question targets;
- duplicate criticism disposition IDs.

### Ranking shape

Intrinsic validation requires positions to form exactly `1..N` for the provided ranking.

Current-context validation requires:

```text
ranking alternative ID set
==
current SolutionAlternatives alternative ID set
```

Therefore:

- zero current alternatives → empty ranking;
- two current alternatives → two complete positions;
- three current alternatives → three complete positions.

### Recommendation consistency

For `RECOMMENDED`:

- ranking must be non-empty;
- `preferred_alternative_id` required;
- preferred ID equals the ID at position 1;
- preferred ID resolves to a current alternative.

For `INSUFFICIENT_EVIDENCE`:

- `preferred_alternative_id` must be absent;
- ranking may still order the current two or three plausible alternatives;
- zero alternatives necessarily use this outcome.

`conclusion_rationale` is mandatory for both outcomes.

### Principal risks

Each principal risk resolves to exactly one current `Risk.id`. The collection may be empty, including when current `RiskAssessment.risks` is empty.

### Unresolved questions

Every reference must resolve exactly. The collection may be empty for a supported recommendation if no material unresolved question remains.

For `INSUFFICIENT_EVIDENCE`:

- if current alternatives are non-empty, at least one unresolved question is required;
- if current alternatives are empty, current `SolutionAlternatives.generation_notes` is already mandatory and supplies the visible reason; unresolved questions may be empty only if `conclusion_rationale` and `next_validation_step` preserve that blocker.

This avoids forcing a duplicate generated question merely to satisfy shape.

### Criticism dispositions

Contextual validation requires complete exact coverage of current `CriticalReview.criticisms`.

### Confidence

Uses existing `QualitativeLevel`. No deterministic rule forces a particular level from outcome; tests validate only the enum and absence of numeric confidence.

### Human authority

The exact fixed decision-support notice is mandatory.

---

## 11. Intrinsic vs Contextual Invariants

### 11.1 Intrinsic domain invariants

Validated without current upstream objects:

- closed/frozen shapes;
- non-blank text;
- collection uniqueness;
- contiguous ranking positions;
- recommendation outcome/preferred-ID consistency;
- `RECOMMENDED` requires non-empty ranking;
- disposition outcome/`reflected_in` compatibility;
- exact fixed notice;
- qualitative confidence;
- no numeric scores/probabilities.

### 11.2 Participant contextual invariants

Require the exact current five inputs:

- ranking cardinality and ID set equal current alternatives;
- preferred alternative resolves and matches position 1;
- principal risk IDs resolve exactly;
- every unresolved-question reference resolves exactly;
- unresolved-question resolved targets are unique;
- every current criticism ID has exactly one disposition and no unknown disposition exists;
- zero alternatives force `INSUFFICIENT_EVIDENCE`;
- insufficient evidence with existing alternatives exposes at least one current unresolved item;
- every validation succeeds before any trusted result is returned.

### 11.3 Deliberately subjective behavior

Deterministic validation SHALL NOT attempt to prove:

- that the model chose the objectively best ranking;
- that a criticism truly should affect one specific section;
- that a dismissed criticism is philosophically irrelevant;
- that confidence should be a particular qualitative level;
- that the next validation step is optimal.

The contract verifies inspectability, traceability, consistency, and allowed behavior—not hidden model reasoning quality.

---

## 12. Coordinator Participant Contract

```python
Coordinator.coordinate(
    review_input: ReviewInput,
    problem_analysis: ProblemAnalysis,
    solution_alternatives: SolutionAlternatives,
    risk_assessment: RiskAssessment,
    critical_review: CriticalReview,
) -> FinalReview
```

Exact call:

```text
LLMPort.generate_structured(
    role="coordinator",
    payload={
        "review_input": ...,
        "problem_analysis": ...,
        "solution_alternatives": ...,
        "risk_assessment": ...,
        "critical_review": ...,
    },
)
```

The payload contains exactly the five JSON-compatible upstream artifacts and no hidden Review state.

Boundary sequence:

```text
generate structured response
        ↓
FinalReview structural validation
        ↓
ranking/recommendation contextual validation
        ↓
principal-risk resolution
        ↓
unresolved-question resolution
        ↓
criticism-disposition completeness
        ↓
trusted FinalReview
```

Any structural or contextual failure raises:

```text
CoordinatorOutputError
```

No partial result is returned.

---

## 13. CoordinatorStageInput

```text
CoordinatorStageInput
- review_input: ReviewInput
- problem_analysis: ProblemAnalysis
- solution_alternatives: SolutionAlternatives
- risk_assessment: RiskAssessment
- critical_review: CriticalReview
```

Configuration:

- frozen;
- extra fields forbidden.

This model records trusted in-memory provenance. It does not serialize generalized artifact references.

---

## 14. StageExecution Extension

Extend explicit unions:

```text
StageInput =
    AnalystStageInput
  | SolutionArchitectStageInput
  | RiskReviewerStageInput
  | CriticStageInput
  | CoordinatorStageInput

StageOutput =
    ProblemAnalysis
  | SolutionAlternatives
  | RiskAssessment
  | CriticalReview
  | FinalReview
```

Coordinator local shapes:

| Status | Inputs | Output | Error |
|---|---|---|---|
| PENDING | none | none | none |
| RUNNING | CoordinatorStageInput | none | none |
| COMPLETED | CoordinatorStageInput | FinalReview | none |
| FAILED | CoordinatorStageInput | none | ReviewError |

No other local Coordinator shape is valid.

---

## 15. Same-Execution Provenance

For Coordinator RUNNING, COMPLETED, and FAILED:

```python
coordinator.inputs.review_input is review.review_input
coordinator.inputs.problem_analysis is analyst.output
coordinator.inputs.solution_alternatives is solution_architect.output
coordinator.inputs.risk_assessment is risk_reviewer.output
coordinator.inputs.critical_review is critic.output
```

Equality with independently constructed copies is insufficient.

This validation belongs to the Review aggregate and remains separate from generated ranking/reference resolution.

---

## 16. Review Lifecycle Matrix

Use identity-based lookup, never tuple position.

Notation:

```text
A  Analyst
S  Solution Architect
R  Risk Reviewer
C  Critic
O  Coordinator
```

### 16.1 Valid RUNNING shapes — exactly 10

```text
A:PENDING   S:PENDING   R:PENDING   C:PENDING   O:PENDING
A:RUNNING   S:PENDING   R:PENDING   C:PENDING   O:PENDING
A:COMPLETED S:PENDING   R:PENDING   C:PENDING   O:PENDING
A:COMPLETED S:RUNNING   R:PENDING   C:PENDING   O:PENDING
A:COMPLETED S:COMPLETED R:PENDING   C:PENDING   O:PENDING
A:COMPLETED S:COMPLETED R:RUNNING   C:PENDING   O:PENDING
A:COMPLETED S:COMPLETED R:COMPLETED C:PENDING   O:PENDING
A:COMPLETED S:COMPLETED R:COMPLETED C:RUNNING   O:PENDING
A:COMPLETED S:COMPLETED R:COMPLETED C:COMPLETED O:PENDING
A:COMPLETED S:COMPLETED R:COMPLETED C:COMPLETED O:RUNNING
```

### 16.2 Valid INCOMPLETE shapes — exactly 5

```text
A:FAILED    S:PENDING   R:PENDING   C:PENDING   O:PENDING
A:COMPLETED S:FAILED    R:PENDING   C:PENDING   O:PENDING
A:COMPLETED S:COMPLETED R:FAILED    C:PENDING   O:PENDING
A:COMPLETED S:COMPLETED R:COMPLETED C:FAILED    O:PENDING
A:COMPLETED S:COMPLETED R:COMPLETED C:COMPLETED O:FAILED
```

### 16.3 Valid COMPLETED shape — exactly 1

```text
A:COMPLETED S:COMPLETED R:COMPLETED C:COMPLETED O:COMPLETED
```

Reject skipped stages, multiple failures, downstream execution after failure, Coordinator completion without `FinalReview`, and Review COMPLETED without Coordinator completion.

---

## 17. Explicit Transitions

### start_coordinator()

Preconditions:

- Review RUNNING;
- first four stages COMPLETED;
- trusted upstream output types present;
- Coordinator PENDING.

Result:

- Coordinator RUNNING;
- exact five current objects captured in `CoordinatorStageInput`;
- Review remains RUNNING.

### complete_coordinator(final_review)

Preconditions:

- Review RUNNING;
- Coordinator RUNNING;
- recorded input is `CoordinatorStageInput`.

Result:

- Coordinator COMPLETED;
- exact recorded input object preserved;
- exact supplied `FinalReview` object stored;
- Review COMPLETED.

### fail_coordinator(error)

Preconditions:

- Review RUNNING;
- Coordinator RUNNING;
- recorded input is `CoordinatorStageInput`.

Result:

- Coordinator FAILED;
- exact recorded input preserved;
- no output;
- exact error stored;
- Review INCOMPLETE.

All transitions reconstruct and validate a complete immutable Review. Tuple order is preserved and stages are found/replaced by identity.

---

## 18. Failure Contracts

Participant structural or contextual failure:

```text
CoordinatorOutputError
    ↓
ReviewError(
    kind=OUTPUT_VALIDATION,
    message="Coordinator output validation failed",
)
```

Ordinary participant/model exception:

```text
ReviewError(
    kind=EXECUTION,
    message="Coordinator execution failed",
)
```

Both produce Coordinator FAILED and Review INCOMPLETE while preserving all upstream completed stages and exact Coordinator inputs.

Internal invariant/type/transition failures outside `Coordinator.coordinate(...)` propagate. `BaseException` control signals are not caught.

---

## 19. Validation Examples

### 19.1 Valid recommendation with two alternatives

```text
ranked_alternatives:
- ALT-002 position 1
- ALT-001 position 2

recommendation_outcome: RECOMMENDED
preferred_alternative_id: ALT-002
conclusion_rationale: visible evidence supports ALT-002
```

Valid only if the current alternatives are exactly ALT-001 and ALT-002 and every other contextual rule succeeds.

### 19.2 Valid insufficient evidence with ranked alternatives

```text
ranked_alternatives:
- ALT-001 position 1
- ALT-002 position 2

recommendation_outcome: INSUFFICIENT_EVIDENCE
preferred_alternative_id: none
unresolved_questions:
- exact reference to current missing information
```

Position 1 expresses current ordering but not a recommendation.

### 19.3 Valid zero-alternative result

```text
ranked_alternatives: []
recommendation_outcome: INSUFFICIENT_EVIDENCE
preferred_alternative_id: none
conclusion_rationale: preserves current GenerationNotes blocker
next_validation_step: obtain the missing information
```

### 19.4 Invalid preferred alternative

```text
position 1: ALT-001
preferred_alternative_id: ALT-002
recommendation_outcome: RECOMMENDED
```

Reject complete output.

### 19.5 Invalid criticism coverage

Current criticisms:

```text
CRIT-001
CRIT-002
```

Generated dispositions:

```text
CRIT-001 REFLECTED
```

Reject because CRIT-002 is omitted.

---

## 20. Design Decisions

1. Reuse `QualitativeLevel` for confidence.
2. Preserve upstream alternative cardinality exactly at 0, 2, or 3.
3. Use explicit ranking positions with no scores or ties.
4. Use `RecommendationOutcome.RECOMMENDED | INSUFFICIENT_EVIDENCE`.
5. Require conclusion rationale for both outcomes.
6. Select principal risks by exact `Risk.id`.
7. Use a bounded discriminated union only for unresolved-question sources, including exact Analyst and alternative assumptions.
8. Give every current Criticism ID exactly one explicit disposition.
9. Infer no materiality threshold from Criticism importance.
10. Use a fixed application-owned decision-support notice.
11. Keep generated-reference validation separate from object-identity provenance.
12. Add only explicit Coordinator lifecycle and orchestration behavior.

---

## 21. Questions for Review

Before approval, verify:

1. whether `PrincipalRisk.rationale` adds useful inspectability without duplicating the Risk description;
2. whether the corrected unresolved-question matrix now covers Analyst assumptions and alternative-local assumptions without enabling global or fuzzy lookup;
3. whether `CriticUnresolvedReference.value` compatibility mappings are the correct visible values;
4. whether `FinalReviewSection` is sufficiently bounded for reflected criticism without becoming a generic path system;
5. whether insufficient evidence with existing alternatives should always require at least one unresolved question;
6. whether zero alternatives may omit `unresolved_questions` when GenerationNotes, conclusion rationale, and next step already expose the blocker;
7. whether the fixed notice text is appropriate;
8. whether all intrinsic invariants belong in domain and all current-review checks remain in the participant;
9. whether exact 10/5/1 lifecycle and five-object provenance are complete.

No `tasks.md` or implementation work SHALL begin until this data model is reviewed and explicitly approved.
