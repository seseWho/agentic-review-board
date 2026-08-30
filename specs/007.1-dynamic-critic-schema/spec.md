# Slice 7.1 — Context-Bound Critic Output Schema v0.1

**Status:** Approved — trust-boundary correction reviewed and approved by the user on 2026-08-30  
**Branch:** `007.1-dynamic-critic-schema`  
**Depends on:** Slices 1–7  
**Observed evidence:** local vLLM runs recorded on 2026-08-29  
**Canonical sources:** `docs/01-product-vision.md`, `docs/02-requirements.md`, `docs/03-architecture.md`, `docs/04-agent-model.md`, `docs/05-quality-security.md`, `.specify/memory/constitution.md`, ADR-0001, ADR-0002

## 1. Purpose

Slice 7.1 reduces a demonstrated Critic failure mode without weakening the trusted
Critic contract or changing the provider-neutral `LLMPort`.

The current JSON Schema constrains the shape of a `CriticalReview`, but it cannot
express that each generated `CriticReference` must be one exact reference visible in
the current Review. A local Qwen3-8B-AWQ run returned syntactically valid JSON containing
illegal combinations such as `PROBLEM_ANALYSIS + STATED_FACT`, IDs on value-only
references, and contradiction statements that paraphrased their referenced values.
The participant correctly rejected the output and left Coordinator pending.

This slice SHALL build a request-specific Critic output schema from the current
four-artifact payload. The schema SHALL expose only legal exact references and SHALL
bind each contradiction statement to the exact visible value of its selected reference.
The existing participant validation remains authoritative and fail-closed.

## 2. Current Baseline

Slice 7 already provides:

- an unchanged provider-neutral `LLMPort.generate_structured(role, payload)`;
- static role prompt definitions generated from authoritative Pydantic output models;
- `JSON_OBJECT`, `JSON_SCHEMA`, and `PROMPT_ONLY` modes;
- strict-schema normalization for required properties and bounded arrays;
- direct JSON parsing with no repair;
- exact structural and contextual Critic validation after generation;
- deterministic adapter tests and opt-in live tests;
- raw-output observation for explicitly enabled diagnostics.

The baseline MUST continue rejecting all invalid output even when a provider ignores or
does not support request-time schema guidance.

## 3. Scope

### 3.1 In Scope

Slice 7.1 SHALL:

1. recognize the exact current Critic payload shape containing `review_input`,
   `problem_analysis`, `solution_alternatives`, and `risk_assessment`;
2. expose every current semantic target that the existing contextual validator can resolve,
   using at least one canonical legal reference representation per target;
3. preserve exact `source`, `kind`, optional `item_id`, and optional `value` semantics;
4. correlate complete reference objects rather than independently enumerating fields;
5. generate contradiction-side alternatives that pair one exact reference with its
   exact visible statement;
6. construct a deterministic request-specific `CriticalReview` JSON Schema;
7. carry that request-specific schema as clearly delimited untrusted request data for all
   structured output modes, without placing payload-derived values in the trusted system
   instruction;
8. use it as the provider `response_format.json_schema.schema` in `JSON_SCHEMA` mode;
9. keep the authoritative static output model and semantic role instruction unchanged;
10. preserve all current parsing, participant validation, stage failure, and orchestration
    behavior;
11. fail safely before network I/O when the Critic payload cannot produce a trustworthy
    request schema;
12. provide deterministic tests proving exact reference coverage, exclusion, correlation,
    immutability, request construction, and regression safety;
13. add an opt-in local evaluation procedure that records whether Critic and Coordinator
    complete without treating one successful generation as proof of reliability.

### 3.2 Out of Scope

Slice 7.1 SHALL NOT:

- change `LLMPort`, participant signatures, domain models, Review lifecycle, or stage order;
- relax, bypass, duplicate-repair, or replace `Critic._validate_structure` or contextual
  validation;
- silently rewrite `source`, `kind`, IDs, values, statements, or model output;
- add automatic retries, fallback models, provider routing, or schema-mode downgrade;
- make a schema-guided response trusted before participant validation;
- constrain Critic prose to predetermined conclusions or guarantee intellectual quality;
- introduce a generic schema framework, rules engine, JSONPath system, provider SDK, or
  new runtime dependency;
- generate dynamic schemas for Analyst, Solution Architect, Risk Reviewer, or Coordinator;
- add UI, persistence, history, RAG, tools, autonomous action, or production observability;
- expose full sensitive payloads or generated schemas in default logs/errors.

## 4. User Stories

### US1 — Prevent invalid Critic reference combinations

As an operator, I want the guided Critic request to offer only references valid for the
current Review so that capable compatible models cannot emit illegal source/kind/ID/value
combinations merely because the static schema allowed them.

#### Acceptance criteria

1. Every offered reference is resolvable by the current Critic contextual rules.
2. `REVIEW_INPUT` exposes only its six approved kinds and value-only shapes.
3. `PROBLEM_ANALYSIS` exposes only its objective and five approved finding collections.
4. `SOLUTION_ALTERNATIVES` exposes only current alternatives, their approved nested
   values, and current generation-note values when present.
5. `RISK_ASSESSMENT` exposes only current risks, approved risk fields, and current overall
   observations.
6. Empty or absent optional collections contribute no fabricated reference alternative.
7. Complete objects are correlated; selecting one source cannot be combined with the kind,
   ID, or value of another object.
8. When the current contract accepts more than one representation of the same target, the
   guided request may expose one stricter canonical representation rather than every weaker
   equivalent variant.

### US2 — Bind contradiction statements to exact evidence

As a reviewer, I want a contradiction side to copy the exact visible upstream proposition
so that a plausible paraphrase cannot masquerade as a traceable quotation.

#### Acceptance criteria

1. Every allowed contradiction side pairs one allowed reference with its resolved visible
   value as `statement`.
2. No alternative pairs a reference with a statement from another reference.
3. Value-only, finding, alternative, and risk references resolve to the same visible value
   used by existing Critic validation.
4. The existing participant still checks this equality after generation.

### US3 — Preserve provider-neutral behavior

As a maintainer, I want this reliability improvement isolated behind the adapter boundary
so that participants and providers remain interchangeable.

#### Acceptance criteria

1. `LLMPort` remains byte-for-byte unchanged.
2. Critic continues sending the same four JSON payload keys.
3. Domain CriticalReview and CriticReference models remain authoritative and unchanged.
4. Non-Critic roles continue using their current static schemas.
5. `JSON_OBJECT` and `PROMPT_ONLY` receive the dynamic schema only as delimited request
   data; `JSON_SCHEMA` additionally sends it to the compatible provider.
6. No provider-specific type crosses into participants, application, or domain.
7. The fully empty `CriticalReview`, empty individual finding collections, and currently
   optional Critic references remain representable; guidance does not force activity.

### US4 — Fail closed during schema construction

As a user, I want an invalid or ambiguous Critic request context to fail visibly before
calling the provider so that schema generation cannot silently widen constraints.

#### Acceptance criteria

1. Missing, extra, malformed, or wrong-typed required Critic payload artifacts are rejected.
2. Duplicate JSON keys remain handled by existing configuration/response rules and are not
   introduced by schema construction.
3. Duplicate exact schema alternatives resolving to the same semantic target are
   deterministically deduplicated. An emitted reference that would resolve ambiguously to
   different current targets is excluded completely; no target is guessed.
4. Construction failure performs no HTTP request.
5. The public error is fixed, provider-neutral, and contains no payload content.
6. The existing orchestrator maps the adapter exception through its current safe execution
   failure behavior; this slice adds no new Review error category.

### US5 — Verify the improvement deterministically and live

As a maintainer, I want deterministic schema tests plus controlled local evidence so that
we distinguish contract enforcement from model quality.

#### Acceptance criteria

1. Default tests need no endpoint, GPU, credentials, or network.
2. Tests cover every allowed source/kind family and all observed illegal combinations.
3. Tests prove deterministic byte-equivalent schemas for equivalent payloads.
4. Tests prove input payloads and nested values are not mutated.
5. Adapter request tests assert the delimited data-message schema and provider schema are
   the same dynamic logical schema, and that payload-derived values never enter the system
   instruction.
6. A live evaluation records stage outcomes and raw diagnostic outputs only when explicitly
   authorized.
7. Success criteria report a distribution across repeated runs; no retry-until-success
   evidence is accepted.

## 5. Functional Requirements

### DCS-FR-001 — Unchanged Port

The feature SHALL operate through the existing `generate_structured` signature. Payload-
dependent schema generation is an adapter implementation detail.

### DCS-FR-002 — Exact Critic Activation

Dynamic schema generation SHALL activate only when `role` is exactly `critic`. Unknown
roles retain existing failure behavior. The other four supported roles retain their current
static schema behavior.

### DCS-FR-003 — Required Context Snapshot

Request constraint construction SHALL consume one snapshot of the supplied Critic payload
and SHALL require exactly the four approved artifact keys. It SHALL not read mutable global
Review state, perform network I/O, or resolve data from another execution.

### DCS-FR-004 — Existing Semantics Are Canonical

Every exposed canonical reference SHALL match current `CriticReference` shape rules and
visible-value semantics. Every unambiguous current semantic target SHALL have at least one
exposed canonical reference. The feature need not expose weaker equivalent representations,
such as omitting an available disambiguating ID or an optional exact visible value. Tests
SHALL detect drift between request constraints and participant validation.

### DCS-FR-005 — Correlated Reference Alternatives

The schema SHALL represent each allowed reference as one atomic alternative containing
only its exact legal fields. It SHALL NOT model source, kind, ID, and value as independent
enums that permit an invalid Cartesian product.

### DCS-FR-006 — Exact Optionality

Fields absent for a reference kind SHALL be absent from its schema alternative. A
value-only reference SHALL not acquire `item_id`; an ID-primary or nested reference SHALL
not omit its required ID; optional finding IDs SHALL reflect the actual current artifact.

### DCS-FR-007 — Exact Contradiction Sides

Each contradiction-side alternative SHALL contain one exact allowed reference and a
`statement` constrained to that reference's resolved visible value.

### DCS-FR-008 — Authoritative Outer Contract

The request-specific constraint SHALL be derived from the authoritative `CriticalReview`
contract and SHALL narrow only current-reference selection and contradiction-side pairing.
All other fields, enums, requiredness, closed-object behavior, optionality, collection
cardinality, and bounded-output behavior SHALL remain equivalent to Slice 7. The exact
schema-transformation strategy is deferred to the plan and data model.

### DCS-FR-009 — One Schema Snapshot per Call

Request construction SHALL build one logical schema per Critic call and use that same
snapshot in the delimited untrusted data message and, in `JSON_SCHEMA` mode, provider
guidance. It SHALL not rebuild from a later or mutated payload state.

### DCS-FR-010 — Deterministic Serialization

Equivalent ordered semantic catalogs SHALL produce byte-equivalent serialized schemas.
Ordering SHALL be application-controlled and independent of hash iteration.

### DCS-FR-011 — Payload Immutability

Schema construction and request construction SHALL not mutate the caller's mapping,
nested collections, or artifact values.

### DCS-FR-012 — Safe Construction Error

Invalid dynamic-schema input SHALL produce a distinguishable provider-neutral construction
failure with a fixed safe public message. The exact error type and message are deferred to
the plan and data model. Causes may be retained internally but must not be surfaced by the
product.

### DCS-FR-013 — No Trust Promotion

Provider conformance to the dynamic schema SHALL not bypass direct JSON parsing,
`CriticalReview.model_validate`, or current-context Critic validation.

### DCS-FR-014 — Mode Behavior

- `JSON_SCHEMA`: the data message includes the dynamic schema and `response_format` carries
  its strict form.
- `JSON_OBJECT`: the data message includes the dynamic schema and response format remains
  `{ "type": "json_object" }`.
- `PROMPT_ONLY`: the data message includes the dynamic schema and response format remains
  absent.

No mode fallback or provider probing is permitted.

Only a compatible provider honoring `JSON_SCHEMA` guidance is expected to prevent invalid
combinations during decoding. `JSON_OBJECT` and `PROMPT_ONLY` receive the constraint as
untrusted data but provide no equivalent enforcement guarantee; existing validation remains
mandatory in every mode.

### DCS-FR-015 — Bounded Size and No Truncation

The constraint SHALL include at least one canonical legal reference for every unambiguous
current semantic target. It SHALL not silently truncate that catalog to reduce prompt size.
Tests SHALL record schema size for maximum contract-valid fixture cardinalities. If a
supported provider cannot accept that schema, the call fails visibly or the profile uses
another explicit mode; the adapter does not weaken constraints automatically.

### DCS-FR-016 — Data Minimization

Only values already present in the Critic payload and necessary to express legal references
or contradiction statements may appear in the dynamic schema. Credentials, endpoint data,
unrelated environment values, hidden reasoning, and data from previous Reviews SHALL not
appear. Payload-derived values SHALL remain in the untrusted data boundary and SHALL NOT be
promoted into system/developer instructions.

### DCS-FR-017 — Observability Policy

The dynamic schema SHALL not be logged by default. Existing opt-in raw-output observation
continues to capture provider output, not complete request payloads or schemas.

### DCS-FR-018 — Live Evaluation

The documented local evaluation SHALL run a fixed scenario multiple times without automatic
retry. It SHALL record model/image/configuration, elapsed time, each stage outcome, the failed
contract family when known, and whether Coordinator completed.

### DCS-FR-019 — Preserve Valid Critic Inactivity and Optionality

The dynamic constraint SHALL preserve every currently valid no-activity shape, including a
fully empty `CriticalReview`, empty individual finding collections, and criticism shapes
whose target reference is legitimately absent under the existing Critic contract. It SHALL
not force a criticism, validated point, missing alternative, contradiction, unresolved issue,
or reference merely because candidate references are available.

## 6. Edge Cases

1. Minimal ReviewInput with empty context, facts, or constraints.
2. Problem findings with and without optional IDs.
3. Duplicate visible text in one finding collection where ID disambiguates targets.
4. Duplicate visible value across different sources or kinds.
5. Zero alternatives with generation notes.
6. Two or three alternatives with repeated characteristic text.
7. Optional alternative assumptions absent.
8. Empty risk collection and risks without residual uncertainty.
9. Duplicate overall-observation text, which current exact lookup treats as ambiguous.
10. Unicode and JSON-significant characters in exact values.
11. Payload mappings supplied in different key orders.
12. Caller mutation after schema snapshot creation.
13. Provider ignores or cannot enforce `JSON_SCHEMA` and returns invalid content.
14. Dynamic schema exceeds a provider-specific request limit.
15. Fully empty `CriticalReview` and criticism with a legitimately absent single target.
16. Prompt-injection-like text inside any exact referenced value remains escaped and confined
    to the untrusted data message.

## 7. Success Criteria

### SC-001 — Deterministic contract coverage

Every reference alternative emitted by deterministic fixtures is accepted by the existing
Critic resolver, and every observed illegal source/kind combination is absent.

### SC-002 — Observed failure prevention

With a compatible provider honoring `JSON_SCHEMA`, the exact 2026-08-29 invalid patterns
are not permitted by the guided schema:

- `PROBLEM_ANALYSIS + STATED_FACT`;
- `PROBLEM_ANALYSIS + CONTEXT`;
- `item_id` on value-only references;
- a contradiction statement differing from its selected reference value.

### SC-003 — Regression safety

The complete deterministic suite, Ruff, mypy, and dependency checks pass without changing
existing trusted output semantics.

### SC-004 — Local evidence

At least five explicitly initiated local runs are recorded with no retry-until-success
selection. The result may still be incomplete, but any remaining failure is classified
separately from the four prevented patterns above.

## 8. Assumptions

1. OpenAI-compatible providers may support different subsets of JSON Schema; Slice 7.1
   guarantees request construction and local reference validation, not universal provider
   acceptance.
2. vLLM 0.8.5 with the current local profile is the first live evaluation target.
3. Current participant payloads originate from already validated domain artifacts.
4. Static Pydantic schemas remain the source of outer output shape truth.
5. Exact reference copying is intentional traceability, not a request for hidden reasoning.
6. Provider support for the selected JSON Schema subset is an explicit compatibility
   condition verified separately from deterministic contract correctness.

## 9. Dependencies and Constraints

- No production dependency change is expected.
- Pydantic v2 and standard-library JSON remain sufficient.
- ADR-0002 remains valid; no new provider access pattern is introduced.
- The Constitution's validation, traceability, visible failure, provider independence,
  minimal architecture, and deterministic testing requirements are mandatory.

## 10. Review Gate

Before approval of this specification, confirm:

1. request-specific narrowing belongs in infrastructure and does not redefine domain truth;
2. the four-artifact payload is sufficient to expose every unambiguous current semantic
   target through a canonical legal Critic reference;
3. full correlated alternatives are preferable to independent field enums;
4. contradiction statements must remain exact;
5. no retry or silent repair enters this slice;
6. five local runs are an evidence target, not a product reliability guarantee;
7. valid empty Critic output and legitimate reference optionality remain possible;
8. enforcement claims are limited to compatible providers honoring `JSON_SCHEMA`.
9. payload-derived exact values never enter the trusted system instruction.

No plan SHALL be treated as approved and no implementation SHALL begin until this
`spec.md` has been reviewed and explicitly approved by the user. After approval, the plan
will be reviewed as the next independent Spec Kit gate.
