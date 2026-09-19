# pydantic-stream-file

**High-performance $O(1)$ RAM streaming file validation glue layer for Pydantic.**

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Pydantic](https://img.shields.io/badge/Pydantic-v2.5+-red.svg)](https://docs.pydantic.dev/)
[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue.svg)](https://bartoszgolebiowski.github.io/pydantic-stream-file/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📖 Documentation

- **Full Documentation Site**: [https://bartoszgolebiowski.github.io/pydantic-stream-file/](https://bartoszgolebiowski.github.io/pydantic-stream-file/)
- **For AI Coding Agents**: [`docs/agent-guide.md`](docs/agent-guide.md) or [`docs/llms.txt`](docs/llms.txt)

---

## ⚡ Highlights

- **Strict $O(1)$ Memory Overhead**: Memory consumption remains flat regardless of whether the file is 10 MB or 50 GB. Built for serverless (AWS Lambda) and container runtimes.
- **Fail-Safe & Dead Letter Queue (DLQ)**: A single corrupt row will not abort your pipeline. In `YIELD_RESULT` mode, errors are captured with raw payloads and exact file coordinates.
- **Delimiter & Multiline Cell Resilience**: `CsvAdapter` handles any separator (`,`, `;`, `\t`, `|`), preserves cells with internal `\n` enclosed in quotes, and coerces custom null sentinels (`""`, `"NULL"`, `"N/A"`).
- **Constant-Memory XML Streaming**: `XmlAdapter` streams massive XML documents via `iterparse`, ruthlessly clearing subtrees and severing parent node references to prevent DOM accumulation.
- **Parent Context Extraction**: Seamlessly extracts attributes from ancestor tags (e.g., `batch_id` from `<orders batch_id="1">`) and injects them into child models.
- **Vectorized Rust Batch Validation**: Leverages compiled Rust batching (`TypeAdapter(list[Model])`) in `pydantic-core`, boosting throughput by up to 40%+ while isolating single-row errors.
- **Sync & Async Dualism**: Drop-in identical APIs for blocking streams (`StreamValidator`) and async runtimes like FastAPI or S3 chunk downloads (`StreamValidatorAsync`).
- **Zero Heavy Runtime Dependencies**: Core depends strictly on `pydantic`.

---

## 📦 Installation

```bash
pip install pydantic-stream-file
```

---

## 🚀 Quick Examples

### 1. Delimited Flat File (CSV) with Dead Letter Queue Routing

```python
from typing import Optional
from pydantic import BaseModel
from pydantic_stream_file import StreamValidator, adapters, ErrorPolicy

class Transaction(BaseModel):
    id: int
    amount: float
    description: str
    notes: Optional[str] = None

# Initialize adapter with custom delimiter and null sentinels
csv_adapter = adapters.CsvAdapter(
    source="transactions.csv",  # or sys.stdin, open file handle, io.StringIO
    delimiter=",",
    null_values=["", "NULL", "N/A"]
)

# Connect validation engine
validator = StreamValidator(
    adapter=csv_adapter,
    model=Transaction,
    on_error=ErrorPolicy.YIELD_RESULT,
    batch_size=1000,
)

for result in validator:
    if result.is_valid:
        # Validated Pydantic model:
        save_clean_record(result.item)
    else:
        # Route to Dead Letter Queue:
        log_to_dlq(
            raw_payload=result.raw_data,
            error=result.error,
            location=result.location  # e.g., "Lines: 42-45 (Record: 40)"
        )
```

---

### 2. Constant-Memory XML Streaming with Parent Metadata

```python
from pydantic import BaseModel
from pydantic_stream_file import StreamValidator, adapters

class Order(BaseModel):
    batch_id: str
    order_id: str
    amount: float

xml_adapter = adapters.XmlAdapter(
    source="massive_orders_50GB.xml",
    target_tag="order",
    context_tags=["orders"],  # extracts batch_id from <orders batch_id="...">
    attr_prefix="",
)

for order in StreamValidator(xml_adapter, Order, on_error="skip"):
    process(order)
```

---

### 3. Non-Blocking Async Streaming (`FastAPI` / `aiobotocore`)

```python
from pydantic_stream_file import StreamValidatorAsync

async def process_stream(async_adapter, model):
    validator = StreamValidatorAsync(
        adapter=async_adapter,
        model=model,
        on_error="yield_result",
        batch_size=500
    )
    async for result in validator:
        if result.is_valid:
            await forward_to_kafka(result.item)
        else:
            await send_to_dlq(result.raw_data, result.error)
```

---

## 📑 Error Policies

| Policy | Behavior | Return Type |
| :--- | :--- | :--- |
| `ErrorPolicy.RAISE` (`"raise"`) | Halts stream and raises `ValidationError` on first invalid record. | Yields `T` |
| `ErrorPolicy.SKIP` (`"skip"`) | Silently drops invalid records. | Yields `T` |
| `ErrorPolicy.YIELD_RESULT` (`"yield_result"`) | Never halts. Yields a [`StreamResult[T]`](docs/api-reference.md) for every record. | Yields `StreamResult[T]` |

---

## 🛠️ Running the Test Suite

```bash
python -m pytest tests
```

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
