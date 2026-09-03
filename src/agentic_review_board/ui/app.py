"""Session state, input, and rendering boundary for the Streamlit Review UI."""

from dataclasses import dataclass, replace
from enum import StrEnum
from hashlib import sha256
from typing import Protocol

import streamlit as st
from pydantic import BaseModel, ValidationError
from streamlit.runtime.uploaded_file_manager import UploadedFile

from agentic_review_board.application.observation import ReviewObserver
from agentic_review_board.domain.execution import (
    Review,
    ReviewStatus,
    StageIdentity,
    StageStatus,
)
from agentic_review_board.domain.review import ReviewInput
from agentic_review_board.ui.markdown_case import (
    MarkdownCaseError,
    MarkdownReviewCase,
    decode_markdown_case,
)
from agentic_review_board.ui.presentation import (
    STAGE_DESCRIPTORS,
    STAGE_STATUS_LABELS,
    OutputSection,
    StagePresentation,
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
NEW_REVIEW_KEY = "arb_new_review"
MARKDOWN_UPLOAD_KEY = "arb_markdown_upload"
MARKDOWN_DIGEST_KEY = "arb_markdown_digest"
MARKDOWN_ERROR_KEY = "arb_markdown_error"
MARKDOWN_SUCCESS_KEY = "arb_markdown_success"

FORM_WIDGET_KEYS = (
    TITLE_KEY,
    DESCRIPTION_KEY,
    OBJECTIVE_KEY,
    CONSTRAINTS_KEY,
    CONTEXT_KEY,
    STATED_FACTS_KEY,
)

RESET_WIDGET_KEYS = (
    *FORM_WIDGET_KEYS,
    MARKDOWN_UPLOAD_KEY,
    MARKDOWN_DIGEST_KEY,
    MARKDOWN_ERROR_KEY,
    MARKDOWN_SUCCESS_KEY,
    STATE_KEY,
    NEW_REVIEW_KEY,
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
    error: UiError | None = None

    def __post_init__(self) -> None:
        if self.phase is UiPhase.FORM:
            valid = self.review is None and self.error is None
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


_STAGE_STATUS_SYMBOLS = {
    StageStatus.PENDING: "○",
    StageStatus.RUNNING: "◉",
    StageStatus.COMPLETED: "✓",
    StageStatus.FAILED: "!",
}
_REVIEW_STATUS_SUMMARIES = {
    ReviewStatus.CREATED: "Not started",
    ReviewStatus.RUNNING: "Running",
    ReviewStatus.COMPLETED: "Completed",
    ReviewStatus.INCOMPLETE: "Incomplete",
}


def configure_page() -> None:
    """Apply the fixed modern page configuration owned by this adapter."""

    st.set_page_config(
        page_title="Agentic Review Board",
        page_icon="🧭",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def _stage_step(identity: StageIdentity) -> int:
    return tuple(STAGE_DESCRIPTORS).index(identity) + 1


def _active_stage_name(review: Review | None) -> str:
    if review is None:
        return STAGE_DESCRIPTORS[StageIdentity.ANALYST].display_name
    running = next(
        (stage for stage in review.stages if stage.status is StageStatus.RUNNING),
        None,
    )
    if running is not None:
        return STAGE_DESCRIPTORS[running.identity].display_name
    if review.status is ReviewStatus.COMPLETED:
        return "Complete"
    failed = next(
        (stage for stage in review.stages if stage.status is StageStatus.FAILED),
        None,
    )
    if failed is not None:
        return f"Stopped at {STAGE_DESCRIPTORS[failed.identity].display_name}"
    return STAGE_DESCRIPTORS[StageIdentity.ANALYST].display_name


def _render_review_summary(review: Review | None) -> None:
    status = ReviewStatus.CREATED if review is None else review.status
    resolved = (
        0
        if review is None
        else sum(
            stage.status in {StageStatus.COMPLETED, StageStatus.FAILED}
            for stage in review.stages
        )
    )
    status_column, progress_column, active_column = st.columns((1.4, 1.0, 1.4))
    status_column.metric("Review status", _REVIEW_STATUS_SUMMARIES[status])
    progress_column.metric("Resolved stages", f"{resolved} / 5")
    active_column.metric("Current focus", _active_stage_name(review))
    st.progress(resolved / 5, text=f"{resolved} of 5 agent stages resolved")
    st.caption(
        "Canonical execution: 1 Analyst → 2 Solution Architect → 3 Risk Reviewer → "
        "4 Critic → 5 Coordinator"
    )


def _render_preview_card(identity: StageIdentity) -> None:
    descriptor = STAGE_DESCRIPTORS[identity]
    label = f"○ Step {_stage_step(identity)} · {descriptor.display_name} · Pending"
    with st.expander(label, expanded=False):
        st.caption(descriptor.responsibility)
        st.markdown("**Consumes:** " + ", ".join(descriptor.input_artifact_labels))
        st.markdown(f"**Produces:** {descriptor.output_artifact_label}")
        st.info("This agent has not started.")


def _render_stage_card(presentation: StagePresentation) -> None:
    stage = presentation.execution
    descriptor = presentation.descriptor
    step = _stage_step(stage.identity)
    status_label = STAGE_STATUS_LABELS[stage.status]
    label = (
        f"{_STAGE_STATUS_SYMBOLS[stage.status]} Step {step} · "
        f"{descriptor.display_name} · {status_label}"
    )
    expanded = stage.status in {StageStatus.RUNNING, StageStatus.FAILED}

    with st.expander(label, expanded=expanded):
        overview_tab, output_tab, inputs_tab, technical_tab = st.tabs(
            ("Overview", "Trusted output", "Inputs", "Technical")
        )
        with overview_tab:
            st.caption(descriptor.responsibility)
            st.markdown(f"**Status:** {status_label}")
            st.markdown("**Consumes:** " + ", ".join(descriptor.input_artifact_labels))
            st.markdown(f"**Produces:** {descriptor.output_artifact_label}")
            if presentation.blocked_by is not None:
                blocker = STAGE_DESCRIPTORS[presentation.blocked_by].display_name
                st.warning(
                    f"Not executed because the mandatory upstream {blocker} stage failed."
                )
            if stage.status is StageStatus.FAILED and stage.error is not None:
                st.error(f"{stage.error.kind.value}: {stage.error.message}")

        with output_tab:
            if stage.status is StageStatus.COMPLETED:
                _render_sections(output_sections(stage))
            elif stage.status is StageStatus.FAILED:
                st.info("No trusted output is available for this failed stage.")
            else:
                st.info("No trusted output is available for this stage.")

        with inputs_tab:
            if stage.inputs is None:
                st.info("This agent has not received an input snapshot.")
            else:
                _render_value(stage.inputs)

        with technical_tab:
            if stage.status in {StageStatus.COMPLETED, StageStatus.FAILED}:
                st.json(stage.model_dump(mode="json"))
            else:
                st.info("Technical detail becomes available after the stage is reached.")


def _render_agent_grid(review: Review | None) -> None:
    st.markdown("#### Final synthesis")
    if review is None:
        _render_preview_card(StageIdentity.COORDINATOR)
    else:
        coordinator = next(
            item
            for item in stage_presentations(review)
            if item.execution.identity is StageIdentity.COORDINATOR
        )
        _render_stage_card(coordinator)

    st.markdown("#### Specialist workspace")
    specialist_identities = (
        StageIdentity.ANALYST,
        StageIdentity.SOLUTION_ARCHITECT,
        StageIdentity.RISK_REVIEWER,
        StageIdentity.CRITIC,
    )
    presentations = (
        {}
        if review is None
        else {item.execution.identity: item for item in stage_presentations(review)}
    )
    for first, second in (
        specialist_identities[:2],
        specialist_identities[2:],
    ):
        left, right = st.columns(2, gap="medium")
        with left:
            if review is None:
                _render_preview_card(first)
            else:
                _render_stage_card(presentations[first])
        with right:
            if review is None:
                _render_preview_card(second)
            else:
                _render_stage_card(presentations[second])


def _render_topology_preview() -> None:
    st.subheader("Agent workspace")
    _render_review_summary(None)
    _render_agent_grid(None)


def _render_process(review: Review) -> None:
    st.subheader("Agent workspace")
    _render_review_summary(review)
    _render_agent_grid(review)


def _render_submitted_input(review: Review) -> None:
    review_input = review.review_input
    case_label = review_input.title or "Untitled review case"
    with st.expander(f"Submitted case · {case_label}", expanded=False):
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


def _render_final(review: Review) -> None:
    final = final_result(review)
    if final is None:
        return
    st.header("Decision workspace")
    with st.container(border=True):
        st.markdown("### Final result")
        overview_tab, alternatives_tab, risks_tab, evidence_tab, technical_tab = st.tabs(
            ("Overview", "Alternatives", "Risks", "Evidence & next steps", "Technical")
        )
        with overview_tab:
            st.markdown(
                f"**Recommendation outcome:** `{final.recommendation_outcome.value}`"
            )
            st.markdown("**Situation summary**")
            st.write(final.situation_summary)
            st.markdown("**Preferred alternative**")
            _render_value(final.preferred_alternative_id)
            st.markdown("**Conclusion rationale**")
            st.write(final.conclusion_rationale)
            st.markdown("**Qualitative confidence**")
            st.code(final.confidence.value)
            st.warning(final.decision_support_notice)
        with alternatives_tab:
            st.markdown("**Ranked alternatives**")
            _render_value(final.ranked_alternatives)
        with risks_tab:
            st.markdown("**Principal risks**")
            _render_value(final.principal_risks)
        with evidence_tab:
            st.markdown("**Unresolved questions**")
            _render_value(final.unresolved_questions)
            st.markdown("**Criticism dispositions**")
            _render_value(final.criticism_dispositions)
            st.markdown("**Next validation step (advisory)**")
            st.write(final.next_validation_step)
        with technical_tab:
            st.json(final.model_dump(mode="json"))


def _render_new_review() -> None:
    st.caption(
        "Starting a new Review clears the current in-memory result. No history is retained."
    )
    if st.button("New Review", key=NEW_REVIEW_KEY, use_container_width=True):
        for key in RESET_WIDGET_KEYS:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()


def _render_active_case_sidebar(state: ReviewUiState) -> None:
    with st.sidebar:
        st.header("Review case")
        if state.review is None:
            st.info("No submitted case is available for this run.")
        else:
            _render_submitted_input(state.review)
        _render_new_review()


def _render_active_state(state: ReviewUiState) -> None:
    if state.error is not None:
        st.error(state.error.public_message)
    review = state.review
    if review is None:
        _render_topology_preview()
        return
    _render_process(review)
    if state.phase is UiPhase.RESULT:
        _render_final(review)


def _draft_from_widgets() -> ReviewInputDraft:
    return ReviewInputDraft(
        title=st.session_state[TITLE_KEY],
        description=st.session_state[DESCRIPTION_KEY],
        objective=st.session_state[OBJECTIVE_KEY],
        constraints_text=st.session_state[CONSTRAINTS_KEY],
        context_text=st.session_state[CONTEXT_KEY],
        stated_facts_text=st.session_state[STATED_FACTS_KEY],
    )


def _apply_imported_case(case: MarkdownReviewCase) -> None:
    st.session_state[TITLE_KEY] = case.title
    st.session_state[DESCRIPTION_KEY] = case.description
    st.session_state[OBJECTIVE_KEY] = case.objective
    st.session_state[CONSTRAINTS_KEY] = "\n".join(case.constraints)
    st.session_state[CONTEXT_KEY] = "\n".join(case.context)
    st.session_state[STATED_FACTS_KEY] = "\n".join(case.stated_facts)


def _process_markdown_upload(uploaded: UploadedFile | None) -> None:
    if uploaded is None:
        for key in (MARKDOWN_DIGEST_KEY, MARKDOWN_ERROR_KEY, MARKDOWN_SUCCESS_KEY):
            st.session_state.pop(key, None)
        return

    content = uploaded.getvalue()
    digest = sha256(content).hexdigest()
    if st.session_state.get(MARKDOWN_DIGEST_KEY) == digest:
        return
    st.session_state[MARKDOWN_DIGEST_KEY] = digest
    st.session_state.pop(MARKDOWN_ERROR_KEY, None)
    st.session_state.pop(MARKDOWN_SUCCESS_KEY, None)
    try:
        imported = decode_markdown_case(content)
    except MarkdownCaseError as error:
        st.session_state[MARKDOWN_ERROR_KEY] = str(error)
        return
    _apply_imported_case(imported)
    st.session_state[MARKDOWN_SUCCESS_KEY] = (
        "Case imported. Review the editable fields before starting."
    )


def _render_case_editor_sidebar() -> ReviewInputDraft | None:
    submitted = False
    with st.sidebar:
        st.header("Review case")
        st.caption("Import a UTF-8 Markdown case or complete the fields manually.")
        uploaded = st.file_uploader(
            "Import Markdown",
            type=("md", "markdown"),
            accept_multiple_files=False,
            max_upload_size=1,
            key=MARKDOWN_UPLOAD_KEY,
        )
        _process_markdown_upload(uploaded)
        import_error = st.session_state.get(MARKDOWN_ERROR_KEY)
        import_success = st.session_state.get(MARKDOWN_SUCCESS_KEY)
        if isinstance(import_error, str):
            st.error(import_error)
        elif isinstance(import_success, str):
            st.success(import_success)

        with st.expander("Case editor", expanded=True):
            with st.form("arb_review_form"):
                st.text_input("Title (optional)", key=TITLE_KEY)
                st.text_area("Description (required)", key=DESCRIPTION_KEY, height=140)
                st.text_area("Objective (optional)", key=OBJECTIVE_KEY, height=100)
                st.text_area(
                    "Constraints (optional, one per line)",
                    key=CONSTRAINTS_KEY,
                    height=110,
                )
                st.text_area(
                    "Context (optional, one per line)",
                    key=CONTEXT_KEY,
                    height=110,
                )
                st.text_area(
                    "Stated facts (optional, one per line)",
                    key=STATED_FACTS_KEY,
                    height=110,
                )
                submitted = st.form_submit_button(
                    "Start Review",
                    key=START_KEY,
                    type="primary",
                    use_container_width=True,
                )
        st.caption("Importing or editing never starts agents automatically.")
    return _draft_from_widgets() if submitted else None


def _execute_review(state: ReviewUiState, executor: ReviewExecutor) -> None:
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
        "Trace five specialized agents from evidence-rich case input to transparent "
        "decision support."
    )
    state = _session_state()
    if state.phase is UiPhase.FORM:
        draft = _render_case_editor_sidebar()
        if draft is not None:
            try:
                state = begin_review(state, draft)
            except (ValidationError, ValueError):
                with st.sidebar:
                    st.error("Description is required before the Review can start.")
            else:
                _store_state(state)
                st.rerun()
        _render_topology_preview()
        return

    _render_active_case_sidebar(state)
    if state.phase is UiPhase.EXECUTING:
        _execute_review(state, executor)
        return
    _render_active_state(state)
