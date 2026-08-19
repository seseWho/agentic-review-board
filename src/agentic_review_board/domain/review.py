from pydantic import BaseModel, ConfigDict, field_validator


class ReviewInput(BaseModel):
    """Immutable user-provided input for one review execution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    description: str
    title: str | None = None
    objective: str | None = None
    constraints: list[str] = []
    context: list[str] = []
    stated_facts: list[str] = []

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("description must not be empty")
        return value
