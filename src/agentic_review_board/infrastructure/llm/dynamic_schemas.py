from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import NoReturn

from agentic_review_board.domain.analysis import (
    AnalysisFinding,
    FactFinding,
    ProblemAnalysis,
)
from agentic_review_board.domain.critics import (
    CriticReferenceKind,
    CriticReferenceSource,
)
from agentic_review_board.domain.review import ReviewInput
from agentic_review_board.domain.risks import RiskAssessment
from agentic_review_board.domain.solutions import (
    FindingReference,
    SolutionAlternatives,
)
from agentic_review_board.infrastructure.llm.errors import LLMRequestSchemaError

_CRITIC_PAYLOAD_KEYS = frozenset(
    {
        "review_input",
        "problem_analysis",
        "solution_alternatives",
        "risk_assessment",
    }
)


def _reject_non_json_constant(_value: str) -> NoReturn:
    raise ValueError("non-JSON numeric constant")


@dataclass(frozen=True, slots=True)
class CriticPayloadSnapshot:
    serialized_payload: str
    review_input: ReviewInput
    problem_analysis: ProblemAnalysis
    solution_alternatives: SolutionAlternatives
    risk_assessment: RiskAssessment


@dataclass(frozen=True, slots=True)
class AllowedCriticReference:
    source: CriticReferenceSource
    kind: CriticReferenceKind
    item_id: str | None
    value: str | None
    visible_value: str
    target_key: tuple[str, ...]

    @property
    def emitted_identity(
        self,
    ) -> tuple[CriticReferenceSource, CriticReferenceKind, str | None, str | None]:
        return (self.source, self.kind, self.item_id, self.value)


def build_critic_payload_snapshot(
    payload: Mapping[str, object],
) -> CriticPayloadSnapshot:
    try:
        if not isinstance(payload, Mapping):
            raise TypeError("Critic payload must be a mapping")
        owned_top_level = dict(payload)
        if len(owned_top_level) != 4 or frozenset(owned_top_level) != _CRITIC_PAYLOAD_KEYS:
            raise ValueError("Critic payload keys are invalid")
        serialized_payload = json.dumps(
            owned_top_level,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        detached = json.loads(
            serialized_payload,
            parse_constant=_reject_non_json_constant,
        )
        if not isinstance(detached, dict):
            raise TypeError("Critic payload snapshot must be an object")
        return CriticPayloadSnapshot(
            serialized_payload=serialized_payload,
            review_input=ReviewInput.model_validate(detached["review_input"]),
            problem_analysis=ProblemAnalysis.model_validate(detached["problem_analysis"]),
            solution_alternatives=SolutionAlternatives.model_validate(
                detached["solution_alternatives"]
            ),
            risk_assessment=RiskAssessment.model_validate(detached["risk_assessment"]),
        )
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error


def _reference(
    source: CriticReferenceSource,
    kind: CriticReferenceKind,
    *,
    value: str,
    target_key: tuple[str, ...],
    item_id: str | None = None,
    visible_value: str | None = None,
) -> AllowedCriticReference:
    return AllowedCriticReference(
        source=source,
        kind=kind,
        item_id=item_id,
        value=value,
        visible_value=value if visible_value is None else visible_value,
        target_key=target_key,
    )


def _scalar_reference(
    source: CriticReferenceSource,
    kind: CriticReferenceKind,
    value: str | None,
    *target_tail: str,
    item_id: str | None = None,
) -> AllowedCriticReference | None:
    if value is None:
        return None
    return _reference(
        source,
        kind,
        value=value,
        item_id=item_id,
        target_key=(source.value, kind.value, *target_tail),
    )


def _unique_text_references(
    source: CriticReferenceSource,
    kind: CriticReferenceKind,
    values: Sequence[str],
    *target_prefix: str,
    item_id: str | None = None,
) -> Iterable[AllowedCriticReference]:
    counts: dict[str, int] = defaultdict(int)
    for value in values:
        counts[value] += 1
    for index, value in enumerate(values):
        if counts[value] == 1:
            yield _reference(
                source,
                kind,
                value=value,
                item_id=item_id,
                target_key=(source.value, kind.value, *target_prefix, str(index)),
            )


Finding = FactFinding | AnalysisFinding | FindingReference


def _finding_references(
    source: CriticReferenceSource,
    kind: CriticReferenceKind,
    findings: Sequence[Finding],
) -> Iterable[AllowedCriticReference]:
    for index, finding in enumerate(findings):
        if finding.id is None:
            matches = sum(candidate.text == finding.text for candidate in findings)
        else:
            matches = sum(
                candidate.id == finding.id and candidate.text == finding.text
                for candidate in findings
            )
        if matches == 1:
            yield _reference(
                source,
                kind,
                value=finding.text,
                item_id=finding.id,
                target_key=(source.value, kind.value, str(index)),
            )


def _review_input_references(snapshot: CriticPayloadSnapshot) -> Iterable[AllowedCriticReference]:
    source = CriticReferenceSource.REVIEW_INPUT
    review_input = snapshot.review_input
    for kind, value in (
        (CriticReferenceKind.DESCRIPTION, review_input.description),
        (CriticReferenceKind.TITLE, review_input.title),
        (CriticReferenceKind.REVIEW_OBJECTIVE, review_input.objective),
    ):
        reference = _scalar_reference(source, kind, value)
        if reference is not None:
            yield reference
    for kind, values in (
        (CriticReferenceKind.REVIEW_CONSTRAINT, review_input.constraints),
        (CriticReferenceKind.CONTEXT, review_input.context),
        (CriticReferenceKind.STATED_FACT, review_input.stated_facts),
    ):
        yield from _unique_text_references(source, kind, values)


def _problem_analysis_references(
    snapshot: CriticPayloadSnapshot,
) -> Iterable[AllowedCriticReference]:
    source = CriticReferenceSource.PROBLEM_ANALYSIS
    analysis = snapshot.problem_analysis
    objective = _scalar_reference(
        source,
        CriticReferenceKind.PROBLEM_OBJECTIVE,
        analysis.objective,
    )
    assert objective is not None
    yield objective
    for kind, findings in (
        (CriticReferenceKind.PROBLEM_FACT, analysis.facts),
        (CriticReferenceKind.PROBLEM_CONSTRAINT, analysis.constraints),
        (CriticReferenceKind.PROBLEM_ASSUMPTION, analysis.assumptions),
        (CriticReferenceKind.MISSING_INFORMATION, analysis.missing_information),
        (CriticReferenceKind.UNCERTAINTY, analysis.uncertainties),
    ):
        yield from _finding_references(source, kind, findings)


def _solution_alternative_references(
    snapshot: CriticPayloadSnapshot,
) -> Iterable[AllowedCriticReference]:
    source = CriticReferenceSource.SOLUTION_ALTERNATIVES
    alternatives = snapshot.solution_alternatives.alternatives
    for alternative in alternatives:
        yield _reference(
            source,
            CriticReferenceKind.ALTERNATIVE,
            value=alternative.name,
            item_id=alternative.id,
            target_key=(source.value, CriticReferenceKind.ALTERNATIVE.value, alternative.id),
        )
    for kind, attribute in (
        (CriticReferenceKind.ALTERNATIVE_NAME, "name"),
        (CriticReferenceKind.ALTERNATIVE_DESCRIPTION, "description"),
    ):
        for alternative in alternatives:
            value = getattr(alternative, attribute)
            yield _reference(
                source,
                kind,
                value=value,
                item_id=alternative.id,
                target_key=(source.value, kind.value, alternative.id),
            )
    for kind, attribute in (
        (CriticReferenceKind.ADVANTAGE, "advantages"),
        (CriticReferenceKind.DISADVANTAGE, "disadvantages"),
        (CriticReferenceKind.ALTERNATIVE_ASSUMPTION, "assumptions"),
    ):
        for alternative in alternatives:
            values = getattr(alternative, attribute)
            yield from _unique_text_references(
                source,
                kind,
                values,
                alternative.id,
                item_id=alternative.id,
            )
    for alternative in alternatives:
        kind = CriticReferenceKind.IMPLEMENTATION_COMPLEXITY
        yield _reference(
            source,
            kind,
            value=alternative.implementation_complexity.value,
            item_id=alternative.id,
            target_key=(source.value, kind.value, alternative.id),
        )
    notes = snapshot.solution_alternatives.generation_notes
    if notes is not None:
        yield _reference(
            source,
            CriticReferenceKind.GENERATION_EXPLANATION,
            value=notes.explanation,
            target_key=(source.value, CriticReferenceKind.GENERATION_EXPLANATION.value),
        )
        yield from _finding_references(
            source,
            CriticReferenceKind.BLOCKING_MISSING_INFORMATION,
            notes.blocking_missing_information,
        )
        yield from _finding_references(
            source,
            CriticReferenceKind.BLOCKING_UNCERTAINTY,
            notes.blocking_uncertainties,
        )


def _risk_assessment_references(
    snapshot: CriticPayloadSnapshot,
) -> Iterable[AllowedCriticReference]:
    source = CriticReferenceSource.RISK_ASSESSMENT
    risks = snapshot.risk_assessment.risks
    for risk in risks:
        yield _reference(
            source,
            CriticReferenceKind.RISK,
            value=risk.description,
            item_id=risk.id,
            target_key=(source.value, CriticReferenceKind.RISK.value, risk.id),
        )
    for kind, attribute in (
        (CriticReferenceKind.RISK_CATEGORY, "category"),
        (CriticReferenceKind.RISK_DESCRIPTION, "description"),
        (CriticReferenceKind.RISK_SEVERITY, "severity"),
        (CriticReferenceKind.MITIGATION, "mitigation"),
        (CriticReferenceKind.RESIDUAL_UNCERTAINTY, "residual_uncertainty"),
    ):
        for risk in risks:
            raw_value = getattr(risk, attribute)
            value = raw_value.value if hasattr(raw_value, "value") else raw_value
            reference = _scalar_reference(
                source,
                kind,
                value,
                risk.id,
                item_id=risk.id,
            )
            if reference is not None:
                yield reference
    yield from _unique_text_references(
        source,
        CriticReferenceKind.OVERALL_OBSERVATION,
        snapshot.risk_assessment.overall_observations,
    )


def normalize_allowed_critic_references(
    candidates: Iterable[AllowedCriticReference],
) -> tuple[AllowedCriticReference, ...]:
    groups: dict[
        tuple[CriticReferenceSource, CriticReferenceKind, str | None, str | None],
        list[AllowedCriticReference],
    ] = {}
    for candidate in candidates:
        groups.setdefault(candidate.emitted_identity, []).append(candidate)
    normalized = tuple(
        group[0]
        for group in groups.values()
        if len({candidate.target_key for candidate in group}) == 1
    )
    if not normalized:
        raise LLMRequestSchemaError()
    return normalized


def build_allowed_critic_references(
    snapshot: CriticPayloadSnapshot,
) -> tuple[AllowedCriticReference, ...]:
    try:
        candidates = (
            *_review_input_references(snapshot),
            *_problem_analysis_references(snapshot),
            *_solution_alternative_references(snapshot),
            *_risk_assessment_references(snapshot),
        )
        return normalize_allowed_critic_references(candidates)
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error
