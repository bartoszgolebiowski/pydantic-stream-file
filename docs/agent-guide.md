# AI Coding Agent Guide: `pydantic-stream-file`

> This document is optimized for LLMs, autonomous agents, and AI pair programmers to quickly generate correct, idiomatic code using `pydantic-stream-file`.

---

## Cheat Sheet & Rules of Thumb

1. **Memory Guarantee**: Always use `StreamValidator` for files > 10 MB. Never collect full streams into lists with `list(validator)` unless writing unit tests on small fixtures.
2. **Dead Letter Queue (DLQ)**: When user wants pipeline resilience, use `on_error="yield_result"` (or `ErrorPolicy.YIELD_RESULT`).
3. **Pydantic Models**: Standard Pydantic v2 `BaseModel` classes are fully supported.
4. **Discriminated Unions**: Pass `TypeAdapter(UnionModel)` when validating polymorphic streams.
5. **CSV Delimiters**: Pass `delimiter=";"` or `delimiter="\t"` to `adapters.CsvAdapter`.
6. **XML streaming**: Pass `target_tag="item"` and optional `context_tags=["parent"]` to `adapters.XmlAdapter`.

---

## Canonical Snippets

### Snippet 1: Resilient CSV ETL Pipeline
```python
from typing import Optional
from pydantic import BaseModel
from pydantic_stream_file import StreamValidator, adapters, ErrorPolicy

class Record(BaseModel):
    id: int
    name: str
    email: Optional[str] = None

adapter = adapters.CsvAdapter(
    source="input.csv",
    delimiter=",",
    null_values=["", "NULL", "N/A"]
)

validator = StreamValidator(
    adapter=adapter,
    model=Record,
    on_error=ErrorPolicy.YIELD_RESULT,
    batch_size=1000
)

for res in validator:
    if res.is_valid:
        save(res.item)
    else:
        log_error(raw=res.raw_data, error=res.error, line=res.location)
```

### Snippet 2: Constant-Memory XML Streaming with Parent Metadata
```python
from pydantic import BaseModel
from pydantic_stream_file import StreamValidator, adapters

class Order(BaseModel):
    batch_id: str
    order_id: str
    amount: float

adapter = adapters.XmlAdapter(
    source="orders_50GB.xml",
    target_tag="order",
    context_tags=["orders"],  # extracts batch_id from <orders batch_id="...">
    attr_prefix="",
)

for order in StreamValidator(adapter, Order, on_error="skip"):
    save(order)
```

### Snippet 3: Non-Blocking Async Streaming (FastAPI / S3)
```python
from pydantic_stream_file import StreamValidatorAsync

async def process_async(async_adapter, model):
    validator = StreamValidatorAsync(
        adapter=async_adapter,
        model=model,
        on_error="yield_result",
        batch_size=500
    )
    async for res in validator:
        if res.is_valid:
            await push_queue(res.item)
        else:
            await push_dlq(res.raw_data, res.error)
```
