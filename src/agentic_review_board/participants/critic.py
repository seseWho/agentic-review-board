from collections.abc import Callable, Mapping
from dataclasses import dataclass

from pydantic import ValidationError

from agentic_review_board.application.ports import LLMPort
from agentic_review_board.domain.analysis import (
    AnalysisFinding,
    FactFinding,
    ProblemAnalysis,
)
from agentic_review_board.domain.critics import (
    ContradictionSupportStatus,
    CriticalReview,
    Criticism,
    CriticismTargetType,
    CriticReference,
    CriticReferenceKind,
)
from agentic_review_board.domain.review import ReviewInput
from agentic_review_board.domain.risks import Risk, RiskAssessment
from agentic_review_board.domain.solutions import (
    FindingReference,
    GenerationNotes,
    SolutionAlternative,
    SolutionAlternatives,
)


class CriticOutputError(ValueError):
    """Raised when generated Critic output violates its trusted contract."""


@dataclass(frozen=True)
class _ResolvedReference:
    target_key: tuple[str, ...]
    visible_value: str


class Critic:
    """Transforms four trusted upstream artifacts into a validated critical review."""

    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    def review(
        self,
        review_input: ReviewInput,
        problem_analysis: ProblemAnalysis,
        solution_alternatives: SolutionAlternatives,
        risk_assessment: RiskAssessment,
    ) -> CriticalReview:
        raw = self._llm.generate_structured(
            role="critic",
            payload={
                "review_input": review_input.model_dump(mode="json"),
                "problem_analysis": problem_analysis.model_dump(mode="json"),
                "solution_alternatives": solution_alternatives.model_dump(mode="json"),
                "risk_assessment": risk_assessment.model_dump(mode="json"),
            },
        )

        critical_review = self._validate_structure(raw)
        self._validate_context(
            critical_review,
            review_input,
            problem_analysis,
            solution_alternatives,
            risk_assessment,
        )
        return critical_review

    @staticmethod
    def _validate_structure(raw: Mapping[str, object]) -> CriticalReview:
        try:
            return CriticalReview.model_validate(raw)
        except ValidationError as exc:
            raise CriticOutputError("invalid Critic output") from exc

    @classmethod
    def _validate_context(
        cls,
        critical_review: CriticalReview,
        review_input: ReviewInput,
        problem_analysis: ProblemAnalysis,
        solution_alternatives: SolutionAlternatives,
        risk_assessment: RiskAssessment,
    ) -> None:
        def resolve(reference: CriticReference) -> _ResolvedReference:
            return cls._resolve_reference(
                reference,
                review_input,
                problem_analysis,
                solution_alternatives,
                risk_assessment,
            )

        for criticism in critical_review.criticisms:
            cls._validate_criticism(criticism, resolve)

        for point in critical_review.validated_points:
            resolve(point.target_reference)

        for missing_alternative in critical_review.missing_alternatives:
            for reference in missing_alternative.basis_references:
                resolve(reference)

        for contradiction in critical_review.contradictions:
            if contradiction.support_status is not ContradictionSupportStatus.UNVERIFIED:
                raise CriticOutputError("Critic cannot claim contradiction evidence")
            side_a = resolve(contradiction.side_a.reference)
            side_b = resolve(contradiction.side_b.reference)
            if contradiction.side_a.statement != side_a.visible_value:
                raise CriticOutputError("invalid Critic output")
            if contradiction.side_b.statement != side_b.visible_value:
                raise CriticOutputError("invalid Critic output")

        for unresolved_issue in critical_review.unresolved_issues:
            for reference in unresolved_issue.basis_references:
                resolve(reference)

    @classmethod
    def _validate_criticism(
        cls,
        criticism: Criticism,
        resolve: Callable[[CriticReference], _ResolvedReference],
    ) -> None:
        resolved: list[_ResolvedReference] = []
        if criticism.target_reference is not None:
            resolved.append(resolve(criticism.target_reference))
        resolved.extend(resolve(reference) for reference in criticism.basis_references)

        if criticism.target_type not in {
            CriticismTargetType.CROSS_ARTIFACT_CONCLUSION,
            CriticismTargetType.OMISSION,
        } and criticism.target_reference is None:
            raise CriticOutputError("invalid Critic output")

        if criticism.target_type is CriticismTargetType.CROSS_ARTIFACT_CONCLUSION:
            keys = {reference.target_key for reference in resolved}
            if len(keys) < 2:
                raise CriticOutputError("invalid Critic output")

    @classmethod
    def _resolve_reference(
        cls,
        reference: CriticReference,
        review_input: ReviewInput,
        problem_analysis: ProblemAnalysis,
        solution_alternatives: SolutionAlternatives,
        risk_assessment: RiskAssessment,
    ) -> _ResolvedReference:
        if reference.source.value == "REVIEW_INPUT":
            return cls._resolve_review_input(reference, review_input)
        if reference.source.value == "PROBLEM_ANALYSIS":
            return cls._resolve_problem_analysis(reference, problem_analysis)
        if reference.source.value == "SOLUTION_ALTERNATIVES":
            return cls._resolve_solution_alternatives(reference, solution_alternatives)
        if reference.source.value == "RISK_ASSESSMENT":
            return cls._resolve_risk_assessment(reference, risk_assessment)
        raise CriticOutputError("invalid Critic output")

    @classmethod
    def _resolve_review_input(
        cls,
        reference: CriticReference,
        review_input: ReviewInput,
    ) -> _ResolvedReference:
        kind = reference.kind
        value = cls._required_value(reference)

        if kind is CriticReferenceKind.DESCRIPTION:
            cls._require_exact_scalar(value, review_input.description)
            return _ResolvedReference(("REVIEW_INPUT", kind.value), value)
        if kind is CriticReferenceKind.TITLE:
            cls._require_exact_scalar(value, review_input.title)
            return _ResolvedReference(("REVIEW_INPUT", kind.value), value)
        if kind is CriticReferenceKind.REVIEW_OBJECTIVE:
            cls._require_exact_scalar(value, review_input.objective)
            return _ResolvedReference(("REVIEW_INPUT", kind.value), value)
        if kind is CriticReferenceKind.REVIEW_CONSTRAINT:
            index = cls._require_unique_text(value, review_input.constraints)
            return _ResolvedReference(("REVIEW_INPUT", kind.value, str(index)), value)
        if kind is CriticReferenceKind.CONTEXT:
            index = cls._require_unique_text(value, review_input.context)
            return _ResolvedReference(("REVIEW_INPUT", kind.value, str(index)), value)
        if kind is CriticReferenceKind.STATED_FACT:
            index = cls._require_unique_text(value, review_input.stated_facts)
            return _ResolvedReference(("REVIEW_INPUT", kind.value, str(index)), value)
        raise CriticOutputError("invalid Critic output")

    @classmethod
    def _resolve_problem_analysis(
        cls,
        reference: CriticReference,
        problem_analysis: ProblemAnalysis,
    ) -> _ResolvedReference:
        kind = reference.kind
        value = cls._required_value(reference)

        if kind is CriticReferenceKind.PROBLEM_OBJECTIVE:
            cls._require_exact_scalar(value, problem_analysis.objective)
            return _ResolvedReference(("PROBLEM_ANALYSIS", kind.value), value)

        findings = cls._problem_findings(kind, problem_analysis)
        index = cls._require_unique_finding(
            reference.item_id,
            value,
            findings,
        )
        return _ResolvedReference(("PROBLEM_ANALYSIS", kind.value, str(index)), value)

    @staticmethod
    def _problem_findings(
        kind: CriticReferenceKind,
        problem_analysis: ProblemAnalysis,
    ) -> tuple[FactFinding | AnalysisFinding, ...]:
        if kind is CriticReferenceKind.PROBLEM_FACT:
            return problem_analysis.facts
        if kind is CriticReferenceKind.PROBLEM_CONSTRAINT:
            return problem_analysis.constraints
        if kind is CriticReferenceKind.PROBLEM_ASSUMPTION:
            return problem_analysis.assumptions
        if kind is CriticReferenceKind.MISSING_INFORMATION:
            return problem_analysis.missing_information
        if kind is CriticReferenceKind.UNCERTAINTY:
            return problem_analysis.uncertainties
        raise CriticOutputError("invalid Critic output")

    @classmethod
    def _resolve_solution_alternatives(
        cls,
        reference: CriticReference,
        solution_alternatives: SolutionAlternatives,
    ) -> _ResolvedReference:
        kind = reference.kind

        if kind is CriticReferenceKind.GENERATION_EXPLANATION:
            notes = cls._required_generation_notes(solution_alternatives)
            value = cls._required_value(reference)
            cls._require_exact_scalar(value, notes.explanation)
            return _ResolvedReference(("SOLUTION_ALTERNATIVES", kind.value), value)

        if kind in {
            CriticReferenceKind.BLOCKING_MISSING_INFORMATION,
            CriticReferenceKind.BLOCKING_UNCERTAINTY,
        }:
            notes = cls._required_generation_notes(solution_alternatives)
            findings = (
                notes.blocking_missing_information
                if kind is CriticReferenceKind.BLOCKING_MISSING_INFORMATION
                else notes.blocking_uncertainties
            )
            value = cls._required_value(reference)
            index = cls._require_unique_finding(reference.item_id, value, findings)
            return _ResolvedReference(
                ("SOLUTION_ALTERNATIVES", kind.value, str(index)),
                value,
            )

        alternative = cls._required_alternative(reference, solution_alternatives)
        if kind is CriticReferenceKind.ALTERNATIVE:
            if reference.value is not None and reference.value != alternative.name:
                raise CriticOutputError("invalid Critic output")
            return _ResolvedReference(
                ("SOLUTION_ALTERNATIVES", kind.value, alternative.id),
                alternative.name,
            )

        value = cls._required_value(reference)
        target_key = ("SOLUTION_ALTERNATIVES", kind.value, alternative.id)

        if kind is CriticReferenceKind.ALTERNATIVE_NAME:
            cls._require_exact_scalar(value, alternative.name)
            return _ResolvedReference(target_key, value)
        if kind is CriticReferenceKind.ALTERNATIVE_DESCRIPTION:
            cls._require_exact_scalar(value, alternative.description)
            return _ResolvedReference(target_key, value)
        if kind is CriticReferenceKind.ADVANTAGE:
            index = cls._require_unique_text(value, alternative.advantages)
            return _ResolvedReference((*target_key, str(index)), value)
        if kind is CriticReferenceKind.DISADVANTAGE:
            index = cls._require_unique_text(value, alternative.disadvantages)
            return _ResolvedReference((*target_key, str(index)), value)
        if kind is CriticReferenceKind.ALTERNATIVE_ASSUMPTION:
            index = cls._require_unique_text(value, alternative.assumptions)
            return _ResolvedReference((*target_key, str(index)), value)
        if kind is CriticReferenceKind.IMPLEMENTATION_COMPLEXITY:
            cls._require_exact_scalar(value, alternative.implementation_complexity.value)
            return _ResolvedReference(target_key, value)
        raise CriticOutputError("invalid Critic output")

    @classmethod
    def _required_alternative(
        cls,
        reference: CriticReference,
        solution_alternatives: SolutionAlternatives,
    ) -> SolutionAlternative:
        item_id = cls._required_item_id(reference)
        matches = [
            alternative
            for alternative in solution_alternatives.alternatives
            if alternative.id == item_id
        ]
        if len(matches) != 1:
            raise CriticOutputError("invalid Critic output")
        return matches[0]

    @staticmethod
    def _required_generation_notes(
        solution_alternatives: SolutionAlternatives,
    ) -> GenerationNotes:
        if solution_alternatives.generation_notes is None:
            raise CriticOutputError("invalid Critic output")
        return solution_alternatives.generation_notes

    @classmethod
    def _resolve_risk_assessment(
        cls,
        reference: CriticReference,
        risk_assessment: RiskAssessment,
    ) -> _ResolvedReference:
        kind = reference.kind

        if kind is CriticReferenceKind.OVERALL_OBSERVATION:
            value = cls._required_value(reference)
            index = cls._require_unique_text(value, risk_assessment.overall_observations)
            return _ResolvedReference(("RISK_ASSESSMENT", kind.value, str(index)), value)

        risk = cls._required_risk(reference, risk_assessment)
        if kind is CriticReferenceKind.RISK:
            if reference.value is not None and reference.value != risk.description:
                raise CriticOutputError("invalid Critic output")
            return _ResolvedReference(
                ("RISK_ASSESSMENT", kind.value, risk.id),
                risk.description,
            )

        value = cls._required_value(reference)
        target_key = ("RISK_ASSESSMENT", kind.value, risk.id)

        if kind is CriticReferenceKind.RISK_CATEGORY:
            cls._require_exact_scalar(value, risk.category)
            return _ResolvedReference(target_key, value)
        if kind is CriticReferenceKind.RISK_DESCRIPTION:
            cls._require_exact_scalar(value, risk.description)
            return _ResolvedReference(target_key, value)
        if kind is CriticReferenceKind.RISK_SEVERITY:
            cls._require_exact_scalar(value, risk.severity.value)
            return _ResolvedReference(target_key, value)
        if kind is CriticReferenceKind.MITIGATION:
            cls._require_exact_scalar(value, risk.mitigation)
            return _ResolvedReference(target_key, value)
        if kind is CriticReferenceKind.RESIDUAL_UNCERTAINTY:
            cls._require_exact_scalar(value, risk.residual_uncertainty)
            return _ResolvedReference(target_key, value)
        raise CriticOutputError("invalid Critic output")

    @classmethod
    def _required_risk(
        cls,
        reference: CriticReference,
        risk_assessment: RiskAssessment,
    ) -> Risk:
        item_id = cls._required_item_id(reference)
        matches = [risk for risk in risk_assessment.risks if risk.id == item_id]
        if len(matches) != 1:
            raise CriticOutputError("invalid Critic output")
        return matches[0]

    @staticmethod
    def _required_item_id(reference: CriticReference) -> str:
        if reference.item_id is None:
            raise CriticOutputError("invalid Critic output")
        return reference.item_id

    @staticmethod
    def _required_value(reference: CriticReference) -> str:
        if reference.value is None:
            raise CriticOutputError("invalid Critic output")
        return reference.value

    @staticmethod
    def _require_exact_scalar(generated: str, current: str | None) -> None:
        if current is None or generated != current:
            raise CriticOutputError("invalid Critic output")

    @staticmethod
    def _require_unique_text(generated: str, current: tuple[str, ...]) -> int:
        matches = [index for index, value in enumerate(current) if value == generated]
        if len(matches) != 1:
            raise CriticOutputError("invalid Critic output")
        return matches[0]

    @staticmethod
    def _require_unique_finding(
        item_id: str | None,
        value: str,
        findings: tuple[FactFinding | AnalysisFinding | FindingReference, ...],
    ) -> int:
        if item_id is None:
            matches = [
                index
                for index, finding in enumerate(findings)
                if finding.text == value
            ]
        else:
            matches = [
                index
                for index, finding in enumerate(findings)
                if finding.id == item_id and finding.text == value
            ]
        if len(matches) != 1:
            raise CriticOutputError("invalid Critic output")
        return matches[0]
