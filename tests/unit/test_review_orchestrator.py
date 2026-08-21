from collections.abc import Mapping

from agentic_review_board.application.orchestrator import ReviewOrchestrator
from agentic_review_board.domain.execution import (
    AnalystStageInput,
    Review,
    ReviewStatus,
    SolutionArchitectStageInput,
    StageIdentity,
    StageStatus,
)
from agentic_review_board.domain.review import ReviewInput
from agentic_review_board.participants.analyst import Analyst
from agentic_review_board.participants.solution_architect import SolutionArchitect


class RecordingLLM:
    def __init__(
        self,
        responses: Mapping[str, Mapping[str, object]],
        events: list[str] | None = None,
    ) -> None:
        self._responses = responses
        self.events = events if events is not None else []
        self.calls: list[tuple[str, Mapping[str, object]]] = []

    def generate_structured(
        self,
        *,
        role: str,
        payload: Mapping[str, object],
    ) -> Mapping[str, object]:
        self.events.append(f"invoke:{role}")
        self.calls.append((role, payload))
        return self._responses[role]


def analyst_response() -> dict[str, object]:
    return {
        "objective": "Determine whether further evaluation is useful.",
        "facts": [],
        "constraints": [],
        "assumptions": [],
        "missing_information": [],
        "uncertainties": [],
    }


def two_alternative_response() -> dict[str, object]:
    return {
        "alternatives": [
            {
                "id": "ALT-001",
                "name": "Local deployment",
                "description": "Run the capability in the existing local environment.",
                "advantages": ["Keeps operation local."],
                "disadvantages": ["Requires local lifecycle management."],
                "assumptions": ["Suitable local compute is available."],
                "implementation_complexity": "MEDIUM",
                "relevant_constraints": [],
            },
            {
                "id": "ALT-002",
                "name": "Managed deployment",
                "description": "Run the capability in a managed environment.",
                "advantages": ["Reduces local operational work."],
                "disadvantages": ["Introduces an external operational dependency."],
                "assumptions": ["A managed environment is available."],
                "implementation_complexity": "MEDIUM",
                "relevant_constraints": [],
            },
        ]
    }


def zero_alternative_response() -> dict[str, object]:
    return {
        "alternatives": [],
        "generation_notes": {
            "explanation": "Current evidence is insufficient for useful alternatives.",
            "blocking_missing_information": [],
            "blocking_uncertainties": [],
        },
    }


def create_review() -> Review:
    return Review.create(
        ReviewInput(
            description="Review a proposed technical change.",
            title="Technical change review",
        )
    )


def test_orchestrator_executes_analyst_then_solution_architect_with_trusted_handoff(
    monkeypatch,
) -> None:
    events: list[str] = []
    original_start_analyst = Review.start_analyst
    original_start_solution_architect = Review.start_solution_architect

    def recording_start_analyst(self: Review) -> Review:
        events.append("record:analyst_inputs")
        return original_start_analyst(self)

    def recording_start_solution_architect(self: Review) -> Review:
        events.append("record:solution_architect_inputs")
        return original_start_solution_architect(self)

    monkeypatch.setattr(Review, "start_analyst", recording_start_analyst)
    monkeypatch.setattr(
        Review,
        "start_solution_architect",
        recording_start_solution_architect,
    )

    llm = RecordingLLM(
        {
            "analyst": analyst_response(),
            "solution_architect": two_alternative_response(),
        },
        events,
    )
    created = create_review()

    result = ReviewOrchestrator(Analyst(llm), SolutionArchitect(llm)).execute(created)

    assert created.status is ReviewStatus.CREATED
    assert result.status is ReviewStatus.RUNNING
    assert events == [
        "record:analyst_inputs",
        "invoke:analyst",
        "record:solution_architect_inputs",
        "invoke:solution_architect",
    ]
    assert [role for role, _ in llm.calls] == ["analyst", "solution_architect"]

    analyst_stage = result.stage(StageIdentity.ANALYST)
    architect_stage = result.stage(StageIdentity.SOLUTION_ARCHITECT)

    assert analyst_stage.status is StageStatus.COMPLETED
    assert architect_stage.status is StageStatus.COMPLETED
    assert isinstance(analyst_stage.inputs, AnalystStageInput)
    assert isinstance(architect_stage.inputs, SolutionArchitectStageInput)
    assert analyst_stage.inputs.review_input is result.review_input
    assert architect_stage.inputs.review_input is result.review_input
    assert architect_stage.inputs.problem_analysis is analyst_stage.output

    for identity in (
        StageIdentity.RISK_REVIEWER,
        StageIdentity.CRITIC,
        StageIdentity.COORDINATOR,
    ):
        stage = result.stage(identity)
        assert stage.status is StageStatus.PENDING
        assert stage.inputs is None
        assert stage.output is None
        assert stage.error is None


def test_orchestrator_accepts_valid_zero_alternative_result_without_false_failure() -> None:
    llm = RecordingLLM(
        {
            "analyst": analyst_response(),
            "solution_architect": zero_alternative_response(),
        }
    )

    result = ReviewOrchestrator(Analyst(llm), SolutionArchitect(llm)).execute(create_review())

    architect_stage = result.stage(StageIdentity.SOLUTION_ARCHITECT)
    assert architect_stage.status is StageStatus.COMPLETED
    assert architect_stage.output is not None
    assert architect_stage.output.alternatives == ()
    assert result.status is ReviewStatus.RUNNING
