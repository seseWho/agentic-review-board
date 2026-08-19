from collections.abc import Mapping

from agentic_review_board.application.ports import LLMPort
from agentic_review_board.domain.analysis import FactFinding, ProblemAnalysis, ReferencedFinding
from agentic_review_board.domain.review import ReviewInput


class AnalystOutputError(ValueError):
    """Raised when generated Analyst output violates its structured contract."""


class Analyst:
    """Transforms ReviewInput into a validated ProblemAnalysis."""

    _FACT_SOURCES = frozenset(
        {"description", "title", "objective", "constraints", "context", "stated_facts"}
    )

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
        return self._parse_output(raw)

    def _parse_output(self, raw: Mapping[str, object]) -> ProblemAnalysis:
        objective = self._required_text(raw, "objective")
        facts = tuple(self._parse_fact(item) for item in self._required_list(raw, "facts"))
        constraints = self._parse_findings(raw, "constraints")
        assumptions = self._parse_findings(raw, "assumptions")
        missing_information = self._parse_findings(raw, "missing_information")
        uncertainties = self._parse_findings(raw, "uncertainties")
        self._validate_unique_ids(
            facts,
            constraints,
            assumptions,
            missing_information,
            uncertainties,
        )
        return ProblemAnalysis(
            objective=objective,
            facts=facts,
            constraints=constraints,
            assumptions=assumptions,
            missing_information=missing_information,
            uncertainties=uncertainties,
        )

    def _parse_findings(
        self,
        raw: Mapping[str, object],
        key: str,
    ) -> tuple[ReferencedFinding, ...]:
        return tuple(self._parse_finding(item, key) for item in self._required_list(raw, key))

    def _parse_fact(self, item: object) -> FactFinding:
        mapping = self._mapping(item, "facts")
        finding_id = self._required_text(mapping, "id")
        text = self._required_text(mapping, "text")
        source_ref = self._required_text(mapping, "source_ref")
        if source_ref not in self._FACT_SOURCES:
            raise AnalystOutputError(f"invalid fact source_ref: {source_ref}")
        return FactFinding(id=finding_id, text=text, source_ref=source_ref)

    def _parse_finding(self, item: object, field: str) -> ReferencedFinding:
        mapping = self._mapping(item, field)
        return ReferencedFinding(
            id=self._required_text(mapping, "id"),
            text=self._required_text(mapping, "text"),
        )

    @staticmethod
    def _mapping(item: object, field: str) -> Mapping[str, object]:
        if not isinstance(item, Mapping):
            raise AnalystOutputError(f"{field} items must be mappings")
        return item

    @staticmethod
    def _required_text(mapping: Mapping[str, object], key: str) -> str:
        value = mapping.get(key)
        if not isinstance(value, str) or not value.strip():
            raise AnalystOutputError(f"{key} must be non-empty text")
        return value

    @staticmethod
    def _required_list(mapping: Mapping[str, object], key: str) -> list[object]:
        value = mapping.get(key)
        if not isinstance(value, list):
            raise AnalystOutputError(f"{key} must be a list")
        return value

    @staticmethod
    def _validate_unique_ids(*groups: tuple[object, ...]) -> None:
        ids: list[str] = []
        for group in groups:
            for item in group:
                item_id = getattr(item, "id", None)
                if not isinstance(item_id, str):
                    raise AnalystOutputError("all findings must expose an id")
                ids.append(item_id)
        if len(ids) != len(set(ids)):
            raise AnalystOutputError("finding ids must be unique within ProblemAnalysis")
