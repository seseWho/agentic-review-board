from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from contextlib import contextmanager

import httpx
import pytest
from pydantic import BaseModel

from agentic_review_board.domain.analysis import ProblemAnalysis
from agentic_review_board.domain.critics import CriticalReview
from agentic_review_board.domain.execution import (
    Review,
    ReviewErrorKind,
    ReviewStatus,
    StageIdentity,
    StageStatus,
)
from agentic_review_board.domain.final_reviews import (
    FinalReview,
    RecommendationOutcome,
)
from agentic_review_board.domain.review import ReviewInput
from agentic_review_board.domain.risks import RiskAssessment
from agentic_review_board.domain.shared import QualitativeLevel
from agentic_review_board.domain.solutions import (
    GenerationNotes,
    SolutionAlternatives,
)
from agentic_review_board.infrastructure.llm.composition import ConfiguredReviewRuntime
from agentic_review_board.infrastructure.llm.config import (
    RawLLMRuntimeConfig,
    ResolvedLLMProfile,
    resolve_llm_runtime_config,
)
from agentic_review_board.infrastructure.llm.openai_compatible import (
    OpenAICompatibleLLMAdapter,
)
from agentic_review_board.participants.analyst import Analyst, AnalystOutputError
from agentic_review_board.participants.coordinator import (
    Coordinator,
    CoordinatorOutputError,
)
from agentic_review_board.participants.critic import Critic, CriticOutputError
from agentic_review_board.participants.risk_reviewer import (
    RiskReviewer,
    RiskReviewerOutputError,
)
from agentic_review_board.participants.solution_architect import (
    SolutionArchitect,
    SolutionArchitectOutputError,
)


def resolved_profile() -> ResolvedLLMProfile:
    config = RawLLMRuntimeConfig.model_validate(
        {
            "profiles": {
                "integration": {
                    "base_url": "https://integration.example.test/v1",
                    "model": "integration-model",
                    "timeout_seconds": 5.0,
                    "structured_output_mode": "PROMPT_ONLY",
                }
            },
            "assignments": {
                "analyst": "integration",
                "solution_architect": "integration",
                "risk_reviewer": "integration",
                "critic": "integration",
                "coordinator": "integration",
            },
        }
    )
    return resolve_llm_runtime_config(config, {}).analyst


@contextmanager
def adapter_returning(
    output: BaseModel | Mapping[str, object],
) -> Iterator[tuple[OpenAICompatibleLLMAdapter, list[httpx.Request]]]:
    requests: list[httpx.Request] = []
    content = (
        output.model_dump_json()
        if isinstance(output, BaseModel)
        else json.dumps(dict(output))
    )

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": content}}
                ]
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        yield OpenAICompatibleLLMAdapter(
            profile=resolved_profile(),
            client=client,
        ), requests


def trusted_inputs() -> tuple[
    ReviewInput,
    ProblemAnalysis,
    SolutionAlternatives,
    RiskAssessment,
    CriticalReview,
]:
    review_input = ReviewInput(description="Evaluate the integration contract.")
    analysis = ProblemAnalysis(
        objective="Evaluate the integration contract.",
        facts=(),
        constraints=(),
        assumptions=(),
        missing_information=(),
        uncertainties=(),
    )
    alternatives = SolutionAlternatives(
        alternatives=(),
        generation_notes=GenerationNotes(
            explanation="No alternatives are justified by the available input.",
            blocking_missing_information=(),
            blocking_uncertainties=(),
        ),
    )
    assessment = RiskAssessment(risks=(), overall_observations=())
    critique = CriticalReview()
    return review_input, analysis, alternatives, assessment, critique


def final_review() -> FinalReview:
    return FinalReview(
        situation_summary="The current input does not justify alternatives.",
        ranked_alternatives=(),
        recommendation_outcome=RecommendationOutcome.INSUFFICIENT_EVIDENCE,
        preferred_alternative_id=None,
        conclusion_rationale="No supported recommendation can be made.",
        principal_risks=(),
        unresolved_questions=(),
        criticism_dispositions=(),
        next_validation_step="Provide additional decision constraints.",
        confidence=QualitativeLevel.LOW,
    )


def mixed_runtime_config() -> RawLLMRuntimeConfig:
    return RawLLMRuntimeConfig.model_validate(
        {
            "profiles": {
                "local": {
                    "base_url": "http://localhost:11434/v1",
                    "model": "local-model",
                    "timeout_seconds": 5.0,
                    "structured_output_mode": "PROMPT_ONLY",
                },
                "remote": {
                    "base_url": "https://api.example.test/v1",
                    "model": "remote-model",
                    "api_key_env": "REMOTE_KEY",
                    "timeout_seconds": 5.0,
                    "structured_output_mode": "JSON_OBJECT",
                },
            },
            "assignments": {
                "analyst": "local",
                "solution_architect": "remote",
                "risk_reviewer": "local",
                "critic": "remote",
                "coordinator": "remote",
            },
        }
    )


def test_production_adapter_integrates_with_analyst() -> None:
    review_input, expected, _, _, _ = trusted_inputs()

    with adapter_returning(expected) as (adapter, requests):
        result = Analyst(adapter).analyze(review_input)

    assert result == expected
    assert len(requests) == 1


def test_production_adapter_integrates_with_solution_architect() -> None:
    review_input, analysis, expected, _, _ = trusted_inputs()

    with adapter_returning(expected) as (adapter, requests):
        result = SolutionArchitect(adapter).propose(review_input, analysis)

    assert result == expected
    assert len(requests) == 1


def test_production_adapter_integrates_with_risk_reviewer() -> None:
    review_input, analysis, alternatives, expected, _ = trusted_inputs()

    with adapter_returning(expected) as (adapter, requests):
        result = RiskReviewer(adapter).assess(
            review_input,
            analysis,
            alternatives,
        )

    assert result == expected
    assert len(requests) == 1


def test_production_adapter_integrates_with_critic() -> None:
    review_input, analysis, alternatives, assessment, expected = trusted_inputs()

    with adapter_returning(expected) as (adapter, requests):
        result = Critic(adapter).review(
            review_input,
            analysis,
            alternatives,
            assessment,
        )

    assert result == expected
    assert len(requests) == 1


def test_production_adapter_integrates_with_coordinator() -> None:
    review_input, analysis, alternatives, assessment, critique = trusted_inputs()
    expected = final_review()

    with adapter_returning(expected) as (adapter, requests):
        result = Coordinator(adapter).coordinate(
            review_input,
            analysis,
            alternatives,
            assessment,
            critique,
        )

    assert result == expected
    assert len(requests) == 1


def test_analyst_owns_semantically_invalid_adapter_object_rejection() -> None:
    review_input, _, _, _, _ = trusted_inputs()

    with adapter_returning({"objective": 123}) as (adapter, requests):
        with pytest.raises(AnalystOutputError):
            Analyst(adapter).analyze(review_input)

    assert len(requests) == 1


def test_solution_architect_owns_semantically_invalid_adapter_object_rejection() -> None:
    review_input, analysis, _, _, _ = trusted_inputs()
    one_alternative = {
        "alternatives": [
            {
                "id": "ALT-001",
                "name": "Only option",
                "description": "One option violates the approved result cardinality.",
                "advantages": [],
                "disadvantages": [],
                "assumptions": [],
                "implementation_complexity": "LOW",
                "relevant_constraints": [],
            }
        ],
        "generation_notes": None,
    }

    with adapter_returning(one_alternative) as (adapter, requests):
        with pytest.raises(SolutionArchitectOutputError):
            SolutionArchitect(adapter).propose(review_input, analysis)

    assert len(requests) == 1


def test_risk_reviewer_owns_semantically_invalid_adapter_object_rejection() -> None:
    review_input, analysis, alternatives, _, _ = trusted_inputs()
    invalid_assessment = {
        "risks": "not-a-risk-collection",
        "overall_observations": [],
    }

    with adapter_returning(invalid_assessment) as (adapter, requests):
        with pytest.raises(RiskReviewerOutputError):
            RiskReviewer(adapter).assess(review_input, analysis, alternatives)

    assert len(requests) == 1


def test_critic_owns_semantically_invalid_adapter_object_rejection() -> None:
    review_input, analysis, alternatives, assessment, _ = trusted_inputs()
    invalid_critique = {"criticisms": "not-a-criticism-collection"}

    with adapter_returning(invalid_critique) as (adapter, requests):
        with pytest.raises(CriticOutputError):
            Critic(adapter).review(
                review_input,
                analysis,
                alternatives,
                assessment,
            )

    assert len(requests) == 1


def test_critic_rejects_provider_output_that_ignores_dynamic_reference_guidance() -> None:
    review_input, analysis, alternatives, assessment, _ = trusted_inputs()
    invalid_critique = {
        "criticisms": [],
        "validated_points": [
            {
                "id": "VAL-001",
                "target_reference": {
                    "source": "PROBLEM_ANALYSIS",
                    "kind": "STATED_FACT",
                    "value": "Fabricated cross-family reference.",
                },
                "rationale": "This must remain untrusted.",
            }
        ],
        "missing_alternatives": [],
        "contradictions": [],
        "unresolved_issues": [],
    }

    with adapter_returning(invalid_critique) as (adapter, requests):
        with pytest.raises(CriticOutputError):
            Critic(adapter).review(
                review_input,
                analysis,
                alternatives,
                assessment,
            )

    assert len(requests) == 1


def test_coordinator_owns_semantically_invalid_adapter_object_rejection() -> None:
    review_input, analysis, alternatives, assessment, critique = trusted_inputs()
    invalid_final_review = {"situation_summary": 123}

    with adapter_returning(invalid_final_review) as (adapter, requests):
        with pytest.raises(CoordinatorOutputError):
            Coordinator(adapter).coordinate(
                review_input,
                analysis,
                alternatives,
                assessment,
                critique,
            )

    assert len(requests) == 1


def test_mixed_profile_runtime_executes_complete_review_in_fixed_order() -> None:
    review_input, analysis, alternatives, assessment, critique = trusted_inputs()
    outputs: list[BaseModel] = [
        analysis,
        alternatives,
        assessment,
        critique,
        final_review(),
    ]
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        output = outputs[len(requests)]
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": output.model_dump_json()}}
                ]
            },
        )

    with ConfiguredReviewRuntime.from_config(
        mixed_runtime_config(),
        {"REMOTE_KEY": "remote-secret-marker"},
        transport=httpx.MockTransport(handler),
    ) as runtime:
        result = runtime.execute(Review.create(review_input))

    assert result.status is ReviewStatus.COMPLETED
    assert all(stage.status is StageStatus.COMPLETED for stage in result.stages)
    assert [str(request.url) for request in requests] == [
        "http://localhost:11434/v1/chat/completions",
        "https://api.example.test/v1/chat/completions",
        "http://localhost:11434/v1/chat/completions",
        "https://api.example.test/v1/chat/completions",
        "https://api.example.test/v1/chat/completions",
    ]
    assert [json.loads(request.content)["model"] for request in requests] == [
        "local-model",
        "remote-model",
        "local-model",
        "remote-model",
        "remote-model",
    ]
    assert [request.headers.get("authorization") for request in requests] == [
        None,
        "Bearer remote-secret-marker",
        None,
        "Bearer remote-secret-marker",
        "Bearer remote-secret-marker",
    ]


def test_selected_remote_provider_failure_stops_without_local_fallback() -> None:
    review_input, analysis, _, _, _ = trusted_inputs()
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"content": analysis.model_dump_json()}}
                    ]
                },
            )
        return httpx.Response(503, content=b"provider detail must not escape")

    with ConfiguredReviewRuntime.from_config(
        mixed_runtime_config(),
        {"REMOTE_KEY": "remote-secret-marker"},
        transport=httpx.MockTransport(handler),
    ) as runtime:
        result = runtime.execute(Review.create(review_input))

    failed_stage = result.stage(StageIdentity.SOLUTION_ARCHITECT)
    assert result.status is ReviewStatus.INCOMPLETE
    assert result.stage(StageIdentity.ANALYST).status is StageStatus.COMPLETED
    assert failed_stage.status is StageStatus.FAILED
    assert failed_stage.error is not None
    assert failed_stage.error.kind is ReviewErrorKind.EXECUTION
    assert failed_stage.error.message == "Solution Architect execution failed"
    assert result.stage(StageIdentity.RISK_REVIEWER).status is StageStatus.PENDING
    assert result.stage(StageIdentity.CRITIC).status is StageStatus.PENDING
    assert result.stage(StageIdentity.COORDINATOR).status is StageStatus.PENDING
    assert [str(request.url) for request in requests] == [
        "http://localhost:11434/v1/chat/completions",
        "https://api.example.test/v1/chat/completions",
    ]
