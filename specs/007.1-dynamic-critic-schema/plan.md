# Implementation Plan: Context-Bound Critic Output Schema v0.1

**Branch:** `007.1-dynamic-critic-schema`  
**Specification:** `specs/007.1-dynamic-critic-schema/spec.md` — Approved  
**Status:** Approved — second review corrections approved by the user on 2026-08-30

## 1. Objective

Add the smallest provider-boundary mechanism that constrains the Critic request to
canonical references grounded in the current Review. With a compatible provider honoring
`JSON_SCHEMA`, illegal reference combinations are excluded during decoding:

```text
validated participant artifacts serialized as Critic payload
                         ↓
             immutable payload snapshot
                         ↓
       exact allowed-reference catalog + visible values
                         ↓
 authoritative static CriticalReview JSON Schema
                         ↓ narrow selected definitions
         request-specific Critic output schema
                  ↙                     ↘
 static trusted system instruction      JSON_SCHEMA response_format
                  ↓                     ↙
 delimited user/data message containing payload + dynamic schema
                  ↓
                   provider response
                         ↓
 direct JSON parsing + existing Critic structural/context validation
```

The domain remains the source of truth. Guided generation reduces invalid output; it does
not create trusted output.

## 2. Observed Limitation

The local run produced schema-shaped JSON but failed before Coordinator because a static
Pydantic schema permits combinations that are legal at field level and illegal together:

- `source=PROBLEM_ANALYSIS`, `kind=STATED_FACT`;
- `source=PROBLEM_ANALYSIS`, `kind=CONTEXT`;
- `item_id=context` on value-only references;
- contradiction statements paraphrasing their exact reference values.

Prompt strengthening alone has not reliably prevented similar reference fabrication. The
limitation is evidenced, bounded, and located at request-schema construction.

## 3. Design Principles

### 3.1 Narrow generation; never weaken validation

The dynamic schema is an upstream constraint. Existing `CriticalReview` parsing and
`Critic._validate_context` remain unchanged and mandatory.

### 3.2 Keep `LLMPort` unchanged

The adapter already receives role and payload. A request-specific schema can be derived
inside infrastructure without leaking schemas or provider options into participant APIs.

### 3.3 Preserve one authoritative outer model

`CriticalReview.model_json_schema()` remains the base. A dedicated Critic builder deep-copies
and narrows only the definitions representing `CriticReference` and `ContradictionSide`.
It does not hand-maintain a second complete CriticalReview schema.

### 3.4 Correlate complete alternatives

Independent field enums produce a Cartesian product and repeat the current bug. Each
unambiguous semantic target is represented by one canonical complete closed schema
alternative with constant field values.

### 3.5 Pure deterministic construction

The builder performs no I/O, reads no environment/global state, mutates no caller data, and
orders output canonically. Equivalent payloads produce equivalent schemas.

## 4. Technical Context

- Language: Python 3.12+
- Validation: Pydantic v2
- HTTP: HTTPX through existing direct OpenAI-compatible adapter
- Schema transport: Chat Completions `response_format.type=json_schema`
- Tests: pytest with injected HTTPX transport
- Runtime dependency changes: none
- Architectural decision changes: none; ADR-0002 remains applicable

## 5. Proposed Components

### 5.1 `dynamic_schemas.py`

Add one focused infrastructure module under
`src/agentic_review_board/infrastructure/llm/` containing:

- immutable internal `AllowedCriticReference` values;
- immutable internal `AllowedContradictionSide` values;
- strict Critic payload snapshot validation;
- explicit enumeration functions for each of the four artifact families;
- deterministic deduplication and exclusion of ambiguous emitted references;
- a function that produces one `RequestOutputSchema` for a role/payload pair;
- a Critic-only schema-narrowing function.

The module is not a generic schema framework. The public-to-infrastructure entry point may
dispatch Critic versus static role behavior, but all dynamic semantics remain explicitly
named for Critic.

### 5.2 Prompt definition separation

`RolePromptDefinition` continues to own:

- exact role;
- semantic instruction;
- authoritative output model;
- cached static serialized schema.

It SHALL not cache a request-specific schema. The adapter obtains the role definition, then
asks the schema builder for the one call snapshot. Static roles receive the existing schema.

### 5.3 Adapter integration

`OpenAICompatibleLLMAdapter.generate_structured` will:

1. resolve the exact role before payload serialization;
2. snapshot/serialize the payload using current safe behavior;
3. build one request output schema from the role, definition, and snapshot;
4. serialize that schema once into a separately delimited section of the user/data message;
5. reuse the same logical schema for strict provider guidance in `JSON_SCHEMA` mode;
6. retain existing modes, headers, HTTP errors, parsing, and observer behavior.

No network call occurs if schema construction fails.

### 5.4 Safe error

Add `LLMRequestSchemaError` to the existing safe adapter error family. It has one fixed
message and no payload-bearing fields. Participant/orchestrator behavior remains the existing
ordinary provider execution failure path.

## 6. Critic Payload Snapshot

The builder requires exactly:

```text
review_input
problem_analysis
solution_alternatives
risk_assessment
```

Each value is validated against its existing authoritative Pydantic domain model to reject
malformed direct adapter calls. Validation creates an isolated immutable semantic snapshot;
it does not replace or mutate participant-owned objects and is not written to Review state.

Extra top-level payload keys fail closed for Critic because an unexpected artifact could
otherwise influence the schema or conceal a port misuse.

## 7. Allowed-Reference Enumeration

Enumeration mirrors existing Critic resolution.

### 7.1 ReviewInput

- `DESCRIPTION`, `TITLE`, `REVIEW_OBJECTIVE`: current scalar when present/required;
- `REVIEW_CONSTRAINT`: each exact constraint value;
- `CONTEXT`: each exact context value;
- `STATED_FACT`: each exact stated fact value.

All are value-only references and omit `item_id`.

### 7.2 ProblemAnalysis

- `PROBLEM_OBJECTIVE`: exact objective, value-only;
- `PROBLEM_FACT`, `PROBLEM_CONSTRAINT`, `PROBLEM_ASSUMPTION`,
  `MISSING_INFORMATION`, `UNCERTAINTY`: exact text plus the actual optional ID.

If an optional ID is absent, the generated reference omits `item_id` only when its exact text
occurs once in that source collection. If the text is duplicated, the no-ID semantic target
is ambiguous and contributes no branch, even when another duplicate happens to have an ID.

### 7.3 SolutionAlternatives

- `ALTERNATIVE`: exact alternative ID and exact name value;
- `ALTERNATIVE_NAME`, `ALTERNATIVE_DESCRIPTION`, `ADVANTAGE`, `DISADVANTAGE`,
  `ALTERNATIVE_ASSUMPTION`, `IMPLEMENTATION_COMPLEXITY`: exact alternative ID and exact
  visible value;
- `GENERATION_EXPLANATION`: exact value-only explanation when notes exist;
- `BLOCKING_MISSING_INFORMATION`, `BLOCKING_UNCERTAINTY`: exact text and actual optional
  finding ID from generation notes.

The same optional-ID eligibility rule applies to generation blockers: an ID-bearing blocker
uses exact ID+text; an ID-less blocker is exposed only when text lookup is unique in its
approved blocker collection.

The catalog uses the stricter canonical ALTERNATIVE representation with exact ID and exact
name. The existing resolver accepts a missing value, but the weaker equivalent representation
does not improve target coverage and is not exposed by guidance.

### 7.4 RiskAssessment

- `RISK`: exact risk ID and exact description;
- `RISK_CATEGORY`, `RISK_DESCRIPTION`, `RISK_SEVERITY`, `MITIGATION`: exact risk ID/value;
- `RESIDUAL_UNCERTAINTY`: only when present;
- `OVERALL_OBSERVATION`: exact value-only observation.

The catalog uses the stricter canonical RISK representation with exact ID and exact
description. The weaker accepted ID-only variant is not exposed by guidance.

## 8. Duplicate and Ambiguity Policy

The catalog tracks both the emitted object and its semantic target key.

- Identical emitted object + identical target: retain one deterministic alternative.
- Identical visible value but different valid targets: retain distinct reference alternatives
  when their emitted objects differ.
- Two distinct semantic targets collapsing to the same emitted object: omit that emitted
  object completely because the current contextual validator cannot resolve it uniquely.
- Before emitted-identity normalization, each family applies the existing resolver's lookup
  eligibility: value-only and ID-less references require unique text in their lookup scope;
  ID-bearing findings require one exact ID+text match; alternative/risk IDs and nested tuple
  values use their existing owner-local uniqueness rules.
- Existing contextual uniqueness requirements remain authoritative after generation.

Catalog ordering is fixed by artifact family, kind order, tuple order, and nested field order;
it does not sort user text or depend on hash order.

## 9. Dynamic JSON Schema Strategy

### 9.1 Base schema

Start from a deep copy of `CriticalReview.model_json_schema()`. Apply the existing strict
normalization after dynamic narrowing so all object properties are required according to
the current provider contract and arrays retain `maxItems=10`.

### 9.2 Reference definition

Replace the referenced `CriticReference` definition with a `oneOf` list. Each branch is a
closed object schema containing `const` constraints for the exact fields present in one
allowed reference.

Conceptually:

```json
{
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "source": {"const": "PROBLEM_ANALYSIS"},
    "kind": {"const": "UNCERTAINTY"},
    "item_id": {"const": "UNC-004"},
    "value": {"const": "The potential performance degradation ..."}
  },
  "required": ["source", "kind", "item_id", "value"]
}
```

If a legal field is absent from that reference, it is omitted from `properties` and cannot
be generated because the branch is closed.

### 9.3 Contradiction-side definition

Replace `ContradictionSide` with a `oneOf` list where each branch contains:

- the exact closed reference schema for one catalog entry;
- `statement` constrained by `const` to its resolved visible value;
- no additional properties.

This duplicates reference alternatives inside the schema but guarantees correlation without
changing the response contract.

### 9.4 Empty catalog

The four valid artifacts always expose at least ReviewInput description/objective values.
If no allowed reference can be produced, construction fails safely rather than emitting an
unconstrained reference definition.

### 9.5 Compatibility validation

Deterministic tests validate generated schema structure. A marked live vLLM test validates
that the reference `oneOf`/`const` subset is accepted by the configured server. Universal
provider compatibility is not inferred.

### 9.6 Preserve empty and optional Critic shapes

Narrowing changes only which concrete references may be selected. It does not make any
CriticalReview collection non-empty, does not require Critic activity, and does not remove
the existing null/absent-target branch for criticism types that legitimately lack one single
target. A fully empty CriticalReview remains valid and generatable.

## 10. Trusted Instruction and Data-Message Behavior

The system message remains entirely application-controlled and contains the static role
instruction plus the authoritative static output schema. It contains no exact value derived
from ReviewInput or upstream model output.

The user/data message contains two independently delimited JSON sections:

```text
UNTRUSTED_PAYLOAD_JSON_BEGIN
serialized Critic payload
UNTRUSTED_PAYLOAD_JSON_END

UNTRUSTED_REQUEST_SCHEMA_JSON_BEGIN
request-specific serialized schema
UNTRUSTED_REQUEST_SCHEMA_JSON_END
```

Delimiter labels and the static instruction to treat both sections as data are application-
controlled. JSON serialization escapes embedded newlines, quotes, delimiter-looking text,
and prompt-injection-like content; payload-derived strings never become system content.

The serialized dynamic schema is produced once from the snapshot. `JSON_SCHEMA` provider
guidance uses an independent deep copy so it cannot mutate the data-message schema. Logical
constraints must be equivalent in both representations.

`JSON_OBJECT` and `PROMPT_ONLY` receive the same schema as untrusted request data, but the
adapter makes no decoding-enforcement claim for those modes. Existing output validation is
mandatory for every mode and remains the only trust boundary.

## 11. Error and Failure Flow

```text
invalid Critic payload / empty safe catalog / schema invariant failure
                         ↓
              LLMRequestSchemaError
                         ↓
           no HTTP call, no raw output observer
                         ↓
 existing participant/orchestrator safe execution failure mapping
                         ↓
        Critic FAILED; Coordinator PENDING; Review INCOMPLETE
```

Provider rejection of a syntactically valid dynamic schema remains an `LLMHTTPStatusError`.
Provider output violating it remains subject to existing parsing and Critic output errors.

## 12. Testing Strategy

### 12.1 Catalog unit tests

Use deterministic full/minimal fixtures to prove every source/kind/value/ID family, absent
optionals, duplicates, Unicode, escaping, immutability, and safe malformed-payload failure.

### 12.2 Schema unit tests

Assert correlated branches rather than brittle whole-document snapshots. Additionally assert
deterministic serialized equality, no free source/kind enums in the narrowed definition,
exact contradiction pairs, strict required fields, closed branches, fully empty output,
legitimate missing target reference, and maximum-fixture size.

### 12.3 Adapter request tests

Capture HTTP requests for all three modes. Prove Critic uses the dynamic snapshot, static roles
are unchanged, payload-derived values never occur in the system message, both user/data
sections remain correctly delimited/parseable, construction failure performs zero requests,
and observer behavior is unchanged.

### 12.4 Participant parity tests

For every catalog reference, build the smallest valid CriticalReview location and prove the
existing Critic resolver accepts it against the same artifacts. Add explicit regressions for
the observed invalid source/kind and paraphrase patterns.

### 12.5 Live evidence

Run at least five independent invocations with the same versioned scenario/configuration.
Preserve every result, including failure, and summarize distributions by failed stage and
failure class. Do not implement automatic retries.

## 13. Requirements Traceability

| Specification requirement | Plan coverage | Verification strategy |
|---|---|---|
| DCS-FR-001 Unchanged Port | §§3.2, 5.3 | Contract/import regression |
| DCS-FR-002 Exact Critic Activation | §§5.1–5.3 | Closed role-dispatch request tests |
| DCS-FR-003 Required Context Snapshot | §6 | Snapshot shape and no-I/O tests |
| DCS-FR-004 Canonical Existing Semantics | §§7–8 | Catalog/participant parity tests |
| DCS-FR-005 Correlated References | §§3.4, 9.2 | Branch correlation tests |
| DCS-FR-006 Exact Optionality | §§7, 9.2 | Present/absent field tests |
| DCS-FR-007 Exact Contradiction Sides | §9.3 | Reference/statement pair tests |
| DCS-FR-008 Authoritative Outer Contract | §§3.3, 9.1 | Unchanged-schema comparison |
| DCS-FR-009 One Snapshot per Call | §§5.3, 10 | Mutation and request-equivalence tests |
| DCS-FR-010 Deterministic Serialization | §§3.5, 8, 10 | Byte-equivalence tests |
| DCS-FR-011 Payload Immutability | §§3.5, 6 | Deep input-preservation tests |
| DCS-FR-012 Safe Construction Error | §§5.4, 11 | Safe message and zero-request tests |
| DCS-FR-013 No Trust Promotion | §§3.1, 11 | Invalid-provider-output regression |
| DCS-FR-014 Mode Behavior | §§5.3, 10 | Three-mode captured requests |
| DCS-FR-015 No Truncation | §§8, 9, 12.2 | Maximum-fixture size/coverage test |
| DCS-FR-016 Data Minimization | §§6–10 | Schema-content and trust-boundary inspection |
| DCS-FR-017 Observability | §§5.4, 11 | Error/log/observer tests |
| DCS-FR-018 Live Evaluation | §§9.5, 12.5 | Five recorded fixed-scenario runs |
| DCS-FR-019 Valid Inactivity/Optionality | §§9.6, 12.2 | Empty review and absent-target tests |

All current specification requirements have an explicit design location and verification
path. After specification re-approval, the data model may refine internal shapes but may not
remove or weaken any row.

## 14. File Impact

Expected additions:

- `src/agentic_review_board/infrastructure/llm/dynamic_schemas.py`;
- `tests/unit/infrastructure/llm/test_dynamic_schemas.py`;
- optional explicitly marked live compatibility test or fixture extension;
- Slice 7.1 evaluation notes in the existing local vLLM guide.

Expected modifications:

- `src/agentic_review_board/infrastructure/llm/openai_compatible.py`;
- `src/agentic_review_board/infrastructure/llm/errors.py`;
- adapter/prompt/error tests;
- infrastructure exports only if genuinely used outside the package.

Expected unchanged files:

- `application/ports.py`;
- all domain model modules;
- all five participant implementations;
- `application/orchestrator.py`;
- `domain/execution.py`;
- runtime configuration models and composition behavior.

## 15. Constitution Check

- **Role integrity:** Critic responsibility and Coordinator authority remain unchanged.
- **Structured validation:** guidance narrows output; trusted validation is preserved.
- **Traceability:** exact current references and statements are strengthened.
- **Human authority:** no action or recommendation authority changes.
- **Minimal architecture:** one focused builder addresses an observed repeated limitation;
  no framework or dependency is introduced.
- **Provider independence:** feature remains behind the existing LLM adapter boundary.
- **Deterministic testability:** the builder is pure and fully testable offline.
- **Security:** only current necessary payload values enter the schema; those values remain
  delimited untrusted data and never enter the system instruction; no new logging.
- **Incremental delivery:** one role and one failure family are addressed.

No constitutional violation or new ADR trigger is identified.

## 16. Alternatives Considered

### A. More prompt instructions

Rejected as primary solution: already attempted and repeatedly insufficient for exact
cross-field reference semantics.

### B. Relax or repair participant validation

Rejected: violates fail-closed validation and traceability.

### C. Automatic retry with validation feedback

Deferred: may improve completion rate but does not prevent invalid states and can conceal
failure frequency.

### D. Change `LLMPort` to accept a schema

Rejected for this slice: unnecessary boundary widening because the adapter already has the
role and payload required to derive the constraint.

### E. Replace reference objects with opaque tokens

Deferred/rejected for v0.1: would require response translation or domain contract changes and
reduce direct inspectability.

### F. Generic runtime rule engine

Rejected: unjustified complexity for one evidenced role-specific need.

### G. Put the payload-derived dynamic schema in the system message

Rejected: exact reference values originate in user input and upstream model output. Moving
them into a privileged system message would violate the established untrusted-data boundary,
even when JSON escaping prevents mechanical delimiter breakout. The selected design keeps
static instructions in `system`, dynamic values in delimited user/data content, and the
machine-readable constraint in `response_format` only for explicit `JSON_SCHEMA` mode.

## 17. Plan Review Gate

Before approval of this plan, confirm:

1. the reopened specification is re-approved and covered without scope expansion;
2. canonical `ALTERNATIVE` ID+name and `RISK` ID+description representations are acceptable;
3. exclusion behavior for ambiguous emitted objects and failure only when no safe
   catalog entry remains;
4. schema-size measurement is evidence, not a silent truncation mechanism;
5. empty CriticalReview and legitimate missing target references remain generatable;
6. `JSON_OBJECT` and `PROMPT_ONLY` make no enforcement promise;
7. payload-derived values remain outside the trusted system instruction;
8. optional-ID and value-only eligibility exactly matches current lookup uniqueness;
9. no new ADR or production dependency is required.

No data model SHALL be treated as approved and no implementation SHALL begin until this
`plan.md` has been reviewed and explicitly approved by the user. After approval, the data
model will be reviewed as the next independent Spec Kit gate.
