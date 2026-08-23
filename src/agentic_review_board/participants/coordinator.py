from collections.abc import Mapping

from pydantic import ValidationError

from agentic_review_board.application.ports import LLMPort
from agentic_review_board.domain.analysis import ProblemAnalysis
from agentic_review_board.domain.critics import CriticalReview
from agentic_review_board.domain.final_reviews import (
    DECISION_SUPPORT_NOTICE,
    FinalReview,
)
from agentic_review_board.domain.review import ReviewInput
from agentic_review_board.domain.risks import RiskAssessment
from agentic_review_board.domain.solutions import SolutionAlternatives


class CoordinatorOutputError(ValueError):
    """Raised when generated Coordinator output violates its trusted contract."""


class Coordinator:
    """Transforms five trusted artifacts into a validated final review."""

    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    def coordinate(
        self,
        review_input: ReviewInput,
        problem_analysis: ProblemAnalysis,
        solution_alternatives: SolutionAlternatives,
        risk_assessment: RiskAssessment,
        critical_review: CriticalReview,
    ) -> FinalReview:
        raw = self._llm.generate_structured(
            role="coordinator",
            payload={
                "review_input": review_input.model_dump(mode="json"),
                "problem_analysis": problem_analysis.model_dump(mode="json"),
                "solution_alternatives": solution_alternatives.model_dump(mode="json"),
                "risk_assessment": risk_assessment.model_dump(mode="json"),
                "critical_review": critical_review.model_dump(mode="json"),
            },
        )
        final_review = self._validate_structure(raw)
        self._validate_ranking_and_risks(
            final_review,
            solution_alternatives,
            risk_assessment,
        )
        return final_review

    @staticmethod
    def _validate_structure(raw: Mapping[str, object]) -> FinalReview:
        candidate = dict(raw)
        candidate.setdefault("decision_support_notice", DECISION_SUPPORT_NOTICE)
        try:
            return FinalReview.model_validate(candidate)
        except ValidationError as exc:
            raise CoordinatorOutputError("invalid Coordinator output") from exc


    @staticmethod
    def _validate_ranking_and_risks(
        final_review: FinalReview,
        solution_alternatives: SolutionAlternatives,
        risk_assessment: RiskAssessment,
    ) -> None:
        current_alternative_ids = {
            alternative.id for alternative in solution_alternatives.alternatives
        }
        ranked_alternative_ids = {
            alternative.alternative_id
            for alternative in final_review.ranked_alternatives
        }
        if ranked_alternative_ids != current_alternative_ids:
            raise CoordinatorOutputError("invalid Coordinator output")

        if not current_alternative_ids:
            if final_review.recommendation_outcome.value != "INSUFFICIENT_EVIDENCE":
                raise CoordinatorOutputError("invalid Coordinator output")
        elif final_review.preferred_alternative_id is not None:
            if final_review.preferred_alternative_id not in current_alternative_ids:
                raise CoordinatorOutputError("invalid Coordinator output")

        current_risk_ids = {risk.id for risk in risk_assessment.risks}
        if any(
            principal.risk_id not in current_risk_ids
            for principal in final_review.principal_risks
        ):
            raise CoordinatorOutputError("invalid Coordinator output")
