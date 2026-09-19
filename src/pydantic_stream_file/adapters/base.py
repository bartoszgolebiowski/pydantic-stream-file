from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterator
from pydantic_stream_file.types import RawRecord


class StreamAdapter(ABC):
    """Abstract base class for synchronous stream adapters."""

    @abstractmethod
    def __iter__(self) -> Iterator[RawRecord]:
        """Iterate over raw records extracted from the stream."""
        ...


class AsyncStreamAdapter(ABC):
    """Abstract base class for asynchronous stream adapters."""

    @abstractmethod
    def __aiter__(self) -> AsyncIterator[RawRecord]:
        """Asynchronously iterate over raw records extracted from the stream."""
        ...
