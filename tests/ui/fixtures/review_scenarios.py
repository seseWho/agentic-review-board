"""Deterministic five-participant scenarios used by functional UI tests."""

from collections.abc import Mapping
from enum import StrEnum
from time import sleep
from typing import cast

from agentic_review_board.application.observation import ReviewObserver
from agentic_review_board.application.orchestrator import ReviewOrchestrator
from agentic_review_board.domain.execution import Review
from agentic_review_board.participants.analyst import Analyst
from agentic_review_board.participants.coordinator import Coordinator
from agentic_review_board.participants.critic import Critic
from agentic_review_board.participants.risk_reviewer import RiskReviewer
from agentic_review_board.participants.solution_architect import SolutionArchitect


class ScenarioKind(StrEnum):
    COMPLETE = "COMPLETE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CRITIC_OUTPUT_VALIDATION_FAILURE = "CRITIC_OUTPUT_VALIDATION_FAILURE"
    CRITIC_EXECUTION_FAILURE = "CRITIC_EXECUTION_FAILURE"
    STARTUP_FAILURE = "STARTUP_FAILURE"
    APPLICATION_FAILURE = "APPLICATION_FAILURE"


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise AssertionError("scenario expected a mapping")
    return cast(Mapping[str, object], value)


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or any(
        not isinstance(item, str) for item in value
    ):
        raise AssertionError("scenario expected a string collection")
    return tuple(cast(list[str] | tuple[str, ...], value))


def _required_string(mapping: Mapping[str, object], key: str) -> str:
    value = mapping[key]
    if not isinstance(value, str):
        raise AssertionError(f"scenario expected string field: {key}")
    return value


def _analyst_response(payload: Mapping[str, object]) -> dict[str, object]:
    stated_facts = _strings(payload["stated_facts"])
    context = _strings(payload["context"])
    constraints = _strings(payload["constraints"])
    objective = payload["objective"]
    return {
        "objective": (
            objective
            if isinstance(objective, str)
            else "Determine the next evidence-producing action."
        ),
        "facts": [
            {
                "id": f"FACT-{index:03d}",
                "text": text,
                "source_ref": source,
            }
            for index, (text, source) in enumerate(
                (
                    *((item, "stated_facts") for item in stated_facts),
                    *((item, "context") for item in context),
                ),
                start=1,
            )
        ],
        "constraints": [
            {"id": f"CON-{index:03d}", "text": text}
            for index, text in enumerate(constraints, start=1)
        ],
        "assumptions": [{"id": "ASM-001", "text": "The PoC remains single-session."}],
        "missing_information": [],
        "uncertainties": [
            {"id": "UNC-001", "text": "Operational effort is not measured."}
        ],
    }


def _alternatives_response(
    payload: Mapping[str, object],
    *,
    empty: bool,
) -> dict[str, object]:
    if empty:
        return {
            "alternatives": [],
            "generation_notes": {
                "explanation": "Current evidence is insufficient for useful alternatives.",
                "blocking_missing_information": [],
                "blocking_uncertainties": [],
            },
        }
    problem_analysis = _mapping(payload["problem_analysis"])
    raw_constraints = problem_analysis["constraints"]
    if not isinstance(raw_constraints, list):
        raise AssertionError("scenario expected serialized constraints")
    first_constraint = _mapping(raw_constraints[0]) if raw_constraints else None
    relevant_constraints = (
        [
            {
                "source": "PROBLEM_ANALYSIS",
                "kind": "ID",
                "value": _required_string(first_constraint, "id"),
            }
        ]
        if first_constraint is not None
        else []
    )
    return {
        "alternatives": [
            {
                "id": "ALT-001",
                "validation_status": "PROPOSED",
                "name": "Local deployment",
                "description": "Run the capability in the local environment.",
                "solution_design": {
                    "summary": "Use a local-first runtime with explicitly owned state.",
                    "building_blocks": [
                        "Local client runtime and local persistence boundary."
                    ],
                    "key_interactions": [
                        "User operations flow from the client to local persisted state."
                    ],
                    "operational_model": [
                        "Package, deploy, monitor, and support the runtime locally."
                    ],
                    "delivery_steps": [
                        "Build a pilot and roll out after operational acceptance."
                    ],
                    "validation_checks": [
                        "Exercise the complete workflow without network connectivity."
                    ],
                },
                "advantages": ["Keeps operation local."],
                "disadvantages": ["Requires local lifecycle management."],
                "assumptions": ["Suitable local capacity is available."],
                "implementation_complexity": "MEDIUM",
                "relevant_constraints": relevant_constraints,
            },
            {
                "id": "ALT-002",
                "validation_status": "PROPOSED",
                "name": "Managed deployment",
                "description": "Run the capability in a managed environment.",
                "solution_design": {
                    "summary": "Use a managed runtime behind a controlled integration boundary.",
                    "building_blocks": [
                        "Managed service and local integration adapter."
                    ],
                    "key_interactions": [
                        "Local requests cross the integration boundary to managed state."
                    ],
                    "operational_model": [
                        "Split deployment and support ownership with the provider."
                    ],
                    "delivery_steps": [
                        "Integrate, pilot, and approve the managed dependency."
                    ],
                    "validation_checks": [
                        "Verify availability and behavior during network loss."
                    ],
                },
                "advantages": ["Reduces local operational work."],
                "disadvantages": ["Adds an external dependency."],
                "assumptions": ["A managed environment is available."],
                "implementation_complexity": "MEDIUM",
                "relevant_constraints": [],
            },
        ]
    }


def _risk_response(*, empty: bool) -> dict[str, object]:
    if empty:
        return {
            "risks": [],
            "overall_observations": [
                "No bounded alternative exists to assess with current evidence."
            ],
        }
    return {
        "risks": [
            {
                "id": "RISK-001",
                "category": "operational",
                "description": "Local lifecycle ownership may create operational burden.",
                "affected_scope": {
                    "kind": "ALTERNATIVES",
                    "alternative_ids": ["ALT-001"],
                },
                "severity": "MEDIUM",
                "basis": [
                    {
                        "source": "SOLUTION_ALTERNATIVE",
                        "alternative_id": "ALT-001",
                        "characteristic": "DISADVANTAGE",
                        "value": "Requires local lifecycle management.",
                    }
                ],
                "mitigation": "Assign explicit local lifecycle ownership.",
                "residual_uncertainty": "Actual support effort is not measured.",
            }
        ],
        "overall_observations": ["Risk remains qualitative at this stage."],
    }


def _critic_response(payload: Mapping[str, object]) -> dict[str, object]:
    problem_analysis = _mapping(payload["problem_analysis"])
    raw_assumptions = problem_analysis["assumptions"]
    raw_uncertainties = problem_analysis["uncertainties"]
    if not isinstance(raw_assumptions, list) or not raw_assumptions:
        raise AssertionError("scenario expected a problem-analysis assumption")
    if not isinstance(raw_uncertainties, list) or not raw_uncertainties:
        raise AssertionError("scenario expected a problem-analysis uncertainty")
    assumption = _mapping(raw_assumptions[0])
    uncertainty = _mapping(raw_uncertainties[0])
    assumption_id = _required_string(assumption, "id")
    assumption_text = _required_string(assumption, "text")
    uncertainty_id = _required_string(uncertainty, "id")
    uncertainty_text = _required_string(uncertainty, "text")
    return {
        "criticisms": [
            {
                "id": "CRIT-001",
                "target_type": "ASSUMPTION",
                "target_reference": {
                    "source": "PROBLEM_ANALYSIS",
                    "kind": "PROBLEM_ASSUMPTION",
                    "item_id": assumption_id,
                    "value": assumption_text,
                },
                "basis_references": [
                    {
                        "source": "PROBLEM_ANALYSIS",
                        "kind": "UNCERTAINTY",
                        "item_id": uncertainty_id,
                        "value": uncertainty_text,
                    }
                ],
                "issue": "The operating assumption lacks measured support.",
                "importance": "HIGH",
                "rationale": "The current uncertainty prevents treating it as established.",
                "correction_or_question": "What measurement would validate this assumption?",
            }
        ],
        "validated_points": [],
        "missing_alternatives": [],
        "contradictions": [
            {
                "id": "CONTRA-001",
                "support_status": "UNVERIFIED",
                "side_a": {
                    "reference": {
                        "source": "PROBLEM_ANALYSIS",
                        "kind": "PROBLEM_ASSUMPTION",
                        "item_id": assumption_id,
                        "value": assumption_text,
                    },
                    "statement": assumption_text,
                },
                "side_b": {
                    "reference": {
                        "source": "PROBLEM_ANALYSIS",
                        "kind": "UNCERTAINTY",
                        "item_id": uncertainty_id,
                        "value": uncertainty_text,
                    },
                    "statement": uncertainty_text,
                },
                "rationale": "The operating assumption remains subject to measured uncertainty.",
            }
        ],
        "unresolved_issues": [],
    }


def _invalid_critic_response() -> dict[str, object]:
    return {
        "criticisms": [],
        "validated_points": [
            {
                "id": "VALID-INVALID",
                "target_reference": {
                    "source": "SOLUTION_ALTERNATIVES",
                    "kind": "ALTERNATIVE",
                    "item_id": "ALT-999",
                },
                "rationale": "The nonexistent alternative cannot be validated.",
            }
        ],
        "missing_alternatives": [],
        "contradictions": [],
        "unresolved_issues": [],
    }


def _coordinator_response(payload: Mapping[str, object]) -> dict[str, object]:
    alternatives_document = _mapping(payload["solution_alternatives"])
    raw_alternatives = alternatives_document["alternatives"]
    if not isinstance(raw_alternatives, list):
        raise AssertionError("scenario expected serialized alternatives")
    alternatives = tuple(_mapping(item) for item in raw_alternatives)
    ranking = [
        {
            "alternative_id": _required_string(alternative, "id"),
            "validation_status": _required_string(
                alternative,
                "validation_status",
            ),
            "position": index,
            "justification": "Current evidence supports this relative position.",
            "considerations": ["Validate the remaining assumptions."],
            "conditions_that_could_change_ranking": [
                "New operational evidence could change this position."
            ],
        }
        for index, alternative in enumerate(alternatives, start=1)
    ]
    has_alternatives = bool(ranking)
    risk_document = _mapping(payload["risk_assessment"])
    raw_risks = risk_document["risks"]
    if not isinstance(raw_risks, list):
        raise AssertionError("scenario expected serialized risks")
    principal_risks = (
        [
            {
                "risk_id": _required_string(_mapping(raw_risks[0]), "id"),
                "rationale": "This risk affects the current leading option.",
            }
        ]
        if raw_risks
        else []
    )
    problem_analysis = _mapping(payload["problem_analysis"])
    raw_uncertainties = problem_analysis["uncertainties"]
    if not isinstance(raw_uncertainties, list) or not raw_uncertainties:
        raise AssertionError("scenario expected a problem-analysis uncertainty")
    uncertainty = _mapping(raw_uncertainties[0])
    uncertainty_id = _required_string(uncertainty, "id")
    uncertainty_text = _required_string(uncertainty, "text")
    return {
        "situation_summary": "The five agents produced a bounded decision review.",
        "ranked_alternatives": ranking,
        "recommendation_outcome": (
            "RECOMMENDED" if has_alternatives else "INSUFFICIENT_EVIDENCE"
        ),
        "preferred_alternative_id": (
            ranking[0]["alternative_id"] if has_alternatives else None
        ),
        "conclusion_rationale": (
            "A preference is supported by current evidence."
            if has_alternatives
            else "Current evidence does not support a preferred alternative."
        ),
        "principal_risks": principal_risks,
        "unresolved_questions": [
            {
                "id": "QUESTION-001",
                "reference": {
                    "source": "PROBLEM_ANALYSIS",
                    "kind": "UNCERTAINTY",
                    "item_id": uncertainty_id,
                    "value": uncertainty_text,
                },
                "question": "What operational effort will the selected approach require?",
                "rationale": "The Analyst marked that effort as unmeasured.",
            }
        ],
        "criticism_dispositions": [
            {
                "criticism_id": "CRIT-001",
                "outcome": "REFLECTED",
                "rationale": "The next validation step retains the Critic concern.",
                "reflected_in": ["NEXT_VALIDATION_STEP"],
            }
        ],
        "next_validation_step": "Validate the remaining operational assumptions.",
        "confidence": "MEDIUM" if has_alternatives else "LOW",
    }


class ScriptedScenarioLLM:
    def __init__(self, kind: ScenarioKind) -> None:
        self.kind = kind
        self.calls: list[tuple[str, Mapping[str, object]]] = []

    def generate_structured(
        self,
        *,
        role: str,
        payload: Mapping[str, object],
    ) -> Mapping[str, object]:
        self.calls.append((role, payload))
        insufficient = self.kind is ScenarioKind.INSUFFICIENT_EVIDENCE
        if role == "analyst":
            return _analyst_response(payload)
        if role == "solution_architect":
            return _alternatives_response(payload, empty=insufficient)
        if role == "risk_reviewer":
            return _risk_response(empty=insufficient)
        if role == "critic":
            if self.kind is ScenarioKind.CRITIC_EXECUTION_FAILURE:
                raise RuntimeError("provider-secret-marker")
            if self.kind is ScenarioKind.CRITIC_OUTPUT_VALIDATION_FAILURE:
                return _invalid_critic_response()
            return _critic_response(payload)
        if role == "coordinator":
            return _coordinator_response(payload)
        raise AssertionError(f"unexpected scenario role: {role}")


class ScenarioExecutor:
    def __init__(
        self,
        kind: ScenarioKind,
        *,
        transition_delay_seconds: float = 0.0,
    ) -> None:
        if transition_delay_seconds < 0:
            raise ValueError("transition delay must not be negative")
        self.kind = kind
        self.transition_delay_seconds = transition_delay_seconds
        self._llm = ScriptedScenarioLLM(kind)
        self._observations: list[list[Review]] = []
        self._orchestrator = ReviewOrchestrator(
            Analyst(self._llm),
            SolutionArchitect(self._llm),
            RiskReviewer(self._llm),
            Critic(self._llm),
            Coordinator(self._llm),
        )

    @property
    def calls(self) -> tuple[tuple[str, Mapping[str, object]], ...]:
        return tuple(self._llm.calls)

    @property
    def observations(self) -> tuple[tuple[Review, ...], ...]:
        return tuple(tuple(batch) for batch in self._observations)

    @property
    def execution_count(self) -> int:
        return len(self._observations)

    def __call__(
        self,
        created_review: Review,
        *,
        observer: ReviewObserver,
    ) -> Review:
        observed: list[Review] = []
        self._observations.append(observed)

        def record(review: Review) -> None:
            observed.append(review)
            observer(review)
            if self.transition_delay_seconds:
                sleep(self.transition_delay_seconds)

        if self.kind is ScenarioKind.STARTUP_FAILURE:
            raise RuntimeError("startup-secret-marker")
        if self.kind is ScenarioKind.APPLICATION_FAILURE:
            record(created_review.start())
            raise RuntimeError("application-secret-marker")
        return self._orchestrator.execute(created_review, observer=record)


def scenario_executor(
    kind: ScenarioKind,
    *,
    transition_delay_seconds: float = 0.0,
) -> ScenarioExecutor:
    return ScenarioExecutor(
        kind,
        transition_delay_seconds=transition_delay_seconds,
    )
