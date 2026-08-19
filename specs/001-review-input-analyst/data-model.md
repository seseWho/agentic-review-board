# Data Model: Review Input + Analyst v0.1

**Feature:** `specs/001-review-input-analyst/spec.md`  
**Plan:** `specs/001-review-input-analyst/plan.md`  
**ADR:** `docs/adr/ADR-0001-pydantic-v2-for-structured-contracts.md`  
**Status:** Draft — awaiting review

## 1. Purpose

This document defines the structured data introduced by the **Review Input + Analyst v0.1** increment.

It refines the semantic contracts already defined by the canonical Agent Model without adding new product requirements.

Pydantic v2 is the approved implementation mechanism for these structured contracts. The semantic contract remains defined by the fields and invariants documented here, not by provider-specific schemas or transport envelopes.

## 2. Shared Modeling Rules

The following rules apply to the contracts introduced by this increment:

- models use Pydantic v2 `BaseModel`;
- accepted review data is immutable where mutation would break traceability;
- closed generated-output contracts reject unexpected fields deterministically;
- valid supplied text is preserved rather than silently trimmed or rewritten;
- required text may be rejected when empty or whitespace-only;
- generated structured content is untrusted until both structural validation and applicable contextual invariants succeed;
- Pydantic validation establishes structural validity, not factual truth;
- provider-specific request/response types are not part of these models.

## 3. ReviewInput

Represents the original information supplied by the user for the current review.

### Fields

```text
ReviewInput
- description: str
- title: str | None
- objective: str | None
- constraints: collection[str]
- context: collection[str]
- stated_facts: collection[str]
```

### Semantics

- `description` is the only mandatory user input.
- `title`, `objective`, `constraints`, `context`, and `stated_facts` are optional context.
- Empty optional collections are valid.
- The exact user-provided textual values remain unchanged after validation.

### Validation rules

- `description` MUST reject empty or whitespace-only input.
- A valid non-empty description MUST NOT be silently stripped or rewritten.
- Optional text fields MUST remain optional.
- Collection items, when present, are textual values supplied by the user.
- The model is configured as frozen after successful construction so accepted input cannot be reassigned accidentally.

### Pydantic configuration intent

Conceptually:

```text
frozen = true
extra = forbid
```

The exact Python syntax belongs to implementation, but the observable behavior is part of this data-model design.

## 4. AnalysisFinding

Represents a structured Analyst finding that is not classified as a user-provided fact.

Used for:

- constraints;
- assumptions;
- missing information;
- uncertainties.

### Fields

```text
AnalysisFinding
- text: str
- id: str | None
```

### Validation rules

- `text` is required and non-empty.
- `id` is optional because the canonical Agent Model states that review-local identifiers SHOULD be present where useful, not that every finding MUST have one.
- when an `id` is present, it must be non-empty.

The absence of an identifier alone does not make a finding invalid.

## 5. FactFinding

Represents a statement that the Analyst classifies as explicitly supported by the current `ReviewInput`.

### Fields

```text
FactFinding
- text: str
- source_ref: ReviewInputSource
- id: str | None
```

### ReviewInputSource

`source_ref` uses a closed vocabulary corresponding to the conceptual fields of `ReviewInput`:

```text
description
title
objective
constraints
context
stated_facts
```

This vocabulary may be represented by an enum or equivalent strongly validated type.

### Structural validation

Pydantic validates:

- `text` is present and valid text;
- `source_ref` belongs to the allowed vocabulary;
- optional `id`, when present, is valid text;
- unexpected fields are rejected.

### Contextual validation

Structural validity alone is insufficient to trust a fact.

The Analyst/application validation boundary must additionally verify that the referenced source is actually applicable to the current `ReviewInput`.

Examples:

- `source_ref = title` is invalid for a fact if the current `ReviewInput.title` is absent;
- `source_ref = stated_facts` is valid only when the current input contains stated facts;
- `source_ref = description` can reference the mandatory description.

This check establishes structural provenance only. It does not independently prove that the generated fact text is objectively true or perfectly entailed by the referenced source.

## 6. ProblemAnalysis

Represents the validated structured output of the Analyst.

### Fields

```text
ProblemAnalysis
- objective: str
- facts: collection[FactFinding]
- constraints: collection[AnalysisFinding]
- assumptions: collection[AnalysisFinding]
- missing_information: collection[AnalysisFinding]
- uncertainties: collection[AnalysisFinding]
```

All six semantic categories are required by the Analyst contract, although the collections may be empty when no relevant finding exists.

### Structural invariants

Pydantic validates at minimum:

- `objective` exists and contains non-empty text;
- all five collections exist;
- every nested item conforms to its declared contract;
- facts remain structurally distinct from assumptions;
- unexpected top-level fields are rejected;
- unexpected nested fields are rejected where the nested contract is closed.

### Cross-item invariants

Review-local identifiers are optional.

When identifiers are supplied:

- duplicate non-null identifiers within the same `ProblemAnalysis` are invalid because they would create ambiguous references;
- missing identifiers do not invalidate otherwise valid findings.

This preserves the canonical SHOULD semantics for local identifiers.

### Analyst role boundary

`ProblemAnalysis` MUST NOT contain fields whose semantics belong to later participants, including:

- solution alternatives;
- alternative ranking;
- architecture recommendation;
- risk ranking owned by later stages;
- preferred solution;
- final recommendation or decision.

If generated output includes such unexpected fields, the closed contract rejects them instead of silently accepting role leakage.

## 7. Validation Boundary

The trust transition for this increment is:

```text
ReviewInput
    ↓
Analyst requests generated structured content
    ↓
untrusted generated representation
    ↓
Pydantic structural validation
    ↓
contextual Analyst invariants
    ↓
trusted ProblemAnalysis
```

### Pydantic responsibility

Pydantic owns ordinary contract concerns such as:

- required fields;
- field types;
- nested model structure;
- closed-schema behavior;
- allowed `source_ref` vocabulary;
- model-level invariants that depend only on the candidate `ProblemAnalysis` itself.

### Analyst/application responsibility

The Analyst/application boundary retains rules that require trusted review context, including:

- checking that a fact's source reference is applicable to the actual current `ReviewInput`;
- normalizing structural validation failures into the application's Analyst-output validation error category;
- ensuring invalid generated content is never returned as trusted `ProblemAnalysis`.

No missing required value is manufactured to repair generated output.

## 8. LLMPort Relationship

`LLMPort` is an application boundary, not a data entity and not part of the persisted domain model.

For this feature it provides only the provider-neutral capability needed by the Analyst to request structured model output.

The data-model contract deliberately does **not** define a concrete method signature, transport representation, provider envelope, or SDK type for `LLMPort`.

Those details belong to the application-port implementation and later provider adapter decisions.

A future provider adapter may use the JSON Schema generated from `ProblemAnalysis` to request provider-native structured output, but local validation remains mandatory before the result becomes trusted review data.

## 9. Error Semantics

Malformed or contract-invalid generated Analyst content must result in an explicit Analyst-output validation failure.

The application should distinguish this category from:

- invalid user input;
- provider/transport failure;
- unexpected internal failure.

The concrete exception class or error representation belongs to implementation, not to the semantic data contract.

## 10. Deferred Data

This increment intentionally does not yet model:

- `Review` aggregate/lifecycle;
- `StageExecution`;
- stage status values;
- `SolutionAlternatives`;
- `RiskAssessment`;
- `CriticalReview`;
- `FinalReview`;
- persistent identifiers;
- review history;
- provider request/response models;
- UI view models;
- persistence schemas.

Those concepts will be introduced only by later approved increments when their behavior is required.

## 11. Traceability to Canonical Documents

This data model remains subordinate to and consistent with:

- `docs/02-requirements.md` — Review Input and Analyst requirements;
- `docs/03-architecture.md` — validation before trusted Review state and provider-neutral boundaries;
- `docs/04-agent-model.md` — conceptual `ReviewInput`, `ProblemAnalysis`, local identifiers, Analyst invariants, and prohibited behavior;
- `docs/05-quality-security.md` — fail-closed generated-output validation, deterministic unknown-field behavior, and fact provenance;
- `.specify/memory/constitution.md` — structured contracts, traceability, provider independence, and minimal incremental architecture;
- `docs/adr/ADR-0001-pydantic-v2-for-structured-contracts.md` — approved Pydantic v2 validation policy.
