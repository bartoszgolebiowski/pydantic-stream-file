# Quickstart & Validation Guide: `pydantic-stream-file`

**Feature**: `001-stream-file-validation`  
**Date**: 2026-09-19  

This guide provides runnable scenarios verifying end-to-end functionality across core features: CSV streaming with Dead Letter Queue routing, XML constant-memory streaming with parent context injection, batch validation performance, and async streaming.

---

## 1. Prerequisites & Environment Setup

- Python 3.10+
- `pip install pydantic>=2.5.0 pytest>=8.0.0 pytest-asyncio`

---

## 2. Validation Scenarios

### Scenario 1: Delimited CSV Stream with Dead Letter Queue (DLQ)

**Objective**: Verify multiline field parsing, null sentinel coercion, and non-halting DLQ error routing.

**Setup**: A CSV file containing 3 rows:
1. Valid transaction with embedded multiline description (`"Groceries\nand supplies"`).
2. Malformed transaction with invalid price (`"invalid_amount"`).
3. Valid transaction with sentinel empty string for an optional field.

```python
from pydantic import BaseModel
from typing import Optional
from pydantic_stream_file import StreamValidator, adapters, ErrorPolicy

class Transaction(BaseModel):
    id: int
    amount: float
    description: str
    note: Optional[str] = None

csv_stream = adapters.CsvAdapter(
    source="tests/fixtures/transactions.csv",
    delimiter=",",
    null_values=["", "NULL"]
)

validator = StreamValidator(
    adapter=csv_stream,
    model=Transaction,
    on_error=ErrorPolicy.YIELD_RESULT,
    batch_size=10
)

results = list(validator)
assert len(results) == 3

# Row 1: Valid multiline
assert results[0].is_valid is True
assert "\n" in results[0].item.description

# Row 2: Invalid row routed to DLQ
assert results[1].is_valid is False
assert results[1].item is None
assert results[1].error is not None
assert results[1].raw_data["amount"] == "invalid_amount"
assert "Line:" in results[1].location

# Row 3: Coerced null
assert results[2].is_valid is True
assert results[2].item.note is None
```

**Expected Outcome**: 2 valid records processed, 1 invalid record captured in DLQ without raising an unhandled exception.

---

### Scenario 2: Constant-Memory XML Streaming with Parent Context

**Objective**: Verify streaming extraction of repeated elements, XML attribute prefixes (`@`), text mapping, and parent attribute inheritance (`batch_id`).

**Setup**: An XML feed containing a parent `<orders batch_id="BATCH-001">` with multiple child `<order>` elements.

```python
from pydantic import BaseModel
from pydantic_stream_file import StreamValidator, adapters

class Order(BaseModel):
    batch_id: str
    order_id: str
    amount: float

xml_stream = adapters.XmlAdapter(
    source="tests/fixtures/orders.xml",
    target_tag="order",
    context_tags=["orders"],
    attr_prefix="@",
)

validator = StreamValidator(
    adapter=xml_stream,
    model=Order,
    on_error="raise"
)

orders = list(validator)
assert len(orders) > 0
for order in orders:
    assert order.batch_id == "BATCH-001"
```

**Expected Outcome**: Parent context (`batch_id`) is injected into all child orders, and memory remains constant regardless of file size.

---

### Scenario 3: Vectorized Batching Performance Verification

**Objective**: Verify that `batch_size=5000` demonstrates at least a 30% reduction in processing duration compared to `batch_size=1` on 100,000 synthetic records.

**Execution**:
```bash
pytest tests/benchmarks/test_batch_throughput.py -v -s
```

**Expected Outcome**: Test asserts `elapsed_batch_5000 <= 0.70 * elapsed_batch_1`.

---

### Scenario 4: Asynchronous Stream Parity

**Objective**: Confirm asynchronous stream yields identical results to synchronous iteration for the same dataset.

```python
import pytest
from pydantic_stream_file import StreamValidator, StreamValidatorAsync

@pytest.mark.asyncio
async def test_parity(sync_adapter, async_adapter, model):
    sync_results = list(StreamValidator(sync_adapter, model, on_error="yield_result"))
    async_results = [r async for r in StreamValidatorAsync(async_adapter, model, on_error="yield_result")]

    assert len(sync_results) == len(async_results)
    for s_res, a_res in zip(sync_results, async_results):
        assert s_res.is_valid == a_res.is_valid
        assert s_res.raw_data == a_res.raw_data
        assert s_res.location == a_res.location
```

**Expected Outcome**: 100% equivalence between sync and async stream results.
