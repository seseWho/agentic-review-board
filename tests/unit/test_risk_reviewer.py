from collections.abc import Mapping

import pytest

from agentic_review_board.domain.analysis import (
    AnalysisFinding,
    FactFinding,
    ProblemAnalysis,
    ReviewInputSource,
)
from agentic_review_board.domain.review import ReviewInput
from agentic_review_board.domain.risks import (
    ProblemAnalysisBasisReference,
    ProblemAnalysisFindingKind,
    RiskAssessment,
)
from agentic_review_board.domain.shared import QualitativeLevel
from agentic_review_board.domain.solutions import (
    ConstraintReference,
    ConstraintReferenceKind,
    ConstraintSource,
    GenerationNotes,
    SolutionAlternative,
    SolutionAlternatives,
)
from agentic_review_board.participants.risk_reviewer import (
    RiskReviewer,
    RiskReviewerOutputError,
)


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
    objective: str | None = "Assess material deployment risk.",
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


def problem_analysis(
    *,
    duplicate_constraint_text: bool = False,
) -> ProblemAnalysis:
    constraints = (
        AnalysisFinding(id="CON-001", text="Must run offline"),
        AnalysisFinding(id="CON-002", text="Must run offline"),
    ) if duplicate_constraint_text else (
        AnalysisFinding(id="CON-001", text="Must run offline"),
        AnalysisFinding(id="CON-002", text="Keep deployment simple"),
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


def constraint_reference() -> ConstraintReference:
    return ConstraintReference(
        source=ConstraintSource.PROBLEM_ANALYSIS,
        kind=ConstraintReferenceKind.ID,
        value="CON-001",
    )


def solution_alternatives(
    *,
    duplicate_advantage_text: bool = False,
    duplicate_constraint_reference: bool = False,
) -> SolutionAlternatives:
    advantages = (
        "Keeps operation local.",
        "Keeps operation local.",
    ) if duplicate_advantage_text else (
        "Keeps operation local.",
        "Avoids a network dependency.",
    )
    reference = constraint_reference()
    relevant_constraints = (reference, reference) if duplicate_constraint_reference else (reference,)

    return SolutionAlternatives(
        alternatives=(
            SolutionAlternative(
                id="ALT-001",
                name="Local deployment",
                description="Run the capability in the existing local environment.",
                advantages=advantages,
                disadvantages=("Requires local lifecycle management.",),
                assumptions=("Local compute is available.",),
                implementation_complexity=QualitativeLevel.MEDIUM,
                relevant_constraints=relevant_constraints,
            ),
            SolutionAlternative(
                id="ALT-002",
                name="Managed edge deployment",
                description="Run the capability in a managed edge environment.",
                advantages=("Reduces local lifecycle work.",),
                disadvantages=("Introduces an external operational dependency.",),
                assumptions=("A suitable managed environment is available.",),
                implementation_complexity=QualitativeLevel.HIGH,
                relevant_constraints=(),
            ),
        )
    )


def zero_alternatives() -> SolutionAlternatives:
    return SolutionAlternatives(
        alternatives=(),
        generation_notes=GenerationNotes(
            explanation="Current evidence is insufficient for meaningful alternatives.",
            blocking_missing_information=(),
            blocking_uncertainties=(),
        ),
    )


def review_input_basis(field: str, value: object) -> dict[str, object]:
    return {
        "source": "REVIEW_INPUT",
        "field": field,
        "value": value,
    }


def problem_analysis_basis(
    kind: str,
    text: str,
    *,
    finding_id: str | None = None,
) -> dict[str, object]:
    reference: dict[str, object] = {
        "source": "PROBLEM_ANALYSIS",
        "kind": kind,
        "text": text,
    }
    if finding_id is not None:
        reference["id"] = finding_id
    return reference


def solution_basis(
    alternative_id: str,
    characteristic: str,
    value: object,
) -> dict[str, object]:
    return {
        "source": "SOLUTION_ALTERNATIVE",
        "alternative_id": alternative_id,
        "characteristic": characteristic,
        "value": value,
    }


def risk_response(
    *,
    basis: list[dict[str, object]] | None = None,
    scope: dict[str, object] | None = None,
    risk_id: str = "RISK-001",
) -> dict[str, object]:
    return {
        "risks": [
            {
                "id": risk_id,
                "category": "operational",
                "description": "Lifecycle ownership may create operational burden.",
                "affected_scope": scope or {"kind": "OVERALL", "alternative_ids": []},
                "severity": "MEDIUM",
                "basis": basis or [
                    review_input_basis(
                        "description",
                        "Review a proposed technical deployment change.",
                    )
                ],
                "mitigation": "Define explicit operational ownership.",
                "residual_uncertainty": "Actual support effort is not yet measured.",
            }
        ],
        "overall_observations": ["Risk remains qualitative at this stage."],
    }


def assess(
    response: Mapping[str, object],
    *,
    current_input: ReviewInput | None = None,
    analysis: ProblemAnalysis | None = None,
    alternatives: SolutionAlternatives | None = None,
) -> RiskAssessment:
    return RiskReviewer(RecordingLLM(response)).assess(
        current_input or review_input(),
        analysis or problem_analysis(),
        alternatives or solution_alternatives(),
    )


def test_risk_reviewer_returns_trusted_assessment_and_uses_exact_provider_payload() -> None:
    current_input = review_input()
    analysis = problem_analysis()
    alternatives = solution_alternatives()
    llm = RecordingLLM(risk_response())

    result = RiskReviewer(llm).assess(current_input, analysis, alternatives)

    assert isinstance(result, RiskAssessment)
    assert len(result.risks) == 1
    assert len(llm.calls) == 1
    role, payload = llm.calls[0]
    assert role == "risk_reviewer"
    assert set(payload) == {"review_input", "problem_analysis", "solution_alternatives"}
    assert payload["review_input"] == current_input.model_dump(mode="json")
    assert payload["problem_analysis"] == analysis.model_dump(mode="json")
    assert payload["solution_alternatives"] == alternatives.model_dump(mode="json")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("description", "Review a proposed technical deployment change."),
        ("title", "Deployment review"),
        ("objective", "Assess material deployment risk."),
        ("constraints", "Must run offline"),
        ("context", "The current environment is locally managed."),
        ("stated_facts", "The capability must remain available without internet access."),
    ],
)
def test_review_input_basis_resolves_every_supported_source(field: str, value: str) -> None:
    result = assess(risk_response(basis=[review_input_basis(field, value)]))

    assert result.risks[0].basis


@pytest.mark.parametrize(
    ("field", "actual", "generated"),
    [
        ("description", "Review a proposed technical deployment change.", "Different description"),
        ("title", "Deployment review", "Different title"),
        ("objective", "Assess material deployment risk.", "Different objective"),
    ],
)
def test_review_input_scalar_basis_requires_exact_value(
    field: str,
    actual: str,
    generated: str,
) -> None:
    assert actual != generated

    with pytest.raises(RiskReviewerOutputError):
        assess(risk_response(basis=[review_input_basis(field, generated)]))


@pytest.mark.parametrize("field", ["title", "objective"])
def test_review_input_optional_scalar_basis_fails_when_source_is_absent(field: str) -> None:
    current_input = review_input(title=None) if field == "title" else review_input(objective=None)

    with pytest.raises(RiskReviewerOutputError):
        assess(
            risk_response(basis=[review_input_basis(field, "Generated unsupported value")]),
            current_input=current_input,
        )


@pytest.mark.parametrize(
    ("field", "current_input"),
    [
        (
            "constraints",
            review_input(constraints=("Must run offline", "Must run offline")),
        ),
        (
            "context",
            review_input(
                context=(
                    "The current environment is locally managed.",
                    "The current environment is locally managed.",
                )
            ),
        ),
        (
            "stated_facts",
            review_input(
                stated_facts=(
                    "The capability must remain available without internet access.",
                    "The capability must remain available without internet access.",
                )
            ),
        ),
    ],
)
def test_review_input_collection_basis_fails_when_duplicate_text_is_ambiguous(
    field: str,
    current_input: ReviewInput,
) -> None:
    value = current_input.model_dump(mode="json")[field][0]

    with pytest.raises(RiskReviewerOutputError):
        assess(
            risk_response(basis=[review_input_basis(field, value)]),
            current_input=current_input,
        )


@pytest.mark.parametrize(
    ("kind", "finding_id", "text"),
    [
        (
            "FACT",
            "FACT-001",
            "The capability must remain available without internet access.",
        ),
        ("CONSTRAINT", "CON-001", "Must run offline"),
        ("ASSUMPTION", "ASM-001", "Local compute is available."),
        ("MISSING_INFORMATION", "MISS-001", "Peak load is unknown."),
        ("UNCERTAINTY", "UNC-001", "Operational ownership is unclear."),
    ],
)
def test_problem_analysis_basis_resolves_all_finding_kinds_by_id_and_text(
    kind: str,
    finding_id: str,
    text: str,
) -> None:
    result = assess(
        risk_response(
            basis=[problem_analysis_basis(kind, text, finding_id=finding_id)]
        )
    )

    assert result.risks[0].basis


@pytest.mark.parametrize(
    ("kind", "text"),
    [
        ("FACT", "The capability must remain available without internet access."),
        ("CONSTRAINT", "Must run offline"),
        ("ASSUMPTION", "Local compute is available."),
        ("MISSING_INFORMATION", "Peak load is unknown."),
        ("UNCERTAINTY", "Operational ownership is unclear."),
    ],
)
def test_problem_analysis_basis_resolves_by_unique_text_without_id(
    kind: str,
    text: str,
) -> None:
    result = assess(risk_response(basis=[problem_analysis_basis(kind, text)]))

    assert result.risks[0].basis


def test_problem_analysis_assumption_basis_remains_explicitly_an_assumption() -> None:
    result = assess(
        risk_response(
            basis=[
                problem_analysis_basis(
                    "ASSUMPTION",
                    "Local compute is available.",
                    finding_id="ASM-001",
                )
            ]
        )
    )

    reference = result.risks[0].basis[0]
    assert isinstance(reference, ProblemAnalysisBasisReference)
    assert reference.kind is ProblemAnalysisFindingKind.ASSUMPTION


@pytest.mark.parametrize(
    "reference",
    [
        problem_analysis_basis("CONSTRAINT", "Must run offline", finding_id="CON-999"),
        problem_analysis_basis("CONSTRAINT", "Different text", finding_id="CON-001"),
        problem_analysis_basis("CONSTRAINT", "Unknown constraint"),
    ],
)
def test_problem_analysis_basis_rejects_unknown_or_mismatched_reference(
    reference: dict[str, object],
) -> None:
    with pytest.raises(RiskReviewerOutputError):
        assess(risk_response(basis=[reference]))


def test_problem_analysis_text_only_basis_fails_when_text_is_ambiguous() -> None:
    with pytest.raises(RiskReviewerOutputError):
        assess(
            risk_response(
                basis=[problem_analysis_basis("CONSTRAINT", "Must run offline")]
            ),
            analysis=problem_analysis(duplicate_constraint_text=True),
        )


@pytest.mark.parametrize(
    ("characteristic", "value"),
    [
        ("DESCRIPTION", "Run the capability in the existing local environment."),
        ("ADVANTAGE", "Keeps operation local."),
        ("DISADVANTAGE", "Requires local lifecycle management."),
        ("ASSUMPTION", "Local compute is available."),
        ("IMPLEMENTATION_COMPLEXITY", "MEDIUM"),
        (
            "RELEVANT_CONSTRAINT",
            {"source": "PROBLEM_ANALYSIS", "kind": "ID", "value": "CON-001"},
        ),
    ],
)
def test_solution_alternative_basis_resolves_every_supported_characteristic(
    characteristic: str,
    value: object,
) -> None:
    result = assess(
        risk_response(
            basis=[solution_basis("ALT-001", characteristic, value)]
        )
    )

    assert result.risks[0].basis


def test_solution_alternative_basis_rejects_unknown_alternative() -> None:
    with pytest.raises(RiskReviewerOutputError):
        assess(
            risk_response(
                basis=[
                    solution_basis(
                        "ALT-999",
                        "DESCRIPTION",
                        "Run the capability in the existing local environment.",
                    )
                ]
            )
        )


@pytest.mark.parametrize(
    ("characteristic", "value"),
    [
        ("DESCRIPTION", "Different description"),
        ("ADVANTAGE", "Different advantage"),
        ("DISADVANTAGE", "Different disadvantage"),
        ("ASSUMPTION", "Different assumption"),
        ("IMPLEMENTATION_COMPLEXITY", "HIGH"),
    ],
)
def test_solution_alternative_basis_rejects_characteristic_value_mismatch(
    characteristic: str,
    value: str,
) -> None:
    with pytest.raises(RiskReviewerOutputError):
        assess(
            risk_response(
                basis=[solution_basis("ALT-001", characteristic, value)]
            )
        )


def test_solution_alternative_text_basis_fails_when_characteristic_text_is_ambiguous() -> None:
    with pytest.raises(RiskReviewerOutputError):
        assess(
            risk_response(
                basis=[solution_basis("ALT-001", "ADVANTAGE", "Keeps operation local.")]
            ),
            alternatives=solution_alternatives(duplicate_advantage_text=True),
        )


def test_solution_alternative_relevant_constraint_basis_must_resolve_exactly() -> None:
    with pytest.raises(RiskReviewerOutputError):
        assess(
            risk_response(
                basis=[
                    solution_basis(
                        "ALT-001",
                        "RELEVANT_CONSTRAINT",
                        {
                            "source": "REVIEW_INPUT",
                            "kind": "TEXT",
                            "value": "Keep deployment simple",
                        },
                    )
                ]
            )
        )


def test_duplicate_identical_relevant_constraints_make_basis_ambiguous() -> None:
    with pytest.raises(RiskReviewerOutputError):
        assess(
            risk_response(
                basis=[
                    solution_basis(
                        "ALT-001",
                        "RELEVANT_CONSTRAINT",
                        {
                            "source": "PROBLEM_ANALYSIS",
                            "kind": "ID",
                            "value": "CON-001",
                        },
                    )
                ]
            ),
            alternatives=solution_alternatives(duplicate_constraint_reference=True),
        )


def test_overall_scope_is_valid_without_alternative_lookup() -> None:
    result = assess(
        risk_response(scope={"kind": "OVERALL", "alternative_ids": []})
    )

    assert result.risks[0].affected_scope.alternative_ids == ()


@pytest.mark.parametrize(
    "alternative_ids",
    [
        ["ALT-001"],
        ["ALT-001", "ALT-002"],
    ],
)
def test_alternative_scope_resolves_one_or_multiple_current_alternatives(
    alternative_ids: list[str],
) -> None:
    result = assess(
        risk_response(
            scope={"kind": "ALTERNATIVES", "alternative_ids": alternative_ids}
        )
    )

    assert result.risks[0].affected_scope.alternative_ids == tuple(alternative_ids)


def test_alternative_scope_rejects_unknown_current_alternative_id() -> None:
    with pytest.raises(RiskReviewerOutputError):
        assess(
            risk_response(
                scope={"kind": "ALTERNATIVES", "alternative_ids": ["ALT-999"]}
            )
        )


def test_alternative_scope_is_invalid_when_solution_architect_produced_zero_alternatives() -> None:
    with pytest.raises(RiskReviewerOutputError):
        assess(
            risk_response(
                scope={"kind": "ALTERNATIVES", "alternative_ids": ["ALT-001"]}
            ),
            alternatives=zero_alternatives(),
        )


def test_zero_risk_assessment_is_trusted_without_artificial_risk_generation() -> None:
    result = assess(
        {
            "risks": [],
            "overall_observations": [
                "No material risk is justified by the current trusted inputs."
            ],
        }
    )

    assert result.risks == ()
    assert result.overall_observations == (
        "No material risk is justified by the current trusted inputs.",
    )


def test_zero_alternative_input_still_allows_grounded_overall_risk() -> None:
    result = assess(
        risk_response(
            basis=[
                review_input_basis(
                    "constraints",
                    "Must run offline",
                )
            ],
            scope={"kind": "OVERALL", "alternative_ids": []},
        ),
        alternatives=zero_alternatives(),
    )

    assert len(result.risks) == 1
    assert result.risks[0].affected_scope.alternative_ids == ()


@pytest.mark.parametrize(
    "response",
    [
        risk_response(
            scope={"kind": "ALTERNATIVES", "alternative_ids": ["ALT-001"]}
        ),
        risk_response(
            basis=[
                solution_basis(
                    "ALT-001",
                    "DESCRIPTION",
                    "Run the capability in the existing local environment.",
                )
            ]
        ),
    ],
)
def test_zero_alternative_input_rejects_fabricated_alternative_specific_risk(
    response: dict[str, object],
) -> None:
    with pytest.raises(RiskReviewerOutputError):
        assess(response, alternatives=zero_alternatives())


@pytest.mark.parametrize(
    "response",
    [
        {"risks": [{"id": "RISK-001"}], "overall_observations": []},
        {
            "risks": [],
            "overall_observations": [],
            "ranking": ["ALT-001", "ALT-002"],
        },
        risk_response(
            basis=[review_input_basis("constraints", "Unknown constraint")]
        ),
    ],
)
def test_structural_or_contextual_generated_output_failure_is_dedicated_and_fail_closed(
    response: Mapping[str, object],
) -> None:
    llm = RecordingLLM(response)

    with pytest.raises(RiskReviewerOutputError):
        RiskReviewer(llm).assess(
            review_input(),
            problem_analysis(),
            solution_alternatives(),
        )

    assert len(llm.calls) == 1


@pytest.mark.parametrize(
    "generated_value",
    [
        "Review a proposed technical deployment change. ",
        "review a proposed technical deployment change.",
    ],
)
def test_contextual_resolution_does_not_silently_trim_or_case_repair_generated_text(
    generated_value: str,
) -> None:
    with pytest.raises(RiskReviewerOutputError):
        assess(
            risk_response(
                basis=[review_input_basis("description", generated_value)]
            )
        )


def test_one_invalid_risk_prevents_partial_trust_of_an_otherwise_valid_assessment() -> None:
    valid_risk = risk_response()["risks"]
    assert isinstance(valid_risk, list)
    response: dict[str, object] = {
        "risks": [
            valid_risk[0],
            {
                "id": "RISK-002",
                "description": "Generated risk with an unresolved basis.",
                "affected_scope": {"kind": "OVERALL", "alternative_ids": []},
                "severity": "LOW",
                "basis": [review_input_basis("constraints", "Unknown constraint")],
            },
        ],
        "overall_observations": [],
    }

    with pytest.raises(RiskReviewerOutputError):
        assess(response)
