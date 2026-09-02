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


class AnalystOutputError(ValueError):
    """Raised when generated Analyst output violates its structured contract."""


class Analyst:
    """Transforms ReviewInput into a validated ProblemAnalysis."""

    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    def analyze(self, review_input: ReviewInput) -> ProblemAnalysis:
        raw = self._llm.generate_structured(
            role="analyst",
            payload={
                "description": review_input.description,
                "title": review_input.title,
                "objective": review_input.objective,
                "constraints": review_input.constraints,
                "context": review_input.context,
                "stated_facts": review_input.stated_facts,
            },
        )

        analysis = self._validate_structure(raw)
        self._validate_fact_provenance(analysis, review_input)
        self._validate_authoritative_inputs(analysis, review_input)
        return analysis

    @staticmethod
    def _validate_structure(raw: Mapping[str, object]) -> ProblemAnalysis:
        try:
            return ProblemAnalysis.model_validate(raw)
        except ValidationError as exc:
            raise AnalystOutputError("invalid Analyst output") from exc

    @staticmethod
    def _validate_fact_provenance(
        analysis: ProblemAnalysis,
        review_input: ReviewInput,
    ) -> None:
        for fact in analysis.facts:
            if not Analyst._source_is_applicable(fact.source_ref, review_input):
                raise AnalystOutputError(
                    f"fact source_ref is not applicable to current ReviewInput: {fact.source_ref.value}"
                )

    @staticmethod
    def _validate_authoritative_inputs(
        analysis: ProblemAnalysis,
        review_input: ReviewInput,
    ) -> None:
        expected_facts = tuple(
            FactFinding(
                id=f"FACT-{index:03d}",
                text=text,
                source_ref=ReviewInputSource.STATED_FACTS,
            )
            for index, text in enumerate(review_input.stated_facts, start=1)
        )
        if analysis.facts != expected_facts:
            raise AnalystOutputError("Analyst did not preserve authoritative stated facts")

        expected_constraints = tuple(
            AnalysisFinding(id=f"CON-{index:03d}", text=text)
            for index, text in enumerate(review_input.constraints, start=1)
        )
        if analysis.constraints != expected_constraints:
            raise AnalystOutputError("Analyst did not preserve authoritative constraints")

    @staticmethod
    def _source_is_applicable(source: ReviewInputSource, review_input: ReviewInput) -> bool:
        if source is ReviewInputSource.DESCRIPTION:
            return True
        if source is ReviewInputSource.TITLE:
            return review_input.title is not None
        if source is ReviewInputSource.OBJECTIVE:
            return review_input.objective is not None
        if source is ReviewInputSource.CONSTRAINTS:
            return bool(review_input.constraints)
        if source is ReviewInputSource.CONTEXT:
            return bool(review_input.context)
        if source is ReviewInputSource.STATED_FACTS:
            return bool(review_input.stated_facts)
        return False
