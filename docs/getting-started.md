# Getting Started

## Installation

Install `pydantic-stream-file` from PyPI:

```bash
pip install pydantic-stream-file
```

### Test Suite Installation

For running tests and contributing:

```bash
pip install pydantic-stream-file[test]
```

---

## Core Concepts

Understanding `pydantic-stream-file` involves three simple components:

### 1. `StreamAdapter`
The source reader. It takes a file path, open stream, or network socket, splits it into raw records (`dict`), and attaches a `StreamLocation` coordinate (line numbers or XPath).
- [`CsvAdapter`](adapters/csv.md): Delimited flat files (CSV, TSV, PSV).
- [`XmlAdapter`](adapters/xml.md): Constant-memory XML streaming with subtree pruning.

### 2. `StreamValidator`
The validation engine. It takes a `StreamAdapter` and a Pydantic model (or `TypeAdapter`), accumulates records into vectorized batches, validates them via `pydantic-core`, and yields validated models or `StreamResult` envelopes according to the configured `ErrorPolicy`.

### 3. `ErrorPolicy`
Controls what happens when dirty or malformed records appear:
- `ErrorPolicy.RAISE` (`"raise"`): Halts the loop immediately and raises the `ValidationError`.
- `ErrorPolicy.SKIP` (`"skip"`): Silently omits invalid records and yields only valid model instances.
- `ErrorPolicy.YIELD_RESULT` (`"yield_result"`): Returns a `StreamResult` for every record, enabling Dead Letter Queue (DLQ) routing.

---

## First Step: Delimited CSV Pipeline

Create a file named `pipeline.py`:

```python
from typing import Optional
from pydantic import BaseModel
from pydantic_stream_file import StreamValidator, adapters, ErrorPolicy

# Define your data contract
class Customer(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    balance: float

# Initialize the adapter
csv_adapter = adapters.CsvAdapter(
    source="customers.csv",
    delimiter=",",
    null_values=["", "NULL", "None"]
)

# Connect validator in DLQ mode
validator = StreamValidator(
    adapter=csv_adapter,
    model=Customer,
    on_error=ErrorPolicy.YIELD_RESULT,
    batch_size=1000
)

# Run the stream
clean_records = 0
dlq_records = 0

for result in validator:
    if result.is_valid:
        clean_records += 1
        # Access the typed Pydantic instance:
        print(f"Validated customer: {result.item.name} (${result.item.balance})")
    else:
        dlq_records += 1
        # Inspect failure coordinates and raw payload:
        print(f"Rejected row at {result.location}: {result.raw_data}")
        print(f"Reason: {result.error}")

print(f"Finished: {clean_records} clean, {dlq_records} routed to DLQ.")
```
