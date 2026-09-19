from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, Optional, TypeVar
from pydantic import ValidationError

T = TypeVar("T")


class ErrorPolicy(str, Enum):
    RAISE = "raise"
    SKIP = "skip"
    YIELD_RESULT = "yield_result"


@dataclass(frozen=True)
class StreamLocation:
    logical_record: int
    physical_line_start: Optional[int] = None
    physical_line_end: Optional[int] = None
    xpath: Optional[str] = None

    def __str__(self) -> str:
        parts: list[str] = []
        if self.physical_line_start is not None:
            if self.physical_line_end is not None and self.physical_line_end != self.physical_line_start:
                parts.append(f"Lines: {self.physical_line_start}-{self.physical_line_end}")
            else:
                parts.append(f"Line: {self.physical_line_start}")
        if self.xpath is not None:
            parts.append(f"XPath: {self.xpath}")
        parts.append(f"Record: {self.logical_record}")
        return " | ".join(parts) if len(parts) > 1 and self.physical_line_start is None else (
            f"{parts[0]} (Record: {self.logical_record})" if len(parts) > 1 else parts[0]
        )


@dataclass(frozen=True)
class RawRecord:
    data: dict[str, Any]
    location: StreamLocation


@dataclass(frozen=True)
class StreamResult(Generic[T]):
    is_valid: bool
    item: Optional[T] = None
    raw_data: dict[str, Any] = field(default_factory=dict)
    error: Optional[ValidationError] = None
    location: str = ""
