# Tasks: Context-Bound Critic Output Schema v0.1

**Specification:** `specs/007.1-dynamic-critic-schema/spec.md` — Approved  
**Plan:** `specs/007.1-dynamic-critic-schema/plan.md` — Approved  
**Data model:** `specs/007.1-dynamic-critic-schema/data-model.md` — Approved  
**Branch:** `007.1-dynamic-critic-schema`  
**Status:** Approved — second review corrections approved by the user on 2026-08-30  
**Tests:** Required; implementation SHALL proceed tests-first in small verified blocks

## Execution Rules

- Complete tasks in identifier order unless tasks are explicitly marked `[P]` inside the
  same tests-first group.
- Every production block begins with deterministic failing tests and confirmation that the
  failure is caused by the missing Slice 7.1 behavior.
- Run focused tests after each implementation task and the full deterministic suite at each
  phase checkpoint.
- Do not start the next phase until the current checkpoint has been reviewed.
- Default tests and CI require no endpoint, GPU, credential, model download, or network.
- `[P]` means safe to execute in parallel after shared prerequisites; `[TEST]` marks a test
  or verification task; `[DOC]` marks documentation; `[GATE]` marks a mandatory checkpoint.

## Phase 1: Critic Payload Snapshot and Reference Catalog

**Purpose:** Derive a deterministic complete catalog of exact legal Critic references from
one four-artifact payload without network access or mutation.

### Tests first

- [X] T001 [TEST] [US1] Create `tests/unit/infrastructure/llm/test_dynamic_schemas.py` with canonical full and minimal Critic payload fixtures built from real current domain models.
- [X] T002 [TEST] [US4] Test Critic snapshot accepts exactly `review_input`, `problem_analysis`, `solution_alternatives`, and `risk_assessment`, and rejects missing, extra, wrong-typed, malformed, non-JSON, and non-mapping values with `LLMRequestSchemaError`.
- [X] T003 [TEST] [US4] Test snapshot construction serializes the four-key payload once, validates only the detached parsed value, leaves caller/nested values unchanged after success and failure, and keeps `serialized_payload` stable after later caller mutation.
- [ ] T004 [US1] Test ReviewInput catalog coverage for DESCRIPTION, TITLE, REVIEW_OBJECTIVE, every REVIEW_CONSTRAINT, CONTEXT, and STATED_FACT; prove all omit `item_id`.
- [ ] T005 [US1] Test ProblemAnalysis coverage for PROBLEM_OBJECTIVE and exact PROBLEM_FACT, PROBLEM_CONSTRAINT, PROBLEM_ASSUMPTION, MISSING_INFORMATION, and UNCERTAINTY findings with actual present/absent optional IDs.
- [ ] T006 [US1] Test SolutionAlternatives coverage for canonical ALTERNATIVE ID+name, name, description, advantages, disadvantages, assumptions, complexity, generation explanation, and both blocker families.
- [ ] T007 [US1] Test zero alternatives/generation notes, absent assumptions, empty blocker collections, repeated characteristic values, and exact alternative-local target identities.
- [ ] T008 [US1] Test RiskAssessment coverage for canonical RISK ID+description, category, description, severity, mitigation, present residual uncertainty, and overall observations; prove absent residual uncertainty contributes no branch.
- [ ] T009 [US1] Test fixed catalog ordering across artifact families/kinds/tuple positions, exact string-form target-key indices, and byte-equivalent snapshot/schema serialization for equivalent payload mappings with different key insertion order.
- [ ] T010 [US4] Test identical emitted identity + same target deduplicates deterministically, while an indistinguishable emitted identity for different target keys is completely excluded rather than guessed; an empty normalized catalog fails closed.
- [ ] T011 [US1] Test Unicode, quotes, backslashes, newlines, JSON-looking text, and prompt-like content are retained as exact data values without interpretation or corruption.
- [ ] T012 [US1] Add explicit regression assertions that catalog entries never include `PROBLEM_ANALYSIS + STATED_FACT`, `PROBLEM_ANALYSIS + CONTEXT`, or `item_id` on value-only kinds.

### Implementation

- [ ] T013 [US4] Add `LLMRequestSchemaError` to `src/agentic_review_board/infrastructure/llm/errors.py` with fixed safe string/repr behavior and no unsafe fields.
- [ ] T014 [US4] Create `src/agentic_review_board/infrastructure/llm/dynamic_schemas.py` with frozen `CriticPayloadSnapshot`, one safe canonical serialize/strict-parse boundary, exact top-level keys, stored `serialized_payload`, and validation of the detached value through existing Pydantic domain models.
- [ ] T015 [US1] Implement frozen `AllowedCriticReference`, explicit target-key helpers, canonical emitted identity, and safe catalog normalization.
- [ ] T016 [US1] Implement explicit ReviewInput and ProblemAnalysis enumeration matching current Critic resolver semantics.
- [ ] T017 [US1] Implement explicit SolutionAlternatives enumeration, including canonical ALTERNATIVE ID+name and generation-note behavior.
- [ ] T018 [US1] Implement explicit RiskAssessment enumeration, including canonical RISK ID+description and optional residual uncertainty behavior.

**Checkpoint:** complete deterministic allowed-reference catalog passes; no JSON Schema or adapter request behavior changed.

### T001–T003 red evidence

- Focused collection fails only with the expected missing Slice 7.1 module:
  `ModuleNotFoundError: agentic_review_board.infrastructure.llm.dynamic_schemas`.
- No production module, error contract, schema construction, adapter behavior, or network
  access was added in this tests-first block.
- Ruff passes for `tests/unit/infrastructure/llm/test_dynamic_schemas.py`.

## Phase 2: Correlated Dynamic Critic Schema

**Purpose:** Narrow the authoritative CriticalReview schema so invalid reference cross-products
and contradiction paraphrases are not generatable under compatible guided decoding.

### Tests first

- [ ] T019 [US1] Test each AllowedCriticReference becomes one closed object branch whose exact present fields use `const`, whose forbidden fields are absent, and whose required list equals its properties.
- [ ] T020 [US1] Test the dynamic CriticReference definition contains exactly the normalized catalog branches and no free source/kind/item/value Cartesian-product schema.
- [ ] T021 [US2] Test one AllowedContradictionSide exists per catalog reference and always has `statement == visible_value`.
- [ ] T022 [US2] Test each ContradictionSide branch correlates one exact reference branch with one exact statement const; cross-paired and paraphrased statements match no branch.
- [ ] T023 [US1] Test schema transformation starts from `CriticalReview.model_json_schema()`, changes only the approved CriticReference and ContradictionSide definitions plus existing strict normalization, and preserves fully empty CriticalReview output, empty individual collections, nullable legitimate `target_reference`, unrelated enums, requiredness, and cardinality.
- [ ] T024 [US3] Test all four non-Critic roles bypass Critic snapshot/catalog behavior, keep current payload errors and schemas, and do not require Critic payload keys.
- [ ] T025 [US5] Test deterministic serialization: equivalent payloads produce byte-identical compact Unicode-preserving JSON text; strict parsing yields a fresh document deeply equal to the schema on every call and mutation of one parsed document cannot affect later calls.
- [ ] T026 [US4] Test missing/renamed/unexpected authoritative `$defs`, empty catalog, or internal branch invariant failure raises safe schema error with no fallback to unconstrained static Critic schema.
- [ ] T027 [US1] Test schema construction does not mutate `RolePromptDefinition`, cached serialized schema, Pydantic schema objects, catalog branches, or prior call results.
- [ ] T028 [US5] Document that ReviewInput, analysis findings, alternative characteristics, blockers, risks, and observations have no finite contract maximum; build a deterministic high-cardinality stress fixture with explicit counts, use every real bounded maximum (including three alternatives), assert the exact expected reference/side branch formulas with no truncation, and record fixture counts, byte size, and branch counts in this phase's evidence without turning the chosen stress counts into product limits.

### Implementation

- [ ] T029 [US1] Implement exact closed reference-branch construction with deep ownership and canonical property/required ordering.
- [ ] T030 [US2] Implement frozen AllowedContradictionSide and exact correlated side-branch construction.
- [ ] T031 [US1] Implement Critic schema deep-copy/narrowing with explicit expected-definition checks and no generic traversal framework.
- [ ] T032 [US3] Implement serialized-only `RequestOutputSchema` with strict fresh-document parsing and closed Critic/static role dispatch without forcing non-Critic requests through the Critic snapshot path.
- [ ] T033 [US5] Apply existing strict required/maxItems normalization to an independent final schema and deterministic serialization without mutable aliases.

**Checkpoint:** dynamic schema deterministically excludes every observed invalid pattern; adapter still unchanged.

## Phase 3: Adapter Integration and Safe Failure

**Purpose:** Use one request-specific schema snapshot consistently in the prompt and provider
request while preserving all Slice 7 modes and transport behavior.

### Tests first

- [ ] T034 [TEST] [US3] Extend `tests/unit/infrastructure/llm/test_openai_compatible.py` to prove a Critic call keeps its system message static and payload-derived-value-free, while its user/data message contains independently delimited `CriticPayloadSnapshot.serialized_payload` and dynamic-schema JSON sections; prove newline- and delimiter-looking values remain inside parsed JSON and cannot create extra boundary lines.
- [ ] T035 [US3] Test Critic `JSON_SCHEMA` parses the exact dynamic-schema text from the user/data section to a document deeply equal to `response_format.json_schema.schema`, while retaining name `critic_output`, strict flag, configured sampling fields, and one HTTP request.
- [ ] T036 [US3] Test Critic `JSON_OBJECT` carries the dynamic schema only in untrusted user/data content and keeps exact `{type: json_object}` response format without claiming schema enforcement.
- [ ] T037 [US3] Test Critic `PROMPT_ONLY` carries the dynamic schema only in untrusted user/data content and omits response format without claiming schema enforcement.
- [ ] T038 [US3] Test Analyst, Solution Architect, Risk Reviewer, and Coordinator request bodies remain equivalent to Slice 7 behavior in all applicable modes.
- [ ] T039 [US4] Test malformed Critic payload raises `LLMRequestSchemaError` before credential/header access, client invocation, and output observer invocation; non-Critic serialization failures retain `LLMPayloadSerializationError`.
- [ ] T040 [US4] Test safe schema error string/repr and orchestrator mapping contain no payload text, exact reference values, schema fragments, endpoint details, credentials, or chained validation text.
- [ ] T041 [US3] Test successful parsing and output observer still receive only the provider's parsed mapping; dynamic schema does not mark it trusted or alter returned content.
- [ ] T042 [US3] Test provider ignoring guidance and returning an invalid Critic mapping still reaches unchanged participant structural/contextual rejection and fail-closed stage behavior.

### Implementation

- [ ] T043 [US3] Refactor adapter request construction after exact role resolution so Critic creates one detached `CriticPayloadSnapshot`, uses its stored payload text, and derives exactly one `RequestOutputSchema` from its four semantic artifacts; preserve the existing non-Critic path.
- [ ] T044 [US3] Keep the trusted system message on the unchanged static role instruction/schema and append the serialized dynamic schema only inside the new delimited Critic user/data section for every mode.
- [ ] T045 [US3] Parse a fresh independent document from the same `RequestOutputSchema.serialized` for Critic `JSON_SCHEMA` provider guidance; preserve `JSON_OBJECT`/`PROMPT_ONLY` behavior and prevent mutable aliases.
- [ ] T046 [US4] Preserve existing HTTP/parsing/observer behavior and ensure schema failures occur before all network/output side effects.

**Checkpoint:** captured adapter requests prove one-snapshot dynamic Critic guidance; all other roles/modes regress unchanged.

## Phase 4: Parity With Trusted Critic Validation

**Purpose:** Prove schema guidance matches rather than redefines the current trusted boundary.

### Tests first

- [ ] T047 [US1] Add parameterized parity tests showing every ReviewInput catalog reference resolves through current Critic contextual validation against the same artifacts.
- [ ] T048 [US1] Add parity tests for every ProblemAnalysis reference family, including present/absent optional IDs and duplicate-text ambiguity behavior.
- [ ] T049 [US1] Add parity tests for every SolutionAlternatives reference family, canonical ALTERNATIVE value, tuple characteristics, generation notes, and blockers.
- [ ] T050 [US1] Add parity tests for every RiskAssessment reference family, canonical RISK value, optional residual uncertainty, and observations.
- [ ] T051 [US2] Add parity tests showing every generated contradiction side passes exact statement resolution and all observed paraphrases fail existing participant validation.
- [ ] T052 [US1] Add a checked-in deterministic regression fixture derived from the 2026-08-29 scenario, containing the four matching upstream artifacts and offending Critic mapping without depending on ignored local artifacts; prove its illegal references match no dynamic branches while participant rejection remains unchanged.
- [ ] T053 [US3] Run existing Critic domain/participant/orchestration tests unchanged to prove no trusted contract, lifecycle, or failure-message change.

### Implementation

- [ ] T054 [US1] Make only parity-driven corrections to explicit catalog enumeration; do not alter participant/domain validation to make generated branches pass.

**Checkpoint:** every allowed dynamic reference is accepted by trusted validation; the known rejected output remains rejected.

## Phase 5: Live Compatibility and Evaluation

**Purpose:** Verify the selected JSON Schema subset on local vLLM and collect honest completion
evidence without adding runtime retries.

- [ ] T055 [US5] Add or extend an explicitly marked live test that obtains a minimal schema through the real Slice 7.1 Critic builder/adapter path—not a hand-written substitute—and checks only provider acceptance and direct JSON-object parsing with no retry.
- [ ] T056 [US5] Update `docs/vllm-local-docker-guide.md` with Slice 7.1 activation, diagnostic commands, schema-compatibility expectations, and result-recording format.
- [ ] T057 [US5] Execute the opt-in live smoke against `config/llm.vllm.json`; record model, vLLM image, GPU, context, result, and elapsed time.
- [ ] T058 [US5] Execute exactly five independently invoked fixed-scenario full reviews with temperature 0/seed 0, unique run-numbered output paths, and no automatic retry, overwrite, rerun substitution, or selective deletion; retain trusted aggregates and opt-in raw outputs under ignored `artifacts/`.
- [ ] T059 [DOC] [US5] Create `specs/007.1-dynamic-critic-schema/live-evaluation.md` with the command/config/model/vLLM-image/GPU context and one row for every run number, summarizing completed/failed stage, safe error family, Critic completion, Coordinator completion, elapsed time, and recurrence of prevented source/kind/paraphrase patterns; reference ignored artifact paths without copying payload/schema/raw-output contents into the document.
- [ ] T060 [US5] If vLLM rejects the `oneOf`/`const` schema itself, record the provider limitation and stop; do not silently weaken, retry another mode, or mark Slice 7.1 successful.

**Checkpoint:** local evidence is recorded honestly; one successful run is not treated as reliability proof.

## Phase 6: Cross-Cutting Verification

- [ ] T061 Run full deterministic `python -m pytest` with no live endpoint requirement.
- [ ] T062 Run `python -m ruff check .` without weakening repository rules.
- [ ] T063 Run strict `python -m mypy` for internal immutable values, JSON mappings, exhaustive role/reference dispatch, and tests without adding ignores solely for convenience.
- [ ] T064 Run `python -m pip check` and confirm no production dependency change.
- [ ] T065 Inspect production imports and `pyproject.toml` for no provider SDK, retry/fallback, router, generic schema/rules framework, persistence, RAG, tools, UI, or domain-facing provider types.
- [ ] T066 Review error paths for no prompt, payload, dynamic schema, exact sensitive values, endpoint details, or credentials in public errors/default logs.
- [ ] T067 Review implementation against Slice 7.1 artifacts, Slice 5 Critic contracts, Slice 7 adapter contracts, canonical docs, Constitution 1.1.0, ADR-0001, and ADR-0002.
- [ ] T068 Confirm `LLMPort`, domain models, participant signatures/validation, orchestration, Review lifecycle, configuration format, and non-Critic role request semantics remain unchanged.

## Dependencies and Gate

```text
Payload snapshot + catalog (T001–T018)
                ↓
Dynamic correlated schema (T019–T033)
                ↓
Adapter integration (T034–T046)
                ↓
Trusted-validator parity (T047–T054)
                ↓
Live evidence (T055–T060)
                ↓
Cross-cutting verification (T061–T068)
```

No production task begins before its corresponding tests exist and fail for the expected
missing behavior. Live tasks begin only after deterministic parity and adapter tests pass.

Do not implement retries, fallback, schema repair, output repair, participant/domain
relaxation, dynamic schemas for other roles, generic rule engines, UI, persistence, or model
routing as part of any task above.

Only after all four Slice 7.1 artifacts are reviewed and explicitly approved may
implementation begin.
