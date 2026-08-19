from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReviewInput:
    """Immutable user-provided input for one review execution."""

    description: str
    title: str | None = None
    objective: str | None = None
    constraints: tuple[str, ...] = ()
    context: tuple[str, ...] = ()
    stated_facts: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.description.strip():
            raise ValueError("description must not be empty")
