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
        return self._validate_structure(raw)

    @staticmethod
    def _validate_structure(raw: Mapping[str, object]) -> FinalReview:
        candidate = dict(raw)
        candidate.setdefault("decision_support_notice", DECISION_SUPPORT_NOTICE)
        try:
            return FinalReview.model_validate(candidate)
        except ValidationError as exc:
            raise CoordinatorOutputError("invalid Coordinator output") from exc
