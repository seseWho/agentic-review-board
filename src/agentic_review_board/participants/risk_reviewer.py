from collections.abc import Mapping

from pydantic import ValidationError

from agentic_review_board.application.ports import LLMPort
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
    ReviewInputBasisReference,
    RiskAssessment,
    RiskScopeKind,
    SolutionAlternativeBasisReference,
    SolutionAlternativeCharacteristicKind,
)
from agentic_review_board.domain.solutions import (
    ConstraintReference,
    SolutionAlternative,
    SolutionAlternatives,
)


class RiskReviewerOutputError(ValueError):
    """Raised when generated Risk Reviewer output violates its trusted contract."""


class RiskReviewer:
    """Transforms trusted upstream artifacts into a validated qualitative risk assessment."""

    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    def assess(
        self,
        review_input: ReviewInput,
        problem_analysis: ProblemAnalysis,
        solution_alternatives: SolutionAlternatives,
    ) -> RiskAssessment:
        raw = self._llm.generate_structured(
            role="risk_reviewer",
            payload={
                "review_input": review_input.model_dump(mode="json"),
                "problem_analysis": problem_analysis.model_dump(mode="json"),
                "solution_alternatives": solution_alternatives.model_dump(mode="json"),
            },
        )

        assessment = self._validate_structure(raw)
        self._validate_scope_references(assessment, solution_alternatives)
        self._validate_basis_references(
            assessment,
            review_input,
            problem_analysis,
            solution_alternatives,
        )
        return assessment

    @staticmethod
    def _validate_structure(raw: Mapping[str, object]) -> RiskAssessment:
        try:
            return RiskAssessment.model_validate(raw)
        except ValidationError as exc:
            raise RiskReviewerOutputError("invalid Risk Reviewer output") from exc

    @staticmethod
    def _validate_scope_references(
        assessment: RiskAssessment,
        solution_alternatives: SolutionAlternatives,
    ) -> None:
        current_ids = {alternative.id for alternative in solution_alternatives.alternatives}

        for risk in assessment.risks:
            scope = risk.affected_scope
            if scope.kind is RiskScopeKind.OVERALL:
                continue
            if any(alternative_id not in current_ids for alternative_id in scope.alternative_ids):
                raise RiskReviewerOutputError("invalid Risk Reviewer output")

    @staticmethod
    def _validate_basis_references(
        assessment: RiskAssessment,
        review_input: ReviewInput,
        problem_analysis: ProblemAnalysis,
        solution_alternatives: SolutionAlternatives,
    ) -> None:
        for risk in assessment.risks:
            for reference in risk.basis:
                if isinstance(reference, ReviewInputBasisReference):
                    RiskReviewer._resolve_review_input_basis(reference, review_input)
                elif isinstance(reference, ProblemAnalysisBasisReference):
                    RiskReviewer._resolve_problem_analysis_basis(reference, problem_analysis)
                elif isinstance(reference, SolutionAlternativeBasisReference):
                    RiskReviewer._resolve_solution_alternative_basis(
                        reference,
                        solution_alternatives,
                    )
                else:
                    raise RiskReviewerOutputError("invalid Risk Reviewer output")

    @staticmethod
    def _resolve_review_input_basis(
        reference: ReviewInputBasisReference,
        review_input: ReviewInput,
    ) -> None:
        if reference.field is ReviewInputSource.DESCRIPTION:
            RiskReviewer._require_exact_scalar_match(reference.value, review_input.description)
            return
        if reference.field is ReviewInputSource.TITLE:
            RiskReviewer._require_exact_scalar_match(reference.value, review_input.title)
            return
        if reference.field is ReviewInputSource.OBJECTIVE:
            RiskReviewer._require_exact_scalar_match(reference.value, review_input.objective)
            return
        if reference.field is ReviewInputSource.CONSTRAINTS:
            RiskReviewer._require_single_text_match(reference.value, review_input.constraints)
            return
        if reference.field is ReviewInputSource.CONTEXT:
            RiskReviewer._require_single_text_match(reference.value, review_input.context)
            return
        if reference.field is ReviewInputSource.STATED_FACTS:
            RiskReviewer._require_single_text_match(reference.value, review_input.stated_facts)
            return
        raise RiskReviewerOutputError("invalid Risk Reviewer output")

    @staticmethod
    def _require_exact_scalar_match(generated: str, current: str | None) -> None:
        if current is None or generated != current:
            raise RiskReviewerOutputError("invalid Risk Reviewer output")

    @staticmethod
    def _require_single_text_match(generated: str, current: tuple[str, ...]) -> None:
        if sum(value == generated for value in current) != 1:
            raise RiskReviewerOutputError("invalid Risk Reviewer output")

    @staticmethod
    def _resolve_problem_analysis_basis(
        reference: ProblemAnalysisBasisReference,
        problem_analysis: ProblemAnalysis,
    ) -> None:
        findings = RiskReviewer._problem_analysis_findings(reference.kind, problem_analysis)

        if reference.id is not None:
            matches = [
                finding
                for finding in findings
                if finding.id == reference.id and finding.text == reference.text
            ]
        else:
            matches = [finding for finding in findings if finding.text == reference.text]

        if len(matches) != 1:
            raise RiskReviewerOutputError("invalid Risk Reviewer output")

    @staticmethod
    def _problem_analysis_findings(
        kind: ProblemAnalysisFindingKind,
        problem_analysis: ProblemAnalysis,
    ) -> tuple[FactFinding | AnalysisFinding, ...]:
        if kind is ProblemAnalysisFindingKind.FACT:
            return problem_analysis.facts
        if kind is ProblemAnalysisFindingKind.CONSTRAINT:
            return problem_analysis.constraints
        if kind is ProblemAnalysisFindingKind.ASSUMPTION:
            return problem_analysis.assumptions
        if kind is ProblemAnalysisFindingKind.MISSING_INFORMATION:
            return problem_analysis.missing_information
        if kind is ProblemAnalysisFindingKind.UNCERTAINTY:
            return problem_analysis.uncertainties
        raise RiskReviewerOutputError("invalid Risk Reviewer output")

    @staticmethod
    def _resolve_solution_alternative_basis(
        reference: SolutionAlternativeBasisReference,
        solution_alternatives: SolutionAlternatives,
    ) -> None:
        alternatives = [
            alternative
            for alternative in solution_alternatives.alternatives
            if alternative.id == reference.alternative_id
        ]
        if len(alternatives) != 1:
            raise RiskReviewerOutputError("invalid Risk Reviewer output")

        alternative = alternatives[0]
        RiskReviewer._resolve_alternative_characteristic(reference, alternative)

    @staticmethod
    def _resolve_alternative_characteristic(
        reference: SolutionAlternativeBasisReference,
        alternative: SolutionAlternative,
    ) -> None:
        characteristic = reference.characteristic
        value = reference.value

        if characteristic is SolutionAlternativeCharacteristicKind.DESCRIPTION:
            RiskReviewer._require_alternative_scalar_text(value, alternative.description)
            return
        if characteristic is SolutionAlternativeCharacteristicKind.ADVANTAGE:
            RiskReviewer._require_alternative_collection_text(value, alternative.advantages)
            return
        if characteristic is SolutionAlternativeCharacteristicKind.DISADVANTAGE:
            RiskReviewer._require_alternative_collection_text(value, alternative.disadvantages)
            return
        if characteristic is SolutionAlternativeCharacteristicKind.ASSUMPTION:
            RiskReviewer._require_alternative_collection_text(value, alternative.assumptions)
            return
        if characteristic is SolutionAlternativeCharacteristicKind.IMPLEMENTATION_COMPLEXITY:
            RiskReviewer._require_alternative_scalar_text(
                value,
                alternative.implementation_complexity.value,
            )
            return
        if characteristic is SolutionAlternativeCharacteristicKind.RELEVANT_CONSTRAINT:
            RiskReviewer._require_alternative_constraint(value, alternative.relevant_constraints)
            return
        raise RiskReviewerOutputError("invalid Risk Reviewer output")

    @staticmethod
    def _require_alternative_scalar_text(
        generated: str | ConstraintReference,
        current: str,
    ) -> None:
        if not isinstance(generated, str) or generated != current:
            raise RiskReviewerOutputError("invalid Risk Reviewer output")

    @staticmethod
    def _require_alternative_collection_text(
        generated: str | ConstraintReference,
        current: tuple[str, ...],
    ) -> None:
        if not isinstance(generated, str) or sum(value == generated for value in current) != 1:
            raise RiskReviewerOutputError("invalid Risk Reviewer output")

    @staticmethod
    def _require_alternative_constraint(
        generated: str | ConstraintReference,
        current: tuple[ConstraintReference, ...],
    ) -> None:
        if not isinstance(generated, ConstraintReference):
            raise RiskReviewerOutputError("invalid Risk Reviewer output")
        if sum(reference == generated for reference in current) != 1:
            raise RiskReviewerOutputError("invalid Risk Reviewer output")
