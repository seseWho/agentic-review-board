# Tasks: Context-Bound Risk Reviewer Output Schema v0.1

**Specification:** `specs/007.2-dynamic-risk-reviewer-schema/spec.md` — Approved  
**Plan:** `specs/007.2-dynamic-risk-reviewer-schema/plan.md` — Approved  
**Data model:** `specs/007.2-dynamic-risk-reviewer-schema/data-model.md` — Approved  
**Branch:** `007.2-dynamic-risk-reviewer-schema`  
**Status:** Approved — reviewed and approved by the user on 2026-08-30  
**Tests:** Required; implementation SHALL proceed tests-first in small verified blocks

## Execution Rules

- Complete tasks in identifier order unless tasks are explicitly marked `[P]` inside the
  same tests-first group.
- Each production block starts only after its focused deterministic tests have been added,
  run, and confirmed red for the missing Slice 7.2 behavior rather than an unrelated
  baseline defect.
- Record concise red/green evidence beneath the applicable phase checkpoint while
  implementing; do not mark a task complete merely because code was written.
- Run focused tests after every implementation task and the full deterministic suite at
  every phase checkpoint.
- Stop at each checkpoint for review before starting the next phase.
- Default tests and CI require no endpoint, GPU, credential, model download, or network.
- `[P]` means independent after the stated shared prerequisites, `[TEST]` marks tests or
  verification, `[DOC]` marks documentation, and `[GATE]` marks a mandatory checkpoint.
- Live tasks require explicit opt-in and begin only after deterministic parity passes.

## Phase 1: Risk Reviewer Snapshot and Exact Basis Catalog

**Purpose:** Derive one complete, deterministic catalog of canonical Risk Reviewer basis
references from one detached three-artifact payload without network access or mutation.

### Tests first

- [X] T001 [TEST] [US1] Create `tests/unit/infrastructure/llm/test_dynamic_risk_schemas.py` with minimal, full, duplicate-heavy, zero-alternative, and malformed Risk Reviewer payload fixtures built from current domain-compatible values.
- [X] T002 [TEST] [US4] Test `RiskReviewerPayloadSnapshot` accepts exactly `review_input`, `problem_analysis`, and `solution_alternatives`, while missing, extra, malformed, wrong-typed, non-mapping, non-JSON, and contract-invalid values raise fixed-safe `LLMRequestSchemaError`.
- [X] T003 [TEST] [US3] Test snapshot construction serializes once, validates only the detached parsed value, preserves caller and nested values after success/failure, retains stable `serialized_payload` after caller mutation, and performs no I/O.
- [X] T004 [TEST] [US3] Extend `tests/unit/infrastructure/llm/test_dynamic_schemas.py` with Critic regressions proving shared exact-payload detachment leaves its four-key validation, canonical serialized bytes, safe failures, and mutation isolation unchanged.
- [X] T005 [TEST] [P] [US1] Test ReviewInput catalog coverage for exact `description`, present `title`/`objective`, and every eligible `constraints`, `context`, and `stated_facts` value with exact lowercase `field` and `source=REVIEW_INPUT`.
- [X] T006 [TEST] [P] [US1] Test absent/blank optional ReviewInput scalars, blank collection values, owner-field duplicate text, and equal text across different fields follow the approved inclusion/exclusion rules without normalization.
- [X] T007 [TEST] [P] [US1] Test Problem Analysis coverage and fixed order for exact `FACT`, `CONSTRAINT`, `ASSUMPTION`, `MISSING_INFORMATION`, and `UNCERTAINTY` findings with canonical present/absent IDs.
- [X] T008 [TEST] [P] [US1] Test ID-less duplicate text, ID-bearing duplicate text, equal text across kinds, wrong kind/ID/text combinations, and collection-local lookup eligibility exactly match the participant resolver.
- [X] T009 [TEST] [P] [US1] Test Solution Alternative coverage for `DESCRIPTION`, `ADVANTAGE`, `DISADVANTAGE`, `ASSUMPTION`, and `IMPLEMENTATION_COMPLEXITY` in the fixed family/alternative/tuple order; prove generation notes and names contribute no basis.
- [X] T010 [TEST] [P] [US1] Test `RELEVANT_CONSTRAINT` retains an exact structured `ConstraintReference`, excludes owner-local duplicate objects, permits equal constraints in different alternatives, and never flattens nested source/kind/value.
- [X] T011 [TEST] [US1] Test exact target-key shapes, string-form indices, canonical nested emitted identities, fixed global order, and equivalent results for payload mappings with different insertion order.
- [X] T012 [TEST] [US4] Test identical emitted identity plus identical semantic target deduplicates to the first candidate, an emitted identity collapsing distinct targets is wholly excluded, unrelated candidates survive, and empty normalization remains a valid zero-risk input to later narrowing.
- [X] T013 [TEST] [US3] Test Unicode, quotes, slashes, newlines, JSON-looking strings, delimiter-looking text, and prompt-injection-like values remain exact data in the snapshot, domain reference, emitted identity, and fresh wire projection.
- [X] T014 [TEST] [US1] Add `tests/fixtures/risk_reviewer_2026-08-30_invalid_references.json` as a minimal synthetic checked-in reproduction containing matching upstream artifacts plus the observed constraint-as-assumption kind/ID/text mismatch; prove fixture loading needs no ignored local artifact.

### Implementation

- [X] T015 [US3] Add the private exact-payload detachment helper and frozen `RiskReviewerPayloadSnapshot` in `src/agentic_review_board/infrastructure/llm/dynamic_schemas.py`; move Critic snapshot mechanics onto the helper only when T004 proves byte-equivalent behavior.
- [X] T016 [US1] Add frozen `AllowedRiskBasis`, validated existing basis-subtype storage, fresh `exclude_none` wire projection, canonical JSON emitted identity, private target-key invariants, and deterministic normalization.
- [X] T017 [US1] Implement explicit ReviewInput, Problem Analysis, and Solution Alternative basis enumeration with resolver-equivalent scalar, text, optional-ID, and structured-constraint eligibility and no unsupported families.

### Phase 1 checkpoint

- [X] T018 [GATE] Run the focused Phase 1 tests, full deterministic pytest suite, focused Ruff, and strict mypy; record red/green evidence and confirm no JSON Schema, adapter request, participant, domain, configuration, dependency, or network behavior changed.

### T009–T018 green evidence

- Focused Risk/Critic snapshot and catalog suite: 82 tests passed.
- Full deterministic pytest suite passed with the two existing live tests skipped.
- Repository-wide Ruff check passed.
- Strict mypy passed for all 29 source files.
- `git diff --check` passed; changes remain limited to the Phase 1 schema module,
  focused tests, synthetic fixture, and task evidence.

### T001–T004 red evidence

- Added minimal, full, duplicate-heavy, zero-alternative, malformed, one-read, mutation,
  and key-order fixtures/tests for the exact three-artifact Risk Reviewer snapshot.
- The combined focused collection fails only at the expected missing
  `RiskReviewerPayloadSnapshot` / `build_risk_reviewer_payload_snapshot` imports; no
  production Slice 7.2 behavior exists yet.
- Existing Critic dynamic-schema regression suite, including the new shared-detachment
  byte-equivalence test: **44 passed**.
- Ruff passes for both dynamic-schema test modules.
- The workspace `.venv` launcher references a removed Python 3.12 installation; tests
  were executed non-destructively with the available Python 3.12 plus the existing
  `.venv/Lib/site-packages`. No environment or dependency files were changed.

### T005–T008 red evidence

- Added exact ReviewInput field/value/order/target-key assertions, including absent and
  blank optionals, owner-field duplicates, equal cross-field text, and whitespace
  preservation.
- Added all five Problem Analysis kind families with canonical present/absent IDs,
  ID-less ambiguity exclusion, distinct ID-bearing duplicate text, cross-kind equality,
  and the observed forbidden constraint-as-assumption combination.
- Focused collection fails only at the expected absent `AllowedRiskBasis` /
  `build_allowed_risk_bases` Slice 7.2 imports; production remains untouched.
- Ruff passes for the expanded Risk Reviewer dynamic-schema test module.

## Phase 2: Exact Scope Catalog and Dynamic RiskAssessment Schema

**Purpose:** Narrow only Risk basis selection and affected scope while preserving every
other strict RiskAssessment shape and valid zero-risk result.

### Tests first

- [X] T019 [TEST] [US2] Test the allowed scope catalog returns exactly 1, 5, and 16 frozen `RiskScope` values for zero, two, and three alternatives, in overall-then-length-then-permutation order.
- [X] T020 [TEST] [US2] Test every current non-empty ordered alternative-ID sequence appears exactly once and no empty `ALTERNATIVES`, repeated ID, unknown ID, stale ID, ranking, or canonical-preference behavior appears.
- [X] T021 [TEST] [P] [US1] Test each ReviewInput and Problem Analysis `AllowedRiskBasis` becomes one fresh closed branch with exact `const` properties, canonical property/required order, absent optional ID omission, and no discriminator/free enum/nullable route.
- [X] T022 [TEST] [P] [US1] Test each string-valued Solution Alternative basis branch binds exact source, alternative, characteristic, and value without Cartesian-product combinations.
- [X] T023 [TEST] [P] [US1] Test a relevant-constraint branch contains a fresh nested closed object with exact source/kind/value constants and cannot combine the outer alternative/characteristic with another constraint.
- [X] T024 [TEST] [P] [US2] Test every allowed `RiskScope` becomes one fresh closed `kind + alternative_ids` branch using scalar/array `const`, including exact overall and reversed-order examples.
- [X] T025 [TEST] [US1] Test RiskAssessment narrowing starts from the authoritative strict schema, replaces the complete Risk `basis.items` discriminated union with exact catalog `oneOf`, sets `basis.minItems=1`, retains `basis.maxItems=10`, and changes no unrelated definition.
- [X] T026 [TEST] [US2] Test narrowing replaces only `RiskScope` with the exact scope branches, preserves every legal current order, and leaves no free kind/ID item route or `uniqueItems` dependency.
- [X] T027 [TEST] [US3] Test fully empty and observation-only RiskAssessment remain representable; optional category/mitigation/residual uncertainty, qualitative severity, root arrays, forbidden extra fields, and Slice 7 bounds remain equivalent to the strict static contract.
- [X] T028 [TEST] [US4] Test empty basis catalog narrows root `risks.maxItems` to zero without empty `oneOf`, open/fallback basis, or construction failure, while non-empty observations remain representable.
- [X] T029 [TEST] [US5] Test deterministic compact Unicode-preserving schema serialization, fresh `new_document()` ownership, mutation isolation, no alias to base/catalog/branches/prior calls, and byte equivalence for semantically equivalent snapshots.
- [X] T030 [TEST] [US5] Build a documented high-cardinality contract-valid fixture using the real maximum of three alternatives and explicit unbounded-input stress counts; assert exact basis/scope branch formulas, no truncation, and recorded UTF-8 schema size without creating product limits.
- [X] T031 [TEST] [US4] Test missing, renamed, wrongly typed, unexpectedly referenced, or otherwise drifted authoritative Risk/RiskScope schema locations and internal branch invariant failures raise `LLMRequestSchemaError` with no static-schema fallback.

### Implementation

- [X] T032 [US2] Implement deterministic `tuple[RiskScope, ...]` construction with overall first and ordered permutations without replacement, plus exact fresh scope-branch projection.
- [X] T033 [US1] Implement exact fresh basis-branch projection, including explicit nested `ConstraintReference`, canonical required ordering, and fail-safe rejection of unexpected nested values.
- [X] T034 [US1] Implement strict-before-narrow RiskAssessment transformation with explicit structural checks, exact basis-item replacement, non-empty-basis bounds, empty-catalog zero-risk behavior, and exact RiskScope replacement.
- [X] T035 [US3] Implement dynamic Risk Reviewer schema serialization through the unchanged `RequestOutputSchema`, then extend the existing general schema builder so exact `risk_reviewer` receives this schema while Critic and static-role semantics remain unchanged.

### Phase 2 checkpoint

- [X] T036 [GATE] Run focused Phase 1–2 tests, full deterministic pytest, Ruff, and strict mypy; record catalog/branch counts and schema bytes, and confirm the adapter, prompts, participant/domain validation, and network behavior remain unchanged.

### T019–T036 green evidence

- Focused Phase 1–2 Risk/Critic schema suite: 96 tests passed.
- Full deterministic pytest suite passed with the two existing live tests skipped.
- Repository-wide Ruff and strict mypy (29 source files) passed.
- Scope catalogs contain exactly 1, 5, and 16 branches for zero, two, and three
  alternatives.
- The high-cardinality fixture produces 509 exact basis branches and 16 exact scope
  branches without truncation; canonical UTF-8 schema size is 154,324 bytes.
- Adapter transport, prompts, participant/domain validation, configuration,
  dependencies, and network behavior remain unchanged in this phase.

## Phase 3: One-Snapshot Dynamic Dispatch and Adapter Integration

**Purpose:** Carry one role-specific dynamic snapshot consistently in untrusted message data
and provider guidance while retaining all existing modes and safe failure behavior.

### Tests first

- [X] T037 [TEST] [US3] Test frozen `DynamicRequestContext` pairs one snapshot's exact serialized payload with its `RequestOutputSchema`, stores no mutable document/provider data, and is rebuilt independently per invocation.
- [X] T038 [TEST] [US3] Test closed dispatch returns Risk Reviewer context for exact `risk_reviewer`, existing Critic context for exact `critic`, and `None` for Analyst, Solution Architect, and Coordinator; unknown roles retain existing failure before dispatch.
- [X] T039 [TEST] [US3] Test the general request-schema helper returns each dynamic role's schema and preserves byte-equivalent strict static schemas for the three static roles without requiring dynamic payload keys.
- [X] T040 [TEST] [US3] Extend `tests/unit/infrastructure/llm/test_openai_compatible.py` so a Risk Reviewer call retains the exact static payload-value-free system message and includes independently delimited snapshot payload and dynamic-schema JSON only in user/data content; include newline- and delimiter-looking values and prove they remain inside parsed JSON without creating extra boundary lines.
- [X] T041 [TEST] [US3] Test Risk Reviewer `JSON_SCHEMA` uses a fresh provider document deeply equal to the delimited dynamic schema while retaining `risk_reviewer_output`, `strict=true`, configured sampling/max-token fields, and one request.
- [X] T042 [TEST] [P] [US3] Test Risk Reviewer `JSON_OBJECT` carries dynamic schema only as untrusted data and retains exact `{type: json_object}` response format without an enforcement claim.
- [X] T043 [TEST] [P] [US3] Test Risk Reviewer `PROMPT_ONLY` carries dynamic schema only as untrusted data and omits response format without an enforcement claim.
- [X] T044 [TEST] [US3] Test Critic request bodies remain Slice 7.1-equivalent and Analyst, Solution Architect, and Coordinator remain Slice 7-equivalent across applicable modes; Risk Reviewer is removed only from the former static-role regression set.
- [X] T045 [TEST] [US4] Test invalid Risk Reviewer snapshot/schema construction fails before credential extraction, header construction, HTTP invocation, and output observation; static-role serialization failures retain `LLMPayloadSerializationError`.
- [X] T046 [TEST] [US4] Test schema-error `str`/`repr` and orchestrator mapping contain no payload marker, basis/scope value, target key, schema fragment, endpoint/profile/model detail, credential, raw output, or nested validation text.
- [X] T047 [TEST] [US3] Test successful adapter parsing and observer invocation still return only the exact provider mapping; dynamic guidance does not instantiate RiskAssessment, mark output trusted, or alter response content.
- [X] T048 [TEST] [US4] Test a provider ignoring guidance and returning the checked-in invalid Risk Reviewer mapping still reaches unchanged participant rejection, `Risk Reviewer FAILED + Review INCOMPLETE`, and pending Critic/Coordinator.

### Implementation

- [X] T049 [US3] Add `DynamicRequestContext` and the exact two-role/three-static-role dispatcher in `dynamic_schemas.py`, reusing existing Critic builders without a registry, reflection, or externally configurable rules.
- [X] T050 [US3] Refactor `OpenAICompatibleLLMAdapter.generate_structured` to consume the closed dynamic context for Risk Reviewer and Critic, use the existing serializer for static roles, and keep one common downstream transport path.
- [X] T051 [US3] Append the dynamic schema only to the delimited untrusted user/data message for both dynamic roles and reuse a fresh document from the same serialization only in `JSON_SCHEMA` provider guidance.
- [X] T052 [US4] Preserve existing mode, header, credential, timeout, HTTP, parsing, observer, and safe-error behavior while ensuring every dynamic construction failure occurs before side effects.

### Phase 3 checkpoint

- [X] T053 [GATE] Run focused dynamic-schema, adapter, integration, participant, and orchestrator tests plus the full deterministic suite, Ruff, and strict mypy; confirm one-snapshot Risk Reviewer behavior and unchanged Critic/static-role requests.

### T037–T053 green evidence

- Focused dynamic-schema, adapter, participant, integration, and orchestrator suite:
  252 tests passed.
- Full deterministic pytest suite passed with the two existing live tests skipped.
- Repository-wide Ruff and strict mypy (29 source files) passed.
- Risk Reviewer and Critic each read one payload snapshot and reuse one canonical schema
  serialization across untrusted message data and provider guidance.
- Static-role request bodies, transport behavior, credentials, observer behavior, and
  safe error surfaces remain covered by unchanged regressions.

## Phase 4: Parity With Trusted Risk Reviewer Validation

**Purpose:** Prove request guidance mirrors rather than replaces the existing participant
scope and basis resolvers.

### Tests first

- [X] T054 [TEST] [P] [US1] Add parameterized parity tests showing every generated ReviewInput basis subtype passes current exact scalar/collection resolution against the same snapshot, including blank/duplicate exclusions.
- [X] T055 [TEST] [P] [US1] Add parity tests showing every generated Problem Analysis basis passes selected-kind resolution with exact present/absent ID behavior and matching semantic target.
- [X] T056 [TEST] [P] [US1] Add parity tests showing every generated Solution Alternative scalar, text-collection, complexity, and structured-constraint basis passes owner-local current resolution.
- [X] T057 [TEST] [P] [US2] Add parity tests showing every generated RiskScope passes `RiskScope` structural validation and current alternative membership validation for zero, two, and three alternatives.
- [X] T058 [TEST] [US1] Validate every emitted wire projection through the authoritative discriminated `RiskBasisReference` type and prove every generated branch represents that same projection exactly.
- [X] T059 [TEST] [US1] Use the checked-in 2026-08-30 fixture to prove the observed constraint-as-assumption kind/ID/text identities match no catalog/schema branch while unchanged participant validation rejects the mapping.
- [X] T060 [TEST] [US3] Run existing Risk, Risk Reviewer, adapter-participant, orchestration, Critic, and final-review tests unchanged to prove no trusted contract, role responsibility, lifecycle, error message, or downstream behavior changed.

### Implementation

- [X] T061 [US1] Make only parity-driven corrections to explicit Risk Reviewer catalog/scope/schema construction; do not change participant/domain validators, coerce outputs, or make tests pass by broadening guidance.

### Phase 4 checkpoint

- [X] T062 [GATE] Run all parity and regression tests plus the full deterministic suite, Ruff, strict mypy, and dependency check; record that every offered basis/scope is accepted by unchanged trusted validation and the known invalid output remains rejected.

### T054–T062 green evidence

- Every emitted ReviewInput, Problem Analysis, and Solution Alternative basis passed the
  unchanged trusted participant resolver against the same validated snapshot.
- Every generated scope for zero, two, and three alternatives passed both `RiskScope`
  validation and unchanged current-alternative membership validation.
- Every wire object validated through the authoritative discriminated
  `RiskBasisReference` union and matched the sole instance encoded by its exact branch.
- The checked-in cross-kind reference matched no catalog or schema branch and remained
  rejected by the unchanged Problem Analysis resolver.
- Focused domain/participant/adapter/orchestrator parity suite: 557 tests passed.
- Full deterministic pytest passed with two existing live tests skipped; repository-wide
  Ruff, strict mypy (29 source files), and `pip check` all passed.
- No parity correction to production or trusted domain/participant validation was needed.

## Phase 5: Local vLLM Compatibility and Fixed-Run Evidence

**Purpose:** Verify the additional schema subset against the approved local profile and
collect honest completion evidence without retries or result selection.

- [X] T063 [TEST] [US5] Extend `tests/live/test_llm_smoke.py` with a minimal valid three-artifact payload that obtains its schema through the real Risk Reviewer snapshot/adapter path and checks provider acceptance plus direct JSON-object parsing with no retry.
- [X] T064 [DOC] [US5] Create `specs/007.2-dynamic-risk-reviewer-schema/live-evaluation.md` with exact opt-in commands, current fixed scenario/configuration, profile/model/vLLM/GPU/context fields, unique-path preconditions, a five-row result table, and interpretation rules before executing runs.
- [X] T065 [TEST] [US5] Execute the selected-profile static smoke, Slice 7.1 Critic dynamic smoke, and Slice 7.2 Risk Reviewer dynamic smoke against `config/llm.vllm.json`; record elapsed time and safe failure without changing mode/profile automatically.
- [ ] T066 [US5] Execute exactly five independently initiated fixed-scenario full reviews with temperature 0/seed 0, assert every aggregate/raw path is absent before invocation, use unique Slice 7.2 run numbers, and perform no automatic retry, overwrite, rerun substitution, or selective deletion.
- [ ] T067 [DOC] [US5] Complete every live-evaluation row with Review and five stage statuses, safe failure family, elapsed time, whether the observed Risk basis mismatch recurred, whether Critic/Coordinator completed, and ignored artifact paths without copying full payload/schema/raw output into documentation.
- [X] T068 [US5] If vLLM rejects array-valued `const`, `minItems`, or another required schema feature, record the compatibility boundary and stop the affected campaign; do not weaken, truncate, retry another mode/model, or claim Slice 7.2 live success.
- [X] T069 [DOC] [US5] Classify any remaining failure separately from the prevented basis/scope patterns, state explicitly whether the five-run evidence target—not end-to-end reliability—was completed, and update `docs/vllm-local-docker-guide.md` only if shared commands or profile interpretation actually changed.

### Phase 5 checkpoint

- [X] T070 [GATE] Review the preserved run set and evaluation document for no retries, replacement, overwrite, selective deletion, unsupported reliability claim, sensitive request logging, or configuration drift.

## Phase 6: Cross-Cutting Verification

- [X] T071 [TEST] Run full deterministic `python -m pytest` with live tests skipped by default and no endpoint/GPU/network requirement.
- [X] T072 [TEST] Run `python -m ruff check .` without weakening repository rules or excluding new files.
- [ ] T073 [TEST] Run strict `python -m mypy` over source and tests for immutable values, discriminated union projections, nested JSON mappings, scope permutations, exhaustive dispatch, and optional empty-catalog paths without convenience ignores.
- [X] T074 [TEST] Run `python -m pip check` and confirm no production dependency change.
- [X] T075 [TEST] Run `docker compose config`, validate the checked-in local profile/guide commands, and confirm Slice 7.2 requires no Compose image, volume, model, environment-variable, or configuration-format change.
- [X] T076 Inspect production imports and `pyproject.toml` for no provider SDK, retry/fallback/router, generic schema/rules engine, persistence, RAG, tools, UI, new model assignment, or domain-facing provider type.
- [X] T077 Review default logs, exception strings/reprs, observer data, and checked-in fixtures/docs for no credentials, endpoint details, complete payloads, generated schemas, raw outputs, exact sensitive markers, or private target keys.
- [X] T078 Review implementation against Slice 7.2 spec/plan/data model, Slice 4 Risk Reviewer, Slice 7 adapter, Slice 7.1 Critic correction, canonical docs, Constitution 1.1.0, ADR-0001, and ADR-0002.
- [X] T079 Confirm `LLMPort`, all domain models, all participants, orchestration, Review lifecycle, error taxonomy/messages, prompts, runtime configuration/composition, and three static-role semantics remain unchanged; confirm Critic remains Slice 7.1-equivalent.

### Phase 6 checkpoint

- [ ] T080 [GATE] Run `git diff --check`, review only intended files, record final deterministic/live evidence under the relevant checkpoints, and mark tasks complete only when their observable outcome is actually satisfied.

## Requirement and Story Coverage

| Approved scope | Task coverage |
|---|---|
| US1 / RDS-FR-004–RDS-FR-008 | T005–T017, T021–T025, T033–T034, T054–T061 |
| US2 / RDS-FR-009 | T019–T020, T024, T026, T032, T057 |
| US3 / RDS-FR-001–RDS-FR-003, RDS-FR-010–RDS-FR-014, RDS-FR-017 | T003–T004, T015, T025–T029, T035–T044, T049–T053, T060 |
| US4 / RDS-FR-015–RDS-FR-016 | T002, T012, T028, T031, T045–T048, T052, T059 |
| US5 / RDS-FR-018, RDS-FR-021 | T029–T030, T063–T070 |
| RDS-FR-019–RDS-FR-020 | T003, T013, T029, T040, T046–T047, T051–T052, T077 |
| Full regression and governance | T018, T036, T053, T062, T071–T080 |

## Dependencies and Gates

```text
Snapshot + basis catalog (T001–T018)
                 ↓
Scope + dynamic schema (T019–T036)
                 ↓
Dynamic dispatch + adapter (T037–T053)
                 ↓
Trusted-validator parity (T054–T062)
                 ↓
Live compatibility/evidence (T063–T070)
                 ↓
Cross-cutting verification (T071–T080)
```

Within a phase, `[P]` tests may be prepared together only after their common fixtures exist.
Production tasks remain ordered after the complete red contract for that block. Live tasks
remain explicitly opt-in and never run as part of the default suite.

Do not implement retries, fallback, schema/output repair, participant/domain relaxation,
dynamic schemas for additional roles, generic rule engines, UI, persistence, model routing,
or automatic profile changes as part of any task above.

## Tasks Review Gate

Before approval, confirm:

1. all 21 approved requirements and five user stories have implementation and verification
   coverage;
2. every production block is preceded by focused deterministic red tests;
3. shared payload detachment cannot change Critic behavior without an explicit regression;
4. basis and scope builders are tested independently before schema transformation;
5. empty-basis handling preserves zero-risk output without widening;
6. adapter integration starts only after catalog/schema determinism is proven;
7. participant parity is proven before live execution;
8. live paths are unique and checked absent before each no-retry invocation;
9. live evidence can complete honestly even if the Review remains incomplete;
10. full quality/security/governance gates follow the live evidence phase;
11. no task authorizes domain, participant, port, orchestration, configuration, dependency,
    retry, repair, fallback, routing, persistence, or UI expansion;
12. task completion requires recorded observable evidence, not implementation intent.

No implementation SHALL begin until this `tasks.md` has been self-reviewed and explicitly
approved by the user. After approval, implementation may proceed in small related groups,
stopping at the defined phase checkpoints for review.
