from collections.abc import Mapping

from agentic_review_board.domain.analysis import ProblemAnalysis
from agentic_review_board.domain.critics import CriticalReview
from agentic_review_board.domain.final_reviews import FinalReview
from agentic_review_board.domain.review import ReviewInput
from agentic_review_board.domain.risks import RiskAssessment
from agentic_review_board.domain.solutions import (
    SolutionAlternative,
    SolutionAlternatives,
)
from agentic_review_board.participants.coordinator import Coordinator


class RecordingLLM:
    def __init__(self, response: Mapping[str, object]) -> None:
        self.response = response
        self.calls: list[tuple[str, Mapping[str, object]]] = []

    def generate_structured(
        self,
        *,
        role: str,
        payload: Mapping[str, object],
    ) -> Mapping[str, object]:
        self.calls.append((role, payload))
        return self.response


def review_input() -> ReviewInput:
    return ReviewInput(
        title="Deployment review",
        description="Review a proposed deployment change.",
        objective="Choose the most suitable approach.",
        constraints=("Must run offline.",),
        context=("The environment is locally managed.",),
        stated_facts=("Local compute is available.",),
    )


def problem_analysis() -> ProblemAnalysis:
    return ProblemAnalysis(
        objective="Choose a suitable deployment approach.",
        facts=(),
        constraints=(),
        assumptions=(),
        missing_information=(),
        uncertainties=(),
    )


def solution_alternative(
    alternative_id: str,
    name: str,
    description: str,
) -> SolutionAlternative:
    return SolutionAlternative(
        id=alternative_id,
        name=name,
        description=description,
        advantages=("Works offline.",),
        disadvantages=("Requires local maintenance.",),
        assumptions=("Local compute remains available.",),
        implementation_complexity="MEDIUM",
        relevant_constraints=(),
    )


def solution_alternatives() -> SolutionAlternatives:
    return SolutionAlternatives(
        alternatives=(
            solution_alternative(
                "ALT-001",
                "Local deployment",
                "Deploy the capability locally.",
            ),
            solution_alternative(
                "ALT-002",
                "Managed appliance",
                "Use a managed on-premises appliance.",
            ),
        ),
    )


def risk_assessment() -> RiskAssessment:
    return RiskAssessment(risks=(), overall_observations=())


def critical_review() -> CriticalReview:
    return CriticalReview()


def recommended_response() -> dict[str, object]:
    return {
        "situation_summary": "Two viable offline approaches remain.",
        "ranked_alternatives": [
            {
                "alternative_id": "ALT-002",
                "position": 2,
                "justification": "A viable fallback.",
                "considerations": ["Confirm appliance support."],
            },
            {
                "alternative_id": "ALT-001",
                "position": 1,
                "justification": "Best aligned with current constraints.",
                "considerations": ["Confirm operational ownership."],
            },
        ],
        "recommendation_outcome": "RECOMMENDED",
        "preferred_alternative_id": "ALT-001",
        "conclusion_rationale": "Current evidence supports local deployment.",
        "principal_risks": [],
        "unresolved_questions": [],
        "criticism_dispositions": [],
        "next_validation_step": "Confirm operational ownership.",
        "confidence": "MEDIUM",
    }


def test_coordinator_calls_exact_boundary_and_returns_separate_trusted_review() -> None:
    current_input = review_input()
    analysis = problem_analysis()
    alternatives = solution_alternatives()
    risks = risk_assessment()
    critique = critical_review()
    upstream = (current_input, analysis, alternatives, risks, critique)
    before = tuple(artifact.model_dump(mode="json") for artifact in upstream)
    llm = RecordingLLM(recommended_response())

    result = Coordinator(llm).coordinate(
        current_input,
        analysis,
        alternatives,
        risks,
        critique,
    )

    assert isinstance(result, FinalReview)
    assert result.preferred_alternative_id == "ALT-001"
    assert id(result) not in {id(artifact) for artifact in upstream}
    assert tuple(artifact.model_dump(mode="json") for artifact in upstream) == before

    assert llm.calls == [
        (
            "coordinator",
            {
                "review_input": before[0],
                "problem_analysis": before[1],
                "solution_alternatives": before[2],
                "risk_assessment": before[3],
                "critical_review": before[4],
            },
        )
    ]
