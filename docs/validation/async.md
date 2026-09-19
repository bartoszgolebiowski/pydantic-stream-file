# Asynchronous Streaming (`StreamValidatorAsync`)

For non-blocking applications (such as **FastAPI**, **Starlette**, or async cloud downloads with **aiobotocore** / **httpx**), `StreamValidatorAsync` provides an asynchronous generator interface.

---

## Key Characteristics

- **Full Feature Parity**: Uses the identical batch validation engine, error policies, and data models as the synchronous validator.
- **Non-Blocking**: Yields records as chunks arrive without blocking the asyncio event loop.
- **Pluggable Async Adapters**: Implements `AsyncStreamAdapter`.

---

## Basic Usage

```python
import asyncio
from pydantic import BaseModel
from pydantic_stream_file import StreamValidatorAsync, ErrorPolicy
from pydantic_stream_file.adapters import AsyncStreamAdapter
from pydantic_stream_file.types import RawRecord, StreamLocation

class Event(BaseModel):
    id: int
    data: str

# Example custom async stream adapter
class AsyncNetworkAdapter(AsyncStreamAdapter):
    async def __aiter__(self):
        # Asynchronously read from socket / response stream
        for idx in range(1, 100):
            await asyncio.sleep(0.01)
            yield RawRecord(
                data={"id": str(idx), "data": f"Event {idx}"},
                location=StreamLocation(logical_record=idx)
            )

async def main():
    adapter = AsyncNetworkAdapter()
    validator = StreamValidatorAsync(
        adapter=adapter,
        model=Event,
        on_error=ErrorPolicy.YIELD_RESULT,
        batch_size=50
    )

    async for result in validator:
        if result.is_valid:
            print("Valid event:", result.item)
        else:
            print("Failed event:", result.raw_data)

asyncio.run(main())
```

---

## Using with FastAPI / Starlette Streaming Uploads

To stream request body chunks through `StreamValidatorAsync`, implement an `AsyncStreamAdapter` that splits chunks into records:

```python
from fastapi import FastAPI, Request
from pydantic import BaseModel
from pydantic_stream_file import StreamValidatorAsync, ErrorPolicy
from pydantic_stream_file.adapters import AsyncStreamAdapter
from pydantic_stream_file.types import RawRecord, StreamLocation

app = FastAPI()

class LogLine(BaseModel):
    timestamp: str
    level: str
    message: str

class RequestLineAdapter(AsyncStreamAdapter):
    """Adapter streaming CSV lines directly from a FastAPI/Starlette request."""
    def __init__(self, request: Request):
        self.request = request

    async def __aiter__(self):
        buffer = ""
        record_idx = 0
        async for chunk in self.request.stream():
            buffer += chunk.decode("utf-8")
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                record_idx += 1
                parts = line.split(",")
                if len(parts) >= 3:
                    yield RawRecord(
                        data={"timestamp": parts[0], "level": parts[1], "message": parts[2]},
                        location=StreamLocation(logical_record=record_idx)
                    )

@app.post("/ingest-stream")
async def ingest_stream(request: Request):
    adapter = RequestLineAdapter(request)
    validator = StreamValidatorAsync(
        adapter=adapter,
        model=LogLine,
        on_error=ErrorPolicy.YIELD_RESULT,
    )
    async for result in validator:
        if result.is_valid:
            process_log(result.item)
        else:
            send_to_dlq(result.raw_data, result.error)
    return {"status": "success"}
```
