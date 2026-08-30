# Data Model: Context-Bound Critic Output Schema v0.1

**Branch:** `007.1-dynamic-critic-schema`  
**Specification:** `specs/007.1-dynamic-critic-schema/spec.md` — Approved  
**Plan:** `specs/007.1-dynamic-critic-schema/plan.md` — Approved  
**Status:** Approved — second review corrections approved by the user on 2026-08-30

## 1. Purpose

Define the exact internal values, invariants, lookup eligibility, JSON representations, and
trust-boundary behavior required to build one context-bound Critic schema from one current
four-artifact payload.

These are infrastructure request-construction models. They are not new Review domain
entities, do not change `LLMPort`, and never promote provider output into trusted state.

## 2. Boundary Overview

```text
LLMPort role + Mapping[str, object]
                 ↓ exact Critic dispatch
          CriticPayloadSnapshot
                 ↓ explicit enumeration + resolver-equivalent eligibility
       tuple[AllowedCriticReference, ...]
                 ↓ exact visible-value pairing
       tuple[AllowedContradictionSide, ...]
                 ↓ narrow authoritative CriticalReview schema
          RequestOutputSchema
             ↙                 ↘
serialized JSON in           fresh parsed document in
delimited user/data          JSON_SCHEMA response_format
             ↘                 ↙
             provider response remains untrusted
                            ↓
        existing CriticalReview + contextual validation
```

The system message remains application-controlled and contains no payload-derived exact
value. The dynamic schema is untrusted request data even though the application constructs
it deterministically.

## 3. Model Inventory

### 3.1 New internal immutable values

| Model | Representation | Purpose |
|---|---|---|
| `CriticPayloadSnapshot` | frozen dataclass | Validated four-artifact semantic snapshot |
| `AllowedCriticReference` | frozen dataclass | One canonical legal reference and its resolution metadata |
| `AllowedContradictionSide` | frozen dataclass | One legal reference paired with its exact visible statement |
| `RequestOutputSchema` | frozen dataclass containing only `str` | Canonical immutable dynamic schema serialization |

### 3.2 New safe error

| Error | Base | Exact public message |
|---|---|---|
| `LLMRequestSchemaError` | `LLMAdapterError` | `LLM request schema construction failed` |

### 3.3 New wire delimiters

```text
UNTRUSTED_REQUEST_SCHEMA_JSON_BEGIN
UNTRUSTED_REQUEST_SCHEMA_JSON_END
```

They complement the existing payload delimiters. They are application constants, not
configuration and not model-generated values.

### 3.4 Existing models reused unchanged

- `ReviewInput`
- `ProblemAnalysis`
- `SolutionAlternatives`
- `RiskAssessment`
- `CriticalReview`
- `CriticReference`
- `CriticReferenceSource`
- `CriticReferenceKind`
- `RolePromptDefinition`
- `StructuredOutputMode`
- `OpenAICompatibleLLMAdapter`

## 4. `CriticPayloadSnapshot`

### 4.1 Shape

```python
@dataclass(frozen=True, slots=True)
class CriticPayloadSnapshot:
    serialized_payload: str
    review_input: ReviewInput
    problem_analysis: ProblemAnalysis
    solution_alternatives: SolutionAlternatives
    risk_assessment: RiskAssessment
```

### 4.2 Construction input

The source must be a `Mapping[str, object]` containing exactly:

```text
review_input
problem_analysis
solution_alternatives
risk_assessment
```

No aliases, case folding, whitespace normalization, missing keys, or extra keys are accepted.

Snapshot construction first copies the four top-level entries into a newly owned dictionary
and serializes that dictionary exactly once with the existing safe canonical payload settings:

```python
json.dumps(
    owned_top_level,
    allow_nan=False,
    ensure_ascii=False,
    separators=(",", ":"),
    sort_keys=True,
)
```

It then parses that exact serialized text with non-JSON constants rejected. The parsed,
detached object—not the caller's mapping—is the only input to the four Pydantic validations.
`serialized_payload` retains the same immutable text for the Critic user/data message. Thus
the provider-visible payload and the semantic artifacts used to build the catalog describe
one logical snapshot even if the caller mutates its objects after construction.

### 4.3 Validation

Each value from the detached parsed object is validated independently through its existing
authoritative Pydantic model. Validation yields frozen domain value copies suitable for
deterministic enumeration.

Any mapping access failure, missing/extra key, serialization/parsing failure, wrong type,
Pydantic validation failure, or unexpected snapshot-construction failure becomes
`LLMRequestSchemaError` through safe exception chaining. The pre-existing
`LLMPayloadSerializationError` path remains unchanged for non-Critic roles.

### 4.4 Invariants

1. The source mapping and every nested source object remain unchanged.
2. `serialized_payload` and all four semantic artifacts originate from the same detached
   serialized value; neither is rebuilt from the caller's mapping later in the call.
3. Snapshot creation performs no HTTP, filesystem, environment, clock, randomness, or global
   Review-state access.
4. Snapshot equality is value equality; it does not claim same-execution identity.
5. The snapshot is local to one adapter call and is never stored in Review.
6. Participant-owned trusted artifacts remain authoritative; this copy exists only to guide
   an untrusted provider request.

## 5. `AllowedCriticReference`

### 5.1 Shape

```python
@dataclass(frozen=True, slots=True)
class AllowedCriticReference:
    source: CriticReferenceSource
    kind: CriticReferenceKind
    item_id: str | None
    value: str | None
    visible_value: str
    target_key: tuple[str, ...]
```

### 5.2 Field semantics

- `source`, `kind`, `item_id`, `value` are the exact fields offered to provider output.
- `visible_value` is the exact string returned by the current Critic resolver and required
  for a contradiction side's `statement`.
- `target_key` is a private semantic identity used for ambiguity and parity checks. It never
  appears in payloads, prompts, schemas, output, errors, or logs.

### 5.3 Intrinsic invariants

1. The four emitted fields form a valid current `CriticReference` shape.
2. `visible_value` is non-empty.
3. `target_key` is a non-empty tuple of non-empty application constants/identifiers.
4. Value-only references omit `item_id` and contain exact `value`.
5. Optional-ID finding references include the actual ID when present; they omit it only when
   absent and text lookup is unique in the approved collection.
6. Nested alternative/risk references include the exact owner ID and exact visible value.
7. No field is normalized, stripped, case-folded, paraphrased, or repaired.

### 5.4 Canonical choices

The current domain accepts weaker variants for two ID-primary kinds. Guidance exposes only:

```text
ALTERNATIVE → item_id=alternative.id, value=alternative.name
RISK        → item_id=risk.id,        value=risk.description
```

Both use the included value as `visible_value`. ID-only variants remain valid at the trusted
boundary but are intentionally absent from guidance because they add no semantic target.

### 5.5 Emitted identity

```python
tuple[
    CriticReferenceSource,
    CriticReferenceKind,
    str | None,
    str | None,
]
```

Conceptually:

```text
(source, kind, item_id, value)
```

This identity is distinct from `target_key`: one describes provider-visible JSON; the other
describes the current artifact position it must resolve to.

### 5.6 Wire-object projection

`as_wire_object()` returns a fresh dictionary on every call:

```json
{
  "source": "SOLUTION_ALTERNATIVES",
  "kind": "DISADVANTAGE",
  "item_id": "ALT-001",
  "value": "Potential performance issues on ARM64 (UNC-004)"
}
```

Forbidden/absent fields are omitted rather than serialized as `null`. The returned dictionary
is never stored inside the frozen value.

## 6. Resolver-Equivalent Eligibility

Eligibility is decided before emitted-identity normalization. It mirrors the existing
contextual lookup rules exactly.

### 6.1 Exact scalar

For DESCRIPTION, TITLE, REVIEW_OBJECTIVE, PROBLEM_OBJECTIVE, GENERATION_EXPLANATION, and
scalar risk fields:

- include when the current value exists and is non-empty under the trusted model;
- omit when the current optional value is `None`;
- use the exact scalar as `value` and `visible_value`.

### 6.2 Value-only tuple lookup

For REVIEW_CONSTRAINT, CONTEXT, STATED_FACT, ADVANTAGE, DISADVANTAGE,
ALTERNATIVE_ASSUMPTION, and OVERALL_OBSERVATION:

- count exact equal strings inside the same collection used by the current resolver;
- include a value only when the count is exactly one;
- omit every occurrence when the count is zero or greater than one;
- retain the source tuple index in `target_key` only.

Existing domain validation already prohibits duplicates in several collections, but the
schema builder still applies the resolver-equivalent rule rather than assuming it.

### 6.3 Optional-ID finding lookup

For PROBLEM_FACT, PROBLEM_CONSTRAINT, PROBLEM_ASSUMPTION, MISSING_INFORMATION, UNCERTAINTY,
BLOCKING_MISSING_INFORMATION, and BLOCKING_UNCERTAINTY:

- if `item_id` exists, include only when exactly one finding in the lookup collection has
  both that ID and exact text;
- if `item_id` is absent, include only when exactly one finding in the lookup collection has
  that exact text;
- an ID-less finding is excluded when its text is duplicated, even if another duplicate has
  an ID and therefore emits a different wire object;
- the actual ID is never invented from a neighboring or upstream finding.

### 6.4 ID-primary owner lookup

ALTERNATIVE and RISK require exactly one current owner with the selected ID. Existing trusted
aggregate contracts normally guarantee owner-ID uniqueness; construction still fails safely
if its validated snapshot cannot uphold the required lookup.

### 6.5 Nested owner-local lookup

Alternative tuple characteristics use exact text uniqueness inside the selected alternative,
not across all alternatives. Identical text in two different alternatives remains resolvable
because owner IDs differ. Duplicate text inside one alternative contributes no branch.

## 7. Explicit Catalog Enumeration

### 7.1 Output

```python
tuple[AllowedCriticReference, ...]
```

### 7.2 ReviewInput family

Fixed kind order:

1. DESCRIPTION when present (required by current model);
2. TITLE when present;
3. REVIEW_OBJECTIVE when present;
4. REVIEW_CONSTRAINT in tuple order and unique-value eligibility;
5. CONTEXT in tuple order and unique-value eligibility;
6. STATED_FACT in tuple order and unique-value eligibility.

All are value-only and omit `item_id`.

### 7.3 ProblemAnalysis family

Fixed kind order:

1. PROBLEM_OBJECTIVE;
2. PROBLEM_FACT;
3. PROBLEM_CONSTRAINT;
4. PROBLEM_ASSUMPTION;
5. MISSING_INFORMATION;
6. UNCERTAINTY.

Finding collections retain tuple order and follow optional-ID eligibility.

### 7.4 SolutionAlternatives family

Fixed kind order:

1. ALTERNATIVE, by alternative tuple order;
2. ALTERNATIVE_NAME;
3. ALTERNATIVE_DESCRIPTION;
4. ADVANTAGE, by alternative then value tuple order;
5. DISADVANTAGE, by alternative then value tuple order;
6. ALTERNATIVE_ASSUMPTION, by alternative then value tuple order;
7. IMPLEMENTATION_COMPLEXITY;
8. GENERATION_EXPLANATION when generation notes exist;
9. BLOCKING_MISSING_INFORMATION;
10. BLOCKING_UNCERTAINTY.

Generation blocker collections follow optional-ID eligibility in their own approved
collection. They are not re-resolved against ProblemAnalysis during schema construction.

### 7.5 RiskAssessment family

Fixed kind order:

1. RISK, by risk tuple order;
2. RISK_CATEGORY when present;
3. RISK_DESCRIPTION;
4. RISK_SEVERITY;
5. MITIGATION when present;
6. RESIDUAL_UNCERTAINTY when present;
7. OVERALL_OBSERVATION by tuple order and unique-value eligibility.

### 7.6 Global catalog order

```text
ReviewInput
→ ProblemAnalysis
→ SolutionAlternatives
→ RiskAssessment
```

No sorting by user text, locale, object hash, or dictionary iteration is allowed.

## 8. Catalog Normalization and Ambiguity

Normalization processes eligible candidates in deterministic order.

1. Group candidates by emitted identity.
2. If every candidate in a group has the same `target_key`, retain the first.
3. If a group contains different `target_key` values, retain none from that group.
4. Preserve relative order of retained first candidates.
5. Do not renumber IDs or synthesize a distinguishing field.
6. If no reference remains, raise `LLMRequestSchemaError`.

Different emitted identities may share `visible_value` and remain legal when the existing
resolver distinguishes them by source, kind, owner ID, or finding ID.

## 9. Target Keys

Target keys are explicit private tuples, not a generic path language.

| Family | Target key |
|---|---|
| ReviewInput scalar | `("REVIEW_INPUT", kind)` |
| ReviewInput tuple value | `("REVIEW_INPUT", kind, str(index))` |
| Problem objective | `("PROBLEM_ANALYSIS", kind)` |
| Problem finding | `("PROBLEM_ANALYSIS", kind, str(index))` |
| Alternative scalar | `("SOLUTION_ALTERNATIVES", kind, alternative_id)` |
| Alternative tuple value | `("SOLUTION_ALTERNATIVES", kind, alternative_id, str(index))` |
| Generation explanation | `("SOLUTION_ALTERNATIVES", kind)` |
| Generation blocker | `("SOLUTION_ALTERNATIVES", kind, str(index))` |
| Risk scalar | `("RISK_ASSESSMENT", kind, risk_id)` |
| Overall observation | `("RISK_ASSESSMENT", kind, str(index))` |

No public resolver, reflection path, JSONPath, arbitrary tuple consumer, or cross-stage
reference framework is introduced.

Every `kind` component is `kind.value`, and every positional index is converted with
`str(index)`, matching the existing `_ResolvedReference.target_key` representation exactly.

## 10. `AllowedContradictionSide`

### 10.1 Shape

```python
@dataclass(frozen=True, slots=True)
class AllowedContradictionSide:
    reference: AllowedCriticReference
    statement: str
```

### 10.2 Invariants

1. `statement == reference.visible_value`.
2. Statement is non-empty.
3. One side is produced per normalized allowed reference.
4. Side order equals catalog order.
5. No side allows a statement from another reference.

## 11. Exact JSON Schema Branches

### 11.1 Reference branch

Each allowed reference produces one fresh closed object schema:

```json
{
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "source": {"const": "PROBLEM_ANALYSIS"},
    "kind": {"const": "UNCERTAINTY"},
    "item_id": {"const": "UNC-004"},
    "value": {"const": "The potential performance degradation on ARM64 devices."}
  },
  "required": ["source", "kind", "item_id", "value"]
}
```

Property and required order is exactly `source`, `kind`, `item_id`, `value`, omitting absent
fields. A branch contains no `enum`, `default`, nullable alternative, or unconstrained string.

### 11.2 Contradiction-side branch

```json
{
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "reference": {"...": "fresh exact reference branch"},
    "statement": {"const": "The exact visible value"}
  },
  "required": ["reference", "statement"]
}
```

### 11.3 Ownership

Every branch-construction call returns newly owned dictionaries/lists. No branch object is
shared between the catalog, contradiction definitions, static schemas, prior calls, or
provider request bodies.

## 12. Dynamic CriticalReview Schema Transformation

### 12.1 Authoritative input

Start from a fresh deep copy of:

```python
CriticalReview.model_json_schema()
```

### 12.2 Required definitions

The document must contain exactly addressable `$defs` entries for `CriticReference` and
`ContradictionSide`. Missing, wrong-typed, or structurally unexpected entries raise
`LLMRequestSchemaError`. There is no fallback to the unconstrained static Critic schema.

### 12.3 Narrowing

- Replace `CriticReference` with one `oneOf` branch per normalized reference.
- Replace `ContradictionSide` with one `oneOf` branch per allowed side.
- Preserve every unrelated definition and outer field.
- Preserve the nullable `target_reference` route already present in `Criticism`.
- Preserve empty arrays for all five CriticalReview collections.
- Preserve current array maxima and closed-object behavior.
- Do not add `minItems` or any condition that forces Critic activity.

### 12.4 Strict normalization

After narrowing, apply current Slice 7 strict normalization exactly once to the complete
dynamic document:

- every object's declared properties become required for provider compatibility;
- every array receives current `maxItems=10` behavior;
- nullable fields retain their explicit null schema branch;
- branches omit forbidden optional properties rather than declaring them nullable.

The resulting strict narrowed document is the single logical dynamic schema.

## 13. `RequestOutputSchema`

### 13.1 Shape

```python
@dataclass(frozen=True, slots=True)
class RequestOutputSchema:
    serialized: str
```

The class deliberately stores no mutable mapping.

### 13.2 Construction

`serialized` is created from the strict narrowed document using:

```python
json.dumps(
    document,
    allow_nan=False,
    ensure_ascii=False,
    separators=(",", ":"),
    sort_keys=True,
)
```

Construction verifies that parsing the string yields a JSON object. Serialization failure,
non-JSON constants, or a non-object result becomes `LLMRequestSchemaError`.

### 13.3 Provider document

```python
def new_document(self) -> dict[str, object]:
    ...
```

`new_document()` parses `serialized` with strict JSON constant rejection and returns a newly
owned dictionary every time. It never returns an internal cache or shared mutable alias.

### 13.4 Invariants

1. `serialized` is non-empty deterministic JSON text.
2. Equivalent semantic snapshots yield byte-identical strings.
3. `new_document()` is deeply equal on repeated calls but never identical by object identity.
4. Mutating one returned document cannot affect `serialized`, later calls, system content,
   user/data content, or another adapter invocation.
5. `repr` contains the schema text because the value is infrastructure-internal; production
   code SHALL NOT log/repr it. Safe public errors never retain this object.

## 14. Closed Role Dispatch

Conceptual interface:

```python
def build_request_output_schema(
    *,
    definition: RolePromptDefinition,
    payload: Mapping[str, object],
) -> RequestOutputSchema:
    ...
```

Rules:

- exact Critic role creates one `CriticPayloadSnapshot`, builds the dynamic strict schema
  from its semantic artifacts, and uses its `serialized_payload` in the request;
- the other four exact supported roles bypass Critic snapshot/catalog construction and
  reproduce their existing payload serialization and static schema behavior;
- unknown roles fail earlier through `get_role_prompt_definition`;
- no registry, plugin, reflection dispatch, or model/provider branch is added.

For non-Critic roles, the implementation may use a `RequestOutputSchema` internally only if
doing so preserves their current strict provider document exactly. Its value is never added
to their user/data message and never replaces `RolePromptDefinition.serialized_schema` in
their system message. No common abstraction is required merely to force both paths through
the same value object.

## 15. Trusted System and Untrusted Data Wire Model

### 15.1 System message

The system message remains:

```text
static role semantic instruction
static authoritative output schema
static instance-not-schema instruction
```

It contains no value derived from the current payload or dynamic catalog.

### 15.2 Critic user/data message

```text
UNTRUSTED_PAYLOAD_JSON_BEGIN
<CriticPayloadSnapshot.serialized_payload>
UNTRUSTED_PAYLOAD_JSON_END

UNTRUSTED_REQUEST_SCHEMA_JSON_BEGIN
<RequestOutputSchema.serialized>
UNTRUSTED_REQUEST_SCHEMA_JSON_END
```

The dynamic-schema section is added only for exact Critic role. Non-Critic messages remain
byte-equivalent to Slice 7 behavior.

Both Critic sections come from the same request-local snapshot: the payload section uses its
stored serialized text and the schema section is derived only from its validated semantic
artifacts. Request construction never re-reads the caller's Critic mapping after snapshot
creation.

### 15.3 Delimiter safety

Both section contents are JSON serialized before concatenation. Embedded newline, quote,
backslash, delimiter-looking, Markdown, XML, or instruction-like source text remains escaped
inside a JSON string and cannot create a new delimiter line mechanically.

The model may still semantically react to malicious content; therefore both sections remain
explicitly untrusted and participant validation remains mandatory.

### 15.4 Mode matrix

| Mode | System | User/data | `response_format` |
|---|---|---|---|
| `JSON_SCHEMA` | static only | payload + dynamic schema | fresh `new_document()` strict schema |
| `JSON_OBJECT` | static only | payload + dynamic schema | `{ "type": "json_object" }` |
| `PROMPT_ONLY` | static only | payload + dynamic schema | absent |

No fallback, probing, repair, or automatic mode change occurs.

## 16. Error Model

```python
class LLMRequestSchemaError(LLMAdapterError):
    message = "LLM request schema construction failed"
```

### 16.1 Safe representation

- exact fixed `str(error)`;
- inherited fixed-message behavior;
- no payload, schema, catalog, role content, endpoint, profile, model, credential, or nested
  validation detail stored in public fields;
- chained cause permitted for local debugging but never intentionally logged or surfaced.

### 16.2 Failure timing

The error occurs before:

- authorization-header construction;
- HTTP request;
- provider response parsing;
- output observer invocation;
- any trusted participant output.

Existing orchestrator behavior maps it through the current safe ordinary execution-failure
path. No Review error enum or lifecycle change is introduced.

## 17. State and Concurrency

No mutable schema/catalog/snapshot state is stored on `OpenAICompatibleLLMAdapter`.
Everything is local to one synchronous `generate_structured` call. Existing adapter reuse
across participants and Reviews is unchanged.

This slice does not add async execution or claim thread-safety beyond existing HTTPX client
and immutable adapter behavior.

## 18. Validation Examples

### 18.1 Canonical ReviewInput stated fact

```json
{
  "source": "REVIEW_INPUT",
  "kind": "STATED_FACT",
  "value": "WPF on .NET 8 can run on Windows ARM64."
}
```

### 18.2 Canonical ProblemAnalysis fact

```json
{
  "source": "PROBLEM_ANALYSIS",
  "kind": "PROBLEM_FACT",
  "item_id": "FACT-001",
  "value": "WPF on .NET 8 can run on Windows ARM64."
}
```

### 18.3 Forbidden cross-product

```json
{
  "source": "PROBLEM_ANALYSIS",
  "kind": "STATED_FACT",
  "item_id": "FACT-001",
  "value": "WPF on .NET 8 can run on Windows ARM64."
}
```

No reference branch represents it.

### 18.4 ID-less duplicate exclusion

```text
UNCERTAINTY[0]: id=None,    text="same uncertainty"
UNCERTAINTY[1]: id=UNC-002, text="same uncertainty"
```

The first contributes no branch because text-only lookup is ambiguous. The second may
contribute its exact ID+text branch because that lookup is unique.

### 18.5 Exact contradiction side

```json
{
  "reference": {
    "source": "REVIEW_INPUT",
    "kind": "CONTEXT",
    "value": "The current application is built with WPF and .NET Framework 4.8."
  },
  "statement": "The current application is built with WPF and .NET Framework 4.8."
}
```

A paraphrased statement has no branch.

### 18.6 Empty CriticalReview

```json
{
  "criticisms": [],
  "validated_points": [],
  "missing_alternatives": [],
  "contradictions": [],
  "unresolved_issues": []
}
```

It remains valid and generatable even when the catalog contains references.

## 19. Security and Privacy Invariants

1. Payload-derived values appear only in the existing untrusted payload, the new delimited
   untrusted dynamic-schema section, and explicit `JSON_SCHEMA` request configuration.
2. No payload-derived value appears in system/developer messages.
3. Dynamic schemas are not logged, persisted, or included in safe errors by default.
4. Credentials, endpoint values, environment variables, and previous Review data do not
   participate in schema generation.
5. Diagnostic raw output remains opt-in, untrusted, ignored by Git, and outside this model.
6. Schema guidance does not grant tools, actions, routing, fallback, or trust.

## 20. Requirement Coverage

| Requirement group | Data-model sections |
|---|---|
| DCS-FR-001–003 | §§4, 14 |
| DCS-FR-004–006 | §§5–9 |
| DCS-FR-007 | §§10–12 |
| DCS-FR-008–010 | §§12–15 |
| DCS-FR-011–012 | §§4, 13, 16 |
| DCS-FR-013–014 | §§12, 15–17 |
| DCS-FR-015–017 | §§7–8, 12–13, 19 |
| DCS-FR-018 | live evidence belongs to plan/tasks; no persistent domain model added |
| DCS-FR-019 | §§12.3, 15.4, 18.6 |

## 21. Decisions Fixed by This Data Model

1. `ALTERNATIVE` guidance always uses exact ID+name.
2. `RISK` guidance always uses exact ID+description.
3. ID-less findings require unique text even when an ID-bearing duplicate exists.
4. Ambiguous emitted identities are entirely excluded; empty normalized catalog fails.
5. The strict narrowed schema is canonicalized as immutable serialized JSON only.
6. Provider documents are newly parsed copies; no mutable document is stored.
7. Dynamic schema text remains in the user/data boundary, never `system`.
8. Payload validation requires exactly four Critic keys.
9. No reference/schema truncation is allowed.
10. Empty Critic output and legitimate null target-reference shapes remain available.

## 22. Data-Model Review Gate

Before approval, confirm:

1. internal values do not become Review/domain contracts;
2. optional-ID eligibility exactly matches `_require_unique_finding`;
3. value-only and nested eligibility exactly match `_require_unique_text`;
4. canonical ALTERNATIVE/RISK forms remain accepted by current resolution;
5. target keys are private explicit identities, not a generic reference framework;
6. serialized-only RequestOutputSchema provides sufficient immutability;
7. one detached Critic snapshot supplies both the serialized payload and schema semantics;
8. dynamic values remain outside the trusted system message;
9. strict narrowing preserves nullable target references and fully empty output;
10. error timing/representation remains safe;
11. non-Critic payload, prompt, and provider-schema behavior remains unchanged;
12. no new dependency, ADR, lifecycle behavior, retry, fallback, or repair is introduced.

No `tasks.md` SHALL be treated as approved and no implementation SHALL begin until this
`data-model.md` has been reviewed and explicitly approved by the user. After approval,
`tasks.md` will be reviewed as the next independent Spec Kit gate.
