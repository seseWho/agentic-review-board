from collections.abc import Mapping

from pydantic import ValidationError

from agentic_review_board.application.ports import LLMPort
from agentic_review_board.domain.analysis import ProblemAnalysis
from agentic_review_board.domain.critics import CriticalReview
from agentic_review_board.domain.final_reviews import (
    DECISION_SUPPORT_NOTICE,
    CriticUnresolvedKind,
    CriticUnresolvedReference,
    FinalReview,
    ProblemUnresolvedKind,
    ProblemUnresolvedReference,
    RiskUnresolvedReference,
    SolutionUnresolvedKind,
    SolutionUnresolvedReference,
    UnresolvedQuestionReference,
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
        self._validate_unresolved_questions(
            final_review,
            problem_analysis,
            solution_alternatives,
            risk_assessment,
            critical_review,
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


    @classmethod
    def _validate_unresolved_questions(
        cls,
        final_review: FinalReview,
        problem_analysis: ProblemAnalysis,
        solution_alternatives: SolutionAlternatives,
        risk_assessment: RiskAssessment,
        critical_review: CriticalReview,
    ) -> None:
        resolved_targets = [
            cls._resolve_unresolved_reference(
                question.reference,
                problem_analysis,
                solution_alternatives,
                risk_assessment,
                critical_review,
            )
            for question in final_review.unresolved_questions
        ]
        if len(resolved_targets) != len(set(resolved_targets)):
            raise CoordinatorOutputError("invalid Coordinator output")

    @classmethod
    def _resolve_unresolved_reference(
        cls,
        reference: UnresolvedQuestionReference,
        problem_analysis: ProblemAnalysis,
        solution_alternatives: SolutionAlternatives,
        risk_assessment: RiskAssessment,
        critical_review: CriticalReview,
    ) -> tuple[str, ...]:
        if isinstance(reference, ProblemUnresolvedReference):
            return cls._resolve_problem_reference(reference, problem_analysis)
        if isinstance(reference, SolutionUnresolvedReference):
            return cls._resolve_solution_reference(reference, solution_alternatives)
        if isinstance(reference, RiskUnresolvedReference):
            return cls._resolve_risk_reference(reference, risk_assessment)
        if isinstance(reference, CriticUnresolvedReference):
            return cls._resolve_critic_reference(reference, critical_review)
        raise CoordinatorOutputError("invalid Coordinator output")

    @classmethod
    def _resolve_problem_reference(
        cls,
        reference: ProblemUnresolvedReference,
        problem_analysis: ProblemAnalysis,
    ) -> tuple[str, ...]:
        if reference.kind is ProblemUnresolvedKind.PROBLEM_ASSUMPTION:
            findings = problem_analysis.assumptions
        elif reference.kind is ProblemUnresolvedKind.MISSING_INFORMATION:
            findings = problem_analysis.missing_information
        else:
            findings = problem_analysis.uncertainties
        index = cls._require_unique_finding(
            reference.item_id,
            reference.value,
            findings,
        )
        return ("PROBLEM_ANALYSIS", reference.kind.value, str(index))

    @classmethod
    def _resolve_solution_reference(
        cls,
        reference: SolutionUnresolvedReference,
        solution_alternatives: SolutionAlternatives,
    ) -> tuple[str, ...]:
        if reference.kind is SolutionUnresolvedKind.ALTERNATIVE_ASSUMPTION:
            matches = [
                alternative
                for alternative in solution_alternatives.alternatives
                if alternative.id == reference.alternative_id
            ]
            if len(matches) != 1:
                raise CoordinatorOutputError("invalid Coordinator output")
            index = cls._require_unique_text(reference.value, matches[0].assumptions)
            return (
                "SOLUTION_ALTERNATIVES",
                reference.kind.value,
                matches[0].id,
                str(index),
            )

        notes = solution_alternatives.generation_notes
        if notes is None:
            raise CoordinatorOutputError("invalid Coordinator output")
        findings = (
            notes.blocking_missing_information
            if reference.kind
            is SolutionUnresolvedKind.BLOCKING_MISSING_INFORMATION
            else notes.blocking_uncertainties
        )
        index = cls._require_unique_finding(
            reference.item_id,
            reference.value,
            findings,
        )
        return ("SOLUTION_ALTERNATIVES", reference.kind.value, str(index))

    @staticmethod
    def _resolve_risk_reference(
        reference: RiskUnresolvedReference,
        risk_assessment: RiskAssessment,
    ) -> tuple[str, ...]:
        matches = [
            risk
            for risk in risk_assessment.risks
            if risk.id == reference.risk_id
            and risk.residual_uncertainty == reference.value
        ]
        if len(matches) != 1:
            raise CoordinatorOutputError("invalid Coordinator output")
        return ("RISK_ASSESSMENT", reference.risk_id, "RESIDUAL_UNCERTAINTY")

    @staticmethod
    def _resolve_critic_reference(
        reference: CriticUnresolvedReference,
        critical_review: CriticalReview,
    ) -> tuple[str, ...]:
        if reference.kind is CriticUnresolvedKind.MISSING_ALTERNATIVE:
            matches = [
                finding
                for finding in critical_review.missing_alternatives
                if finding.id == reference.item_id
                and finding.category == reference.value
            ]
        elif reference.kind is CriticUnresolvedKind.CONTRADICTION:
            matches = [
                finding
                for finding in critical_review.contradictions
                if finding.id == reference.item_id
                and finding.rationale == reference.value
            ]
        else:
            matches = [
                finding
                for finding in critical_review.unresolved_issues
                if finding.id == reference.item_id
                and finding.issue == reference.value
            ]
        if len(matches) != 1:
            raise CoordinatorOutputError("invalid Coordinator output")
        return ("CRITICAL_REVIEW", reference.kind.value, reference.item_id)

    @staticmethod
    def _require_unique_text(value: str, current: tuple[str, ...]) -> int:
        matches = [index for index, item in enumerate(current) if item == value]
        if len(matches) != 1:
            raise CoordinatorOutputError("invalid Coordinator output")
        return matches[0]

    @staticmethod
    def _require_unique_finding(
        item_id: str | None,
        value: str,
        findings: tuple[object, ...],
    ) -> int:
        matches = [
            index
            for index, finding in enumerate(findings)
            if getattr(finding, "text", None) == value
            and (item_id is None or getattr(finding, "id", None) == item_id)
        ]
        if len(matches) != 1:
            raise CoordinatorOutputError("invalid Coordinator output")
        return matches[0]
