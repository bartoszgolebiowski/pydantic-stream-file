# API Reference

## Top-Level Exports

```python
from pydantic_stream_file import (
    StreamValidator,
    StreamValidatorAsync,
    StreamResult,
    StreamLocation,
    RawRecord,
    ErrorPolicy,
    adapters,
)
```

---

## `StreamValidator[T]`

```python
class StreamValidator(Generic[T]):
    def __init__(
        self,
        adapter: StreamAdapter,
        model: Union[Type[T], TypeAdapter[T]],
        on_error: Union[ErrorPolicy, str] = ErrorPolicy.RAISE,
        batch_size: int = 1000,
    ) -> None: ...
```

- **`adapter`**: An instance of `StreamAdapter` (e.g. `CsvAdapter`, `XmlAdapter`).
- **`model`**: Target Pydantic model class or `TypeAdapter` instance.
- **`on_error`**: Error policy (`"raise"`, `"skip"`, or `"yield_result"`).
- **`batch_size`**: Number of items validated together in compiled Rust before yielding. Default `1000`.

---

## `StreamValidatorAsync[T]`

```python
class StreamValidatorAsync(Generic[T]):
    def __init__(
        self,
        adapter: AsyncStreamAdapter,
        model: Union[Type[T], TypeAdapter[T]],
        on_error: Union[ErrorPolicy, str] = ErrorPolicy.RAISE,
        batch_size: int = 1000,
    ) -> None: ...

    async def __aiter__(self) -> AsyncIterator[Union[T, StreamResult[T]]]: ...
```

---

## `StreamResult[T]`

Result container yielded when operating in `on_error="yield_result"` mode.

| Attribute | Type | Description |
| :--- | :--- | :--- |
| `is_valid` | `bool` | `True` if record passed validation; `False` if corrupt. |
| `item` | `Optional[T]` | Validated Pydantic model instance if `is_valid=True`, else `None`. |
| `raw_data` | `dict[str, Any]` | The original, unaltered dictionary from the adapter. |
| `error` | `Optional[ValidationError]` | Pydantic validation error if `is_valid=False`, else `None`. |
| `location` | `str` | Formatted coordinates string (e.g. `Line: 12 (Record: 11)`, `Lines: 5-8 (Record: 4)`, or `Record: 1`). |

---

## `ErrorPolicy` (Enum)

```python
class ErrorPolicy(str, Enum):
    RAISE = "raise"
    SKIP = "skip"
    YIELD_RESULT = "yield_result"
```

---

## `StreamLocation`

```python
@dataclass(frozen=True)
class StreamLocation:
    logical_record: int
    physical_line_start: Optional[int] = None
    physical_line_end: Optional[int] = None
    xpath: Optional[str] = None
```

---

## `RawRecord`

```python
@dataclass(frozen=True)
class RawRecord:
    data: dict[str, Any]
    location: StreamLocation
```

---

## Adapters (`pydantic_stream_file.adapters`)

### `CsvAdapter`

```python
class CsvAdapter(StreamAdapter):
    def __init__(
        self,
        source: Union[str, Path, TextIO],
        delimiter: str = ",",
        quotechar: str = '"',
        escapechar: Optional[str] = None,
        null_values: Sequence[str] = ("", "NULL", "N/A"),
        encoding: str = "utf-8",
    ) -> None: ...
```

### `XmlAdapter`

```python
class XmlAdapter(StreamAdapter):
    def __init__(
        self,
        source: Union[str, Path, BinaryIO, TextIO],
        target_tag: str,
        context_tags: Sequence[str] = (),
        strip_namespaces: bool = True,
        attr_prefix: str = "@",
        text_key: str = "#text",
    ) -> None: ...
```
