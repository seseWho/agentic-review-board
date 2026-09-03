"""Session state, input, and rendering boundary for the Streamlit Review UI."""

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Protocol

import streamlit as st
from pydantic import BaseModel, ValidationError

from agentic_review_board.application.observation import ReviewObserver
from agentic_review_board.domain.execution import (
    Review,
    ReviewStatus,
    StageIdentity,
    StageStatus,
)
from agentic_review_board.domain.review import ReviewInput
from agentic_review_board.ui.presentation import (
    REVIEW_STATUS_LABELS,
    STAGE_DESCRIPTORS,
    STAGE_STATUS_LABELS,
    OutputSection,
    final_result,
    output_sections,
    stage_presentations,
)

STATE_KEY = "arb_review_ui_state"
TITLE_KEY = "arb_title"
DESCRIPTION_KEY = "arb_description"
OBJECTIVE_KEY = "arb_objective"
CONSTRAINTS_KEY = "arb_constraints"
CONTEXT_KEY = "arb_context"
STATED_FACTS_KEY = "arb_stated_facts"
START_KEY = "arb_start"
STAGE_SELECT_KEY = "arb_stage_select"
NEW_REVIEW_KEY = "arb_new_review"

FORM_WIDGET_KEYS = (
    TITLE_KEY,
    DESCRIPTION_KEY,
    OBJECTIVE_KEY,
    CONSTRAINTS_KEY,
    CONTEXT_KEY,
    STATED_FACTS_KEY,
)


class ReviewExecutor(Protocol):
    """Injected one-Review execution capability owned by root composition."""

    def __call__(
        self,
        created_review: Review,
        *,
        observer: ReviewObserver,
    ) -> Review: ...


@dataclass(frozen=True, slots=True)
class ReviewInputDraft:
    """Transient raw values entered into the six Review input controls."""

    description: str = ""
    title: str = ""
    objective: str = ""
    constraints_text: str = ""
    context_text: str = ""
    stated_facts_text: str = ""


class UiPhase(StrEnum):
    """Session-local interaction phase, separate from trusted Review state."""

    FORM = "FORM"
    EXECUTING = "EXECUTING"
    RESULT = "RESULT"
    APPLICATION_ERROR = "APPLICATION_ERROR"


class UiErrorKind(StrEnum):
    """Sanitized UI failure families that never describe participant failure."""

    STARTUP = "STARTUP"
    APPLICATION = "APPLICATION"


@dataclass(frozen=True, slots=True)
class UiError:
    """Fixed user-safe error owned by the presentation boundary."""

    kind: UiErrorKind
    public_message: str

    def __post_init__(self) -> None:
        if not self.public_message.strip():
            raise ValueError("UI error message must not be empty")


STARTUP_ERROR = UiError(
    kind=UiErrorKind.STARTUP,
    public_message=(
        "The review could not be started. Check the local runtime configuration and try again."
    ),
)
APPLICATION_ERROR = UiError(
    kind=UiErrorKind.APPLICATION,
    public_message="The review interface could not complete this run safely.",
)


@dataclass(frozen=True, slots=True)
class ReviewUiState:
    """One immutable session value referencing at most one trusted Review snapshot."""

    phase: UiPhase = UiPhase.FORM
    review: Review | None = None
    selected_stage: StageIdentity | None = None
    error: UiError | None = None

    def __post_init__(self) -> None:
        if self.selected_stage is not None and self.review is None:
            raise ValueError("inconsistent UI state")

        if self.phase is UiPhase.FORM:
            valid = (
                self.review is None
                and self.selected_stage is None
                and self.error is None
            )
        elif self.phase is UiPhase.EXECUTING:
            valid = self.review is not None and self.error is None
        elif self.phase is UiPhase.RESULT:
            valid = (
                self.review is not None
                and self.review.status
                in {ReviewStatus.COMPLETED, ReviewStatus.INCOMPLETE}
                and self.error is None
            )
        elif self.phase is UiPhase.APPLICATION_ERROR:
            valid = self.error is not None and not (
                self.error.kind is UiErrorKind.STARTUP and self.review is not None
            )
        else:
            valid = False

        if not valid:
            raise ValueError("inconsistent UI state")


def _optional_text(value: str) -> str | None:
    return None if not value.strip() else value


def _repeated_text(value: str) -> tuple[str, ...]:
    return tuple(line for line in value.splitlines() if line.strip())


def to_review_input(draft: ReviewInputDraft) -> ReviewInput:
    """Validate a raw draft while preserving every meaningful value exactly."""

    return ReviewInput(
        description=draft.description,
        title=_optional_text(draft.title),
        objective=_optional_text(draft.objective),
        constraints=_repeated_text(draft.constraints_text),
        context=_repeated_text(draft.context_text),
        stated_facts=_repeated_text(draft.stated_facts_text),
    )


def can_start_review(state: ReviewUiState) -> bool:
    return state.phase is UiPhase.FORM


def begin_review(state: ReviewUiState, draft: ReviewInputDraft) -> ReviewUiState:
    if not can_start_review(state):
        raise ValueError("review cannot start in the current UI phase")
    review = Review.create(to_review_input(draft))
    return ReviewUiState(phase=UiPhase.EXECUTING, review=review)


def _require_current_execution(
    state: ReviewUiState,
    review: Review,
) -> None:
    if state.phase is not UiPhase.EXECUTING or state.review is None:
        raise ValueError("Review snapshot is not expected in the current UI phase")
    if review.review_input is not state.review.review_input:
        raise ValueError("snapshot belongs to a different Review")


def observe_review(state: ReviewUiState, review: Review) -> ReviewUiState:
    _require_current_execution(state, review)
    return replace(state, review=review)


def finish_review(state: ReviewUiState, review: Review) -> ReviewUiState:
    _require_current_execution(state, review)
    if review.status not in {ReviewStatus.COMPLETED, ReviewStatus.INCOMPLETE}:
        raise ValueError("Review executor must return a terminal Review")
    return ReviewUiState(phase=UiPhase.RESULT, review=review)


def select_stage(state: ReviewUiState, identity: StageIdentity) -> ReviewUiState:
    if state.review is None:
        raise ValueError("a stage cannot be selected without a Review")
    state.review.stage(identity)
    return replace(state, selected_stage=identity)


def startup_failure(state: ReviewUiState) -> ReviewUiState:
    if (
        state.phase is not UiPhase.EXECUTING
        or state.review is None
        or state.review.status is not ReviewStatus.CREATED
    ):
        raise ValueError("startup failure requires an unobserved created Review")
    return ReviewUiState(phase=UiPhase.APPLICATION_ERROR, error=STARTUP_ERROR)


def application_failure(state: ReviewUiState) -> ReviewUiState:
    if state.phase is not UiPhase.EXECUTING:
        raise ValueError("application failure requires an executing Review")
    return ReviewUiState(
        phase=UiPhase.APPLICATION_ERROR,
        review=state.review,
        selected_stage=state.selected_stage,
        error=APPLICATION_ERROR,
    )


def reset_review(state: ReviewUiState) -> ReviewUiState:
    del state
    return ReviewUiState()


def _session_state() -> ReviewUiState:
    value = st.session_state.get(STATE_KEY)
    if value is None:
        value = ReviewUiState()
        st.session_state[STATE_KEY] = value
    if not isinstance(value, ReviewUiState):
        raise TypeError("Review UI session state is invalid")
    return value


def _store_state(state: ReviewUiState) -> None:
    st.session_state[STATE_KEY] = state


def _stage_name(identity: StageIdentity) -> str:
    return STAGE_DESCRIPTORS[identity].display_name


def _humanize_field(name: str) -> str:
    return name.replace("_", " ").capitalize()


def _render_value(value: object) -> None:
    if isinstance(value, StrEnum):
        st.code(value.value)
        return
    if isinstance(value, BaseModel):
        for field_name in type(value).model_fields:
            st.markdown(f"**{_humanize_field(field_name)}**")
            _render_value(getattr(value, field_name))
        return
    if isinstance(value, tuple):
        if not value:
            st.info("No items")
            return
        for index, item in enumerate(value, start=1):
            if isinstance(item, (BaseModel, tuple)):
                with st.container(border=True):
                    st.caption(f"Item {index}")
                    _render_value(item)
            else:
                st.markdown(f"- {item}")
        return
    if value is None:
        st.info("Not provided")
        return
    st.write(value)


def _render_sections(sections: tuple[OutputSection, ...]) -> None:
    for section in sections:
        st.markdown(f"#### {section.label}")
        if section.empty_message is not None:
            st.info(section.empty_message)
        else:
            _render_value(section.value)


def _render_topology_preview() -> None:
    st.subheader("Process")
    st.markdown(f"**Overall status:** {REVIEW_STATUS_LABELS[ReviewStatus.CREATED]}")
    for identity in STAGE_DESCRIPTORS:
        descriptor = STAGE_DESCRIPTORS[identity]
        with st.container(border=True):
            st.markdown(f"### {descriptor.display_name}")
            st.markdown(f"**Status:** {STAGE_STATUS_LABELS[StageStatus.PENDING]}")
            st.caption(descriptor.responsibility)
            st.caption(f"Produces: {descriptor.output_artifact_label}")


def _render_process(review: Review) -> None:
    st.subheader("Process")
    st.markdown(f"**Overall status:** {REVIEW_STATUS_LABELS[review.status]}")
    st.markdown(
        "**Sequential dependency:** Analyst → Solution Architect → "
        "Risk Reviewer → Critic → Coordinator"
    )
    for presentation in stage_presentations(review):
        stage = presentation.execution
        descriptor = presentation.descriptor
        with st.container(border=True):
            st.markdown(f"### {descriptor.display_name}")
            st.markdown(f"**Status:** {STAGE_STATUS_LABELS[stage.status]}")
            st.caption(descriptor.responsibility)
            st.markdown(
                "**Consumes:** " + ", ".join(descriptor.input_artifact_labels)
            )
            st.markdown(f"**Produces:** {descriptor.output_artifact_label}")
            if presentation.blocked_by is not None:
                blocker = STAGE_DESCRIPTORS[presentation.blocked_by].display_name
                st.warning(
                    f"Not executed because the mandatory upstream {blocker} stage failed."
                )
            if stage.status is StageStatus.FAILED and stage.error is not None:
                st.error(f"{stage.error.kind.value}: {stage.error.message}")
            if stage.status is StageStatus.COMPLETED:
                with st.expander(
                    f"Inspect trusted {descriptor.output_artifact_label}",
                    expanded=False,
                ):
                    _render_sections(output_sections(stage))


def _render_submitted_input(review: Review) -> None:
    review_input = review.review_input
    with st.expander("Submitted Review input", expanded=False):
        st.markdown("**Description**")
        st.write(review_input.description)
        st.markdown("**Title**")
        _render_value(review_input.title)
        st.markdown("**Objective**")
        _render_value(review_input.objective)
        st.markdown("**Constraints**")
        _render_value(review_input.constraints)
        st.markdown("**Context**")
        _render_value(review_input.context)
        st.markdown("**Stated facts**")
        _render_value(review_input.stated_facts)


def _render_stage_detail(state: ReviewUiState) -> ReviewUiState:
    review = state.review
    if review is None:
        return state
    default_identity = state.selected_stage or StageIdentity.ANALYST
    selected = st.selectbox(
        "Inspect an agent",
        options=tuple(STAGE_DESCRIPTORS),
        index=tuple(STAGE_DESCRIPTORS).index(default_identity),
        format_func=_stage_name,
        key=STAGE_SELECT_KEY,
    )
    if selected is None:
        return state
    state = select_stage(state, selected)
    _store_state(state)
    stage = review.stage(selected)
    descriptor = STAGE_DESCRIPTORS[selected]
    st.subheader(f"Agent detail: {descriptor.display_name}")
    st.write(descriptor.responsibility)
    st.markdown("**Input artifact types**")
    for label in descriptor.input_artifact_labels:
        st.markdown(f"- {label}")
    if stage.inputs is None:
        st.info("This agent has not received an input snapshot.")
    else:
        with st.expander("Inspect trusted stage inputs", expanded=False):
            _render_value(stage.inputs)
    if stage.status is StageStatus.COMPLETED:
        _render_sections(output_sections(stage))
    elif stage.status is StageStatus.FAILED and stage.error is not None:
        st.error(f"{stage.error.kind.value}: {stage.error.message}")
        st.info("No trusted output is available for this failed stage.")
    else:
        st.info("No trusted output is available for this stage.")
    if stage.status in {StageStatus.COMPLETED, StageStatus.FAILED}:
        with st.expander("Trusted technical detail (JSON)", expanded=False):
            st.json(stage.model_dump(mode="json"))
    return state


def _render_final(review: Review) -> None:
    final = final_result(review)
    if final is None:
        return
    st.header("Final result")
    st.markdown(f"**Recommendation outcome:** `{final.recommendation_outcome.value}`")
    st.markdown("**Situation summary**")
    st.write(final.situation_summary)
    st.markdown("**Ranked alternatives**")
    _render_value(final.ranked_alternatives)
    st.markdown("**Preferred alternative**")
    _render_value(final.preferred_alternative_id)
    st.markdown("**Conclusion rationale**")
    st.write(final.conclusion_rationale)
    st.markdown("**Principal risks**")
    _render_value(final.principal_risks)
    st.markdown("**Unresolved questions**")
    _render_value(final.unresolved_questions)
    st.markdown("**Criticism dispositions**")
    _render_value(final.criticism_dispositions)
    st.markdown("**Next validation step (advisory)**")
    st.write(final.next_validation_step)
    st.markdown("**Qualitative confidence**")
    st.code(final.confidence.value)
    st.warning(final.decision_support_notice)


def _render_new_review() -> None:
    st.caption(
        "Starting a new Review clears the current in-memory result. No history is retained."
    )
    if st.button("New Review", key=NEW_REVIEW_KEY):
        for key in (*FORM_WIDGET_KEYS, STAGE_SELECT_KEY, STATE_KEY, NEW_REVIEW_KEY):
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()


def _render_active_state(state: ReviewUiState) -> None:
    if state.error is not None:
        st.error(state.error.public_message)
    review = state.review
    if review is None:
        _render_new_review()
        return
    _render_submitted_input(review)
    _render_process(review)
    if state.phase is not UiPhase.EXECUTING:
        state = _render_stage_detail(state)
        if state.phase is UiPhase.RESULT:
            _render_final(review)
        _render_new_review()


def _draft_from_widgets() -> ReviewInputDraft:
    return ReviewInputDraft(
        title=st.session_state[TITLE_KEY],
        description=st.session_state[DESCRIPTION_KEY],
        objective=st.session_state[OBJECTIVE_KEY],
        constraints_text=st.session_state[CONSTRAINTS_KEY],
        context_text=st.session_state[CONTEXT_KEY],
        stated_facts_text=st.session_state[STATED_FACTS_KEY],
    )


def _render_form(executor: ReviewExecutor) -> None:
    with st.form("arb_review_form"):
        st.text_input("Title (optional)", key=TITLE_KEY)
        st.text_area("Description (required)", key=DESCRIPTION_KEY)
        st.text_area("Objective (optional)", key=OBJECTIVE_KEY)
        st.text_area(
            "Constraints (optional, one per line)",
            key=CONSTRAINTS_KEY,
        )
        st.text_area("Context (optional, one per line)", key=CONTEXT_KEY)
        st.text_area(
            "Stated facts (optional, one per line)",
            key=STATED_FACTS_KEY,
        )
        submitted = st.form_submit_button("Start Review", key=START_KEY)
    if not submitted:
        _render_topology_preview()
        return

    try:
        state = begin_review(_session_state(), _draft_from_widgets())
    except (ValidationError, ValueError):
        st.error("Description is required before the Review can start.")
        return

    _store_state(state)
    created_review = state.review
    assert created_review is not None
    process_slot = st.empty()
    render_count = 0

    with process_slot.container(key="arb_process_snapshot_0"):
        _render_process(created_review)

    def render_snapshot(review: Review) -> None:
        nonlocal render_count, state
        state = observe_review(state, review)
        _store_state(state)
        render_count += 1
        with process_slot.container(key=f"arb_process_snapshot_{render_count}"):
            _render_process(review)

    try:
        result = executor(created_review, observer=render_snapshot)
        state = finish_review(state, result)
    except Exception:
        if state.review is not None and state.review.status is ReviewStatus.CREATED:
            state = startup_failure(state)
        else:
            state = application_failure(state)
    _store_state(state)
    st.rerun()


def render_app(executor: ReviewExecutor) -> None:
    """Render one local, session-scoped pedagogical Review application."""

    st.title("Agentic Review Board")
    st.caption(
        "Inspect how five specialized agents transform trusted artifacts into advisory "
        "decision support."
    )
    state = _session_state()
    if state.phase is UiPhase.FORM:
        _render_form(executor)
    else:
        _render_active_state(state)
