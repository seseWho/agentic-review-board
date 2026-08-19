# Tasks: Review Input + Analyst v0.1

**Input**: Design documents from `specs/001-review-input-analyst/`

## Phase 1: Domain Contracts

- [X] T001 [P] Create immutable `ReviewInput` with required description validation in `src/agentic_review_board/domain/review.py`
- [X] T002 [P] Create `ReferencedFinding`, `FactFinding`, and `ProblemAnalysis` contracts in `src/agentic_review_board/domain/analysis.py`
- [X] T003 [P] Add domain package marker in `src/agentic_review_board/domain/__init__.py`

## Phase 2: Provider-Neutral Boundary

- [X] T004 Create provider-neutral `LLMPort` Protocol in `src/agentic_review_board/application/ports.py`
- [X] T005 [P] Add application package marker in `src/agentic_review_board/application/__init__.py`

## Phase 3: User Story 1 — Structure a Review Problem

**Goal**: Produce a trusted structured `ProblemAnalysis` from a valid `ReviewInput` using a deterministic model substitute.

**Independent test**: A valid fake structured response returns the expected objective, fact provenance, assumptions, missing information, and uncertainties.

- [X] T006 [US1] Implement `Analyst` participant and provider-neutral payload construction in `src/agentic_review_board/participants/analyst.py`
- [X] T007 [US1] Implement conversion from untrusted mappings to trusted `ProblemAnalysis` in `src/agentic_review_board/participants/analyst.py`
- [X] T008 [P] [US1] Add participant package marker in `src/agentic_review_board/participants/__init__.py`
- [X] T009 [US1] Add deterministic Analyst happy-path test in `tests/unit/test_analyst.py`

## Phase 4: User Story 2 — Reject Invalid Review Input

**Goal**: Prevent empty review descriptions from entering participant execution.

**Independent test**: Empty/whitespace description raises validation error; minimal non-empty description succeeds.

- [X] T010 [US2] Add valid minimal ReviewInput test in `tests/unit/test_review_input.py`
- [X] T011 [US2] Add blank-description rejection test in `tests/unit/test_review_input.py`

## Phase 5: User Story 3 — Fail Closed on Invalid Analyst Output

**Goal**: Prevent malformed generated Analyst data from becoming trusted domain state.

**Independent test**: Missing required collections, invalid fact provenance, and duplicate IDs each raise `AnalystOutputError`.

- [X] T012 [US3] Add explicit `AnalystOutputError` and required field/list validation in `src/agentic_review_board/participants/analyst.py`
- [X] T013 [US3] Validate allowed fact source references in `src/agentic_review_board/participants/analyst.py`
- [X] T014 [US3] Validate review-local finding ID uniqueness in `src/agentic_review_board/participants/analyst.py`
- [X] T015 [US3] Add malformed collection test in `tests/unit/test_analyst.py`
- [X] T016 [US3] Add invalid fact source-reference test in `tests/unit/test_analyst.py`
- [X] T017 [US3] Add duplicate finding-ID test in `tests/unit/test_analyst.py`

## Phase 6: Verification

- [X] T018 Run deterministic pytest suite and confirm all feature tests pass
- [X] T019 Run Ruff against source/tests in CI or an environment with development dependencies
- [X] T020 Run mypy strict checks in CI or an environment with development dependencies
- [X] T021 Confirm no production dependency, UI, persistence, real provider SDK, or downstream participant was introduced

## Dependencies

- T001–T005 provide the minimal contracts/boundary required by T006–T017.
- US1 establishes the participant happy path.
- US2 is independently testable once T001 exists.
- US3 depends on the Analyst parser from US1.
- Verification follows all implementation tasks.

## Implementation Strategy

Deliver the smallest end-to-end participant slice first. Do not introduce the full review orchestrator or later participants until this increment proves the contracts and provider boundary with deterministic tests.
