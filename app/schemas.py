"""Request and response schemas with input validation."""

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


def utc_iso(value: datetime) -> str:
    """Convert a timezone-aware datetime to a canonical UTC ISO-8601 string."""
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


class TaskCreate(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=120)]
    description: Annotated[str | None, Field(max_length=2000)] = None
    status: TaskStatus = TaskStatus.TODO
    due_at: datetime

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Title must contain at least one non-space character")
        return cleaned

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("due_at")
    @classmethod
    def due_date_must_include_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Due date must include a timezone offset")
        return value.astimezone(timezone.utc)


class TaskUpdate(BaseModel):
    title: Annotated[str | None, Field(min_length=1, max_length=120)] = None
    description: Annotated[str | None, Field(max_length=2000)] = None
    status: TaskStatus | None = None
    due_at: datetime | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Title must contain at least one non-space character")
        return cleaned

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("due_at")
    @classmethod
    def due_date_must_include_timezone(
        cls, value: datetime | None
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Due date must include a timezone offset")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_update_fields(self) -> "TaskUpdate":
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")
        for field_name in ("title", "status", "due_at"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class TaskStatusUpdate(BaseModel):
    status: TaskStatus


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    status: TaskStatus
    due_at: str
    created_at: str
    updated_at: str
