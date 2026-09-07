from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from itertools import permutations
from typing import NoReturn

from agentic_review_board.domain.analysis import (
    AnalysisFinding,
    FactFinding,
    ProblemAnalysis,
    ReviewInputSource,
    build_authoritative_constraints,
    build_authoritative_facts,
)
from agentic_review_board.domain.critics import (
    ContradictionSupportStatus,
    CriticalReview,
    CriticismTargetType,
    CriticReference,
    CriticReferenceKind,
    CriticReferenceSource,
)
from agentic_review_board.domain.final_reviews import (
    CriticismDispositionOutcome,
    CriticUnresolvedKind,
    CriticUnresolvedReference,
    FinalReview,
    FinalReviewSection,
    ProblemUnresolvedKind,
    ProblemUnresolvedReference,
    RiskUnresolvedReference,
    SolutionUnresolvedKind,
    SolutionUnresolvedReference,
)
from agentic_review_board.domain.review import ReviewInput
from agentic_review_board.domain.risks import (
    ProblemAnalysisBasisReference,
    ProblemAnalysisFindingKind,
    ReviewInputBasisReference,
    RiskAssessment,
    RiskScope,
    RiskScopeKind,
    SolutionAlternativeBasisReference,
    SolutionAlternativeCharacteristicKind,
)
from agentic_review_board.domain.solutions import (
    AlternativeValidationStatus,
    ConstraintReference,
    ConstraintReferenceKind,
    ConstraintSource,
    FindingReference,
    SolutionAlternative,
    SolutionAlternatives,
)
from agentic_review_board.infrastructure.llm.errors import LLMRequestSchemaError
from agentic_review_board.infrastructure.llm.prompts import RolePromptDefinition

_ANALYST_PAYLOAD_KEYS = frozenset(
    {
        "description",
        "title",
        "objective",
        "constraints",
        "context",
        "stated_facts",
    }
)

_SOLUTION_ARCHITECT_PAYLOAD_KEYS = frozenset({"review_input", "problem_analysis"})

_RISK_PAYLOAD_KEYS = frozenset(
    {"review_input", "problem_analysis", "solution_alternatives"}
)

_RISK_BASIS_TYPES = (
    ReviewInputBasisReference,
    ProblemAnalysisBasisReference,
    SolutionAlternativeBasisReference,
)

RiskBasisModel = (
    ReviewInputBasisReference
    | ProblemAnalysisBasisReference
    | SolutionAlternativeBasisReference
)


def _detach_exact_payload(
    payload: Mapping[str, object],
    *,
    expected_keys: frozenset[str],
) -> tuple[str, dict[str, object]]:
    if not isinstance(payload, Mapping):
        raise TypeError("dynamic payload must be a mapping")
    owned_top_level = dict(payload)
    if (
        len(owned_top_level) != len(expected_keys)
        or frozenset(owned_top_level) != expected_keys
    ):
        raise ValueError("dynamic payload keys are invalid")
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
        raise TypeError("dynamic payload snapshot must be an object")
    return serialized_payload, detached


@dataclass(frozen=True, slots=True)
class AnalystPayloadSnapshot:
    serialized_payload: str
    review_input: ReviewInput


def build_analyst_payload_snapshot(
    payload: Mapping[str, object],
) -> AnalystPayloadSnapshot:
    try:
        serialized_payload, detached = _detach_exact_payload(
            payload,
            expected_keys=_ANALYST_PAYLOAD_KEYS,
        )
        return AnalystPayloadSnapshot(
            serialized_payload=serialized_payload,
            review_input=ReviewInput.model_validate(detached),
        )
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error


@dataclass(frozen=True, slots=True)
class SolutionArchitectPayloadSnapshot:
    serialized_payload: str
    review_input: ReviewInput
    problem_analysis: ProblemAnalysis


def build_solution_architect_payload_snapshot(
    payload: Mapping[str, object],
) -> SolutionArchitectPayloadSnapshot:
    try:
        serialized_payload, detached = _detach_exact_payload(
            payload,
            expected_keys=_SOLUTION_ARCHITECT_PAYLOAD_KEYS,
        )
        return SolutionArchitectPayloadSnapshot(
            serialized_payload=serialized_payload,
            review_input=ReviewInput.model_validate(detached["review_input"]),
            problem_analysis=ProblemAnalysis.model_validate(
                detached["problem_analysis"]
            ),
        )
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error


@dataclass(frozen=True, slots=True)
class RiskReviewerPayloadSnapshot:
    serialized_payload: str
    review_input: ReviewInput
    problem_analysis: ProblemAnalysis
    solution_alternatives: SolutionAlternatives


@dataclass(frozen=True, slots=True)
class AllowedRiskBasis:
    reference: RiskBasisModel
    target_key: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.reference) not in _RISK_BASIS_TYPES:
            raise TypeError("reference must be an approved risk basis model")
        if not self.target_key or any(
            not isinstance(component, str) or not component
            for component in self.target_key
        ):
            raise ValueError("target_key must contain non-empty strings")

    @property
    def emitted_identity(self) -> str:
        return json.dumps(
            self.as_wire_object(),
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    def as_wire_object(self) -> dict[str, object]:
        return self.reference.model_dump(mode="json", exclude_none=True)


def build_risk_reviewer_payload_snapshot(
    payload: Mapping[str, object],
) -> RiskReviewerPayloadSnapshot:
    try:
        serialized_payload, detached = _detach_exact_payload(
            payload,
            expected_keys=_RISK_PAYLOAD_KEYS,
        )
        return RiskReviewerPayloadSnapshot(
            serialized_payload=serialized_payload,
            review_input=ReviewInput.model_validate(detached["review_input"]),
            problem_analysis=ProblemAnalysis.model_validate(
                detached["problem_analysis"]
            ),
            solution_alternatives=SolutionAlternatives.model_validate(
                detached["solution_alternatives"]
            ),
        )
    except Exception as error:
        raise LLMRequestSchemaError() from error


def _risk_basis(
    reference: RiskBasisModel,
    target_key: tuple[str, ...],
) -> AllowedRiskBasis:
    return AllowedRiskBasis(reference=reference, target_key=target_key)


def _append_unique_alternative_texts(
    candidates: list[AllowedRiskBasis],
    alternatives: tuple[SolutionAlternative, ...],
    characteristic: SolutionAlternativeCharacteristicKind,
    values_for: Callable[[SolutionAlternative], tuple[str, ...]],
) -> None:
    for alternative in alternatives:
        values = values_for(alternative)
        for index, value in enumerate(values):
            if values.count(value) != 1:
                continue
            candidates.append(
                _risk_basis(
                    SolutionAlternativeBasisReference(
                        alternative_id=alternative.id,
                        characteristic=characteristic,
                        value=value,
                    ),
                    (
                        "SOLUTION_ALTERNATIVE",
                        alternative.id,
                        characteristic.value,
                        str(index),
                    ),
                )
            )


def _append_problem_findings(
    candidates: list[AllowedRiskBasis],
    kind: ProblemAnalysisFindingKind,
    findings: tuple[FactFinding | AnalysisFinding, ...],
) -> None:
    for index, finding in enumerate(findings):
        matches = sum(
            (
                (candidate.id == finding.id and candidate.text == finding.text)
                if finding.id
                else candidate.text == finding.text
            )
            for candidate in findings
        )
        if matches != 1:
            continue
        candidates.append(
            _risk_basis(
                ProblemAnalysisBasisReference(
                    kind=kind,
                    text=finding.text,
                    id=finding.id,
                ),
                ("PROBLEM_ANALYSIS", kind.value, str(index)),
            )
        )


def build_allowed_risk_bases(
    snapshot: RiskReviewerPayloadSnapshot,
) -> tuple[AllowedRiskBasis, ...]:
    try:
        candidates: list[AllowedRiskBasis] = []
        review_input = snapshot.review_input
        review_scalars = (
            (ReviewInputSource.DESCRIPTION, review_input.description),
            (ReviewInputSource.TITLE, review_input.title),
            (ReviewInputSource.OBJECTIVE, review_input.objective),
        )
        for field, value in review_scalars:
            if value:
                candidates.append(
                    _risk_basis(
                        ReviewInputBasisReference(field=field, value=value),
                        ("REVIEW_INPUT", field.value),
                    )
                )

        review_collections = (
            (ReviewInputSource.CONSTRAINTS, review_input.constraints),
            (ReviewInputSource.CONTEXT, review_input.context),
            (ReviewInputSource.STATED_FACTS, review_input.stated_facts),
        )
        for field, values in review_collections:
            for index, value in enumerate(values):
                if not value.strip() or values.count(value) != 1:
                    continue
                candidates.append(
                    _risk_basis(
                        ReviewInputBasisReference(field=field, value=value),
                        ("REVIEW_INPUT", field.value, str(index)),
                    )
                )

        problem_analysis = snapshot.problem_analysis
        _append_problem_findings(
            candidates,
            ProblemAnalysisFindingKind.FACT,
            problem_analysis.facts,
        )
        _append_problem_findings(
            candidates,
            ProblemAnalysisFindingKind.CONSTRAINT,
            problem_analysis.constraints,
        )
        _append_problem_findings(
            candidates,
            ProblemAnalysisFindingKind.ASSUMPTION,
            problem_analysis.assumptions,
        )
        _append_problem_findings(
            candidates,
            ProblemAnalysisFindingKind.MISSING_INFORMATION,
            problem_analysis.missing_information,
        )
        _append_problem_findings(
            candidates,
            ProblemAnalysisFindingKind.UNCERTAINTY,
            problem_analysis.uncertainties,
        )

        alternatives = snapshot.solution_alternatives.alternatives
        for alternative in alternatives:
            candidates.append(
                _risk_basis(
                    SolutionAlternativeBasisReference(
                        alternative_id=alternative.id,
                        characteristic=SolutionAlternativeCharacteristicKind.DESCRIPTION,
                        value=alternative.description,
                    ),
                    (
                        "SOLUTION_ALTERNATIVE",
                        alternative.id,
                        SolutionAlternativeCharacteristicKind.DESCRIPTION.value,
                    ),
                )
            )

        text_families: tuple[
            tuple[
                SolutionAlternativeCharacteristicKind,
                Callable[[SolutionAlternative], tuple[str, ...]],
            ],
            ...,
        ] = (
            (
                SolutionAlternativeCharacteristicKind.ADVANTAGE,
                lambda alternative: alternative.advantages,
            ),
            (
                SolutionAlternativeCharacteristicKind.DISADVANTAGE,
                lambda alternative: alternative.disadvantages,
            ),
            (
                SolutionAlternativeCharacteristicKind.ASSUMPTION,
                lambda alternative: alternative.assumptions,
            ),
        )
        for characteristic, values_for in text_families:
            _append_unique_alternative_texts(
                candidates,
                alternatives,
                characteristic,
                values_for,
            )

        for alternative in alternatives:
            candidates.append(
                _risk_basis(
                    SolutionAlternativeBasisReference(
                        alternative_id=alternative.id,
                        characteristic=(
                            SolutionAlternativeCharacteristicKind.IMPLEMENTATION_COMPLEXITY
                        ),
                        value=alternative.implementation_complexity.value,
                    ),
                    (
                        "SOLUTION_ALTERNATIVE",
                        alternative.id,
                        SolutionAlternativeCharacteristicKind.IMPLEMENTATION_COMPLEXITY.value,
                    ),
                )
            )

        for alternative in alternatives:
            constraint_keys = tuple(
                constraint.model_dump_json()
                for constraint in alternative.relevant_constraints
            )
            for index, constraint in enumerate(alternative.relevant_constraints):
                if constraint_keys.count(constraint_keys[index]) != 1:
                    continue
                candidates.append(
                    _risk_basis(
                        SolutionAlternativeBasisReference(
                            alternative_id=alternative.id,
                            characteristic=(
                                SolutionAlternativeCharacteristicKind.RELEVANT_CONSTRAINT
                            ),
                            value=constraint,
                        ),
                        (
                            "SOLUTION_ALTERNATIVE",
                            alternative.id,
                            SolutionAlternativeCharacteristicKind.RELEVANT_CONSTRAINT.value,
                            str(index),
                        ),
                    )
                )
        return normalize_allowed_risk_bases(candidates)
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error


def normalize_allowed_risk_bases(
    candidates: Iterable[AllowedRiskBasis],
) -> tuple[AllowedRiskBasis, ...]:
    groups: dict[str, list[AllowedRiskBasis]] = {}
    for candidate in candidates:
        groups.setdefault(candidate.emitted_identity, []).append(candidate)
    return tuple(
        group[0]
        for group in groups.values()
        if len({candidate.target_key for candidate in group}) == 1
    )


def build_allowed_risk_scopes(
    snapshot: RiskReviewerPayloadSnapshot,
) -> tuple[RiskScope, ...]:
    try:
        alternative_ids = tuple(
            alternative.id
            for alternative in snapshot.solution_alternatives.alternatives
        )
        scopes = [RiskScope(kind=RiskScopeKind.OVERALL)]
        for length in range(1, len(alternative_ids) + 1):
            scopes.extend(
                RiskScope(
                    kind=RiskScopeKind.ALTERNATIVES,
                    alternative_ids=alternative_ids_permutation,
                )
                for alternative_ids_permutation in permutations(
                    alternative_ids,
                    length,
                )
            )
        return tuple(scopes)
    except Exception as error:
        raise LLMRequestSchemaError() from error


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
class _CriticReferenceSchemaNode:
    name: str
    start: int
    stop: int
    children: tuple[_CriticReferenceSchemaNode, ...] = ()


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


@dataclass(frozen=True, slots=True)
class DynamicRequestContext:
    serialized_payload: str
    output_schema: RequestOutputSchema


_COORDINATOR_PAYLOAD_KEYS = frozenset(
    {
        "review_input",
        "problem_analysis",
        "solution_alternatives",
        "risk_assessment",
        "critical_review",
    }
)

CoordinatorReferenceModel = (
    ProblemUnresolvedReference
    | SolutionUnresolvedReference
    | RiskUnresolvedReference
    | CriticUnresolvedReference
)


@dataclass(frozen=True, slots=True)
class CoordinatorPayloadSnapshot:
    serialized_payload: str
    review_input: ReviewInput
    problem_analysis: ProblemAnalysis
    solution_alternatives: SolutionAlternatives
    risk_assessment: RiskAssessment
    critical_review: CriticalReview


@dataclass(frozen=True, slots=True)
class AllowedCoordinatorReference:
    reference: CoordinatorReferenceModel
    target_key: tuple[str, ...]

    @property
    def emitted_identity(self) -> str:
        return json.dumps(
            self.as_wire_object(),
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    def as_wire_object(self) -> dict[str, object]:
        return self.reference.model_dump(mode="json", exclude_none=True)


def build_coordinator_payload_snapshot(
    payload: Mapping[str, object],
) -> CoordinatorPayloadSnapshot:
    try:
        serialized_payload, detached = _detach_exact_payload(
            payload,
            expected_keys=_COORDINATOR_PAYLOAD_KEYS,
        )
        return CoordinatorPayloadSnapshot(
            serialized_payload=serialized_payload,
            review_input=ReviewInput.model_validate(detached["review_input"]),
            problem_analysis=ProblemAnalysis.model_validate(
                detached["problem_analysis"]
            ),
            solution_alternatives=SolutionAlternatives.model_validate(
                detached["solution_alternatives"]
            ),
            risk_assessment=RiskAssessment.model_validate(detached["risk_assessment"]),
            critical_review=CriticalReview.model_validate(detached["critical_review"]),
        )
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error


def _coordinator_reference(
    reference: CoordinatorReferenceModel,
    *target_key: str,
) -> AllowedCoordinatorReference:
    return AllowedCoordinatorReference(reference=reference, target_key=target_key)


def _problem_unresolved_references(
    snapshot: CoordinatorPayloadSnapshot,
) -> Iterable[AllowedCoordinatorReference]:
    for kind, findings in (
        (
            ProblemUnresolvedKind.PROBLEM_ASSUMPTION,
            snapshot.problem_analysis.assumptions,
        ),
        (
            ProblemUnresolvedKind.MISSING_INFORMATION,
            snapshot.problem_analysis.missing_information,
        ),
        (ProblemUnresolvedKind.UNCERTAINTY, snapshot.problem_analysis.uncertainties),
    ):
        for index, finding in enumerate(findings):
            yield _coordinator_reference(
                ProblemUnresolvedReference(
                    kind=kind,
                    item_id=finding.id,
                    value=finding.text,
                ),
                "PROBLEM_ANALYSIS",
                kind.value,
                str(index),
            )


def _solution_unresolved_references(
    snapshot: CoordinatorPayloadSnapshot,
) -> Iterable[AllowedCoordinatorReference]:
    for alternative in snapshot.solution_alternatives.alternatives:
        for index, assumption in enumerate(alternative.assumptions):
            yield _coordinator_reference(
                SolutionUnresolvedReference(
                    kind=SolutionUnresolvedKind.ALTERNATIVE_ASSUMPTION,
                    alternative_id=alternative.id,
                    value=assumption,
                ),
                "SOLUTION_ALTERNATIVES",
                SolutionUnresolvedKind.ALTERNATIVE_ASSUMPTION.value,
                alternative.id,
                str(index),
            )

    notes = snapshot.solution_alternatives.generation_notes
    if notes is None:
        return
    for kind, findings in (
        (
            SolutionUnresolvedKind.BLOCKING_MISSING_INFORMATION,
            notes.blocking_missing_information,
        ),
        (SolutionUnresolvedKind.BLOCKING_UNCERTAINTY, notes.blocking_uncertainties),
    ):
        for index, finding in enumerate(findings):
            yield _coordinator_reference(
                SolutionUnresolvedReference(
                    kind=kind,
                    item_id=finding.id,
                    value=finding.text,
                ),
                "SOLUTION_ALTERNATIVES",
                kind.value,
                str(index),
            )


def _risk_unresolved_references(
    snapshot: CoordinatorPayloadSnapshot,
) -> Iterable[AllowedCoordinatorReference]:
    for risk in snapshot.risk_assessment.risks:
        if risk.residual_uncertainty is None:
            continue
        yield _coordinator_reference(
            RiskUnresolvedReference(
                risk_id=risk.id,
                value=risk.residual_uncertainty,
            ),
            "RISK_ASSESSMENT",
            risk.id,
            "RESIDUAL_UNCERTAINTY",
        )


def _critic_unresolved_references(
    snapshot: CoordinatorPayloadSnapshot,
) -> Iterable[AllowedCoordinatorReference]:
    critical_review = snapshot.critical_review
    for missing_alternative in critical_review.missing_alternatives:
        yield _coordinator_reference(
            CriticUnresolvedReference(
                kind=CriticUnresolvedKind.MISSING_ALTERNATIVE,
                item_id=missing_alternative.id,
                value=missing_alternative.category,
            ),
            "CRITICAL_REVIEW",
            CriticUnresolvedKind.MISSING_ALTERNATIVE.value,
            missing_alternative.id,
        )
    for contradiction in critical_review.contradictions:
        yield _coordinator_reference(
            CriticUnresolvedReference(
                kind=CriticUnresolvedKind.CONTRADICTION,
                item_id=contradiction.id,
                value=contradiction.rationale,
            ),
            "CRITICAL_REVIEW",
            CriticUnresolvedKind.CONTRADICTION.value,
            contradiction.id,
        )
    for unresolved_issue in critical_review.unresolved_issues:
        yield _coordinator_reference(
            CriticUnresolvedReference(
                kind=CriticUnresolvedKind.UNRESOLVED_ISSUE,
                item_id=unresolved_issue.id,
                value=unresolved_issue.issue,
            ),
            "CRITICAL_REVIEW",
            CriticUnresolvedKind.UNRESOLVED_ISSUE.value,
            unresolved_issue.id,
        )


def build_allowed_coordinator_references(
    snapshot: CoordinatorPayloadSnapshot,
) -> tuple[AllowedCoordinatorReference, ...]:
    try:
        candidates = (
            *_problem_unresolved_references(snapshot),
            *_solution_unresolved_references(snapshot),
            *_risk_unresolved_references(snapshot),
            *_critic_unresolved_references(snapshot),
        )
        groups: dict[str, list[AllowedCoordinatorReference]] = {}
        for candidate in candidates:
            groups.setdefault(candidate.emitted_identity, []).append(candidate)
        return tuple(
            group[0]
            for group in groups.values()
            if len({candidate.target_key for candidate in group}) == 1
        )
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error


def build_critic_payload_snapshot(
    payload: Mapping[str, object],
) -> CriticPayloadSnapshot:
    try:
        serialized_payload, detached = _detach_exact_payload(
            payload,
            expected_keys=_CRITIC_PAYLOAD_KEYS,
        )
        return CriticPayloadSnapshot(
            serialized_payload=serialized_payload,
            review_input=ReviewInput.model_validate(detached["review_input"]),
            problem_analysis=ProblemAnalysis.model_validate(
                detached["problem_analysis"]
            ),
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


def _review_input_references(
    snapshot: CriticPayloadSnapshot,
) -> Iterable[AllowedCriticReference]:
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
            target_key=(
                source.value,
                CriticReferenceKind.ALTERNATIVE.value,
                alternative.id,
            ),
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


def _definition_reference(name: str) -> dict[str, object]:
    if not name:
        raise ValueError("schema definition name must not be empty")
    return {"$ref": f"#/$defs/{name}"}


def _build_critic_reference_schema_tree(
    definitions: dict[str, object],
    references: tuple[AllowedCriticReference, ...],
) -> _CriticReferenceSchemaNode:
    width = max(4, len(str(len(references))))

    def build(start: int, stop: int) -> _CriticReferenceSchemaNode:
        if stop - start == 1:
            name = f"CriticReferenceExact{start:0{width}d}"
            if name in definitions:
                raise ValueError("generated Critic reference definition collides")
            definitions[name] = build_reference_schema_branch(references[start])
            return _CriticReferenceSchemaNode(name=name, start=start, stop=stop)

        middle = start + (stop - start) // 2
        children = (build(start, middle), build(middle, stop))
        name = f"CriticReferenceSet{start:0{width}d}_{stop:0{width}d}"
        if name in definitions:
            raise ValueError("generated Critic reference definition collides")
        definitions[name] = {
            "oneOf": [_definition_reference(child.name) for child in children]
        }
        return _CriticReferenceSchemaNode(
            name=name,
            start=start,
            stop=stop,
            children=children,
        )

    return build(0, len(references))


def _critic_reference_complement(
    node: _CriticReferenceSchemaNode,
    excluded_index: int,
) -> list[dict[str, object]]:
    if excluded_index < node.start or excluded_index >= node.stop:
        return [_definition_reference(node.name)]
    if not node.children:
        return []
    return [
        reference
        for child in node.children
        for reference in _critic_reference_complement(child, excluded_index)
    ]


def _critic_reference_union(branches: list[dict[str, object]]) -> dict[str, object]:
    if not branches:
        raise ValueError("Critic reference union must not be empty")
    if len(branches) == 1:
        return branches[0]
    return {"oneOf": branches}


def _criticism_schema_branch(
    base_criticism: Mapping[str, object],
    *,
    target_reference: Mapping[str, object],
    basis_item: Mapping[str, object] | None,
    target_may_be_null: bool,
    null_target_type: CriticismTargetType | None = None,
) -> dict[str, object]:
    branch = deepcopy(dict(base_criticism))
    properties = branch.get("properties")
    if not isinstance(properties, dict):
        raise TypeError("Criticism properties are absent")
    basis_references = properties.get("basis_references")
    if (
        not isinstance(basis_references, dict)
        or basis_references.get("type") != "array"
    ):
        raise TypeError("Criticism basis references schema is invalid")

    properties["target_reference"] = deepcopy(dict(target_reference))
    if basis_item is None:
        properties["basis_references"] = {"const": []}
    else:
        basis_references["items"] = deepcopy(dict(basis_item))
        if target_may_be_null:
            if null_target_type is None:
                raise TypeError("null-target criticism type is absent")
            basis_references["minItems"] = (
                2
                if null_target_type is CriticismTargetType.CROSS_ARTIFACT_CONCLUSION
                else 1
            )
    if target_may_be_null:
        assert null_target_type is not None
        properties["target_type"] = {"const": null_target_type.value}
    else:
        properties["target_type"] = {
            "enum": [
                target_type.value
                for target_type in CriticismTargetType
                if target_type is not CriticismTargetType.CROSS_ARTIFACT_CONCLUSION
            ]
        }
    return branch


def strict_json_schema_document(schema: Mapping[str, object]) -> dict[str, object]:
    result = deepcopy(dict(schema))

    def require_properties(node: object) -> None:
        if isinstance(node, dict):
            properties = node.get("properties")
            if isinstance(properties, dict):
                node["required"] = list(properties)
            if node.get("type") == "array":
                node.setdefault("maxItems", 10)
            for value in node.values():
                require_properties(value)
        elif isinstance(node, list):
            for value in node:
                require_properties(value)

    require_properties(result)
    return result


def _closed_exact_object_branch(
    wire_object: Mapping[str, object],
) -> dict[str, object]:
    properties: dict[str, object] = {}
    for key, value in wire_object.items():
        if not isinstance(key, str) or not key:
            raise TypeError("exact branch property name is invalid")
        if isinstance(value, str):
            properties[key] = {"const": value}
            continue
        if key != "value" or not isinstance(value, dict):
            raise TypeError("exact basis branch contains an unsupported value")
        if tuple(value) != ("source", "kind", "value") or not all(
            isinstance(component, str) for component in value.values()
        ):
            raise ValueError("structured constraint wire value is invalid")
        nested_properties = {
            nested_key: {"const": nested_value}
            for nested_key, nested_value in value.items()
        }
        properties[key] = {
            "type": "object",
            "additionalProperties": False,
            "properties": nested_properties,
            "required": list(nested_properties),
        }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": list(properties),
    }


def narrow_analyst_schema(
    base_schema: Mapping[str, object],
    review_input: ReviewInput,
) -> dict[str, object]:
    try:
        if not isinstance(review_input, ReviewInput):
            raise TypeError("Analyst ReviewInput is invalid")
        result = deepcopy(dict(base_schema))
        properties = result.get("properties")
        definitions = result.get("$defs")
        if not isinstance(properties, dict) or not isinstance(definitions, dict):
            raise TypeError("ProblemAnalysis schema shape is invalid")
        if not isinstance(definitions.get("FactFinding"), dict):
            raise TypeError("FactFinding definition is invalid")
        if not isinstance(definitions.get("AnalysisFinding"), dict):
            raise TypeError("AnalysisFinding definition is invalid")
        for field in ("objective", "facts", "constraints"):
            if not isinstance(properties.get(field), dict):
                raise TypeError("ProblemAnalysis authoritative property is invalid")

        facts = [
            fact.model_dump(mode="json")
            for fact in build_authoritative_facts(review_input)
        ]
        constraints = [
            constraint.model_dump(mode="json")
            for constraint in build_authoritative_constraints(review_input)
        ]
        properties["facts"] = {"const": facts}
        properties["constraints"] = {"const": constraints}
        if review_input.objective is not None and review_input.objective.strip():
            properties["objective"] = {"const": review_input.objective}
        return strict_json_schema_document(result)
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error


def build_dynamic_analyst_schema(
    snapshot: AnalystPayloadSnapshot,
) -> dict[str, object]:
    try:
        return narrow_analyst_schema(
            ProblemAnalysis.model_json_schema(),
            snapshot.review_input,
        )
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error


def build_allowed_solution_constraint_references(
    snapshot: SolutionArchitectPayloadSnapshot,
) -> tuple[ConstraintReference, ...]:
    try:
        candidates = [
            ConstraintReference(
                source=ConstraintSource.REVIEW_INPUT,
                kind=ConstraintReferenceKind.TEXT,
                value=value,
            )
            for value in snapshot.review_input.constraints
        ]
        constraint_texts = tuple(
            constraint.text for constraint in snapshot.problem_analysis.constraints
        )
        for constraint in snapshot.problem_analysis.constraints:
            if constraint.id is not None:
                candidates.append(
                    ConstraintReference(
                        source=ConstraintSource.PROBLEM_ANALYSIS,
                        kind=ConstraintReferenceKind.ID,
                        value=constraint.id,
                    )
                )
            if constraint_texts.count(constraint.text) == 1:
                candidates.append(
                    ConstraintReference(
                        source=ConstraintSource.PROBLEM_ANALYSIS,
                        kind=ConstraintReferenceKind.TEXT,
                        value=constraint.text,
                    )
                )

        normalized: dict[str, ConstraintReference] = {}
        for candidate in candidates:
            normalized.setdefault(candidate.model_dump_json(), candidate)
        return tuple(normalized.values())
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error


def build_allowed_solution_blocker_references(
    findings: Sequence[AnalysisFinding],
) -> tuple[FindingReference, ...]:
    try:
        candidates: list[FindingReference] = []
        for finding in findings:
            if finding.id is None:
                matches = sum(candidate.text == finding.text for candidate in findings)
                if matches != 1:
                    continue
            candidates.append(FindingReference(id=finding.id, text=finding.text))
        return tuple(candidates)
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error


def build_solution_reference_schema_branch(
    reference: ConstraintReference | FindingReference,
) -> dict[str, object]:
    try:
        if not isinstance(reference, (ConstraintReference, FindingReference)):
            raise TypeError("Solution Architect reference is invalid")
        return _closed_exact_object_branch(
            reference.model_dump(mode="json", exclude_none=True)
        )
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error


def narrow_solution_architect_schema(
    base_schema: Mapping[str, object],
    constraint_references: Iterable[ConstraintReference],
    missing_information_references: Iterable[FindingReference],
    uncertainty_references: Iterable[FindingReference],
) -> dict[str, object]:
    try:
        owned_constraints = tuple(constraint_references)
        owned_missing = tuple(missing_information_references)
        owned_uncertainties = tuple(uncertainty_references)
        result = deepcopy(dict(base_schema))
        definitions = result.get("$defs")
        if not isinstance(definitions, dict):
            raise TypeError("SolutionAlternatives definitions are absent")
        if not isinstance(definitions.get("ConstraintReference"), dict):
            raise TypeError("ConstraintReference definition is invalid")
        alternative = definitions.get("SolutionAlternative")
        generation_notes = definitions.get("GenerationNotes")
        if not isinstance(alternative, dict) or not isinstance(generation_notes, dict):
            raise TypeError("Solution Architect definitions are invalid")
        alternative_properties = alternative.get("properties")
        notes_properties = generation_notes.get("properties")
        if not isinstance(alternative_properties, dict) or not isinstance(
            notes_properties, dict
        ):
            raise TypeError("Solution Architect definition properties are invalid")
        relevant_constraints = alternative_properties.get("relevant_constraints")
        if not isinstance(relevant_constraints, dict):
            raise TypeError("relevant constraints schema is invalid")
        alternative_properties["validation_status"] = {
            "const": AlternativeValidationStatus.PROPOSED.value
        }
        alternative_required = alternative.get("required")
        if not isinstance(alternative_required, list):
            raise TypeError("SolutionAlternative required fields are invalid")
        if "validation_status" not in alternative_required:
            alternative_required.append("validation_status")

        if owned_constraints:
            definitions["ConstraintReference"] = {
                "oneOf": [
                    build_solution_reference_schema_branch(reference)
                    for reference in owned_constraints
                ]
            }
        else:
            alternative_properties["relevant_constraints"] = {"const": []}

        for name, references in (
            ("blocking_missing_information", owned_missing),
            ("blocking_uncertainties", owned_uncertainties),
        ):
            property_schema = notes_properties.get(name)
            if not isinstance(property_schema, dict):
                raise TypeError("generation blocker schema is invalid")
            if references:
                property_schema["items"] = {
                    "oneOf": [
                        build_solution_reference_schema_branch(reference)
                        for reference in references
                    ]
                }
            else:
                notes_properties[name] = {"const": []}
        return strict_json_schema_document(result)
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error


def build_dynamic_solution_architect_schema(
    snapshot: SolutionArchitectPayloadSnapshot,
) -> dict[str, object]:
    try:
        return narrow_solution_architect_schema(
            SolutionAlternatives.model_json_schema(),
            build_allowed_solution_constraint_references(snapshot),
            build_allowed_solution_blocker_references(
                snapshot.problem_analysis.missing_information
            ),
            build_allowed_solution_blocker_references(
                snapshot.problem_analysis.uncertainties
            ),
        )
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error


def build_coordinator_reference_schema_branch(
    reference: AllowedCoordinatorReference,
) -> dict[str, object]:
    try:
        if (
            not isinstance(reference, AllowedCoordinatorReference)
            or not reference.target_key
        ):
            raise TypeError("allowed Coordinator reference is invalid")
        return _closed_exact_object_branch(reference.as_wire_object())
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error


def build_criticism_disposition_schema_branch(
    criticism_id: str,
    outcome: CriticismDispositionOutcome,
) -> dict[str, object]:
    try:
        if not criticism_id or not isinstance(outcome, CriticismDispositionOutcome):
            raise ValueError("criticism disposition branch identity is invalid")
        reflected_in: dict[str, object]
        if outcome is CriticismDispositionOutcome.REFLECTED:
            reflected_in = {
                "type": "array",
                "items": {"enum": [section.value for section in FinalReviewSection]},
                "minItems": 1,
            }
        else:
            reflected_in = {"const": []}
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "criticism_id": {"const": criticism_id},
                "outcome": {"const": outcome.value},
                "rationale": {"type": "string", "minLength": 1},
                "reflected_in": reflected_in,
            },
            "required": ["criticism_id", "outcome", "rationale", "reflected_in"],
        }
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error


def build_risk_basis_schema_branch(
    basis: AllowedRiskBasis,
) -> dict[str, object]:
    try:
        if not isinstance(basis, AllowedRiskBasis):
            raise TypeError("allowed risk basis is invalid")
        return _closed_exact_object_branch(basis.as_wire_object())
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error


def build_risk_scope_schema_branch(scope: RiskScope) -> dict[str, object]:
    try:
        if not isinstance(scope, RiskScope):
            raise TypeError("allowed risk scope is invalid")
        wire_object = scope.model_dump(mode="json")
        if tuple(wire_object) != ("kind", "alternative_ids"):
            raise ValueError("risk scope wire shape is invalid")
        kind = wire_object["kind"]
        alternative_ids = wire_object["alternative_ids"]
        if not isinstance(kind, str) or not isinstance(alternative_ids, list):
            raise TypeError("risk scope wire values are invalid")
        if any(
            not isinstance(alternative_id, str) for alternative_id in alternative_ids
        ):
            raise TypeError("risk scope alternative id is invalid")
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "kind": {"const": kind},
                "alternative_ids": {"const": list(alternative_ids)},
            },
            "required": ["kind", "alternative_ids"],
        }
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error


def narrow_risk_schema(
    base_schema: Mapping[str, object],
    bases: Iterable[AllowedRiskBasis],
    scopes: Iterable[RiskScope],
) -> dict[str, object]:
    try:
        owned_bases = tuple(bases)
        owned_scopes = tuple(scopes)
        if not owned_scopes:
            raise ValueError("allowed risk scope catalog is empty")
        if owned_bases != normalize_allowed_risk_bases(owned_bases):
            raise ValueError("allowed risk basis catalog is not normalized")
        overall_scope = RiskScope(kind=RiskScopeKind.OVERALL)
        singleton_ids = tuple(
            scope.alternative_ids[0]
            for scope in owned_scopes
            if scope.kind is RiskScopeKind.ALTERNATIVES
            and len(scope.alternative_ids) == 1
        )
        expected_scopes = [overall_scope]
        for length in range(1, len(singleton_ids) + 1):
            expected_scopes.extend(
                RiskScope(
                    kind=RiskScopeKind.ALTERNATIVES,
                    alternative_ids=alternative_ids_permutation,
                )
                for alternative_ids_permutation in permutations(singleton_ids, length)
            )
        if owned_scopes != tuple(expected_scopes):
            raise ValueError("allowed risk scope catalog is incomplete or out of order")

        result = strict_json_schema_document(base_schema)
        root_properties = result.get("properties")
        if not isinstance(root_properties, dict):
            raise TypeError("RiskAssessment properties are absent")
        risks_schema = root_properties.get("risks")
        if not isinstance(risks_schema, dict) or risks_schema.get("type") != "array":
            raise TypeError("RiskAssessment risks schema is invalid")

        definitions = result.get("$defs")
        if not isinstance(definitions, dict):
            raise TypeError("RiskAssessment definitions are absent")
        risk_schema = definitions.get("Risk")
        if not isinstance(risk_schema, dict) or risk_schema.get("type") != "object":
            raise TypeError("Risk definition is invalid")
        risk_properties = risk_schema.get("properties")
        if not isinstance(risk_properties, dict):
            raise TypeError("Risk properties are absent")
        basis_schema = risk_properties.get("basis")
        if not isinstance(basis_schema, dict) or basis_schema.get("type") != "array":
            raise TypeError("Risk basis schema is invalid")
        if not isinstance(basis_schema.get("items"), dict):
            raise TypeError("Risk basis item schema is invalid")
        affected_scope = risk_properties.get("affected_scope")
        if not isinstance(affected_scope, dict) or affected_scope.get("$ref") != (
            "#/$defs/RiskScope"
        ):
            raise ValueError("Risk affected scope reference is invalid")
        if not isinstance(definitions.get("RiskScope"), dict):
            raise TypeError("RiskScope definition is invalid")

        if owned_bases:
            basis_schema["items"] = {
                "oneOf": [
                    build_risk_basis_schema_branch(basis) for basis in owned_bases
                ]
            }
            basis_schema["minItems"] = 1
        else:
            risks_schema["maxItems"] = 0

        definitions["RiskScope"] = {
            "oneOf": [build_risk_scope_schema_branch(scope) for scope in owned_scopes]
        }
        return result
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error


def build_dynamic_risk_schema(
    snapshot: RiskReviewerPayloadSnapshot,
) -> dict[str, object]:
    try:
        bases = build_allowed_risk_bases(snapshot)
        scopes = build_allowed_risk_scopes(snapshot)
        return narrow_risk_schema(RiskAssessment.model_json_schema(), bases, scopes)
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error


def narrow_coordinator_schema(
    base_schema: Mapping[str, object],
    references: Iterable[AllowedCoordinatorReference],
    criticism_ids: Iterable[str],
    alternative_statuses: Iterable[tuple[str, AlternativeValidationStatus]],
) -> dict[str, object]:
    try:
        owned_references = tuple(references)
        owned_criticism_ids = tuple(criticism_ids)
        owned_alternative_statuses = tuple(alternative_statuses)
        if any(not criticism_id for criticism_id in owned_criticism_ids):
            raise ValueError("criticism id must not be empty")
        if len(owned_criticism_ids) != len(set(owned_criticism_ids)):
            raise ValueError("criticism ids must be unique")
        alternative_ids = tuple(
            alternative_id for alternative_id, _status in owned_alternative_statuses
        )
        if any(not alternative_id for alternative_id in alternative_ids):
            raise ValueError("alternative id must not be empty")
        if len(alternative_ids) != len(set(alternative_ids)):
            raise ValueError("alternative ids must be unique")

        result = deepcopy(dict(base_schema))
        definitions = result.get("$defs")
        properties = result.get("properties")
        if not isinstance(definitions, dict) or not isinstance(properties, dict):
            raise TypeError("FinalReview schema shape is invalid")
        unresolved_definition = definitions.get("UnresolvedQuestion")
        if not isinstance(unresolved_definition, dict):
            raise TypeError("UnresolvedQuestion definition is invalid")
        unresolved_properties = unresolved_definition.get("properties")
        if not isinstance(unresolved_properties, dict):
            raise TypeError("UnresolvedQuestion properties are invalid")
        if not isinstance(definitions.get("CriticismDisposition"), dict):
            raise TypeError("CriticismDisposition definition is invalid")
        ranked_definition = definitions.get("RankedAlternative")
        if not isinstance(ranked_definition, dict):
            raise TypeError("RankedAlternative definition is invalid")

        if owned_alternative_statuses:
            ranked_branches: list[dict[str, object]] = []
            for alternative_id, status in owned_alternative_statuses:
                if not isinstance(status, AlternativeValidationStatus):
                    raise TypeError("alternative validation status is invalid")
                branch = deepcopy(ranked_definition)
                branch_properties = branch.get("properties")
                branch_required = branch.get("required")
                if not isinstance(branch_properties, dict) or not isinstance(
                    branch_required, list
                ):
                    raise TypeError("RankedAlternative branch shape is invalid")
                branch_properties["alternative_id"] = {"const": alternative_id}
                branch_properties["validation_status"] = {"const": status.value}
                if "validation_status" not in branch_required:
                    branch_required.append("validation_status")
                ranked_branches.append(branch)
            definitions["RankedAlternative"] = {"oneOf": ranked_branches}
        else:
            properties["ranked_alternatives"] = {"const": []}

        if owned_references:
            unresolved_properties["reference"] = {
                "oneOf": [
                    build_coordinator_reference_schema_branch(reference)
                    for reference in owned_references
                ]
            }
        else:
            properties["unresolved_questions"] = {"const": []}

        if owned_criticism_ids:
            definitions["CriticismDisposition"] = {
                "oneOf": [
                    build_criticism_disposition_schema_branch(criticism_id, outcome)
                    for criticism_id in owned_criticism_ids
                    for outcome in CriticismDispositionOutcome
                ]
            }
        else:
            properties["criticism_dispositions"] = {"const": []}

        strict = strict_json_schema_document(result)
        strict_properties = strict.get("properties")
        if not isinstance(strict_properties, dict):
            raise TypeError("strict FinalReview properties are invalid")
        if owned_criticism_ids:
            dispositions = strict_properties.get("criticism_dispositions")
            if not isinstance(dispositions, dict):
                raise TypeError("criticism dispositions schema is invalid")
            dispositions["minItems"] = len(owned_criticism_ids)
            dispositions["maxItems"] = len(owned_criticism_ids)
        return strict
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error


def build_dynamic_coordinator_schema(
    snapshot: CoordinatorPayloadSnapshot,
) -> dict[str, object]:
    try:
        references = build_allowed_coordinator_references(snapshot)
        criticism_ids = tuple(
            criticism.id for criticism in snapshot.critical_review.criticisms
        )
        return narrow_coordinator_schema(
            FinalReview.model_json_schema(),
            references,
            criticism_ids,
            tuple(
                (alternative.id, alternative.validation_status)
                for alternative in snapshot.solution_alternatives.alternatives
            ),
        )
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error


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
        contradiction_definition = definitions.get("Contradiction")
        if not isinstance(contradiction_definition, dict):
            raise TypeError("Contradiction definition is invalid")
        contradiction_properties = contradiction_definition.get("properties")
        contradiction_required = contradiction_definition.get("required")
        if not isinstance(contradiction_properties, dict) or not isinstance(
            contradiction_required, list
        ):
            raise TypeError("Contradiction schema shape is invalid")
        contradiction_properties["support_status"] = {
            "const": ContradictionSupportStatus.UNVERIFIED.value
        }
        if "support_status" not in contradiction_required:
            contradiction_required.append("support_status")
        criticism_definition = definitions.get("Criticism")
        if not isinstance(criticism_definition, dict):
            raise TypeError("Criticism definition is invalid")
        reference_tree = _build_critic_reference_schema_tree(
            definitions,
            owned_references,
        )
        side_branches = [
            build_contradiction_side_schema_branch(side)
            for side in build_allowed_contradiction_sides(owned_references)
        ]
        definitions["CriticReference"] = _definition_reference(reference_tree.name)
        definitions["ContradictionSide"] = {"oneOf": side_branches}
        reference_name_width = max(4, len(str(len(owned_references))))
        criticism_branches = []
        for index in range(len(owned_references)):
            complement = _critic_reference_complement(reference_tree, index)
            criticism_branches.append(
                _criticism_schema_branch(
                    criticism_definition,
                    target_reference=_definition_reference(
                        f"CriticReferenceExact{index:0{reference_name_width}d}"
                    ),
                    basis_item=(
                        _critic_reference_union(complement) if complement else None
                    ),
                    target_may_be_null=False,
                )
            )
        for target_type in (
            CriticismTargetType.OMISSION,
            CriticismTargetType.CROSS_ARTIFACT_CONCLUSION,
        ):
            criticism_branches.append(
                _criticism_schema_branch(
                    criticism_definition,
                    target_reference={"type": "null"},
                    basis_item=_definition_reference("CriticReference"),
                    target_may_be_null=True,
                    null_target_type=target_type,
                )
            )
        definitions["Criticism"] = {"oneOf": criticism_branches}
        return strict_json_schema_document(result)
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


def build_critic_request_output_schema(
    snapshot: CriticPayloadSnapshot,
) -> RequestOutputSchema:
    try:
        return _serialize_request_schema(build_dynamic_critic_schema(snapshot))
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error


def build_analyst_request_output_schema(
    snapshot: AnalystPayloadSnapshot,
) -> RequestOutputSchema:
    try:
        return _serialize_request_schema(build_dynamic_analyst_schema(snapshot))
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error


def build_solution_architect_request_output_schema(
    snapshot: SolutionArchitectPayloadSnapshot,
) -> RequestOutputSchema:
    try:
        return _serialize_request_schema(
            build_dynamic_solution_architect_schema(snapshot)
        )
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error


def build_risk_reviewer_request_output_schema(
    snapshot: RiskReviewerPayloadSnapshot,
) -> RequestOutputSchema:
    try:
        return _serialize_request_schema(build_dynamic_risk_schema(snapshot))
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error


def build_coordinator_request_output_schema(
    snapshot: CoordinatorPayloadSnapshot,
) -> RequestOutputSchema:
    try:
        return _serialize_request_schema(build_dynamic_coordinator_schema(snapshot))
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error


def build_dynamic_request_context(
    *,
    definition: RolePromptDefinition,
    payload: Mapping[str, object],
) -> DynamicRequestContext | None:
    try:
        role = definition.role.value
        if role == "analyst":
            analyst_snapshot = build_analyst_payload_snapshot(payload)
            return DynamicRequestContext(
                serialized_payload=analyst_snapshot.serialized_payload,
                output_schema=build_analyst_request_output_schema(analyst_snapshot),
            )
        if role == "solution_architect":
            solution_snapshot = build_solution_architect_payload_snapshot(payload)
            return DynamicRequestContext(
                serialized_payload=solution_snapshot.serialized_payload,
                output_schema=build_solution_architect_request_output_schema(
                    solution_snapshot
                ),
            )
        if role == "risk_reviewer":
            risk_snapshot = build_risk_reviewer_payload_snapshot(payload)
            return DynamicRequestContext(
                serialized_payload=risk_snapshot.serialized_payload,
                output_schema=build_risk_reviewer_request_output_schema(risk_snapshot),
            )
        if role == "critic":
            critic_snapshot = build_critic_payload_snapshot(payload)
            return DynamicRequestContext(
                serialized_payload=critic_snapshot.serialized_payload,
                output_schema=build_critic_request_output_schema(critic_snapshot),
            )
        if role == "coordinator":
            coordinator_snapshot = build_coordinator_payload_snapshot(payload)
            return DynamicRequestContext(
                serialized_payload=coordinator_snapshot.serialized_payload,
                output_schema=build_coordinator_request_output_schema(
                    coordinator_snapshot
                ),
            )
        raise ValueError("dynamic request role is invalid")
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
        context = build_dynamic_request_context(
            definition=definition,
            payload=payload,
        )
        if context is not None:
            return context.output_schema
        document = strict_json_schema_document(
            definition.output_model.model_json_schema()
        )
        return _serialize_request_schema(document)
    except LLMRequestSchemaError:
        raise
    except Exception as error:
        raise LLMRequestSchemaError() from error
