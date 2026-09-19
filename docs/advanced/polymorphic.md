# Polymorphic Event Routing (Discriminated Unions)

In many event-driven pipelines, a single chronological stream or flat file contains heterogeneous record types (e.g. `LoginEvent`, `PurchaseEvent`, `LogoutEvent`).

`pydantic-stream-file` supports validating heterogeneous streams using **Pydantic Discriminated Unions**, enabling Python 3.10+ `match / case` pattern matching.

---

## Defining Discriminated Unions

Use Pydantic's `Annotated[Union[...], Field(discriminator="...")]`:

```python
from typing import Annotated, Literal, Union
from pydantic import BaseModel, Field, TypeAdapter
from pydantic_stream_file import StreamValidator, adapters

class LoginEvent(BaseModel):
    type: Literal["login"]
    user_id: int
    ip_address: str

class PurchaseEvent(BaseModel):
    type: Literal["purchase"]
    user_id: int
    amount: float
    currency: str

class LogoutEvent(BaseModel):
    type: Literal["logout"]
    user_id: int

# Discriminated Union
EventUnion = Annotated[
    Union[LoginEvent, PurchaseEvent, LogoutEvent],
    Field(discriminator="type")
]
```

---

## Streaming and Routing with `match / case`

Pass `TypeAdapter(EventUnion)` into `StreamValidator`:

```python
adapter = adapters.CsvAdapter(
    source="activity_log.csv",
    delimiter=","
)

validator = StreamValidator(
    adapter=adapter,
    model=TypeAdapter(EventUnion),
    on_error="yield_result",
    batch_size=500
)

for result in validator:
    if not result.is_valid:
        # Unknown event type or schema mismatch sent to DLQ
        route_to_dlq(result.raw_data, result.error)
        continue

    # Clean pattern matching on concrete types
    match result.item:
        case LoginEvent(user_id=uid, ip_address=ip):
            track_login_metric(uid, ip)
        case PurchaseEvent(user_id=uid, amount=amt, currency=curr):
            forward_to_billing(uid, amt, curr)
        case LogoutEvent(user_id=uid):
            invalidate_session(uid)
```
