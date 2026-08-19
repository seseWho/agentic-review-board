# Research: Review Input + Analyst v0.1

**Feature:** `specs/001-review-input-analyst/spec.md`  
**Plan:** `specs/001-review-input-analyst/plan.md`  
**Related ADR:** `docs/adr/ADR-0001-pydantic-v2-for-structured-contracts.md`  
**Status:** Reviewed and reconciled with implementation

## 1. Purpose

This document records the technical questions investigated for the first executable
Analyst increment and the conclusions that informed the implementation plan.

It does not create new product requirements. Product behavior remains governed by the
canonical documents and `spec.md`; architectural decisions remain governed by the
canonical architecture and accepted ADRs.

The research focuses on uncertainties that needed resolution before implementation:

- how to represent and validate structured review contracts;
- how to handle untrusted generated output;
- where validation responsibilities belong;
- how to preserve provider independence;
- how much provenance can be enforced deterministically in this increment;
- whether review orchestration, a real LLM, or UI are necessary yet.

## 2. Research Decision — Pydantic v2 for Structured Contracts

### Question

Should the first review contracts use Python dataclasses with handwritten validation,
a validation library, or remain intentionally library-neutral?

### Evidence

The project requires structured contracts not only for `ReviewInput` and
`ProblemAnalysis`, but later for all remaining participant outputs. The canonical
architecture explicitly deferred selection of the structured-output validation library
until implementation reached this point.

Official Pydantic v2 documentation confirms support for the capabilities relevant to
this project:

- `BaseModel`-based typed models;
- model configuration through `ConfigDict`;
- deterministic control of extra fields, including `extra="forbid"`;
- frozen models;
- strict validation;
- structured validation errors;
- JSON Schema generation.

These capabilities directly cover recurring structural-validation needs without
requiring a larger agent or orchestration framework.

### Decision

Use **Pydantic v2** for the review-domain and participant-output contracts introduced by
this feature, under accepted ADR-0001.

Dependency range:

```text
pydantic>=2.13,<3
```

### Rationale

The validation need is already concrete and will recur across every review participant.
Establishing one contract convention now avoids duplicated handwritten parsing and
inconsistent validation policies later.

### Alternatives considered

- **Standard-library dataclasses plus handwritten validation** — technically viable but
  would require repeated parsing, nested validation, closed-schema handling, and custom
  error construction across multiple participant contracts.
- **TypedDict-only contracts** — useful for static shape documentation but insufficient
  as the sole runtime trust boundary for generated data.
- **Defer the decision** — rejected because validation is required in the current
  increment, not merely a future possibility.

### Boundary

Pydantic is selected for local contract validation. It does not define provider
protocols, persistence formats, UI representation, or review orchestration.

## 3. Research Decision — Fail-Closed Validation for Generated Output

### Question

How should unexpected or malformed fields returned by a model be handled?

### Evidence

The canonical Quality & Security baseline requires handling of unknown generated fields
to be deterministic and testable. It permits either rejection or ignoring as an
implementation choice.

Pydantic v2 supports explicit extra-field policies, including rejecting extra fields.

### Decision

Use fail-closed generated-output contracts and reject unexpected fields where the
contract is intended to be exhaustive.

Baseline model policy:

```text
extra = "forbid"
```

### Rationale

Rejecting unknown generated fields makes contract drift visible and avoids silently
accepting semantic content that has no defined downstream meaning.

### Alternatives considered

- **Ignore unknown fields** — deterministic but may hide model/schema drift during the
  MVP.
- **Allow arbitrary unknown fields** — rejected because it weakens the explicit-contract
  boundary and complicates traceability.

### Boundary

This is the default for generated participant outputs. A future compatibility need may
justify a different deterministic policy for a specific contract.

## 4. Research Decision — Preserve ReviewInput and Freeze Accepted Input

### Question

How should the requirement that original user input remain unchanged be represented?

### Evidence

Canonical requirements state that the original user-provided problem and context remain
unchanged for the duration of the review. Pydantic v2 supports frozen model
configuration, preventing ordinary field reassignment after construction.

Pre-merge regression tests showed that `frozen=True` alone does not make nested mutable
collections immutable: list fields can still be modified in place after model
validation.

### Decision

Represent `ReviewInput` as a frozen Pydantic model and store validated collections using
immutable ordered collection types.

Validation rejects an empty or whitespace-only required description but does not
silently trim or rewrite a valid supplied value. List-shaped external input remains
acceptable through normal Pydantic validation and is normalized into the immutable
validated representation.

### Rationale

Immutability directly supports traceability and prevents later application code from
accidentally rewriting the evidence basis of the review. Deep-enough immutability for
these collection fields is necessary because field reassignment protection alone did
not satisfy the preservation requirement.

### Alternatives considered

- **Mutable model with coding convention** — rejected because the invariant can be
  enforced directly and cheaply.
- **Frozen model with mutable list fields** — rejected after deterministic tests proved
  that post-validation in-place mutation remained possible.
- **Copy input into a second immutable structure later** — unnecessary duplication for
  this increment.

### Boundary

Frozen Pydantic models plus immutable collection fields provide practical
application-level immutability; they are not a security boundary against deliberate
low-level mutation.

## 5. Research Decision — Split Structural and Contextual Validation

### Question

Should all Analyst validation live inside Pydantic models?

### Evidence

Some invariants depend only on the generated candidate structure, while others require
trusted context from the active review.

Examples of structural/model-local validation:

- required fields exist;
- field types are valid;
- extra generated fields are rejected;
- source-reference values belong to the allowed vocabulary;
- duplicate non-null local identifiers are rejected within one candidate
  `ProblemAnalysis`.

Examples of contextual validation:

- a generated fact references a `ReviewInput` field that is actually present or
  applicable in the current review.

The canonical architecture places validation between generated model content and trusted
review contracts, but does not require every invariant to be embedded in one schema
class.

### Decision

Use two validation layers:

```text
untrusted generated content
    ↓
Pydantic structural/model-local validation
    ↓
Analyst/application contextual invariants
    ↓
trusted ProblemAnalysis
```

Duplicate-ID detection belongs to `ProblemAnalysis` because it depends only on the
candidate output. Fact-source applicability remains at the Analyst/application boundary
because it requires the current trusted `ReviewInput`.

### Rationale

This keeps Pydantic focused on reusable contract and model-local validation while
preserving rules that genuinely require active-review context in the
participant/application boundary.

### Alternatives considered

- **Put review-context rules inside Pydantic validators** — rejected because it would
  force trusted external review context into schema validation and blur
  responsibilities.
- **Perform all validation manually in Analyst** — rejected because it duplicates
  structural validation already provided declaratively by Pydantic.

## 6. Research Decision — Provider-Neutral LLM Port

### Question

Should the Analyst call a concrete model client directly, wait until a provider is
selected, or depend on an abstract capability from the start?

### Evidence

The canonical architecture requires review participants to depend on a provider-neutral
LLM Port and prohibits provider SDK types from leaking into domain or participant
contracts. It also identifies the LLM Port as the primary substitution seam for
deterministic tests.

### Decision

Introduce a minimal provider-neutral `LLMPort` abstraction for the capability required
by the Analyst.

The exact provider transport, authentication, SDK, endpoint, and response envelope
remain deferred.

### Rationale

The port is required now to test real participant behavior deterministically without
choosing a provider prematurely.

### Alternatives considered

- **Concrete provider client** — rejected because it violates provider independence.
- **No port until provider integration** — rejected because Analyst tests would then be
  coupled to temporary implementation details or a live model.
- **Agent framework abstraction** — rejected as unnecessary complexity for a single
  capability boundary.

### Boundary

This research does not fix the exact method signature of `LLMPort`. That belongs to the
implementation design and should remain as small as the Analyst use case requires.

## 7. Research Decision — Structural Fact Provenance

### Question

What level of fact provenance can be enforced deterministically in this increment?

### Evidence

The Analyst must distinguish facts explicitly supported by `ReviewInput` from
assumptions. However, proving semantic entailment of an arbitrary paraphrase would
itself require additional model judgment or a more sophisticated evidence mechanism.
Neither is required by the first increment.

### Decision

Require structural provenance for items represented as user-provided facts.

A fact must identify the conceptual `ReviewInput` field that supports it, using the
closed vocabulary:

```text
description
title
objective
constraints
context
stated_facts
```

After structural validation, the Analyst boundary verifies that the referenced field is
actually applicable/present in the current `ReviewInput`.

### Rationale

This gives deterministic traceability without pretending to prove semantic truth.

### Alternatives considered

- **Exact substring matching** — rejected because legitimate concise reformulations or
  paraphrases could fail despite being grounded in the input.
- **No explicit provenance** — rejected because fact traceability would become implicit.
- **LLM-based entailment verification** — deferred because it adds nondeterminism and
  complexity before the product demonstrates a need.

### Boundary

Structural provenance proves where the claimed fact is grounded, not whether the claim
is objectively true outside the supplied review input.

## 8. Research Decision — Review-Local Identifiers Remain Optional

### Question

Should every Analyst finding be required to have a local identifier from the first
increment?

### Evidence

The canonical Agent Model states that structured findings **SHOULD** contain stable local
identifiers where useful. It does not make identifiers mandatory for every finding.

### Decision

Identifiers may be present on Analyst findings but are not universally mandatory in
v0.1.

If identifiers are supplied, they must be non-empty and must not create ambiguous
references within the current `ProblemAnalysis`. Duplicate non-null identifiers are
therefore rejected as a model-level invariant.

### Rationale

This preserves the intended traceability mechanism without strengthening a canonical
SHOULD into an implementation-level MUST.

### Alternatives considered

- **Mandatory ID for every finding** — rejected because it would exceed the canonical
  requirement.
- **No ID support at all** — rejected because later participants will benefit from
  explicit references when available.

## 9. Research Decision — No Review Orchestrator Yet

### Question

Does implementing the Analyst require the full `Review`, `StageExecution`, status model,
and five-stage orchestrator now?

### Evidence

This feature contains one participant and does not expose the complete review lifecycle.
The canonical architecture requires orchestration for the full MVP but also requires
incremental, evidence-driven complexity.

### Decision

Do not implement the full orchestrator or stage lifecycle in this increment.

### Rationale

The first increment can independently demonstrate:

- valid review input;
- provider-neutral participant execution;
- structured validation;
- fact/assumption separation;
- explicit failure on invalid generated output.

Full orchestration becomes necessary when the next stage or user-visible stage execution
state is introduced.

### Alternatives considered

- **Implement the entire five-stage shell now** — rejected as premature architecture
  with little additional evidence from this feature.

## 10. Research Decision — No Real LLM or UI Yet

### Question

Are a concrete LLM adapter and UI necessary to validate this increment?

### Evidence

The architecture and Quality & Security baseline require core behavior to be testable
without a live model or network dependency. The feature specification contains no UI
behavior and deliberately excludes concrete provider integration.

### Decision

Use deterministic test substitutes for `LLMPort` and defer both a real LLM adapter and
UI.

### Rationale

This isolates contract and participant behavior first. Provider and UI decisions can
then be made using evidence from a stable core rather than shaping the core around an
early integration choice.

### Alternatives considered

- **Integrate a real provider now** — rejected because it adds secrets, network failure,
  provider coupling risk, and nondeterminism before required core behavior is proven.
- **Build a minimal UI now** — rejected because it adds no evidence needed to validate
  the Analyst contract itself.

## 11. Items Deliberately Not Resolved by This Research

The following remain outside this feature or require later evidence/ADRs:

- concrete LLM provider and model;
- exact LLM endpoint or SDK;
- exact `LLMPort` method signature beyond the capability needed by Analyst;
- provider-side structured-output mechanism;
- prompt content, storage, templating, and versioning;
- retry and timeout policy;
- synchronous versus asynchronous review execution;
- Review Orchestrator and stage state lifecycle;
- UI technology;
- persistence;
- RAG/document ingestion;
- dependency locking strategy;
- Pydantic mypy plugin;
- agent/orchestration framework.

## 12. Research Conclusion

No unresolved technical question in this feature blocks the completed implementation.

The reconciled direction is:

```text
ReviewInput (Pydantic, preserved/frozen, immutable collections)
    ↓
Analyst
    ↓
provider-neutral LLMPort
    ↓
untrusted generated content
    ↓
Pydantic structural/model-local validation
    ↓
contextual Analyst validation
    ↓
trusted ProblemAnalysis (immutable collections)
```

This direction is consistent with `spec.md`, `plan.md`, `data-model.md`, accepted
ADR-0001, the canonical architecture, the Agent Model, Quality & Security, and the
project Constitution.
