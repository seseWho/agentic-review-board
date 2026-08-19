from agentic_review_board.domain.analysis import (
    AnalysisFinding,
    FactFinding,
    ProblemAnalysis,
    ReviewInputSource,
)


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
