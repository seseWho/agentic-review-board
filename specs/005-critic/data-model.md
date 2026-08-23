# Data Model: Critic v0.1

**Branch**: `005-critic`  
**Specification**: `specs/005-critic/spec.md` — Approved  
**Plan**: `specs/005-critic/plan.md` — Approved  
**Status**: Approved — explicitly approved for task decomposition

## 1. Objective

Define the minimum immutable structured contracts required for Slice 5 Critic while preserving:

- evidence-constrained criticism;
- explicit traceability into current Review artifacts;
- fail-closed contextual reference validation;
- the fact/assumption distinction;
- same-execution provenance as a separate execution concern;
- Critic/Coordinator responsibility separation;
- fully empty `CriticalReview` validity;
- no generic artifact graph or cross-stage reference framework.

The models in this document are Critic-specific. They SHALL NOT be generalized merely because a future slice might also need references.

---

## 2. Modeling Conventions

All trusted Critic-domain models SHALL follow the existing project contract style:

```python
ConfigDict(
    frozen=True,
    extra="forbid",
    str_strip_whitespace=True,
)
```

Required textual fields SHALL reject blank-after-strip values.

Collections SHALL use immutable tuples in trusted domain state.

Generated IDs SHALL be explicit non-blank strings and unique within the collection where they identify findings.

No model in this slice SHALL contain:

- final ranking;
- preferred alternative;
- recommendation;
- numeric confidence/probability;
- provider-specific metadata;
- hidden reasoning / chain-of-thought;
- mutable upstream artifact copies.

---

## 3. Core Design Decision: Critic-Specific References

### 3.1 Why a bounded reference model is needed

Critic can inspect four different upstream artifact families:

```text
ReviewInput
ProblemAnalysis
SolutionAlternatives
RiskAssessment
```

Some upstream items have stable IDs; others are represented by explicit text/value fields. Critic therefore needs a reference structure rich enough to validate generated targets without introducing a generic artifact graph.

### 3.2 `CriticReference`

Use one Critic-specific closed reference object:

```text
CriticReference
- source: CriticReferenceSource
- kind: CriticReferenceKind
- item_id: str | None
- value: str | None
```

`source` identifies the upstream artifact family.

`kind` identifies the semantic item type within that family.

`item_id` is used when the referenced upstream item has a stable explicit ID.

`value` is used as an exact compatibility check and/or as the exact reference value for upstream items that do not have stable IDs.

This object is deliberately **not** named `ArtifactReference`, `EvidenceReference`, or another generic abstraction.

### 3.3 `CriticReferenceSource`

```text
REVIEW_INPUT
PROBLEM_ANALYSIS
SOLUTION_ALTERNATIVES
RISK_ASSESSMENT
```

### 3.4 `CriticReferenceKind`

The bounded v0.1 vocabulary SHALL match the fields that actually exist in the four accepted upstream contracts:

```text
# ReviewInput
DESCRIPTION
TITLE
REVIEW_OBJECTIVE
REVIEW_CONSTRAINT
CONTEXT
STATED_FACT

# ProblemAnalysis
PROBLEM_OBJECTIVE
PROBLEM_FACT
PROBLEM_CONSTRAINT
PROBLEM_ASSUMPTION
MISSING_INFORMATION
UNCERTAINTY

# SolutionAlternatives
ALTERNATIVE
ALTERNATIVE_NAME
ALTERNATIVE_DESCRIPTION
ADVANTAGE
DISADVANTAGE
ALTERNATIVE_ASSUMPTION
IMPLEMENTATION_COMPLEXITY
GENERATION_EXPLANATION
BLOCKING_MISSING_INFORMATION
BLOCKING_UNCERTAINTY

# RiskAssessment
RISK
RISK_CATEGORY
RISK_DESCRIPTION
RISK_SEVERITY
MITIGATION
RESIDUAL_UNCERTAINTY
OVERALL_OBSERVATION
```

The implementation SHALL validate legal `source × kind` combinations rather than treating every enum value as valid for every source.

The vocabulary deliberately excludes fields that do not exist in the accepted upstream models, including generic questions, interpretations, key considerations, dependencies, and residual concerns.

Structured upstream values such as `SolutionAlternative.relevant_constraints`, `Risk.affected_scope`, and `Risk.basis` are not directly referenceable in v0.1. A criticism concerning one of those structures SHALL target its owning alternative or risk and use direct references to the original visible upstream artifacts as additional basis where applicable. This keeps `CriticReference.value` textual and avoids canonical serialization or references-to-references.

No generic free-form kind is allowed.

### 3.5 Reference-shape rules

The reference itself SHALL enforce the following shape-level invariants without consulting upstream context:

1. blank `item_id`/`value` are invalid when present;
2. the `source × kind` combination must be legal;
3. value-only kinds require `item_id=None` and a non-blank `value`;
4. ID-primary kinds require a non-blank `item_id` and permit only their explicitly defined optional compatibility value;
5. optional-finding-ID kinds require a non-blank `value` and permit an optional `item_id`;
6. parent-ID + value kinds require both fields;
7. reference fields are immutable and closed.

These rules are fully enumerated in Section 13. Context-dependent existence, uniqueness, and compatibility rules belong in the Critic participant trust boundary.

### 3.6 Contextual resolution rules

The participant SHALL resolve a `CriticReference` against the exact four current inputs.

For an ID-primary item:

```text
item_id required
value optional but, when supplied, must match the exact kind-specific compatibility field
```

For a finding with an optional upstream ID:

```text
value required
item_id optional
when item_id is supplied, both ID and value must match the same current finding
when item_id is absent, value must identify exactly one current finding
```

For a value-only item:

```text
value required
exactly one current item must match
```

For a nested item owned by an alternative or risk:

```text
item_id identifies the exact parent
value must exactly match the selected field or collection item within that parent
```

Resolution policy:

```text
0 matches  → CriticOutputError
1 match    → valid
>1 matches → CriticOutputError
```

An optional scalar field that is `None` has zero resolvable matches. No fuzzy matching, case folding, nearest match, semantic repair, generated correction, or implicit structured-value serialization is permitted.

---

## 4. `CriticismImportance`

Use a Critic-specific qualitative enum:

```text
LOW
MEDIUM
HIGH
```

Rationale:

- semantics are criticism importance, not risk likelihood/impact;
- reusing a risk enum would couple unrelated domain concepts;
- three qualitative levels satisfy the canonical Critic contract without implying calibration.

No numeric representation is added.

---

## 5. `Criticism`

```text
Criticism
- id: str
- target_type: CriticismTargetType
- target_reference: CriticReference | None
- basis_references: tuple[CriticReference, ...]
- issue: str
- importance: CriticismImportance
- rationale: str
- correction_or_question: str | None
```

### 5.1 `CriticismTargetType`

Use a semantic target classification independent of physical source:

```text
ASSUMPTION
CONSTRAINT
ANALYSIS
ALTERNATIVE
ALTERNATIVE_CHARACTERISTIC
RISK
MITIGATION
CROSS_ARTIFACT_CONCLUSION
OMISSION
```

This classification answers *what kind of reasoning is challenged*, while `CriticReference.source/kind` answers *where the visible target/basis lives*.

### 5.2 Target/basis invariants

`target_reference` represents the single explicit target when the criticism has one.

`basis_references` represents additional visible current-review support for the criticism and is especially important for cross-artifact findings.

Intrinsic rules:

- `id`, `issue`, and `rationale` required/non-blank;
- `correction_or_question` optional, but non-blank when present;
- `basis_references` may be empty only when `target_reference` is present;
- at least one of `target_reference` or `basis_references` SHALL be present;
- duplicate references within `basis_references` are invalid;
- if `target_reference` is repeated in `basis_references`, that duplicate is invalid.

Contextual rules:

- when the finding has one explicit unambiguous target, `target_reference` is required;
- `CROSS_ARTIFACT_CONCLUSION` requires at least two distinct resolved references across target+basis;
- `OMISSION` may have no single target but SHALL have visible basis references;
- all references must resolve against current inputs.

This avoids accepting generic criticism such as “the analysis is weak” with no inspectable basis.

---

## 6. `ValidatedPoint`

```text
ValidatedPoint
- id: str
- target_reference: CriticReference
- rationale: str
```

Rules:

- all fields required/non-blank where textual;
- the target reference is mandatory;
- reference must resolve exactly against current inputs;
- validation does not alter the upstream artifact;
- validation does not change assumption → fact semantics;
- no recommendation/ranking fields are allowed.

### Design decision

The spec says a validated point SHOULD identify an explicit upstream target whenever practical. For v0.1 we deliberately make the reference mandatory because a “validated point” with no identifiable point provides little inspectable value and can become generic praise.

If Critic has nothing explicit to validate, it SHALL omit the finding instead of emitting an untraceable validated point.

---

## 7. `MissingAlternative`

```text
MissingAlternative
- id: str
- category: str
- rationale: str
- weakens_later_recommendation: bool
- basis_references: tuple[CriticReference, ...]
```

Rules:

- `id`, `category`, and `rationale` required/non-blank;
- `basis_references` SHALL contain at least one explicit current-review reference;
- duplicate basis references invalid;
- every basis reference must contextually resolve;
- `weakens_later_recommendation` is descriptive input to Coordinator, not a recommendation by Critic;
- no replacement alternative fields (`title`, `description`, advantages, disadvantages, etc.) are permitted.

### Why boolean instead of severity

The canonical requirement asks whether the omission is serious enough to weaken the later recommendation. A boolean models that exact question with less invented semantics than a new severity scale.

---

## 8. `ContradictionSide`

```text
ContradictionSide
- reference: CriticReference
- statement: str
```

`statement` captures the exact visible proposition being treated as one side of the contradiction.

Rules:

- reference required and contextually resolvable;
- statement required/non-blank;
- statement SHALL be exactly compatible with the referenced visible artifact/item under the participant's contextual validator;
- no hidden inference text belongs in `statement`.

---

## 9. `Contradiction`

```text
Contradiction
- id: str
- side_a: ContradictionSide
- side_b: ContradictionSide
- rationale: str
```

Rules:

- `id` and `rationale` required/non-blank;
- both sides required;
- both references must resolve;
- sides cannot be identical references with identical statements;
- swapping A/B is semantically equivalent for duplicate detection;
- contradiction rationale explains why both visible propositions cannot comfortably coexist as currently expressed;
- the model does not automatically decide which side is true.

### Duplicate rule

Within one `CriticalReview`, two contradictions with the same unordered pair of `(reference, statement)` sides are duplicates and invalid even if IDs differ.

---

## 10. `UnresolvedIssue`

```text
UnresolvedIssue
- id: str
- issue: str
- rationale: str
- basis_references: tuple[CriticReference, ...]
```

Rules:

- `id`, `issue`, and `rationale` required/non-blank;
- at least one basis reference required;
- duplicate basis references invalid;
- every basis reference must resolve against current inputs;
- no invented resolution or recommendation field is allowed.

### Design decision

We require explicit basis in v0.1 rather than allowing an unreferenced textual unresolved issue. Critic receives the complete current review state; if an issue cannot be grounded in any visible input artifact, it should not enter trusted Critic output.

---

## 11. `CriticalReview`

```text
CriticalReview
- criticisms: tuple[Criticism, ...] = ()
- validated_points: tuple[ValidatedPoint, ...] = ()
- missing_alternatives: tuple[MissingAlternative, ...] = ()
- contradictions: tuple[Contradiction, ...] = ()
- unresolved_issues: tuple[UnresolvedIssue, ...] = ()
```

### Intrinsic invariants

1. All collections may be empty simultaneously.
2. IDs SHALL be unique within each finding collection.
3. Duplicate semantic findings within the same collection SHOULD be rejected where deterministic structural comparison is possible.
4. Collections are immutable tuples.
5. Extra fields are forbidden.
6. No collection is required to contain artificial activity.

### Contextual trust rule

A structurally valid `CriticalReview` remains untrusted until **every reference in every nested finding** resolves against the exact current Critic inputs.

Validation is atomic:

```text
one invalid nested reference
        ↓
whole CriticalReview rejected
        ↓
CriticOutputError
```

No partially trusted review is returned.

---

## 12. Referenceability Matrix

The participant SHALL implement an explicit bounded resolver table equivalent to:

| Source | Kind | Exact upstream target | Resolution key |
|---|---|---|---|
| REVIEW_INPUT | DESCRIPTION | `ReviewInput.description` | exact value, unique scalar |
| REVIEW_INPUT | TITLE | `ReviewInput.title` | exact value, unique scalar; no match when `None` |
| REVIEW_INPUT | REVIEW_OBJECTIVE | `ReviewInput.objective` | exact value, unique scalar; no match when `None` |
| REVIEW_INPUT | REVIEW_CONSTRAINT | item in `ReviewInput.constraints` | exact value, unique |
| REVIEW_INPUT | CONTEXT | item in `ReviewInput.context` | exact value, unique |
| REVIEW_INPUT | STATED_FACT | item in `ReviewInput.stated_facts` | exact value, unique |
| PROBLEM_ANALYSIS | PROBLEM_OBJECTIVE | `ProblemAnalysis.objective` | exact value, unique scalar |
| PROBLEM_ANALYSIS | PROBLEM_FACT | item in `ProblemAnalysis.facts` | optional finding ID + exact `text` |
| PROBLEM_ANALYSIS | PROBLEM_CONSTRAINT | item in `ProblemAnalysis.constraints` | optional finding ID + exact `text` |
| PROBLEM_ANALYSIS | PROBLEM_ASSUMPTION | item in `ProblemAnalysis.assumptions` | optional finding ID + exact `text` |
| PROBLEM_ANALYSIS | MISSING_INFORMATION | item in `ProblemAnalysis.missing_information` | optional finding ID + exact `text` |
| PROBLEM_ANALYSIS | UNCERTAINTY | item in `ProblemAnalysis.uncertainties` | optional finding ID + exact `text` |
| SOLUTION_ALTERNATIVES | ALTERNATIVE | item in `SolutionAlternatives.alternatives` | alternative ID; optional exact `name` |
| SOLUTION_ALTERNATIVES | ALTERNATIVE_NAME | `SolutionAlternative.name` | parent alternative ID + exact value |
| SOLUTION_ALTERNATIVES | ALTERNATIVE_DESCRIPTION | `SolutionAlternative.description` | parent alternative ID + exact value |
| SOLUTION_ALTERNATIVES | ADVANTAGE | item in `SolutionAlternative.advantages` | parent alternative ID + exact value |
| SOLUTION_ALTERNATIVES | DISADVANTAGE | item in `SolutionAlternative.disadvantages` | parent alternative ID + exact value |
| SOLUTION_ALTERNATIVES | ALTERNATIVE_ASSUMPTION | item in `SolutionAlternative.assumptions` | parent alternative ID + exact value |
| SOLUTION_ALTERNATIVES | IMPLEMENTATION_COMPLEXITY | `SolutionAlternative.implementation_complexity.value` | parent alternative ID + exact enum value |
| SOLUTION_ALTERNATIVES | GENERATION_EXPLANATION | `GenerationNotes.explanation` | exact value, unique scalar; no match without notes |
| SOLUTION_ALTERNATIVES | BLOCKING_MISSING_INFORMATION | item in `GenerationNotes.blocking_missing_information` | optional finding ID + exact `text`; no match without notes |
| SOLUTION_ALTERNATIVES | BLOCKING_UNCERTAINTY | item in `GenerationNotes.blocking_uncertainties` | optional finding ID + exact `text`; no match without notes |
| RISK_ASSESSMENT | RISK | item in `RiskAssessment.risks` | risk ID; optional exact `description` |
| RISK_ASSESSMENT | RISK_CATEGORY | `Risk.category` | parent risk ID + exact value; no match when `None` |
| RISK_ASSESSMENT | RISK_DESCRIPTION | `Risk.description` | parent risk ID + exact value |
| RISK_ASSESSMENT | RISK_SEVERITY | `Risk.severity.value` | parent risk ID + exact enum value |
| RISK_ASSESSMENT | MITIGATION | `Risk.mitigation` | parent risk ID + exact value; no match when `None` |
| RISK_ASSESSMENT | RESIDUAL_UNCERTAINTY | `Risk.residual_uncertainty` | parent risk ID + exact value; no match when `None` |
| RISK_ASSESSMENT | OVERALL_OBSERVATION | item in `RiskAssessment.overall_observations` | exact value, unique |

### Important interpretation of `item_id`

For `PROBLEM_FACT`, `PROBLEM_CONSTRAINT`, `PROBLEM_ASSUMPTION`, `MISSING_INFORMATION`, `UNCERTAINTY`, `BLOCKING_MISSING_INFORMATION`, and `BLOCKING_UNCERTAINTY`, `item_id` is optional because the accepted upstream finding contracts permit absent IDs. Their `value` always carries the exact finding text.

For alternative and risk nested textual/scalar kinds, `item_id` identifies the stable parent and `value` identifies the exact selected field or collection item. These kinds require both fields.

`ALTERNATIVE` and `RISK` are ID-primary. Their optional compatibility values have fixed meanings: alternative `name` and risk `description`, respectively.

This remains Critic-specific and does not change upstream contracts merely to make Critic references easier.

---

## 13. Exact Reference Shape by Kind

### Value-only references

Require:

```text
item_id = None
value = exact non-blank text
```

Kinds:

- DESCRIPTION
- TITLE
- REVIEW_OBJECTIVE
- REVIEW_CONSTRAINT
- CONTEXT
- STATED_FACT
- PROBLEM_OBJECTIVE
- GENERATION_EXPLANATION
- OVERALL_OBSERVATION

### Optional-finding-ID references

Require:

```text
item_id = optional upstream finding ID
value = exact non-blank finding text
```

Kinds:

- PROBLEM_FACT
- PROBLEM_CONSTRAINT
- PROBLEM_ASSUMPTION
- MISSING_INFORMATION
- UNCERTAINTY
- BLOCKING_MISSING_INFORMATION
- BLOCKING_UNCERTAINTY

When `item_id` is present, ID and value SHALL resolve to the same finding. When absent, value SHALL match exactly one finding in the selected collection.

### ID-primary references

Require:

```text
item_id = stable upstream ID
value = optional exact kind-specific compatibility value
```

Kinds and compatibility values:

- ALTERNATIVE → `SolutionAlternative.name`
- RISK → `Risk.description`

### Parent-ID + value references

Require:

```text
item_id = stable parent ID
value = exact non-blank selected field, collection item, or enum value
```

Kinds:

- ALTERNATIVE_NAME
- ALTERNATIVE_DESCRIPTION
- ADVANTAGE
- DISADVANTAGE
- ALTERNATIVE_ASSUMPTION
- IMPLEMENTATION_COMPLEXITY
- RISK_CATEGORY
- RISK_DESCRIPTION
- RISK_SEVERITY
- MITIGATION
- RESIDUAL_UNCERTAINTY

These rules SHALL be enforced intrinsically from `kind` before contextual resolution.

Structured `ConstraintReference`, `RiskScope`, and `RiskBasisReference` values are deliberately outside the v0.1 direct-reference vocabulary. No string serialization of those objects is accepted as a substitute.

---

## 14. Critic Participant Boundary

The approved participant API is:

```python
Critic.review(
    review_input: ReviewInput,
    problem_analysis: ProblemAnalysis,
    solution_alternatives: SolutionAlternatives,
    risk_assessment: RiskAssessment,
) -> CriticalReview
```

Boundary sequence:

```text
1. serialize exact four inputs
2. LLMPort.generate_structured(role="critic", ...)
3. CriticalReview.model_validate(raw)
4. recursively resolve every CriticReference
5. validate finding-specific contextual rules
6. return trusted CriticalReview
```

Any structural or contextual generated-output failure SHALL become:

```text
CriticOutputError
```

The exception SHALL not expose provider/raw validation internals into trusted Review state.

---

## 15. Execution Model Extension

### 15.1 `CriticStageInput`

```text
CriticStageInput
- review_input: ReviewInput
- problem_analysis: ProblemAnalysis
- solution_alternatives: SolutionAlternatives
- risk_assessment: RiskAssessment
```

The model is immutable and closed.

### 15.2 Stage unions

Extend:

```text
StageInput  += CriticStageInput
StageOutput += CriticalReview
```

Coordinator still has no Slice-5 input/output contract because it remains PENDING-only.

### 15.3 Local `StageExecution` shapes

For `StageIdentity.CRITIC`:

```text
PENDING
input=None
output=None
error=None

RUNNING
input=CriticStageInput
output=None
error=None

COMPLETED
input=CriticStageInput
output=CriticalReview
error=None

FAILED
input=CriticStageInput
output=None
error=StageError
```

No other Critic local shape is valid.

---

## 16. Same-Execution Provenance

For Critic RUNNING/COMPLETED/FAILED, `CriticStageInput` SHALL preserve object identity with the exact current Review artifacts:

```python
critic_input.review_input is review.review_input
critic_input.problem_analysis is analyst_stage.output
critic_input.solution_alternatives is solution_architect_stage.output
critic_input.risk_assessment is risk_reviewer_stage.output
```

Equality is insufficient.

This validation belongs to `Review` aggregate invariants and is separate from generated `CriticReference` resolution.

---

## 17. Review Lifecycle Matrix

Coordinator is omitted from the shorthand below because it SHALL remain `PENDING` in every Slice-5 valid state.

Order shown only for readability:

```text
A = Analyst
S = Solution Architect
R = Risk Reviewer
C = Critic
```

### 17.1 Valid RUNNING shapes — exactly 9

```text
A:PENDING   S:PENDING   R:PENDING   C:PENDING
A:RUNNING   S:PENDING   R:PENDING   C:PENDING
A:COMPLETED S:PENDING   R:PENDING   C:PENDING
A:COMPLETED S:RUNNING   R:PENDING   C:PENDING
A:COMPLETED S:COMPLETED R:PENDING   C:PENDING
A:COMPLETED S:COMPLETED R:RUNNING   C:PENDING
A:COMPLETED S:COMPLETED R:COMPLETED C:PENDING
A:COMPLETED S:COMPLETED R:COMPLETED C:RUNNING
A:COMPLETED S:COMPLETED R:COMPLETED C:COMPLETED
```

### 17.2 Valid INCOMPLETE shapes — exactly 4

```text
A:FAILED    S:PENDING   R:PENDING   C:PENDING
A:COMPLETED S:FAILED    R:PENDING   C:PENDING
A:COMPLETED S:COMPLETED R:FAILED    C:PENDING
A:COMPLETED S:COMPLETED R:COMPLETED C:FAILED
```

No `ReviewStatus.COMPLETED` shape is valid in Slice 5.

Validation SHALL use `StageIdentity`, never tuple position.

---

## 18. Failure Contracts

Critic output validation failure maps to a trusted `StageError` using the established output-validation category and exact message:

```text
Critic output validation failed
```

Ordinary Critic execution failure maps to the established execution-failure category and exact message:

```text
Critic execution failed
```

Raw provider exception text SHALL not enter trusted Review state.

Critic failure preserves the exact `CriticStageInput`, stores no `CriticalReview`, marks Review `INCOMPLETE`, and leaves Coordinator `PENDING`.

---

## 19. Duplicate and Identity Rules

### Finding IDs

Within each collection, finding IDs SHALL be unique.

IDs do not need to be globally unique across different finding types in v0.1.

### References

`CriticReference` equality is structural across `source`, `kind`, `item_id`, and `value`.

Duplicate basis references inside one finding are invalid.

### Validated points

Two validated points with the same `target_reference` are duplicates and invalid even if IDs/rationales differ.

### Missing alternatives

Two missing alternatives with the same normalized-by-Pydantic-stripping `category` are duplicates and invalid. No case folding is introduced.

### Contradictions

Duplicate unordered side pairs are invalid as defined above.

### Unresolved issues

No semantic/fuzzy duplicate detection is attempted. Unique IDs and exact structural validation are sufficient for v0.1.

---

## 20. Deliberately Rejected Alternatives

### Generic `ArtifactReference`
Rejected: premature abstraction across future stages.

### Free-form string targets
Rejected: cannot reliably fail closed or preserve traceability.

### One reference subclass per upstream artifact type
Rejected for v0.1: unnecessary class explosion; bounded `source + kind + item_id/value` is sufficient.

### Requiring stable IDs to be added to every upstream nested item
Rejected: would mutate accepted Slice 1–4 contracts solely for Critic convenience.

### Optional basis for MissingAlternative/UnresolvedIssue
Rejected: would allow unsupported generated findings into trusted state.

### Severity enum for missing-alternative recommendation impact
Rejected: boolean maps more directly to the canonical question and invents less semantics.

### Numeric Critic scoring
Rejected: no approved methodology and risks false precision.

### Forcing at least one Critic finding
Rejected: would encourage fabricated disagreement/activity.

---

## 21. Required Tests Derived from the Model

### Intrinsic contracts

- all models frozen and extra-forbid;
- blank fields rejected;
- legal/illegal source-kind combinations;
- value-only / ID-primary / parent-ID+value reference shapes;
- all Criticism target/basis invariants;
- mandatory ValidatedPoint target;
- mandatory MissingAlternative basis;
- contradiction side/duplicate invariants;
- mandatory UnresolvedIssue basis;
- unique finding IDs;
- fully empty CriticalReview accepted;
- recommendation/ranking/replacement extras rejected.

### Contextual resolution

- exact unique value-only resolution;
- ambiguous duplicate text rejected;
- missing text rejected;
- exact alternative ID resolution;
- alternative ID + incompatible optional value rejected;
- nested alternative parent-ID + value resolution;
- exact risk ID resolution;
- risk ID + incompatible optional value rejected;
- mitigation/residual concern parent-ID + value resolution;
- cross-artifact Criticism requires sufficient distinct basis;
- omission Criticism grounded by basis;
- every ValidatedPoint resolves;
- every MissingAlternative basis resolves;
- both Contradiction sides resolve and statements remain compatible;
- every UnresolvedIssue basis resolves;
- one invalid nested reference rejects whole CriticalReview.

### Execution/provenance

- four exact CriticStageInput identities preserved;
- equal copies rejected;
- exact 9 RUNNING shapes;
- exact 4 INCOMPLETE shapes;
- Coordinator always PENDING;
- noncanonical tuple ordering accepted when semantically valid;
- invalid state combinations rejected.

---

## 22. Data-Model Acceptance Gate

This data model is ready for `tasks.md` only after review confirms:

1. `CriticReference` is sufficiently expressive for current artifacts but remains Critic-specific and bounded;
2. source/kind vocabulary matches actual accepted Slice 1–4 contracts;
3. reference shape rules match which upstream items truly have stable IDs;
4. contextual resolution can be deterministic and fail-closed without fuzzy matching;
5. `Criticism` supports both explicit single targets and genuine cross-artifact/omission findings;
6. `ValidatedPoint` mandatory reference does not conflict with the approved spec;
7. `MissingAlternative` and `UnresolvedIssue` have inspectable evidence basis;
8. `Contradiction` preserves and validates both sides without deciding which is true;
9. all-empty `CriticalReview` remains valid;
10. no ranking/recommendation responsibility has leaked into Critic;
11. exact 9 RUNNING / 4 INCOMPLETE lifecycle shapes are preserved;
12. same-execution provenance remains object-identity-based and separate from generated references;
13. no accepted Slice 1–4 contract must be modified merely to support Critic references;
14. no generic future-facing reference/workflow abstraction has been introduced.

Only after explicit review and approval of this document should `tasks.md` be created.
