# Public Python API Contract: `pydantic-stream-file`

**Feature**: `001-stream-file-validation`  
**Date**: 2026-09-19  

## 1. Top-Level Package Exports

Consuming code imports primary primitives from `pydantic_stream_file`:

```python
from pydantic_stream_file import (
    StreamValidator,
    StreamValidatorAsync,
    StreamResult,
    ErrorPolicy,
    adapters,
)
```

---

## 2. API Signature Specifications

### 2.1. `StreamResult[T]`

```python
from dataclasses import dataclass
from typing import Generic, Optional, TypeVar, Any
from pydantic import ValidationError

T = TypeVar("T")

@dataclass(frozen=True)
class StreamResult(Generic[T]):
    is_valid: bool
    item: Optional[T]
    raw_data: dict[str, Any]
    error: Optional[ValidationError]
    location: str
```

---

### 2.2. `ErrorPolicy`

```python
from enum import Enum

class ErrorPolicy(str, Enum):
    RAISE = "raise"
    SKIP = "skip"
    YIELD_RESULT = "yield_result"
```

---

### 2.3. Source Adapters (`pydantic_stream_file.adapters`)

```python
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterator, Sequence
from pathlib import Path
from typing import Any, BinaryIO, TextIO, Union

class StreamAdapter(ABC):
    @abstractmethod
    def __iter__(self) -> Iterator[RawRecord]:
        """Yield RawRecord instances containing raw dict and location metadata."""
        ...

class AsyncStreamAdapter(ABC):
    @abstractmethod
    def __aiter__(self) -> AsyncIterator[RawRecord]:
        """Asynchronously yield RawRecord instances."""
        ...

class CsvAdapter(StreamAdapter):
    def __init__(
        self,
        source: Union[str, Path, TextIO],
        delimiter: str = ",",
        quotechar: str = '"',
        null_values: Sequence[str] = ("", "NULL", "N/A"),
        encoding: str = "utf-8",
    ) -> None:
        ...

    def __iter__(self) -> Iterator[RawRecord]:
        ...

class XmlAdapter(StreamAdapter):
    def __init__(
        self,
        source: Union[str, Path, BinaryIO, TextIO],
        target_tag: str,
        context_tags: Sequence[str] = (),
        strip_namespaces: bool = True,
        attr_prefix: str = "@",
        text_key: str = "#text",
    ) -> None:
        ...

    def __iter__(self) -> Iterator[RawRecord]:
        ...
```

---

### 2.4. `StreamValidator[T]` (Synchronous)

```python
from typing import Generic, Iterator, Literal, Optional, Type, TypeVar, Union, overload
from pydantic import BaseModel, TypeAdapter

T = TypeVar("T")

class StreamValidator(Generic[T]):
    def __init__(
        self,
        adapter: StreamAdapter,
        model: Union[Type[T], TypeAdapter[T]],
        on_error: Union[ErrorPolicy, str] = ErrorPolicy.RAISE,
        batch_size: int = 1000,
    ) -> None:
        ...

    @overload
    def __iter__(self: "StreamValidator[T]") -> Iterator[T]:
        """When on_error is RAISE or SKIP, yields validated models."""
        ...

    @overload
    def __iter__(self: "StreamValidator[T]") -> Iterator[StreamResult[T]]:
        """When on_error is YIELD_RESULT, yields StreamResult[T]."""
        ...

    def __iter__(self) -> Union[Iterator[T], Iterator[StreamResult[T]]]:
        ...
```

---

### 2.5. `StreamValidatorAsync[T]` (Asynchronous)

```python
from typing import AsyncIterator, Generic, Optional, Type, TypeVar, Union, overload
from pydantic import BaseModel, TypeAdapter

T = TypeVar("T")

class StreamValidatorAsync(Generic[T]):
    def __init__(
        self,
        adapter: AsyncStreamAdapter,
        model: Union[Type[T], TypeAdapter[T]],
        on_error: Union[ErrorPolicy, str] = ErrorPolicy.RAISE,
        batch_size: int = 1000,
    ) -> None:
        ...

    def __aiter__(self) -> Union[AsyncIterator[T], AsyncIterator[StreamResult[T]]]:
        ...
```
