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
- `SolutionAlternative`;
- `SolutionAlternatives`.

It also defines the contextual resolution rules used by the `SolutionArchitect` participant when validating `relevant_constraints` against the trusted upstream artifacts already available from Slice 1.

Pydantic v2 remains the approved structured-contract implementation mechanism under ADR-0001. The semantic contract is defined by the fields and invariants documented here, not by provider-specific request or response formats.

## 2. Shared Modeling Rules

The following rules apply to all generated contracts introduced by this increment:

- models use Pydantic v2 `BaseModel`;
- generated structured content is untrusted until structural validation and applicable contextual invariants both succeed;
- generated-output contracts are closed and reject unexpected fields deterministically;
- trusted models are frozen where mutation would undermine traceability;
- validated collections are represented immutably after successful validation;
- required generated text rejects empty or whitespace-only values;
- valid generated text is not silently trimmed or rewritten;
- generated semantic text uses strict textual validation where coercion could hide malformed output;
- provider SDK objects and provider-specific transport envelopes are not part of the data model;
- Pydantic validation establishes structural validity, not semantic truth, factual correctness, or solution quality.

Conceptually, generated contract models follow:

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

from Slice 1.

The Solution Architect receives both:

```text
SolutionArchitectInput
- review_input: ReviewInput
- problem_analysis: ProblemAnalysis
```

These artifacts remain trusted and immutable while the Solution Architect executes.

## 4. QualitativeLevel

Represents the closed qualitative scale used by the MVP where a qualitative engineering judgment is required.

### Values

```text
LOW
MEDIUM
HIGH
```

### Semantics

For `SolutionAlternative.implementation_complexity`, the value represents a relative engineering judgment about implementation complexity.

It MUST NOT be interpreted as:

- a probability;
- a statistical confidence score;
- a duration estimate;
- a cost estimate;
- a calibrated project-effort measurement.

### Validation

Only the exact supported semantic values are valid.

Unexpected values are rejected rather than normalized heuristically in this increment.

## 5. SolutionAlternative

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
- relevant_constraints: collection[str]
```

### 5.1 `id`

A required review-local identifier for the alternative.

Rules:

- MUST be present;
- MUST be non-empty and not whitespace-only;
- MUST remain opaque to the contract beyond those requirements;
- no mandatory prefix or formatting convention such as `ALT-001` is imposed;
- does not represent a persistent or globally unique identifier.

Uniqueness is enforced at the containing `SolutionAlternatives` level.

### 5.2 `name`

A short distinguishing label for the alternative.

Rules:

- required;
- strict text;
- non-empty and not whitespace-only;
- preserved as generated when valid.

### 5.3 `description`

A concise explanation of the approach.

Rules:

- required;
- strict text;
- non-empty and not whitespace-only;
- preserved as generated when valid.

### 5.4 `advantages`

Explicit advantages associated with this specific alternative.

Rules:

- field is required;
- collection may be empty if the generated result genuinely identifies no material advantage;
- each supplied item must be strict non-empty text;
- order is preserved;
- validated representation is immutable.

The data model does not invent a minimum item count not defined by the approved spec or canonical Agent Model.

### 5.5 `disadvantages`

Explicit disadvantages, limitations, costs, or trade-offs associated with this specific alternative.

Rules mirror `advantages`:

- field required;
- collection may be empty;
- supplied items must be strict non-empty text;
- order preserved;
- immutable after validation.

### 5.6 `assumptions`

Assumptions required for the alternative to be viable.

Rules:

- field required;
- collection may be empty;
- supplied items must be strict non-empty text;
- assumptions remain assumptions by contract placement;
- no assumption is promoted into a fact by this model;
- order preserved;
- immutable after validation.

The collection may contain:

- assumptions already present in `ProblemAnalysis.assumptions`;
- solution-specific assumptions introduced by the Solution Architect.

This data model does not require assumption references in v0.1 because the canonical contract requires assumptions to remain explicit, but does not require each one to carry a formal upstream reference.

### 5.7 `implementation_complexity`

Uses `QualitativeLevel`.

Only:

```text
LOW
MEDIUM
HIGH
```

are accepted.

### 5.8 `relevant_constraints`

Represents review-local textual references to known constraints that materially shape or limit this alternative.

Rules:

- field required;
- collection may be empty when no known constraint materially shapes the alternative;
- each supplied reference must be strict non-empty text;
- order preserved;
- immutable after validation;
- each reference must resolve contextually against the current trusted upstream artifacts before the `SolutionAlternative` can become part of trusted `SolutionAlternatives` output.

Structural validation only verifies that each reference is well-formed text. Resolution belongs to the participant/application boundary because it requires the actual current `ReviewInput` and `ProblemAnalysis`.

## 6. SolutionAlternatives

Represents the validated structured output of the Solution Architect.

### Fields

```text
SolutionAlternatives
- alternatives: collection[SolutionAlternative]
- generation_notes: str | None
```

### 6.1 `alternatives`

Always structurally present.

Valid collection sizes are exactly:

```text
0
2
3
```

Therefore:

- two alternatives are valid;
- three alternatives are valid;
- zero alternatives are valid only under the no-alternative rules below;
- one alternative is invalid;
- more than three alternatives are invalid.

The validated collection preserves order and is immutable.

### 6.2 Alternative identifier uniqueness

Each `SolutionAlternative.id` is required.

Within one `SolutionAlternatives` result:

- all alternative IDs MUST be unique;
- duplicate IDs make the complete result invalid;
- uniqueness is a model-level structural invariant because it depends only on the candidate output.

### 6.3 `generation_notes`

Optional generated text used for concise generation context.

General rules:

- when present, must be strict non-empty text;
- valid text is preserved rather than silently trimmed or rewritten.

#### Alternatives present

When `alternatives` contains two or three valid items:

- `generation_notes` is optional;
- it may describe relevant generation context;
- it does not replace any required per-alternative fields.

#### No-alternative case

When `alternatives` is empty:

- `generation_notes` becomes mandatory;
- it must be non-empty;
- it must explain why multiple meaningful alternatives cannot responsibly be formed yet;
- when material missing information or unresolved uncertainty blocks useful comparison, the explanation must preserve that blocker explicitly.

Pydantic/model validation can enforce the deterministic part of this rule:

```text
alternatives == []
    → generation_notes is required and non-empty
```

Whether the natural-language note semantically identifies the correct reason and blockers is not fully provable by schema validation. That remains a participant behavior/evaluation obligation.

## 7. Relevant-Constraint Resolution Model

### 7.1 Purpose

`relevant_constraints` must remain traceable to the current upstream review artifacts without requiring Slice 1 to retroactively make every Analyst constraint identifier mandatory.

The Solution Architect receives:

```text
ReviewInput.constraints: collection[str]
ProblemAnalysis.constraints: collection[AnalysisFinding]
```

Both are valid sources of known constraints.

The original `ReviewInput` remains authoritative evidence of what the user supplied, while `ProblemAnalysis` is a trusted review artifact that may add structured constraints but may also contain omissions.

### 7.2 Resolution candidates

For contextual validation, construct conceptual candidate keys from the current upstream artifacts.

#### ReviewInput constraint candidate

For each original user constraint:

```text
source = review_input
text = exact original constraint text
reference keys = {text}
```

#### ProblemAnalysis constraint candidate

For each Analyst constraint:

```text
source = problem_analysis
text = finding.text
id = finding.id | None
reference keys = {text}
                 plus {id} when id exists
```

### 7.3 Exact-match policy

No fuzzy matching, semantic similarity, normalization, trimming, lowercasing, index lookup, or model-assisted repair is used.

A generated constraint reference is matched exactly against the candidate reference keys.

This keeps contextual validation deterministic and prevents the application from silently guessing which upstream constraint the model intended.

### 7.4 Equivalent duplicate text across upstream artifacts

The same semantic constraint may legitimately appear in both upstream artifacts, for example:

```text
ReviewInput.constraints:
- "Must run offline"

ProblemAnalysis.constraints:
- text: "Must run offline"
  id: "CON-001"
```

An exact textual reference:

```text
"Must run offline"
```

must NOT fail merely because the same exact constraint text is preserved in both artifacts.

For textual resolution, identical exact text values are treated as one textual resolution target for ambiguity purposes.

This reflects provenance duplication of the same constraint rather than two distinguishable meanings.

If the Analyst constraint has an ID, the ID remains an additional valid unambiguous reference key.

### 7.5 Ambiguity rule

A generated `relevant_constraints` reference is valid only when it identifies one unambiguous known constraint target.

Conceptually:

```text
0 distinct matching targets  → invalid
1 distinct matching target   → valid
>1 distinct matching targets → ambiguous and invalid
```

Important distinction:

- identical textual duplicates across upstream artifacts collapse to one textual target;
- genuinely different constraints that expose the same reference key are ambiguous and fail closed.

Example of a genuine ambiguity:

```text
ProblemAnalysis.constraints:
- id: "SECURITY"
  text: "Must run offline"

- id: null
  text: "SECURITY"
```

Reference:

```text
"SECURITY"
```

may mean either the first constraint's ID or the second constraint's exact text and is therefore ambiguous.

The application MUST NOT guess which one was intended.

### 7.6 Unresolved references

A reference with no match against the current upstream constraint universe is invalid.

The application MUST NOT:

- create a new constraint implicitly;
- rewrite the reference;
- perform fuzzy matching;
- silently drop the reference;
- accept it merely because it appears plausible.

The participant must fail its generated output before trusted `SolutionAlternatives` is returned.

### 7.7 Scope of the guarantee

Successful resolution proves only that a generated reference points to a known upstream constraint.

It does not prove that:

- the alternative interpreted the constraint correctly;
- the constraint is actually material to that alternative;
- the generated alternative satisfies the constraint;
- the Analyst identified every relevant constraint.

Those are semantic-quality concerns, not structural-reference guarantees.

## 8. Structural vs Contextual Validation Ownership

### Pydantic/model responsibility

Pydantic owns rules that depend only on the candidate generated output, including:

- required fields;
- nested structure;
- strict text types;
- empty/whitespace-only required text rejection;
- closed-schema behavior;
- supported `QualitativeLevel` values;
- valid alternatives collection cardinality;
- unique alternative IDs;
- conditional non-empty `generation_notes` requirement when alternatives are empty;
- immutable validated collections.

### Solution Architect/application responsibility

The participant/application boundary owns rules requiring the trusted current upstream context, including:

- resolving every `relevant_constraints` reference against `ReviewInput.constraints` and `ProblemAnalysis.constraints`;
- rejecting unresolved references;
- rejecting genuinely ambiguous references;
- accepting exact textual references to original constraints even when the Analyst omitted them;
- preserving fail-closed behavior when contextual resolution fails;
- normalizing generated structural/contextual failures into the participant output-validation error category.

Provider/transport failures remain distinct from generated-output validation failures.

## 9. Role Boundary

`SolutionAlternative` and `SolutionAlternatives` deliberately contain no fields for:

- ranking;
- preferred alternative;
- winner selection;
- final recommendation;
- final decision;
- risk assessment;
- critical review.

Because generated-output contracts are closed, unexpected top-level or nested fields representing those responsibilities are rejected.

This prevents structured role leakage.

The data model does not claim to detect every possible role violation embedded in arbitrary natural-language prose inside otherwise legitimate text fields.

## 10. Semantic Quality Boundary

The following properties are required by product behavior but are not completely provable through deterministic schema validation alone:

- alternatives are meaningfully distinct;
- an alternative is genuinely compatible with the stated objective;
- trade-offs are substantively correct;
- all important constraints were recognized;
- a partial or conditional solution is accurately characterized;
- no free-text wording subtly declares a winner;
- a no-alternative explanation identifies the correct semantic blockers.

This increment deliberately does not introduce:

- embeddings;
- fuzzy similarity thresholds;
- secondary LLM judging;
- a hidden Critic stage;
- domain-specific semantic rule engines.

Representative deterministic fixtures and later real-model evaluation against canonical reference scenarios are responsible for evaluating those semantic behaviors.

## 11. Provider-Neutral Serialization Relationship

The Solution Architect may serialize the already-trusted `ReviewInput` and `ProblemAnalysis` into standard Python/JSON-compatible structures before supplying them through the existing `LLMPort`.

Conceptually:

```text
payload
- review_input
- problem_analysis
```

This serialization:

- is provider-neutral;
- contains no provider SDK objects;
- does not alter the semantic contracts;
- does not establish trust in generated output;
- does not replace local validation.

Provider-specific request/response adaptation remains outside this increment.

## 12. Error Semantics

Malformed or context-invalid generated Solution Architect content must result in an explicit Solution Architect output-validation failure.

The application should distinguish this category from:

- invalid user input;
- provider/transport failure;
- unexpected internal failure.

Representative output-validation failures include:

- missing mandatory alternative fields;
- unsupported implementation-complexity value;
- invalid alternative count;
- duplicate alternative IDs;
- zero alternatives without non-empty `generation_notes`;
- unknown structured role-leakage fields;
- unresolved relevant-constraint reference;
- genuinely ambiguous relevant-constraint reference.

The exact Python exception class belongs to implementation, not to this semantic data contract.

## 13. Deferred Data

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
- semantic-similarity scores;
- quantitative complexity estimates.

Those concepts remain deferred until an approved later increment requires them.

## 14. Traceability to Approved Sources

This data model remains subordinate to and consistent with:

- `specs/002-solution-architect/spec.md` — approved Slice 2 behavior and scope;
- `specs/002-solution-architect/plan.md` — approved implementation and validation ownership decisions;
- `docs/02-requirements.md` — Solution Architect requirements;
- `docs/03-architecture.md` — explicit participant contracts and validation before trusted Review state;
- `docs/04-agent-model.md` — Solution Architect input/output contracts, no-alternative case, invariants, and prohibited behavior;
- `docs/05-quality-security.md` — deterministic validation, alternative distinctness, assumption preservation, valid references, and fail-closed generated data;
- `.specify/memory/constitution.md` — structured contracts, role integrity, traceability, minimal architecture, provider independence, and deterministic testability;
- `docs/adr/ADR-0001-pydantic-v2-for-structured-contracts.md` — approved Pydantic v2 validation policy and structural/contextual validation boundary.
