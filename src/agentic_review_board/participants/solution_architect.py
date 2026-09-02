from collections.abc import Mapping

from pydantic import ValidationError

from agentic_review_board.application.ports import LLMPort
from agentic_review_board.domain.analysis import AnalysisFinding, ProblemAnalysis
from agentic_review_board.domain.review import ReviewInput
from agentic_review_board.domain.solutions import (
    AlternativeValidationStatus,
    ConstraintReference,
    ConstraintReferenceKind,
    ConstraintSource,
    FindingReference,
    SolutionAlternatives,
)


class SolutionArchitectOutputError(ValueError):
    """Raised when generated Solution Architect output violates its trusted contract."""


class SolutionArchitect:
    """Transforms trusted review artifacts into validated solution alternatives."""

    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    def propose(
        self,
        review_input: ReviewInput,
        problem_analysis: ProblemAnalysis,
    ) -> SolutionAlternatives:
        raw = self._llm.generate_structured(
            role="solution_architect",
            payload={
                "review_input": review_input.model_dump(mode="json"),
                "problem_analysis": problem_analysis.model_dump(mode="json"),
            },
        )

        alternatives = self._validate_structure(raw)
        self._validate_proposal_status(alternatives)
        self._validate_constraint_references(alternatives, review_input, problem_analysis)
        self._validate_generation_notes(alternatives, problem_analysis)
        return alternatives

    @staticmethod
    def _validate_proposal_status(alternatives: SolutionAlternatives) -> None:
        if any(
            alternative.validation_status is not AlternativeValidationStatus.PROPOSED
            for alternative in alternatives.alternatives
        ):
            raise SolutionArchitectOutputError(
                "Solution Architect cannot claim validation evidence"
            )

    @staticmethod
    def _validate_structure(raw: Mapping[str, object]) -> SolutionAlternatives:
        try:
            return SolutionAlternatives.model_validate(raw)
        except ValidationError as exc:
            raise SolutionArchitectOutputError("invalid Solution Architect output") from exc

    @staticmethod
    def _validate_constraint_references(
        alternatives: SolutionAlternatives,
        review_input: ReviewInput,
        problem_analysis: ProblemAnalysis,
    ) -> None:
        for alternative in alternatives.alternatives:
            for reference in alternative.relevant_constraints:
                SolutionArchitect._resolve_constraint_reference(
                    reference,
                    review_input,
                    problem_analysis,
                )

    @staticmethod
    def _resolve_constraint_reference(
        reference: ConstraintReference,
        review_input: ReviewInput,
        problem_analysis: ProblemAnalysis,
    ) -> None:
        if reference.source is ConstraintSource.REVIEW_INPUT:
            if reference.value not in review_input.constraints:
                raise SolutionArchitectOutputError(
                    f"unresolved ReviewInput constraint reference: {reference.value}"
                )
            return

        if reference.kind is ConstraintReferenceKind.ID:
            matches = [
                finding
                for finding in problem_analysis.constraints
                if finding.id == reference.value
            ]
        else:
            matches = [
                finding
                for finding in problem_analysis.constraints
                if finding.text == reference.value
            ]

        SolutionArchitect._require_single_constraint_match(reference, matches)

    @staticmethod
    def _require_single_constraint_match(
        reference: ConstraintReference,
        matches: list[AnalysisFinding],
    ) -> None:
        if len(matches) == 1:
            return
        if not matches:
            raise SolutionArchitectOutputError(
                f"unresolved ProblemAnalysis constraint reference: {reference.value}"
            )
        raise SolutionArchitectOutputError(
            f"ambiguous ProblemAnalysis constraint reference: {reference.value}"
        )

    @staticmethod
    def _validate_generation_notes(
        alternatives: SolutionAlternatives,
        problem_analysis: ProblemAnalysis,
    ) -> None:
        notes = alternatives.generation_notes
        if notes is None:
            return

        for reference in notes.blocking_missing_information:
            SolutionArchitect._resolve_finding_reference(
                reference,
                problem_analysis.missing_information,
                category="missing information",
            )

        for reference in notes.blocking_uncertainties:
            SolutionArchitect._resolve_finding_reference(
                reference,
                problem_analysis.uncertainties,
                category="uncertainty",
            )

    @staticmethod
    def _resolve_finding_reference(
        reference: FindingReference,
        findings: tuple[AnalysisFinding, ...],
        *,
        category: str,
    ) -> None:
        if reference.id is not None:
            matches = [
                finding
                for finding in findings
                if finding.id == reference.id and finding.text == reference.text
            ]
        else:
            matches = [finding for finding in findings if finding.text == reference.text]

        if len(matches) == 1:
            return
        if not matches:
            raise SolutionArchitectOutputError(
                f"unresolved {category} blocker reference: {reference.text}"
            )
        raise SolutionArchitectOutputError(
            f"ambiguous {category} blocker reference: {reference.text}"
        )
