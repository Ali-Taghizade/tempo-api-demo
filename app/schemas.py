"""Request body schema and validation rules for the task resource."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

Day = Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
Category = Literal["study", "work", "personal", "health", "other"]
Priority = Literal["low", "medium", "high"]

DAY_ORDER = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
TIME_PATTERN = r"^([01]\d|2[0-3]):[0-5]\d$"


class TaskIn(BaseModel):
    """Body for POST /tasks and PUT /tasks/{id}. PUT is a full replacement, so the rules are identical."""

    # extra="forbid" -> unknown fields are rejected; strict=True -> no silent type coercion ("1" is not 1).
    model_config = ConfigDict(extra="forbid", strict=True)

    title: str = Field(min_length=3, max_length=100, examples=["Morning run"])
    description: str | None = Field(default=None, max_length=500)
    daysOfWeek: list[Day] = Field(min_length=1, max_length=7, examples=[["tue", "thu"]])
    startTime: str = Field(pattern=TIME_PATTERN, examples=["07:00"])
    endTime: str = Field(pattern=TIME_PATTERN, examples=["07:45"])
    category: Category
    priority: Priority = "medium"
    isFixed: bool = False
    ownerId: str | None = Field(default=None, description="Admin only. Regular users may omit it or send their own id.")

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Title must contain at least 3 non-space characters.")
        return value

    @field_validator("description")
    @classmethod
    def description_trim(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("daysOfWeek")
    @classmethod
    def days_unique_and_sorted(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("Days must not repeat.")
        return sorted(value, key=DAY_ORDER.index)

    @field_validator("endTime")
    @classmethod
    def end_after_start(cls, value: str, info: ValidationInfo) -> str:
        start = info.data.get("startTime")  # only present if startTime itself was valid
        if start is not None and value <= start:
            raise ValueError("endTime must be later than startTime.")
        return value
