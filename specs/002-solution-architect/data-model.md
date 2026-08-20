# Data Model: Solution Architect v0.1

**Feature:** `specs/002-solution-architect/spec.md`  
**Plan:** `specs/002-solution-architect/plan.md`  
**ADR:** `docs/adr/ADR-0001-pydantic-v2-for-structured-contracts.md`  
**Status:** Draft — awaiting review

## 1. Purpose

This document defines the structured data introduced by the **Solution Architect v0.1** increment.

It refines the approved feature specification and implementation plan without adding new product requirements.

The increment introduces:

- `QualitativeLevel`;
- `ConstraintReference`;
- `GenerationNotes`;
- `SolutionAlternative`;
- `SolutionAlternatives`.

Pydantic v2 remains the approved structured-contract implementation mechanism under ADR-0001.

The semantic contract is defined by the fields and invariants documented here, not by provider-specific request/response formats.

## 2. Shared Modeling Rules

The following rules apply to generated contracts introduced by this increment:

- generated structured content is untrusted until structural validation and applicable contextual validation both succeed;
- generated-output contracts are closed and reject unexpected fields deterministically;
- trusted models are frozen where mutation would undermine traceability;
- validated collections become immutable after successful validation;
- required generated text rejects empty or whitespace-only values;
- valid generated text is preserved rather than silently trimmed or rewritten;
- generated semantic text uses strict textual validation where coercion could hide malformed output;
- provider SDK objects and provider-specific envelopes are not domain data;
- Pydantic validation establishes structural validity, not semantic truth or solution quality.

Conceptually:

```text
frozen = true
extra = forbid
```

Exact Python syntax belongs to implementation.

## 3. Existing Upstream Models Reused

This increment consumes but does not redesign:

```text
ReviewInput
ProblemAnalysis
AnalysisFinding
FactFinding
```

The Solution Architect receives:

```text
SolutionArchitectInput
- review_input: ReviewInput
- problem_analysis: ProblemAnalysis
```

Both artifacts remain trusted and immutable while the Solution Architect executes.

## 4. QualitativeLevel

Represents the shared qualitative scale used by the MVP.

### Values

```text
LOW
MEDIUM
HIGH
```

For `SolutionAlternative.implementation_complexity`, the value is a relative engineering judgment.

It is not:

- a probability;
- a statistical confidence score;
- a duration estimate;
- a cost estimate;
- a calibrated effort estimate.

Only the exact supported values are accepted. Unexpected values are rejected rather than heuristically normalized in this increment.

## 5. ConstraintReference

Represents one explicit review-local reference to a known constraint.

### Fields

```text
ConstraintReference
- source: ConstraintSource
- kind: ConstraintReferenceKind
- value: str
```

### 5.1 ConstraintSource

Closed values:

```text
REVIEW_INPUT
PROBLEM_ANALYSIS
```

These indicate which trusted upstream artifact owns the referenced constraint.

### 5.2 ConstraintReferenceKind

Closed values:

```text
TEXT
ID
```

### 5.3 `value`

Rules:

- required;
- strict text;
- non-empty and not whitespace-only;
- preserved exactly when valid;
- no trimming, lowercasing, normalization, fuzzy matching, index interpretation, or semantic repair.

### 5.4 Structural source/kind compatibility

The following combinations are valid in the candidate generated contract:

```text
REVIEW_INPUT + TEXT
PROBLEM_ANALYSIS + TEXT
PROBLEM_ANALYSIS + ID
```

The following is structurally invalid:

```text
REVIEW_INPUT + ID
```

because `ReviewInput.constraints` are plain user-provided strings and Slice 1 defines no IDs for them.

This compatibility rule depends only on the candidate reference and is therefore owned by Pydantic/model validation.

### 5.5 Contextual resolution

After structural validation, the `SolutionArchitect` boundary resolves the reference against the actual current upstream artifacts.

#### REVIEW_INPUT + TEXT

`value` must exactly match a current entry in:

```text
ReviewInput.constraints
```

Identical duplicate input strings are treated as the same textual target because the existing `ReviewInput` contract provides no separate local identity for individual equal strings.

#### PROBLEM_ANALYSIS + ID

`value` must exactly match one non-null `AnalysisFinding.id` in:

```text
ProblemAnalysis.constraints
```

Slice 1 already requires supplied finding IDs to be unique within `ProblemAnalysis`, so a valid ID reference is unambiguous.

#### PROBLEM_ANALYSIS + TEXT

`value` must exactly match one `AnalysisFinding.text` in:

```text
ProblemAnalysis.constraints
```

If more than one distinct Analyst constraint has the same exact text, the textual reference is ambiguous and invalid. A unique Analyst ID should be used when available.

### 5.6 Resolution result

Within the declared `source` and `kind`:

```text
0 matching targets  → invalid
1 matching target   → valid
>1 distinct targets → ambiguous and invalid
```

The application never guesses the intended target.

### 5.7 Scope of the guarantee

A successfully resolved `ConstraintReference` proves only that the reference points to a known upstream constraint.

It does not prove that:

- the constraint is actually material to the alternative;
- the alternative satisfies the constraint;
- the generated interpretation of the constraint is correct;
- the Analyst identified every relevant constraint.

Those remain semantic-quality concerns.

## 6. FindingReference

The no-alternative path needs structured references to existing Analyst `missing_information` and `uncertainties` without introducing a generic repository-wide reference framework.

For this slice, define a small local value object:

```text
FindingReference
- id: str | None
- text: str
```

### Rules

- `text` is required, strict, non-empty generated text;
- `id` is optional because Slice 1 finding IDs are optional;
- when `id` is supplied, it must be non-empty;
- the reference must resolve contextually to exactly one finding in the category in which the reference is used;
- no fuzzy or normalized matching is used.

Resolution rule:

- when `id` is supplied, the ID must match the target finding and `text` must exactly equal that same finding's text;
- when `id` is absent, `text` must exactly match one distinct finding in the applicable category;
- zero matches fail;
- multiple distinct text matches without an ID are ambiguous and fail.

This dual id+text representation keeps references readable while avoiding a false requirement that every Slice 1 finding have an ID.

`FindingReference` is intentionally local to this feature. It does not establish a generic cross-project reference abstraction.

## 7. GenerationNotes

Represents optional structured generation context and, critically, the explicit no-alternative limitation when meaningful alternatives cannot responsibly be produced.

### Fields

```text
GenerationNotes
- explanation: str
- blocking_missing_information: collection[FindingReference]
- blocking_uncertainties: collection[FindingReference]
```

### 7.1 `explanation`

Rules:

- required whenever `GenerationNotes` is present;
- strict text;
- non-empty and not whitespace-only;
- preserved as generated when valid.

### 7.2 `blocking_missing_information`

References material blockers from:

```text
ProblemAnalysis.missing_information
```

Rules:

- field required within `GenerationNotes`;
- collection may be empty when no missing-information item materially blocks comparison;
- each entry is a `FindingReference`;
- every reference must resolve contextually to exactly one current `ProblemAnalysis.missing_information` item;
- order preserved;
- immutable after validation.

### 7.3 `blocking_uncertainties`

References material blockers from:

```text
ProblemAnalysis.uncertainties
```

Rules mirror `blocking_missing_information`:

- field required;
- collection may be empty;
- every item is a `FindingReference`;
- every reference must resolve contextually to exactly one current uncertainty;
- order preserved;
- immutable after validation.

### 7.4 Alternatives-present semantics

When two or three alternatives are present:

- `generation_notes` is optional;
- if present, its blocker collections may be empty;
- it may provide concise structured generation context;
- it does not replace required per-alternative content.

### 7.5 No-alternative semantics

When `alternatives` is empty:

- `generation_notes` is mandatory;
- `explanation` must explain why multiple meaningful alternatives cannot responsibly be formed;
- material `missing_information` and `uncertainties` blocking useful comparison must be represented explicitly in the corresponding collections when applicable;
- the application must not manufacture artificial alternatives merely to satisfy normal cardinality.

Pydantic/model validation can deterministically enforce:

```text
alternatives == []
    → generation_notes is required
    → explanation is non-empty
```

Contextual validation can deterministically enforce that every blocker reference resolves to the correct current upstream category.

Whether the explanation is substantively correct and whether every truly material blocker was identified remain semantic-quality concerns.

## 8. SolutionAlternative

Represents one candidate approach produced by the Solution Architect.

### Fields

```text
SolutionAlternative
- id: str
- name: str
- description: str
- advantages: collection[str]
- disadvantages: collection[str]
- assumptions: collection[str]
- implementation_complexity: QualitativeLevel
- relevant_constraints: collection[ConstraintReference]
```

### 8.1 `id`

Rules:

- required;
- strict text;
- non-empty and not whitespace-only;
- review-local only;
- no mandatory prefix/pattern such as `ALT-001`;
- not persistent or globally unique.

Uniqueness is enforced by `SolutionAlternatives`.

### 8.2 `name`

Required strict non-empty distinguishing text.

### 8.3 `description`

Required strict non-empty concise explanation of the approach.

### 8.4 `advantages`

Rules:

- field required;
- collection may be empty when no material advantage is identified;
- each item must be strict non-empty text;
- order preserved;
- immutable after validation.

No minimum item count is invented beyond the approved contract.

### 8.5 `disadvantages`

Rules mirror `advantages`:

- field required;
- collection may be empty;
- items strict and non-empty;
- order preserved;
- immutable.

### 8.6 `assumptions`

Rules:

- field required;
- collection may be empty;
- supplied items strict and non-empty;
- assumptions remain assumptions by contract placement;
- no assumption is promoted into a fact;
- order preserved;
- immutable.

Items may restate Analyst assumptions or introduce solution-specific assumptions.

Formal assumption references are deliberately deferred because the approved canonical contract requires explicit assumptions but does not require every assumption to carry a reference object.

### 8.7 `implementation_complexity`

Uses `QualitativeLevel` and accepts only:

```text
LOW
MEDIUM
HIGH
```

### 8.8 `relevant_constraints`

Rules:

- field required;
- collection may be empty when no known constraint materially shapes the alternative;
- every item is a `ConstraintReference`;
- order preserved;
- immutable after validation;
- every reference must resolve contextually before the overall generated output becomes trusted.

## 9. SolutionAlternatives

Represents the validated structured output of the Solution Architect.

### Fields

```text
SolutionAlternatives
- alternatives: collection[SolutionAlternative]
- generation_notes: GenerationNotes | None
```

### 9.1 `alternatives`

The field is always structurally present.

Valid collection sizes are exactly:

```text
0
2
3
```

Therefore:

- two alternatives are valid;
- three alternatives are valid;
- zero alternatives use the no-alternative path;
- one alternative is invalid;
- more than three alternatives are invalid.

The validated representation is ordered and immutable.

### 9.2 Alternative ID uniqueness

All `SolutionAlternative.id` values must be unique within one `SolutionAlternatives` result.

Duplicate IDs invalidate the whole result.

This is a model-level invariant because it depends only on the candidate output.

### 9.3 `generation_notes`

When alternatives contain two or three items:

- optional.

When alternatives are empty:

- mandatory;
- must satisfy the no-alternative `GenerationNotes` rules.

No separate `NoAlternativeOutcome` entity is introduced.

## 10. Structural vs Contextual Validation Ownership

### 10.1 Pydantic/model responsibility

Pydantic owns invariants that depend only on candidate generated output:

- required fields;
- nested structure;
- strict textual types;
- non-empty required text;
- closed-schema behavior;
- supported enum values;
- immutable collections/models;
- alternative cardinality `0 | 2 | 3`;
- unique alternative IDs;
- conditional presence of `GenerationNotes` for zero alternatives;
- `ConstraintReference` source/kind structural compatibility;
- local shape of `FindingReference`.

### 10.2 SolutionArchitect/application responsibility

The participant boundary owns contextual checks requiring actual trusted upstream data:

- resolving every `ConstraintReference` against the correct declared upstream source;
- resolving `GenerationNotes.blocking_missing_information` against current `ProblemAnalysis.missing_information`;
- resolving `GenerationNotes.blocking_uncertainties` against current `ProblemAnalysis.uncertainties`;
- rejecting unresolved references;
- rejecting genuinely ambiguous contextual references;
- ensuring invalid generated data never becomes trusted `SolutionAlternatives`.

Generated structural and contextual failures are normalized into a Solution Architect output-validation error category.

Provider/transport errors remain distinct and are not misreported as contract failures.

## 11. Role Boundary

These contracts deliberately contain no fields for:

- ranking;
- preferred alternative;
- winner selection;
- final recommendation;
- final decision;
- risk assessment;
- critical review.

Closed schemas reject unexpected structured role-leakage fields.

The model does not claim to detect every possible role violation embedded in arbitrary legitimate prose fields.

## 12. Semantic Quality Boundary

The following remain required product behaviors but are not completely provable through deterministic schema validation:

- alternatives are meaningfully distinct;
- an alternative genuinely supports the stated objective;
- trade-offs are substantively correct;
- all important constraints were recognized;
- a conditional alternative is characterized appropriately;
- prose does not subtly declare a winner;
- the no-alternative explanation is substantively correct;
- all truly material blockers were identified.

This increment deliberately does not introduce:

- embeddings;
- fuzzy similarity thresholds;
- secondary LLM judging;
- a hidden Critic;
- domain-specific semantic rule engines.

Representative deterministic fixtures and later real-model evaluation against canonical reference scenarios are responsible for those semantic behaviors.

## 13. Provider-Neutral Serialization Relationship

The Solution Architect may serialize trusted `ReviewInput` and `ProblemAnalysis` into standard Python/JSON-compatible structures before supplying them through `LLMPort`.

Conceptually:

```text
payload
- review_input
- problem_analysis
```

This serialization:

- is provider-neutral;
- contains no SDK types;
- does not alter semantic contracts;
- does not establish trust in generated output;
- does not replace local validation.

## 14. Error Semantics

Malformed or context-invalid generated content must produce an explicit Solution Architect output-validation failure.

Representative failures include:

- missing mandatory alternative content;
- unsupported complexity value;
- invalid alternative count;
- duplicate alternative IDs;
- zero alternatives without `GenerationNotes`;
- blank generation explanation;
- invalid `ConstraintReference` source/kind pair;
- unresolved or ambiguous constraint reference;
- unresolved or ambiguous no-alternative blocker reference;
- unknown structured role-leakage fields.

The exact Python exception class belongs to implementation.

## 15. Deferred Data

This increment intentionally does not model:

- `Review` aggregate/lifecycle;
- `StageExecution`;
- stage status values;
- `RiskAssessment`;
- `CriticalReview`;
- `FinalReview`;
- ranking positions;
- preferred alternative;
- persistent/global identifiers;
- persistence schemas;
- provider request/response models;
- UI view models;
- formal assumption references;
- generic repository-wide reference infrastructure;
- semantic-similarity scores;
- quantitative complexity estimates.

## 16. Traceability to Approved Sources

This data model remains subordinate to and consistent with:

- `specs/002-solution-architect/spec.md`;
- `specs/002-solution-architect/plan.md`;
- `docs/02-requirements.md`;
- `docs/03-architecture.md`;
- `docs/04-agent-model.md`;
- `docs/05-quality-security.md`;
- `.specify/memory/constitution.md`;
- `docs/adr/ADR-0001-pydantic-v2-for-structured-contracts.md`.
