from collections.abc import Mapping

import pytest

from agentic_review_board.domain.analysis import (
    AnalysisFinding,
    FactFinding,
    ProblemAnalysis,
    ReviewInputSource,
)
from agentic_review_board.domain.critics import (
    CriticalReview,
    CriticReferenceKind,
)
from agentic_review_board.domain.review import ReviewInput
from agentic_review_board.domain.risks import RiskAssessment
from agentic_review_board.domain.solutions import GenerationNotes, SolutionAlternatives
from agentic_review_board.participants.critic import Critic, CriticOutputError


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


def review_input(
    *,
    title: str | None = "Deployment review",
    objective: str | None = "Assess a proposed deployment.",
    constraints: tuple[str, ...] = ("Must run offline", "Keep deployment simple"),
    context: tuple[str, ...] = ("The current environment is locally managed.",),
    stated_facts: tuple[str, ...] = (
        "The capability must remain available without internet access.",
    ),
) -> ReviewInput:
    return ReviewInput(
        title=title,
        description="Review a proposed technical deployment change.",
        objective=objective,
        constraints=constraints,
        context=context,
        stated_facts=stated_facts,
    )


def problem_analysis(*, duplicate_constraint_text: bool = False) -> ProblemAnalysis:
    constraints = (
        (
            AnalysisFinding(id="CON-001", text="Must run offline"),
            AnalysisFinding(id="CON-002", text="Must run offline"),
        )
        if duplicate_constraint_text
        else (
            AnalysisFinding(id="CON-001", text="Must run offline"),
            AnalysisFinding(id="CON-002", text="Keep deployment simple"),
        )
    )
    return ProblemAnalysis(
        objective="Assess the deployment approaches and their constraints.",
        facts=(
            FactFinding(
                id="FACT-001",
                text="The capability must remain available without internet access.",
                source_ref=ReviewInputSource.STATED_FACTS,
            ),
        ),
        constraints=constraints,
        assumptions=(
            AnalysisFinding(id="ASM-001", text="Local compute is available."),
        ),
        missing_information=(
            AnalysisFinding(id="MISS-001", text="Peak load is unknown."),
        ),
        uncertainties=(
            AnalysisFinding(id="UNC-001", text="Operational ownership is unclear."),
        ),
    )


def solution_alternatives() -> SolutionAlternatives:
    return SolutionAlternatives(
        alternatives=(),
        generation_notes=GenerationNotes(
            explanation="Current evidence is insufficient for meaningful alternatives.",
            blocking_missing_information=(),
            blocking_uncertainties=(),
        ),
    )


def risk_assessment() -> RiskAssessment:
    return RiskAssessment(risks=(), overall_observations=())


def critic_reference(
    source: str,
    kind: str,
    *,
    item_id: str | None = None,
    value: str | None = None,
) -> dict[str, object]:
    reference: dict[str, object] = {
        "source": source,
        "kind": kind,
    }
    if item_id is not None:
        reference["item_id"] = item_id
    if value is not None:
        reference["value"] = value
    return reference


def validated_point_response(reference: dict[str, object]) -> dict[str, object]:
    return {
        "validated_points": [
            {
                "id": "VALID-001",
                "target_reference": reference,
                "rationale": "The referenced point is explicit in the current review.",
            }
        ]
    }


def run_critic(
    response: Mapping[str, object],
    *,
    current_input: ReviewInput | None = None,
    analysis: ProblemAnalysis | None = None,
) -> CriticalReview:
    return Critic(RecordingLLM(response)).review(
        current_input or review_input(),
        analysis or problem_analysis(),
        solution_alternatives(),
        risk_assessment(),
    )


def test_critic_returns_trusted_empty_review_and_uses_exact_provider_payload() -> None:
    current_input = review_input()
    analysis = problem_analysis()
    alternatives = solution_alternatives()
    risks = risk_assessment()
    llm = RecordingLLM({})

    result = Critic(llm).review(current_input, analysis, alternatives, risks)

    assert isinstance(result, CriticalReview)
    assert result == CriticalReview()
    assert len(llm.calls) == 1
    role, payload = llm.calls[0]
    assert role == "critic"
    assert set(payload) == {
        "review_input",
        "problem_analysis",
        "solution_alternatives",
        "risk_assessment",
    }
    assert payload["review_input"] == current_input.model_dump(mode="json")
    assert payload["problem_analysis"] == analysis.model_dump(mode="json")
    assert payload["solution_alternatives"] == alternatives.model_dump(mode="json")
    assert payload["risk_assessment"] == risks.model_dump(mode="json")


@pytest.mark.parametrize(
    ("kind", "value"),
    [
        ("DESCRIPTION", "Review a proposed technical deployment change."),
        ("TITLE", "Deployment review"),
        ("REVIEW_OBJECTIVE", "Assess a proposed deployment."),
        ("REVIEW_CONSTRAINT", "Must run offline"),
        ("CONTEXT", "The current environment is locally managed."),
        ("STATED_FACT", "The capability must remain available without internet access."),
    ],
)
def test_review_input_reference_resolves_every_supported_kind(
    kind: str,
    value: str,
) -> None:
    result = run_critic(
        validated_point_response(
            critic_reference("REVIEW_INPUT", kind, value=value)
        )
    )

    assert result.validated_points[0].target_reference.kind.value == kind


@pytest.mark.parametrize(
    ("kind", "generated"),
    [
        ("DESCRIPTION", "Different description"),
        ("TITLE", "Different title"),
        ("REVIEW_OBJECTIVE", "Different objective"),
        ("REVIEW_CONSTRAINT", "Unknown constraint"),
        ("CONTEXT", "Unknown context"),
        ("STATED_FACT", "Unknown fact"),
    ],
)
def test_review_input_reference_rejects_unknown_or_mismatched_value(
    kind: str,
    generated: str,
) -> None:
    with pytest.raises(CriticOutputError):
        run_critic(
            validated_point_response(
                critic_reference("REVIEW_INPUT", kind, value=generated)
            )
        )


@pytest.mark.parametrize("kind", ["TITLE", "REVIEW_OBJECTIVE"])
def test_review_input_optional_scalar_reference_fails_when_source_is_absent(
    kind: str,
) -> None:
    current_input = (
        review_input(title=None)
        if kind == "TITLE"
        else review_input(objective=None)
    )

    with pytest.raises(CriticOutputError):
        run_critic(
            validated_point_response(
                critic_reference("REVIEW_INPUT", kind, value="Generated value")
            ),
            current_input=current_input,
        )


@pytest.mark.parametrize(
    ("kind", "current_input", "value"),
    [
        (
            "REVIEW_CONSTRAINT",
            review_input(constraints=("Must run offline", "Must run offline")),
            "Must run offline",
        ),
        (
            "CONTEXT",
            review_input(
                context=(
                    "The current environment is locally managed.",
                    "The current environment is locally managed.",
                )
            ),
            "The current environment is locally managed.",
        ),
        (
            "STATED_FACT",
            review_input(
                stated_facts=(
                    "The capability must remain available without internet access.",
                    "The capability must remain available without internet access.",
                )
            ),
            "The capability must remain available without internet access.",
        ),
    ],
)
def test_review_input_collection_reference_fails_when_value_is_ambiguous(
    kind: str,
    current_input: ReviewInput,
    value: str,
) -> None:
    with pytest.raises(CriticOutputError):
        run_critic(
            validated_point_response(
                critic_reference("REVIEW_INPUT", kind, value=value)
            ),
            current_input=current_input,
        )


@pytest.mark.parametrize(
    ("kind", "finding_id", "text"),
    [
        (
            "PROBLEM_FACT",
            "FACT-001",
            "The capability must remain available without internet access.",
        ),
        ("PROBLEM_CONSTRAINT", "CON-001", "Must run offline"),
        ("PROBLEM_ASSUMPTION", "ASM-001", "Local compute is available."),
        ("MISSING_INFORMATION", "MISS-001", "Peak load is unknown."),
        ("UNCERTAINTY", "UNC-001", "Operational ownership is unclear."),
    ],
)
def test_problem_analysis_reference_resolves_all_findings_by_id_and_text(
    kind: str,
    finding_id: str,
    text: str,
) -> None:
    result = run_critic(
        validated_point_response(
            critic_reference(
                "PROBLEM_ANALYSIS",
                kind,
                item_id=finding_id,
                value=text,
            )
        )
    )

    assert result.validated_points[0].target_reference.item_id == finding_id


@pytest.mark.parametrize(
    ("kind", "text"),
    [
        (
            "PROBLEM_FACT",
            "The capability must remain available without internet access.",
        ),
        ("PROBLEM_CONSTRAINT", "Must run offline"),
        ("PROBLEM_ASSUMPTION", "Local compute is available."),
        ("MISSING_INFORMATION", "Peak load is unknown."),
        ("UNCERTAINTY", "Operational ownership is unclear."),
    ],
)
def test_problem_analysis_reference_resolves_all_findings_by_unique_text(
    kind: str,
    text: str,
) -> None:
    result = run_critic(
        validated_point_response(
            critic_reference("PROBLEM_ANALYSIS", kind, value=text)
        )
    )

    assert result.validated_points[0].target_reference.value == text


def test_problem_analysis_objective_reference_resolves_exact_scalar() -> None:
    result = run_critic(
        validated_point_response(
            critic_reference(
                "PROBLEM_ANALYSIS",
                "PROBLEM_OBJECTIVE",
                value="Assess the deployment approaches and their constraints.",
            )
        )
    )

    reference = result.validated_points[0].target_reference
    assert reference.kind is CriticReferenceKind.PROBLEM_OBJECTIVE


@pytest.mark.parametrize(
    "reference",
    [
        critic_reference(
            "PROBLEM_ANALYSIS",
            "PROBLEM_CONSTRAINT",
            item_id="CON-999",
            value="Must run offline",
        ),
        critic_reference(
            "PROBLEM_ANALYSIS",
            "PROBLEM_CONSTRAINT",
            item_id="CON-001",
            value="Different text",
        ),
        critic_reference(
            "PROBLEM_ANALYSIS",
            "PROBLEM_CONSTRAINT",
            value="Unknown constraint",
        ),
        critic_reference(
            "PROBLEM_ANALYSIS",
            "PROBLEM_OBJECTIVE",
            value="Different objective",
        ),
    ],
)
def test_problem_analysis_reference_rejects_unknown_or_mismatched_target(
    reference: dict[str, object],
) -> None:
    with pytest.raises(CriticOutputError):
        run_critic(validated_point_response(reference))


def test_problem_analysis_text_only_reference_fails_when_value_is_ambiguous() -> None:
    with pytest.raises(CriticOutputError):
        run_critic(
            validated_point_response(
                critic_reference(
                    "PROBLEM_ANALYSIS",
                    "PROBLEM_CONSTRAINT",
                    value="Must run offline",
                )
            ),
            analysis=problem_analysis(duplicate_constraint_text=True),
        )
