import pytest
from pydantic import ValidationError

from agentic_review_board.domain.analysis import (
    AnalysisFinding,
    FactFinding,
    ProblemAnalysis,
    ReviewInputSource,
)


def valid_problem_analysis_data() -> dict[str, object]:
    return {
        "objective": "Determine whether the proposal merits further evaluation.",
        "facts": [
            {
                "id": "FACT-001",
                "text": "A technical change is proposed.",
                "source_ref": "description",
            }
        ],
        "constraints": [{"text": "The initial review should stay small."}],
        "assumptions": [{"id": "ASM-001", "text": "The system can be changed."}],
        "missing_information": [{"text": "Current architecture is unknown."}],
        "uncertainties": [{"text": "The expected benefit is unclear."}],
    }


def test_analysis_finding_allows_optional_local_identifier() -> None:
    without_id = AnalysisFinding(text="Current architecture is unknown.")
    with_id = AnalysisFinding(id="MISS-001", text="Current architecture is unknown.")

    assert without_id.id is None
    assert with_id.id == "MISS-001"


def test_fact_finding_uses_closed_review_input_source_vocabulary() -> None:
    expected_sources = {
        "description",
        "title",
        "objective",
        "constraints",
        "context",
        "stated_facts",
    }

    assert {source.value for source in ReviewInputSource} == expected_sources

    fact = FactFinding(
        text="A technical change is proposed.",
        source_ref=ReviewInputSource.DESCRIPTION,
    )

    assert fact.id is None
    assert fact.source_ref is ReviewInputSource.DESCRIPTION


def test_problem_analysis_contains_all_six_semantic_categories() -> None:
    analysis = ProblemAnalysis(
        objective="Determine whether the proposal merits further evaluation.",
        facts=[
            FactFinding(
                id="FACT-001",
                text="A technical change is proposed.",
                source_ref=ReviewInputSource.DESCRIPTION,
            )
        ],
        constraints=[AnalysisFinding(text="The initial review should stay small.")],
        assumptions=[AnalysisFinding(id="ASM-001", text="The system can be changed.")],
        missing_information=[AnalysisFinding(text="Current architecture is unknown.")],
        uncertainties=[AnalysisFinding(text="The expected benefit is unclear.")],
    )

    assert analysis.objective == "Determine whether the proposal merits further evaluation."
    assert analysis.facts[0].text == "A technical change is proposed."
    assert analysis.constraints[0].text == "The initial review should stay small."
    assert analysis.assumptions[0].id == "ASM-001"
    assert analysis.missing_information[0].id is None
    assert analysis.uncertainties[0].text == "The expected benefit is unclear."


def test_facts_and_assumptions_remain_structurally_distinct() -> None:
    fact = FactFinding(
        text="The review description proposes a technical change.",
        source_ref=ReviewInputSource.DESCRIPTION,
    )
    assumption = AnalysisFinding(text="The existing system can be changed safely.")

    analysis = ProblemAnalysis(
        objective="Evaluate the proposal.",
        facts=[fact],
        constraints=[],
        assumptions=[assumption],
        missing_information=[],
        uncertainties=[],
    )

    assert analysis.facts == [fact]
    assert analysis.assumptions == [assumption]
    assert isinstance(analysis.facts[0], FactFinding)
    assert isinstance(analysis.assumptions[0], AnalysisFinding)


@pytest.mark.parametrize(
    "field_name",
    ["facts", "constraints", "assumptions", "missing_information", "uncertainties"],
)
def test_problem_analysis_collections_cannot_change_after_validation(field_name: str) -> None:
    analysis = ProblemAnalysis.model_validate(valid_problem_analysis_data())
    collection = getattr(analysis, field_name)
    original = tuple(collection)
    append = getattr(collection, "append", None)

    if append is not None:
        append("Injected after validation")

    assert tuple(getattr(analysis, field_name)) == original


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(
            lambda data: data.pop("assumptions"),
            id="missing-mandatory-field",
        ),
        pytest.param(
            lambda data: data.update({"ranking": []}),
            id="unexpected-top-level-field",
        ),
        pytest.param(
            lambda data: data["assumptions"][0].update({"confidence": "HIGH"}),
            id="unexpected-nested-field",
        ),
        pytest.param(
            lambda data: data["assumptions"][0].update({"text": 123}),
            id="wrong-strict-text-type",
        ),
        pytest.param(
            lambda data: data["facts"][0].update({"source_ref": "external_knowledge"}),
            id="invalid-review-input-source",
        ),
        pytest.param(
            lambda data: data.update({"uncertainties": ["not-a-finding"]}),
            id="malformed-nested-finding",
        ),
        pytest.param(
            lambda data: data["missing_information"][0].update({"text": "   "}),
            id="empty-finding-text",
        ),
    ],
)
def test_problem_analysis_rejects_structurally_invalid_generated_content(
    mutate: object,
) -> None:
    data = valid_problem_analysis_data()
    assert callable(mutate)
    mutate(data)

    with pytest.raises(ValidationError):
        ProblemAnalysis.model_validate(data)


def test_problem_analysis_rejects_duplicate_non_null_local_identifiers() -> None:
    data = valid_problem_analysis_data()
    data["assumptions"] = [{"id": "FACT-001", "text": "Duplicate identifier."}]

    with pytest.raises(ValidationError):
        ProblemAnalysis.model_validate(data)


def test_problem_analysis_allows_multiple_findings_without_identifiers() -> None:
    data = valid_problem_analysis_data()
    data["facts"] = [
        {"text": "One fact.", "source_ref": "description"},
        {"text": "Another fact.", "source_ref": "description"},
    ]
    data["assumptions"] = [
        {"text": "First assumption."},
        {"text": "Second assumption."},
    ]

    analysis = ProblemAnalysis.model_validate(data)

    assert all(finding.id is None for finding in analysis.facts)
    assert all(finding.id is None for finding in analysis.assumptions)
