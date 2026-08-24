from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import httpx
from pydantic import BaseModel

from agentic_review_board.domain.analysis import ProblemAnalysis
from agentic_review_board.domain.critics import CriticalReview
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
from agentic_review_board.infrastructure.llm.config import (
    RawLLMRuntimeConfig,
    ResolvedLLMProfile,
    resolve_llm_runtime_config,
)
from agentic_review_board.infrastructure.llm.openai_compatible import (
    OpenAICompatibleLLMAdapter,
)
from agentic_review_board.participants.analyst import Analyst
from agentic_review_board.participants.coordinator import Coordinator
from agentic_review_board.participants.critic import Critic
from agentic_review_board.participants.risk_reviewer import RiskReviewer
from agentic_review_board.participants.solution_architect import SolutionArchitect


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
    output: BaseModel,
) -> Iterator[tuple[OpenAICompatibleLLMAdapter, list[httpx.Request]]]:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": output.model_dump_json()}}
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
    expected = FinalReview(
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
