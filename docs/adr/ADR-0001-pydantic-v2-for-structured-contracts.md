# ADR-0001 — Use Pydantic v2 for Structured Contracts and Validation

**Status:** Accepted  
**Date:** 2026-08-19  
**Decision owners:** Agentic Review Board maintainers  
**Related feature:** `specs/001-review-input-analyst/`  
**Related plan:** `specs/001-review-input-analyst/plan.md`

## 1. Context

Agentic Review Board depends on explicit structured contracts between review stages.
Model-generated output is untrusted until it has been parsed and validated before it can
enter trusted Review state or be consumed by another participant.

The canonical architecture deliberately deferred the concrete structured-output
validation and serialization library until implementation reached a point where the
choice was justified. The first executable increment, **Review Input + Analyst v0.1**,
now reaches that point because it introduces the first two reusable structured
contracts:

- `ReviewInput`;
- `ProblemAnalysis`.

The same validation concern will recur for the later participant outputs:

- `SolutionAlternatives`;
- `RiskAssessment`;
- `CriticalReview`;
- `FinalReview`.

A purely handwritten validation approach is possible, but implementing required-field
checks, nested validation, closed-schema behavior, immutability, structured errors, and
schema representation separately for these contracts would create repetitive custom
code and increase the risk of inconsistent validation policy across participants.

The project therefore needs a standard validation mechanism before these contracts
proliferate.

## 2. Decision Drivers

The chosen approach should:

1. preserve the explicit contract and validation boundary required by the canonical
   architecture;
2. keep model-generated content untrusted until local validation succeeds;
3. reduce handwritten structural parsing and validation code;
4. support nested and reusable typed contracts;
5. provide deterministic, structured validation errors;
6. support closed schemas where unexpected generated fields should fail validation;
7. support immutable/frozen review data where appropriate;
8. preserve supplied textual values rather than silently rewriting them;
9. support JSON Schema generation for future provider-neutral structured-output
   integration;
10. remain independent of any concrete LLM provider or SDK;
11. work cleanly with Python >=3.12, pytest, Ruff, and mypy;
12. avoid introducing a larger agent or orchestration framework merely to obtain schema
    validation.

## 3. Decision

Adopt **Pydantic v2** as the standard structured-contract and local validation
foundation for Agentic Review Board review-domain and participant-output contracts.

Pydantic serialization facilities may be used to obtain explicit representations of
validated contracts, but Pydantic does **not** define the application's transport
protocol, provider request/response envelope, persistence format, or UI representation.
Those concerns remain owned by their respective architectural adapters and boundaries.

The project dependency policy for this decision is:

```text
pydantic>=2.13,<3
```

The lower bound reflects the version family selected by the current feature plan. The
project will not depend on a Pydantic v3 API without a future explicit compatibility
review. Patch-level pinning is not part of this ADR and may be introduced later through
a dependency-locking decision if reproducibility requirements justify it.

### 3.1 Where Pydantic is allowed

Pydantic MAY be used for:

- `ReviewInput` and other review-domain data contracts;
- participant input/output contracts;
- local parsing of untrusted structured model output;
- field and model validation;
- immutable/frozen contract configuration;
- explicit serialization of already validated contract data;
- JSON Schema generation for contract representation;
- validation-error information used by the application boundary.

### 3.2 Where Pydantic is not an architectural substitute

Pydantic MUST NOT replace:

- review orchestration;
- participant responsibility boundaries;
- application use-case logic;
- provider-neutral `LLMPort` abstractions;
- contextual/domain invariants that require comparison with other trusted review data;
- explicit application error semantics;
- provider transport or protocol ownership;
- persistence decisions;
- UI representation decisions;
- human decision authority.

A Pydantic model being structurally valid does not automatically make every semantic
claim in generated content true.

### 3.3 Serialization boundary

The semantic contract is defined by the validated review model and its documented
fields/invariants, not by one particular JSON encoding.

Pydantic serialization APIs MAY be used to convert trusted contracts into standard
Python or JSON-compatible representations when an application or adapter boundary needs
them. However:

- domain and participant contracts MUST NOT acquire provider-specific envelope fields;
- a concrete LLM Adapter remains responsible for provider-specific request and response
  formats;
- a future UI Adapter remains responsible for presentation-specific representation;
- any future persistence format requires its own architectural decision when persistence
  is introduced;
- changing a provider-specific transport representation MUST NOT require redesigning the
  semantic review contracts.

This keeps the choice of validation library separate from transport and integration
technology.

## 4. Validation Policy

The default policy for generated structured content is fail-closed.

### 4.1 Closed generated-output contracts

Participant-output models SHOULD use closed schemas where the contract is intended to
be exhaustive:

```text
extra = "forbid"
```

Unexpected fields must not be silently accepted merely because they were generated by
a model.

An exception requires a concrete compatibility need and must remain deterministic and
testable.

### 4.2 Immutability

Review data that represents accepted input or trusted stage output SHOULD be configured
as frozen when mutation after validation would undermine traceability.

`ReviewInput` is expected to be frozen because canonical requirements state that the
original user-provided input remains unchanged for the duration of the review.

### 4.3 Strictness and coercion

Generated contract fields SHOULD avoid permissive coercion where coercion could hide a
malformed model result.

Textual fields representing generated semantic content should reject unrelated
primitive types rather than silently converting them to strings.

Strictness may be applied at model or field level according to the contract, but the
behavior must be explicit and covered by tests.

### 4.4 Text preservation

Validation MUST NOT silently trim or rewrite valid user-provided text merely to satisfy
schema rules.

For required textual fields such as the review description, whitespace-only content may
be rejected while preserving the exact supplied value when it is otherwise valid.

### 4.5 Contextual invariants

Pydantic handles structural validation, but invariants that require trusted external
context remain outside ordinary shape validation.

Examples include:

- verifying that a generated fact references a field that is actually present in the
  current `ReviewInput`;
- checking cross-artifact references against the active review;
- enforcing participant-specific rules that depend on upstream trusted artifacts.

These checks belong to the participant/application validation boundary and must remain
explicit.

## 5. Provider Independence

This decision does not select or constrain the LLM provider.

Provider-specific SDK objects MUST NOT appear in review-domain contracts or participant
interfaces.

The `LLMPort` remains provider-neutral. A future concrete adapter may translate a
Pydantic-generated JSON Schema into provider-specific structured-output configuration,
but provider-side enforcement is an optimization/integration aid, not the trust
boundary.

Returned generated data MUST still pass local application validation before entering
trusted Review state.

Therefore changing between compatible LLM providers must not require redesigning the
Pydantic review contracts or participant semantics.

## 6. Alternatives Considered

### Alternative A — Standard-library dataclasses plus handwritten validation

Use frozen/slotted dataclasses and manually parse dictionaries returned by the model.

**Advantages**

- no production dependency;
- very small runtime footprint;
- complete control over every validation rule;
- no library-specific model API in domain contracts.

**Disadvantages**

- repetitive parsing and type/shape checks;
- custom handling required for nested structures;
- custom error aggregation and reporting;
- manual closed-schema behavior;
- manual schema representation for future structured-output integration;
- growing duplication as five participant contracts are introduced;
- higher risk of inconsistent validation policies across participants.

**Assessment:** Rejected. It is viable for a single tiny contract, but the required
validation behavior would be repeated across the full review workflow and would add
custom code without adding product value.

### Alternative B — Pydantic v2

Use Pydantic `BaseModel`-based contracts with explicit model configuration and retain
contextual invariants in application/participant logic.

**Advantages**

- declarative typed contracts;
- reusable nested validation;
- structured validation errors;
- configurable closed-schema behavior;
- frozen models where appropriate;
- strict validation options;
- explicit serialization facilities;
- JSON Schema generation;
- substantially less handwritten structural validation;
- a common contract pattern across all five participant outputs.

**Disadvantages**

- introduces a core production dependency;
- domain contracts become coupled to the Pydantic v2 model API;
- careless use of coercion or permissive defaults could weaken fail-closed semantics;
- major-version upgrades may require migration work;
- developers need to distinguish schema validation from contextual/domain validation.

**Assessment:** Selected. The simplification and consistency benefits are already
material at the first structured-contract boundary and become stronger as later agents
are added.

### Alternative C — Defer the library decision

Keep the first increment library-neutral and revisit after more contracts exist.

**Advantages**

- avoids committing to a dependency immediately;
- preserves maximum short-term implementation freedom.

**Disadvantages**

- requires temporary handwritten validation for a concern already known to recur;
- encourages inconsistent patterns before the common contract foundation is selected;
- delays schema-generation capability that will likely be useful for real LLM adapters;
- creates unnecessary migration work across several contracts instead of establishing
  the convention with the first one.

**Assessment:** Rejected. The architectural need is no longer hypothetical: the Analyst
increment requires structured parsing and validation now.

## 7. Consequences

### Positive consequences

- `ReviewInput` and `ProblemAnalysis` can use one consistent validation model.
- Later participant contracts can reuse the same conventions.
- Handwritten shape validation should decrease significantly.
- Generated-output failures can expose structured and testable validation details.
- Closed-schema and strictness policies can be expressed declaratively.
- JSON Schema can be produced without coupling domain contracts to a specific LLM SDK.
- Tests can focus more on product/domain invariants and less on repetitive parser code.

### Negative consequences

- Pydantic becomes a production dependency of the review core.
- Pydantic v2 semantics become part of the implementation knowledge required by the
  project.
- A future major Pydantic upgrade may require contract migration.
- The team must guard against assuming that successful Pydantic validation establishes
  factual correctness of LLM-generated content.
- Validation policy must be configured deliberately; permissive defaults must not
  silently weaken canonical fail-closed behavior.

### Neutral / accepted trade-off

The review domain will use library-backed contract classes rather than dependency-free
plain Python data structures. This is accepted because structured validation is a core
architectural concern of the product rather than an incidental utility.

## 8. Testing and Compliance Requirements

Implementation governed by this ADR must include deterministic tests demonstrating at
least:

- valid contract construction;
- required-field rejection;
- unknown-field rejection for closed generated-output contracts;
- strict-type rejection where configured;
- ReviewInput immutability;
- preservation of valid supplied text;
- normalized handling of Pydantic validation failures at the Analyst boundary;
- contextual fact-provenance validation against the actual `ReviewInput`;
- no import or dependency on a concrete LLM provider in core tests.

Existing project quality gates remain:

```text
pytest
ruff check .
mypy
pip check
```

Pydantic-specific mypy plugins are not required by this ADR. They may be evaluated
later only if standard mypy behavior proves insufficient.

## 9. Reconsideration Conditions

Revisit this decision if evidence shows one or more of the following:

- Pydantic materially complicates the domain model more than it simplifies validation;
- model performance or startup overhead becomes significant for the demonstrator;
- a required runtime environment cannot support the selected Pydantic version family;
- generated-output contracts require semantics that cannot be represented cleanly;
- a different validation mechanism provides substantially simpler provider-neutral
  structured contracts with lower project complexity;
- Pydantic v3 introduces breaking changes that justify reconsidering rather than simply
  migrating;
- dependency-minimization requirements change materially.

A reconsideration must be based on observed evidence, not framework preference alone.

## 10. Relationship to Canonical Documents

This ADR implements a decision intentionally deferred by `docs/03-architecture.md`:
selection of the structured-output validation library and serialization mechanism.

It must continue to preserve:

- explicit validated contracts from `docs/02-requirements.md`;
- provider-neutral boundaries from `docs/03-architecture.md`;
- Analyst semantics and fact/assumption separation from `docs/04-agent-model.md`;
- fail-closed validation and deterministic testing from `docs/05-quality-security.md`;
- minimal, evidence-driven complexity and explicit architectural decisions from
  `.specify/memory/constitution.md`.

The ADR does not alter product requirements. It selects the implementation mechanism for
an already-required validation boundary.
