from collections.abc import Callable

import pytest

from agentic_review_board.domain.execution import (
    ReviewError,
    ReviewErrorKind,
    ReviewStatus,
)
from agentic_review_board.ui.app import (
    APPLICATION_ERROR,
    STARTUP_ERROR,
    ReviewInputDraft,
    ReviewUiState,
    UiError,
    UiErrorKind,
    UiPhase,
    application_failure,
    begin_review,
    can_start_review,
    finish_review,
    observe_review,
    reset_review,
    startup_failure,
    to_review_input,
)


def test_draft_preserves_every_non_empty_user_value_exactly() -> None:
    draft = ReviewInputDraft(
        description="  Decide café deployment.  \n",
        title="  Café title  ",
        objective="  Preserve Unicode ✓  ",
        constraints_text="  first constraint  \r\n\r\nsecond constraint\r\n  first constraint  ",
        context_text="one,two\n[not, json]",
        stated_facts_text="  café fact  \n\t\nfinal fact",
    )

    review_input = to_review_input(draft)

    assert review_input.description == "  Decide café deployment.  \n"
    assert review_input.title == "  Café title  "
    assert review_input.objective == "  Preserve Unicode ✓  "
    assert review_input.constraints == (
        "  first constraint  ",
        "second constraint",
        "  first constraint  ",
    )
    assert review_input.context == ("one,two", "[not, json]")
    assert review_input.stated_facts == ("  café fact  ", "final fact")


@pytest.mark.parametrize("description", ["", " ", "\t\r\n"])
def test_draft_rejects_whitespace_only_description(description: str) -> None:
    with pytest.raises(ValueError, match="description must not be empty"):
        to_review_input(ReviewInputDraft(description=description))


def test_draft_maps_whitespace_only_optional_values_to_absence() -> None:
    review_input = to_review_input(
        ReviewInputDraft(
            description="Review this.",
            title="  ",
            objective="\t",
            constraints_text=" \n\t",
            context_text="",
            stated_facts_text="\r\n",
        )
    )

    assert review_input.title is None
    assert review_input.objective is None
    assert review_input.constraints == ()
    assert review_input.context == ()
    assert review_input.stated_facts == ()


def test_state_transitions_keep_one_exact_review_snapshot() -> None:
    initial = ReviewUiState()
    assert initial.phase is UiPhase.FORM
    assert can_start_review(initial)

    executing = begin_review(initial, ReviewInputDraft(description="Review state."))
    created = executing.review
    assert created is not None
    assert created.status is ReviewStatus.CREATED
    assert executing.phase is UiPhase.EXECUTING
    assert not can_start_review(executing)

    running = created.start().start_analyst()
    observed = observe_review(executing, running)
    assert observed.review is running

    terminal = running.fail_analyst(
        ReviewError(kind=ReviewErrorKind.EXECUTION, message="Analyst execution failed")
    )
    terminal_observed = observe_review(observed, terminal)
    assert terminal_observed.phase is UiPhase.EXECUTING
    assert terminal_observed.review is terminal

    result = finish_review(terminal_observed, terminal)
    assert result.phase is UiPhase.RESULT
    assert result.review is terminal
    assert reset_review(result) == ReviewUiState()


def test_duplicate_start_and_cross_review_observation_are_rejected() -> None:
    executing = begin_review(
        ReviewUiState(),
        ReviewInputDraft(description="First Review."),
    )

    with pytest.raises(ValueError, match="review cannot start in the current UI phase"):
        begin_review(executing, ReviewInputDraft(description="Duplicate Review."))

    other = begin_review(
        ReviewUiState(),
        ReviewInputDraft(description="Other Review."),
    )
    assert other.review is not None
    with pytest.raises(ValueError, match="snapshot belongs to a different Review"):
        observe_review(executing, other.review.start())


def test_startup_and_application_failures_remain_outside_domain_state() -> None:
    executing = begin_review(
        ReviewUiState(),
        ReviewInputDraft(description="Failure boundary."),
    )
    startup = startup_failure(executing)
    assert startup == ReviewUiState(
        phase=UiPhase.APPLICATION_ERROR,
        error=STARTUP_ERROR,
    )

    assert executing.review is not None
    observed = observe_review(executing, executing.review.start())
    failed_ui = application_failure(observed)
    assert failed_ui.phase is UiPhase.APPLICATION_ERROR
    assert failed_ui.review is observed.review
    assert failed_ui.error is APPLICATION_ERROR
    assert failed_ui.review is not None
    assert all(stage.error is None for stage in failed_ui.review.stages)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: ReviewUiState(phase=UiPhase.FORM, error=STARTUP_ERROR),
        lambda: ReviewUiState(phase=UiPhase.EXECUTING),
        lambda: ReviewUiState(phase=UiPhase.RESULT),
        lambda: ReviewUiState(phase=UiPhase.APPLICATION_ERROR),
    ],
)
def test_inconsistent_ui_state_is_rejected(
    factory: Callable[[], ReviewUiState],
) -> None:
    with pytest.raises(ValueError, match="inconsistent UI state"):
        factory()


def test_ui_error_messages_are_fixed_and_contain_no_sensitive_detail() -> None:
    secret_markers = (
        "provider-secret",
        "Authorization",
        "Bearer",
        "/chat/completions",
        "raw output",
        "complete prompt",
    )

    assert STARTUP_ERROR.kind is UiErrorKind.STARTUP
    assert APPLICATION_ERROR.kind is UiErrorKind.APPLICATION
    assert STARTUP_ERROR != APPLICATION_ERROR
    for error in (STARTUP_ERROR, APPLICATION_ERROR):
        assert isinstance(error, UiError)
        assert error.public_message.strip()
        assert all(marker not in error.public_message for marker in secret_markers)
