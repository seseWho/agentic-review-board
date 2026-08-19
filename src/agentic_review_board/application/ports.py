from collections.abc import Mapping
from typing import Protocol


class LLMPort(Protocol):
    """Provider-neutral structured-generation capability."""

    def generate_structured(
        self,
        *,
        role: str,
        payload: Mapping[str, object],
    ) -> Mapping[str, object]: ...
