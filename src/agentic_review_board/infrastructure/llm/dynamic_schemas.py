from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from typing import NoReturn

from agentic_review_board.domain.analysis import (
    AnalysisFinding,
    FactFinding,
    ProblemAnalysis,
)
from agentic_review_board.domain.critics import (
    CriticalReview,
    CriticReference,
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
from agentic_review_board.infrastructure.llm.prompts import RolePromptDefinition

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

    def as_wire_object(self) -> dict[str, object]:
        result: dict[str, object] = {
            "source": self.source.value,
            "kind": self.kind.value,
        }
        if self.item_id is not None:
            result["item_id"] = self.item_id
        if self.value is not None:
            result["value"] = self.value
        return result


@dataclass(frozen=True, slots=True)
class AllowedContradictionSide:
    reference: AllowedCriticReference
    statement: str


@dataclass(frozen=True, slots=True)
class RequestOutputSchema:
    serialized: str

    def new_document(self) -> dict[str, object]:
        try:
            document = json.loads(
                self.serialized,
                parse_constant=_reject_non_json_constant,
            )
            if not isinstance(document, dict):
                raise TypeError("request output schema must be an object")
            return document
        except Exception as error:
            raise LLMRequestSchemaError() from error


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


def _validate_allowed_reference(reference: AllowedCriticReference) -> None:
    if not reference.visible_value or not reference.target_key:
        raise ValueError("allowed reference invariant failed")
    if any(not component for component in reference.target_key):
        raise ValueError("allowed reference target key is invalid")
    validated = CriticReference.model_validate(reference.as_wire_object())
    if validated.source is not reference.source or validated.kind is not reference.kind:
        raise ValueError("allowed reference identity changed during validation")
    if validated.item_id != reference.item_id or validated.value != reference.value:
        raise ValueError("allowed reference text changed during validation")


def build_reference_schema_branch(
    reference: AllowedCriticReference,
) -> dict[str, object]:
    try:
        _validate_allowed_reference(reference)
        wire_object = reference.as_wire_object()
        properties = {key: {"const": value} for key, value in wire_object.items()}
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": properties,
            "required": list(properties),
        }
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error


def build_allowed_contradiction_sides(
    references: Iterable[AllowedCriticReference],
) -> tuple[AllowedContradictionSide, ...]:
    try:
        return tuple(
            AllowedContradictionSide(
                reference=reference,
                statement=reference.visible_value,
            )
            for reference in references
        )
    except Exception as error:
        raise LLMRequestSchemaError() from error


def build_contradiction_side_schema_branch(
    side: AllowedContradictionSide,
) -> dict[str, object]:
    try:
        if not side.statement or side.statement != side.reference.visible_value:
            raise ValueError("contradiction side invariant failed")
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "reference": build_reference_schema_branch(side.reference),
                "statement": {"const": side.statement},
            },
            "required": ["reference", "statement"],
        }
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error


def _strict_json_schema_document(schema: Mapping[str, object]) -> dict[str, object]:
    result = deepcopy(dict(schema))

    def require_properties(node: object) -> None:
        if isinstance(node, dict):
            properties = node.get("properties")
            if isinstance(properties, dict):
                node["required"] = list(properties)
            if node.get("type") == "array":
                node["maxItems"] = 10
            for value in node.values():
                require_properties(value)
        elif isinstance(node, list):
            for value in node:
                require_properties(value)

    require_properties(result)
    return result


def narrow_critic_schema(
    base_schema: Mapping[str, object],
    references: Iterable[AllowedCriticReference],
) -> dict[str, object]:
    try:
        owned_references = tuple(references)
        if not owned_references:
            raise ValueError("allowed reference catalog is empty")
        result = deepcopy(dict(base_schema))
        definitions = result.get("$defs")
        if not isinstance(definitions, dict):
            raise TypeError("CriticalReview definitions are absent")
        if not isinstance(definitions.get("CriticReference"), dict):
            raise TypeError("CriticReference definition is invalid")
        if not isinstance(definitions.get("ContradictionSide"), dict):
            raise TypeError("ContradictionSide definition is invalid")
        reference_branches = [
            build_reference_schema_branch(reference) for reference in owned_references
        ]
        side_branches = [
            build_contradiction_side_schema_branch(side)
            for side in build_allowed_contradiction_sides(owned_references)
        ]
        definitions["CriticReference"] = {"oneOf": reference_branches}
        definitions["ContradictionSide"] = {"oneOf": side_branches}
        return _strict_json_schema_document(result)
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error


def build_dynamic_critic_schema(
    snapshot: CriticPayloadSnapshot,
) -> dict[str, object]:
    try:
        references = build_allowed_critic_references(snapshot)
        return narrow_critic_schema(CriticalReview.model_json_schema(), references)
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error


def _serialize_request_schema(document: Mapping[str, object]) -> RequestOutputSchema:
    try:
        serialized = json.dumps(
            dict(document),
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        result = RequestOutputSchema(serialized=serialized)
        result.new_document()
        return result
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error


def build_request_output_schema(
    *,
    definition: RolePromptDefinition,
    payload: Mapping[str, object],
) -> RequestOutputSchema:
    try:
        if definition.role.value == "critic":
            snapshot = build_critic_payload_snapshot(payload)
            document = build_dynamic_critic_schema(snapshot)
        else:
            document = _strict_json_schema_document(
                definition.output_model.model_json_schema()
            )
        return _serialize_request_schema(document)
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error
