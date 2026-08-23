# Tasks: Coordinator v0.1

**Input**: Approved spec.md, plan.md, and data-model.md
**Branch**: 006-coordinator
**Status**: Approved — reviewed against approved artifacts; implementation authorized
**Tests**: Required; implementation proceeds tests-first in small verified blocks

## Phase 1: Intrinsic FinalReview Contracts

**Purpose**: Define immutable closed Coordinator output models without current-context lookup.

### Tests first

- [X] T001 [US3] Create tests/unit/test_final_reviews.py with exact RecommendationOutcome, CriticismDispositionOutcome, and bounded FinalReviewSection enum tests.
- [X] T002 [US2] Test valid RankedAlternative: strict positive position, required ID/justification, non-empty unique considerations, optional unique ranking-change conditions, frozen tuples, and closed schema.
- [X] T003 [US2] Test invalid RankedAlternative: bool/non-integer/non-positive position, blank text, empty/duplicate collections, and embedded replacement-alternative fields.
- [X] T004 [US1] Test PrincipalRisk required risk_id/rationale, frozen/closed behavior, blank rejection, and absence of copied Risk fields.
- [X] T005 [US1] Test ProblemUnresolvedReference intrinsic shapes for PROBLEM_ASSUMPTION, MISSING_INFORMATION, and UNCERTAINTY with required value and optional non-blank item_id.
- [X] T006 [US1] Test SolutionUnresolvedReference shapes: ALTERNATIVE_ASSUMPTION requires alternative_id and forbids item_id; blocker kinds forbid alternative_id and allow optional item_id.
- [X] T007 [US1] Test RiskUnresolvedReference and CriticUnresolvedReference allowed kinds, required identifiers/values, discriminators, frozen behavior, blanks, and extra fields.
- [X] T008 [US1] Test UnresolvedQuestion required ID/reference/question/rationale and immutable discriminated-union parsing.
- [X] T009 [US1] Test CriticismDisposition: REFLECTED requires unique reflected sections; DISMISSED requires none; validate ID/rationale, blanks, frozen and closed behavior.
- [X] T010 [US2] Test valid FinalReview ranking positions independent of tuple order plus unique alternative, risk, question/reference, and disposition identities.
- [X] T011 [US3] Test recommendation consistency: RECOMMENDED requires non-empty ranking and preferred position-1 ID; INSUFFICIENT_EVIDENCE forbids preferred ID but permits ranking; rationale always required.
- [X] T012 [US4] Test zero-ranking + INSUFFICIENT_EVIDENCE valid and RECOMMENDED invalid; do not widen the accepted 0/2/3 SolutionAlternatives cardinality.
- [X] T013 [US1] Test required summary/next step, existing QualitativeLevel confidence, fixed exact decision-support notice, tuple normalization, immutability, unknown fields, and forbidden scoring/probability fields.
- [X] T014 [US6] Test intrinsic aggregate rejection for gaps/ties/duplicate positions or identities, structurally identical unresolved references, wrong notice, blanks, and one invalid nested item; do not attempt current-target resolution in domain-only tests.

### Implementation

- [X] T015 [US1] Create src/agentic_review_board/domain/final_reviews.py with approved enums and four unresolved-question source/kind families; reuse QualitativeLevel.
- [X] T016 [US1] Implement immutable closed RankedAlternative, PrincipalRisk, four source-specific unresolved-reference models and union, UnresolvedQuestion, and CriticismDisposition.
- [X] T017 [US1] Implement FinalReview intrinsic ranking/recommendation/collection invariants and fixed notice without current-review lookup, scoring, or generic references.

**Checkpoint**: intrinsic FinalReview tests pass; no participant/execution changes.

## Phase 2: Coordinator Structural Boundary and Contextual Validation

**Purpose**: Trust a FinalReview only after exact validation against all five current artifacts.

### Tests first

- [X] T018 [US1] Create tests/unit/test_coordinator.py with recording LLMPort and valid two-alternative RECOMMENDED result proving role coordinator, exact five-artifact JSON payload, parsing, trusted return, all five upstream object identities/content unchanged, and FinalReview returned as a separate artifact.
- [X] T019 [US2] Test two/three-alternative complete ID-set equality, contiguous positions, tuple-order independence, per-position justification/considerations, and ranking-change conditions.
- [X] T020 [US2] Test ranking rejection for unknown, duplicate, omitted, extra, blank, mismatched-count, tied, or non-contiguous entries.
- [X] T021 [US3] Test preferred position 1 and reject preferred unknown/not-first/missing for RECOMMENDED or present for INSUFFICIENT_EVIDENCE.
- [X] T022 [US4] Test real zero-alternative GenerationNotes: empty ranking + insufficient evidence succeeds; any ranking/preference/recommendation fails; one alternative remains invalid upstream.
- [X] T023 [US1] Test principal risks resolve exact current Risk.id; empty selection and zero risks valid; duplicate/unknown IDs rejected; upstream Risk content unchanged.
- [X] T024 [US1] Test Problem unresolved assumptions/missing information/uncertainties using exact ID+text or unique text fallback; reject unknown, mismatch, zero, and ambiguity.
- [X] T025 [US1] Test alternative-local assumptions by exact alternative_id+value with no global fallback; test both generation blockers with optional IDs and all missing/mismatch/ambiguity failures.
- [X] T026 [US1] Test Risk unresolved reference resolves only exact risk_id + residual_uncertainty; reject absent uncertainty, unknown ID, mismatch, and other Risk fields.
- [X] T027 [US1] Test Critic unresolved exact ID/value mappings for missing alternative category, contradiction rationale, and unresolved issue text; reject wrong kinds and IDs.
- [X] T028 [US1] Test that structurally different unresolved references resolving to the same current upstream target are rejected contextually; also test recursive atomic validation, no fuzzy/case-folded repair, and no generic paths/string serialization.
- [X] T029 [US1] Test exact Criticism-ID disposition set equality, no importance threshold, REFLECTED/DISMISSED rules, and unknown/duplicate/omitted ID rejection.
- [X] T030 [US3] Test insufficient evidence with 2/3 alternatives requires a valid unresolved question; zero alternatives may omit it when generation notes and required rationale/next step exist.
- [X] T031 [US1] Test empty-Critic and validation-only-Critic require empty dispositions; mixed CriticalReview shows validated points need no disposition.
- [X] T032 [US6] Test malformed/extra/wrong-type and one-invalid-nested-item failures raise CoordinatorOutputError atomically and leave all five inputs unchanged.

### Implementation

- [X] T033 [US1] Create src/agentic_review_board/participants/coordinator.py with Coordinator.coordinate(...), CoordinatorOutputError, exact role/payload, and structural FinalReview parsing.
- [X] T034 [US2] Implement explicit alternative ranking, recommendation, zero-alternative, and principal-risk contextual validation.
- [X] T035 [US1] Implement explicit Coordinator-specific unresolved-question resolver dispatch for every approved source/kind/shape with exact comparisons only.
- [X] T036 [US1] Implement exact Criticism-ID disposition completeness and recursive atomic validation; return only the complete parsed FinalReview.

**Checkpoint**: Coordinator independently validates deterministic output; Review lifecycle unchanged.

## Phase 3: Extend StageExecution and Review Through Coordinator

### Tests first

- [X] T037 [US5] Extend tests/unit/test_review_execution.py for CoordinatorStageInput, explicit unions, and Coordinator PENDING/RUNNING/COMPLETED/FAILED local shapes; completion requires FinalReview.
- [X] T038 [US5] Test exactly ten RUNNING, five INCOMPLETE, and one COMPLETED lifecycle shapes; reject skips, later execution after failure, multiple failures, and false completion.
- [X] T039 [US5] Test exact five-object identity provenance for Coordinator RUNNING/COMPLETED/FAILED and reject equal independent copies one artifact at a time.
- [X] T040 [US5] Test lifecycle/provenance lookup by StageIdentity, valid noncanonical tuples, canonical Review.create(), and order-preserving replacement.

### Implementation

- [X] T041 [US5] Extend src/agentic_review_board/domain/execution.py with CoordinatorStageInput, FinalReview StageOutput, and Coordinator identity/type validation using explicit unions.
- [X] T042 [US5] Extend Review lifecycle validation to exactly 10 RUNNING, 5 INCOMPLETE, and 1 COMPLETED identity-based shapes.
- [X] T043 [US5] Extend same-execution provenance for exact five current Coordinator inputs, separate from generated-reference validation.

## Phase 4: Coordinator Review Transitions

### Tests first

- [ ] T044 [US5] Test start_coordinator() preconditions, exact five captured inputs, prior stages completed, Coordinator pending, and premature/repeated rejection.
- [ ] T045 [US5] Test complete_coordinator(): running required, exact input and supplied FinalReview reused, upstream unchanged, Review COMPLETED.
- [ ] T046 [US6] Test fail_coordinator(): atomic Coordinator FAILED + Review INCOMPLETE, exact inputs/upstream preserved, no output, invalid timing rejected.
- [ ] T047 [US5] Test Coordinator transitions use identity and preserve valid noncanonical tuple order.

### Implementation

- [ ] T048 [US5] Implement start_coordinator(), complete_coordinator(final_review), and fail_coordinator(error) in execution.py with complete immutable reconstruction and no transition engine.

## Phase 5: Extend ReviewOrchestrator Through Coordinator

### Tests first

- [ ] T049 [US5] Extend orchestrator helpers/tests with Coordinator and exact five-role order, five-artifact handoff, trusted FinalReview reuse, Coordinator COMPLETED, Review COMPLETED.
- [ ] T050 [US5] Extend every earlier-stage failure regression to prove Coordinator remains PENDING and is never invoked.
- [ ] T051 [US6] Test real-participant Coordinator output failure maps to FAILED/INCOMPLETE, retains exact inputs, stores no output, preserves upstream, and uses exact OUTPUT_VALIDATION message.
- [ ] T052 [US6] Test ordinary Coordinator Exception maps to exact EXECUTION message without raw detail; invariant misuse propagates and BaseException is not swallowed.
- [ ] T053 [US6] Test sequential success→success and Coordinator-failure→fresh-review isolation across all five inputs and FinalReview outputs.

### Implementation

- [ ] T054 [US5] Extend orchestrator constructor and append explicit fifth-stage start/retrieve/narrow/coordinate/complete sequence without loop, registry, graph, or framework.
- [ ] T055 [US6] Add narrow Coordinator call boundary: CoordinatorOutputError → output validation; ordinary Exception → execution; exact safe messages; fail and return; preserve internal errors.

## Phase 6: Cross-Cutting Verification

- [ ] T056 Run full deterministic python -m pytest with no live LLM/network.
- [ ] T057 Run python -m ruff check . without weakening rules.
- [ ] T058 Run strict python -m mypy for Coordinator models, discriminators, unions, narrowing, and tests without new plugin/dependency.
- [ ] T059 Run python -m pip check and confirm no production dependency change.
- [ ] T060 Inspect production and pyproject.toml for no SDK leakage, autonomous action, replacement alternatives, scoring, persistence/history, RAG/tools/UI, resilience/concurrency, or generic workflow/reference framework.
- [ ] T061 Review against approved artifacts, canonical docs, Constitution, ADR-0001, and real Slice 1–5 contracts: 0/2/3 cardinality, dispositions, fixed notice, assumption semantics, fail-closed references, separate provenance, human authority, and 10/5/1 lifecycle.

## Dependencies and Gate

Order: T001–T017 → T018–T036 → T037–T043 → T044–T048 → T049–T055 → T056–T061.

No production task begins before its corresponding tests exist and fail for the expected missing behavior. Do not implement UI, persistence, history, autonomous execution, provider adapters, scoring, replacement alternatives, one-alternative upstream state, retries/timeouts/concurrency, or generic workflow/reference infrastructure.

Only after this tasks.md is reviewed and explicitly approved may implementation begin.
