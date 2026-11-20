"""Request body schema and validation rules for the task resource."""

from typing import Literal

Day = Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
Category = Literal["study", "work", "personal", "health", "other"]
Priority = Literal["low", "medium", "high"]

DAY_ORDER = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
