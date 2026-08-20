import pytest
from pydantic import ValidationError

import agentic_review_board.domain.solutions as solution_contracts
from agentic_review_board.domain.shared import QualitativeLevel
from agentic_review_board.domain.solutions import (
    ConstraintReference,
    ConstraintReferenceKind,
    ConstraintSource,
    FindingReference,
    GenerationNotes,
    SolutionAlternative,
    SolutionAlternatives,
)


def valid_alternative_data(*, alternative_id: str = "ALT-001") -> dict[str, object]:
    return {
        "id": alternative_id,
        "name": "Local deployment",
        "description": "Run the solution inside the current local environment.",
        "advantages": ["Keeps operational data local."],
        "disadvantages": ["Requires local model lifecycle management."],
        "assumptions": ["Suitable local compute is available."],
        "implementation_complexity": "MEDIUM",
        "relevant_constraints": [
            {
                "source": "REVIEW_INPUT",
                "kind": "TEXT",
                "value": "Must run offline",
            }
        ],
    }


def valid_generation_notes_data() -> dict[str, object]:
    return {
        "explanation": "Alternatives remain comparable with the current evidence.",
        "blocking_missing_information": [],
        "blocking_uncertainties": [],
    }


def no_alternative_notes_data() -> dict[str, object]:
    return {
        "explanation": "Deployment constraints are too incomplete for a useful comparison.",
        "blocking_missing_information": [
            {
                "id": "MISS-001",
                "text": "Available deployment infrastructure is unknown.",
            }
        ],
        "blocking_uncertainties": [
            {
                "text": "Operational ownership is unclear.",
            }
        ],
    }


def two_alternative_data() -> dict[str, object]:
    return {
        "alternatives": [
            valid_alternative_data(alternative_id="ALT-001"),
            valid_alternative_data(alternative_id="ALT-002"),
        ]
    }


def test_shared_solution_vocabularies_are_closed() -> None:
    assert {level.value for level in QualitativeLevel} == {"LOW", "MEDIUM", "HIGH"}
    assert {source.value for source in ConstraintSource} == {
        "REVIEW_INPUT",
        "PROBLEM_ANALYSIS",
    }
    assert {kind.value for kind in ConstraintReferenceKind} == {"TEXT", "ID"}


def test_constraint_reference_accepts_only_supported_source_kind_combinations() -> None:
    review_input_text = ConstraintReference(
        source=ConstraintSource.REVIEW_INPUT,
        kind=ConstraintReferenceKind.TEXT,
        value="Must run offline",
    )
    analysis_text = ConstraintReference(
        source=ConstraintSource.PROBLEM_ANALYSIS,
        kind=ConstraintReferenceKind.TEXT,
        value="Minimize deployment complexity",
    )
    analysis_id = ConstraintReference(
        source=ConstraintSource.PROBLEM_ANALYSIS,
        kind=ConstraintReferenceKind.ID,
        value="CON-001",
    )

    assert review_input_text.value == "Must run offline"
    assert analysis_text.kind is ConstraintReferenceKind.TEXT
    assert analysis_id.kind is ConstraintReferenceKind.ID

    with pytest.raises(ValidationError):
        ConstraintReference(
            source=ConstraintSource.REVIEW_INPUT,
            kind=ConstraintReferenceKind.ID,
            value="CON-001",
        )


def test_finding_reference_allows_optional_local_identifier() -> None:
    without_id = FindingReference(text="Current deployment constraints are unknown.")
    with_id = FindingReference(
        id="MISS-001",
        text="Current deployment constraints are unknown.",
    )

    assert without_id.id is None
    assert with_id.id == "MISS-001"


def test_generation_notes_are_structured_and_immutable() -> None:
    notes = GenerationNotes.model_validate(valid_generation_notes_data())

    assert notes.explanation == "Alternatives remain comparable with the current evidence."
    assert isinstance(notes.blocking_missing_information, tuple)
    assert isinstance(notes.blocking_uncertainties, tuple)

    with pytest.raises(ValidationError):
        notes.explanation = "Changed after validation"


def test_solution_alternative_preserves_explicit_tradeoffs_and_immutable_collections() -> None:
    alternative = SolutionAlternative.model_validate(valid_alternative_data())

    assert alternative.id == "ALT-001"
    assert alternative.name == "Local deployment"
    assert alternative.implementation_complexity is QualitativeLevel.MEDIUM
    assert isinstance(alternative.advantages, tuple)
    assert isinstance(alternative.disadvantages, tuple)
    assert isinstance(alternative.assumptions, tuple)
    assert isinstance(alternative.relevant_constraints, tuple)
    assert alternative.relevant_constraints[0].source is ConstraintSource.REVIEW_INPUT


def test_solution_alternatives_accepts_two_or_three_unique_alternatives() -> None:
    two = SolutionAlternatives.model_validate(two_alternative_data())
    three = SolutionAlternatives.model_validate(
        {
            "alternatives": [
                valid_alternative_data(alternative_id="ALT-001"),
                valid_alternative_data(alternative_id="ALT-002"),
                valid_alternative_data(alternative_id="ALT-003"),
            ],
            "generation_notes": valid_generation_notes_data(),
        }
    )

    assert len(two.alternatives) == 2
    assert two.generation_notes is None
    assert len(three.alternatives) == 3
    assert three.generation_notes is not None
    assert {item.id for item in three.alternatives} == {"ALT-001", "ALT-002", "ALT-003"}
    assert isinstance(two.alternatives, tuple)


def test_required_generated_text_rejects_blank_values_without_rewriting_valid_text() -> None:
    preserved = "  Keep intentional surrounding whitespace.  "
    alternative_data = valid_alternative_data()
    alternative_data["name"] = preserved

    alternative = SolutionAlternative.model_validate(alternative_data)

    assert alternative.name == preserved

    for model, data in (
        (ConstraintReference, {"source": "REVIEW_INPUT", "kind": "TEXT", "value": "   "}),
        (FindingReference, {"text": "   "}),
        (
            GenerationNotes,
            {
                "explanation": "   ",
                "blocking_missing_information": [],
                "blocking_uncertainties": [],
            },
        ),
    ):
        with pytest.raises(ValidationError):
            model.model_validate(data)


def test_generated_solution_contracts_reject_unexpected_fields() -> None:
    data = valid_alternative_data()
    data["ranking"] = 1

    with pytest.raises(ValidationError):
        SolutionAlternative.model_validate(data)


def test_solution_alternatives_model_validation_normalizes_nested_lists_to_tuples() -> None:
    data = valid_alternative_data()
    data["advantages"] = ["First", "Second"]
    result = SolutionAlternatives.model_validate(
        {
            "alternatives": [data, valid_alternative_data(alternative_id="ALT-002")],
        }
    )

    assert isinstance(result.alternatives, tuple)
    assert isinstance(result.alternatives[0].advantages, tuple)
    assert result.alternatives[0].advantages == ("First", "Second")


def test_trusted_solution_output_cannot_be_reassigned_after_validation() -> None:
    result = SolutionAlternatives.model_validate(two_alternative_data())

    with pytest.raises(ValidationError):
        result.alternatives = ()


def test_zero_alternatives_requires_generation_notes() -> None:
    with pytest.raises(ValidationError):
        SolutionAlternatives.model_validate({"alternatives": []})


def test_zero_alternative_generation_notes_preserve_structured_immutable_blockers() -> None:
    result = SolutionAlternatives.model_validate(
        {
            "alternatives": [],
            "generation_notes": no_alternative_notes_data(),
        }
    )

    assert result.alternatives == ()
    assert result.generation_notes is not None
    assert result.generation_notes.explanation.startswith("Deployment constraints")
    assert isinstance(result.generation_notes.blocking_missing_information, tuple)
    assert isinstance(result.generation_notes.blocking_uncertainties, tuple)
    assert result.generation_notes.blocking_missing_information[0].id == "MISS-001"
    assert result.generation_notes.blocking_uncertainties[0].id is None


def test_no_separate_no_alternative_outcome_contract_is_introduced() -> None:
    assert not hasattr(solution_contracts, "NoAlternativeOutcome")


def test_solution_alternative_rejects_missing_mandatory_nested_field() -> None:
    alternative = valid_alternative_data()
    del alternative["description"]

    with pytest.raises(ValidationError):
        SolutionAlternatives.model_validate(
            {
                "alternatives": [
                    alternative,
                    valid_alternative_data(alternative_id="ALT-002"),
                ]
            }
        )


def test_solution_contracts_reject_unexpected_top_level_and_nested_fields() -> None:
    top_level = two_alternative_data()
    top_level["final_recommendation"] = "Choose ALT-001"
    nested = valid_alternative_data()
    nested["preferred_alternative"] = True

    with pytest.raises(ValidationError):
        SolutionAlternatives.model_validate(top_level)
    with pytest.raises(ValidationError):
        SolutionAlternatives.model_validate(
            {
                "alternatives": [nested, valid_alternative_data(alternative_id="ALT-002")]
            }
        )


def test_solution_alternative_rejects_unsupported_complexity_and_non_string_semantic_text() -> None:
    invalid_complexity = valid_alternative_data()
    invalid_complexity["implementation_complexity"] = "VERY_HIGH"
    invalid_text = valid_alternative_data()
    invalid_text["description"] = 123

    for first in (invalid_complexity, invalid_text):
        with pytest.raises(ValidationError):
            SolutionAlternatives.model_validate(
                {
                    "alternatives": [
                        first,
                        valid_alternative_data(alternative_id="ALT-002"),
                    ]
                }
            )


def test_solution_alternative_rejects_blank_required_and_collection_text() -> None:
    blank_name = valid_alternative_data()
    blank_name["name"] = "   "
    blank_advantage = valid_alternative_data()
    blank_advantage["advantages"] = ["   "]

    for first in (blank_name, blank_advantage):
        with pytest.raises(ValidationError):
            SolutionAlternatives.model_validate(
                {
                    "alternatives": [
                        first,
                        valid_alternative_data(alternative_id="ALT-002"),
                    ]
                }
            )


def test_solution_alternative_rejects_review_input_id_constraint_reference() -> None:
    invalid = valid_alternative_data()
    invalid["relevant_constraints"] = [
        {
            "source": "REVIEW_INPUT",
            "kind": "ID",
            "value": "CON-001",
        }
    ]

    with pytest.raises(ValidationError):
        SolutionAlternatives.model_validate(
            {
                "alternatives": [
                    invalid,
                    valid_alternative_data(alternative_id="ALT-002"),
                ]
            }
        )


def test_solution_alternatives_rejects_one_or_more_than_three_alternatives() -> None:
    one = {"alternatives": [valid_alternative_data()]}
    four = {
        "alternatives": [
            valid_alternative_data(alternative_id="ALT-001"),
            valid_alternative_data(alternative_id="ALT-002"),
            valid_alternative_data(alternative_id="ALT-003"),
            valid_alternative_data(alternative_id="ALT-004"),
        ]
    }

    with pytest.raises(ValidationError):
        SolutionAlternatives.model_validate(one)
    with pytest.raises(ValidationError):
        SolutionAlternatives.model_validate(four)


def test_solution_alternatives_rejects_duplicate_alternative_ids() -> None:
    with pytest.raises(ValidationError):
        SolutionAlternatives.model_validate(
            {
                "alternatives": [
                    valid_alternative_data(alternative_id="ALT-001"),
                    valid_alternative_data(alternative_id="ALT-001"),
                ]
            }
        )


def test_zero_alternatives_rejects_blank_generation_explanation() -> None:
    notes = no_alternative_notes_data()
    notes["explanation"] = "   "

    with pytest.raises(ValidationError):
        SolutionAlternatives.model_validate(
            {
                "alternatives": [],
                "generation_notes": notes,
            }
        )


def test_generation_notes_rejects_malformed_finding_reference() -> None:
    notes = no_alternative_notes_data()
    notes["blocking_missing_information"] = [{"id": "MISS-001"}]

    with pytest.raises(ValidationError):
        SolutionAlternatives.model_validate(
            {
                "alternatives": [],
                "generation_notes": notes,
            }
        )
