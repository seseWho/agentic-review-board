"""Read-only observation boundary for validated Review snapshots."""

from collections.abc import Callable

from agentic_review_board.domain.execution import Review

type ReviewObserver = Callable[[Review], None]

__all__ = ("ReviewObserver",)
