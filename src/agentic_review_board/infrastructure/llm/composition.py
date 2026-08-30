from __future__ import annotations

from collections.abc import Callable, Mapping
from types import MappingProxyType
from typing import Self

import httpx

from agentic_review_board.application.orchestrator import ReviewOrchestrator
from agentic_review_board.domain.execution import Review
from agentic_review_board.infrastructure.llm.config import (
    RawLLMRuntimeConfig,
    ResolvedLLMProfile,
    resolve_llm_runtime_config,
)
from agentic_review_board.infrastructure.llm.errors import LLMRuntimeClosedError
from agentic_review_board.infrastructure.llm.http_client import (
    _create_http_client as _build_http_client,
)
from agentic_review_board.infrastructure.llm.openai_compatible import (
    OpenAICompatibleLLMAdapter,
)
from agentic_review_board.participants.analyst import Analyst
from agentic_review_board.participants.coordinator import Coordinator
from agentic_review_board.participants.critic import Critic
from agentic_review_board.participants.risk_reviewer import RiskReviewer
from agentic_review_board.participants.solution_architect import SolutionArchitect

__all__ = ("ConfiguredReviewRuntime",)


def _create_http_client(
    transport: httpx.BaseTransport | None = None,
) -> httpx.Client:
    return _build_http_client(transport)


class ConfiguredReviewRuntime:
    __slots__ = (
        "_client",
        "_closed",
        "_orchestrator",
        "_participant_profile_names",
        "_selected_profile_names",
    )

    def __init__(
        self,
        *,
        client: httpx.Client,
        orchestrator: ReviewOrchestrator,
        selected_profile_names: tuple[str, ...],
        participant_profile_names: Mapping[str, str],
    ) -> None:
        self._client = client
        self._orchestrator = orchestrator
        self._selected_profile_names = selected_profile_names
        self._participant_profile_names = MappingProxyType(dict(participant_profile_names))
        self._closed = False

    @classmethod
    def from_config(
        cls,
        config: RawLLMRuntimeConfig,
        environ: Mapping[str, str],
        transport: httpx.BaseTransport | None = None,
        output_observer: Callable[[str, Mapping[str, object]], None] | None = None,
    ) -> Self:
        assignment = resolve_llm_runtime_config(config, environ)
        profiles_by_role = {
            "analyst": assignment.analyst,
            "solution_architect": assignment.solution_architect,
            "risk_reviewer": assignment.risk_reviewer,
            "critic": assignment.critic,
            "coordinator": assignment.coordinator,
        }
        resolved_by_name: dict[str, ResolvedLLMProfile] = {}
        for profile in profiles_by_role.values():
            resolved_by_name.setdefault(profile.name, profile)

        participant_profile_names = {
            role: profile.name for role, profile in profiles_by_role.items()
        }
        client = _create_http_client(transport)
        try:
            if output_observer is None:
                adapters = {
                    name: OpenAICompatibleLLMAdapter(profile=profile, client=client)
                    for name, profile in resolved_by_name.items()
                }
            else:
                adapters = {
                    name: OpenAICompatibleLLMAdapter(
                        profile=profile,
                        client=client,
                        output_observer=output_observer,
                    )
                    for name, profile in resolved_by_name.items()
                }
            analyst = Analyst(adapters[assignment.analyst.name])
            solution_architect = SolutionArchitect(adapters[assignment.solution_architect.name])
            risk_reviewer = RiskReviewer(adapters[assignment.risk_reviewer.name])
            critic = Critic(adapters[assignment.critic.name])
            coordinator = Coordinator(adapters[assignment.coordinator.name])
            orchestrator = ReviewOrchestrator(
                analyst,
                solution_architect,
                risk_reviewer,
                critic,
                coordinator,
            )
            return cls(
                client=client,
                orchestrator=orchestrator,
                selected_profile_names=tuple(sorted(resolved_by_name)),
                participant_profile_names=participant_profile_names,
            )
        except BaseException:
            try:
                client.close()
            except BaseException:
                pass
            raise

    @property
    def selected_profile_names(self) -> tuple[str, ...]:
        return self._selected_profile_names

    @property
    def participant_profile_names(self) -> Mapping[str, str]:
        return self._participant_profile_names

    @property
    def lifecycle_state(self) -> str:
        return "CLOSED" if self._closed else "OPEN"

    def execute(self, review: Review) -> Review:
        if self._closed:
            raise LLMRuntimeClosedError()
        return self._orchestrator.execute(review)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._client.close()

    def __enter__(self) -> Self:
        if self._closed:
            raise LLMRuntimeClosedError()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object,
    ) -> None:
        self.close()

    def __repr__(self) -> str:
        return (
            "ConfiguredReviewRuntime("
            f"selected_profile_names={self._selected_profile_names!r}, "
            f"participant_profile_names={dict(self._participant_profile_names)!r}, "
            f"lifecycle_state={self.lifecycle_state!r})"
        )
