# Validation Engine & Error Routing

`StreamValidator` orchestrates stream parsing, vectorized schema validation, and error policies.

---

## Vectorized Batching (Pydantic-Core Acceleration)

Validating records one-by-one in a raw Python loop incurs substantial overhead entering and exiting Pydantic's Rust engine (`pydantic-core`).

`StreamValidator` includes a `batch_size` parameter (default `1000`). It accumulates raw dictionaries and validates them in bulk using `TypeAdapter(list[Model]).validate_python()` in compiled Rust.

### Benchmarks & Speedup
- Single-item validation (`batch_size=1`): standard loop overhead.
- Vectorized batch validation (`batch_size=1000` to `5000`): **30% to 50% faster throughput**, with zero difference in yielded output.
- Memory consumption remains strictly bounded to the size of a single batch.

---

## Error Handling Policies (`on_error`)

You can control failure behavior using the `ErrorPolicy` enum (or string values):

```python
from pydantic_stream_file import ErrorPolicy
```

### 1. `ErrorPolicy.YIELD_RESULT` (`"yield_result"`) — Dead Letter Queue Pattern

The stream **never raises an unhandled exception** on malformed records. Instead, it yields a [`StreamResult[T]`](../api-reference.md#streamresultt) envelope for every record.

```python
validator = StreamValidator(
    adapter=adapter,
    model=Transaction,
    on_error=ErrorPolicy.YIELD_RESULT,
    batch_size=2000
)

for result in validator:
    if result.is_valid:
        # result.item contains validated Transaction
        insert_db(result.item)
    else:
        # Route corrupt records to DLQ with line numbers and original payload
        send_to_dlq(
            payload=result.raw_data,
            error=result.error,
            location=result.location
        )
```

#### Automated Error Isolation in Batches
When a vectorized batch contains a malformed record, `StreamValidator` automatically switches to item-level evaluation for that specific batch, isolating the exact failing record without dropping valid siblings.

---

### 2. `ErrorPolicy.SKIP` (`"skip"`)

Discards any row that fails validation. Only successfully validated Pydantic model instances are yielded.

```python
validator = StreamValidator(
    adapter=adapter,
    model=Transaction,
    on_error="skip",
)

for transaction in validator:
    # Always a valid Transaction instance
    process_clean(transaction)
```

---

### 3. `ErrorPolicy.RAISE` (`"raise"`) — Default

Immediately halts iteration and raises the `ValidationError` on the first corrupt record encountered.
