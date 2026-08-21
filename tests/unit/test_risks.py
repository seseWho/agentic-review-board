import pytest
from pydantic import ValidationError

from agentic_review_board.domain.risks import RiskScope, RiskScopeKind


def test_overall_scope_requires_no_alternative_ids() -> None:
    scope = RiskScope(kind=RiskScopeKind.OVERALL)

    assert scope.kind is RiskScopeKind.OVERALL
    assert scope.alternative_ids == ()

    with pytest.raises(ValidationError):
        RiskScope(
            kind=RiskScopeKind.OVERALL,
            alternative_ids=("ALT-001",),
        )


def test_alternatives_scope_requires_at_least_one_alternative_id() -> None:
    scope = RiskScope(
        kind=RiskScopeKind.ALTERNATIVES,
        alternative_ids=("ALT-001", "ALT-002"),
    )

    assert scope.alternative_ids == ("ALT-001", "ALT-002")

    with pytest.raises(ValidationError):
        RiskScope(kind=RiskScopeKind.ALTERNATIVES)


def test_alternative_ids_must_be_non_blank_and_unique() -> None:
    with pytest.raises(ValidationError):
        RiskScope(
            kind=RiskScopeKind.ALTERNATIVES,
            alternative_ids=(" ",),
        )

    with pytest.raises(ValidationError):
        RiskScope(
            kind=RiskScopeKind.ALTERNATIVES,
            alternative_ids=("ALT-001", "ALT-001"),
        )


def test_scope_is_closed_frozen_and_tuple_backed() -> None:
    scope = RiskScope.model_validate(
        {
            "kind": "ALTERNATIVES",
            "alternative_ids": ["ALT-001"],
        }
    )

    assert scope.alternative_ids == ("ALT-001",)
    assert isinstance(scope.alternative_ids, tuple)

    with pytest.raises(ValidationError):
        scope.kind = RiskScopeKind.OVERALL

    with pytest.raises(ValidationError):
        RiskScope.model_validate(
            {
                "kind": "OVERALL",
                "alternative_ids": [],
                "unexpected": "not allowed",
            }
        )
