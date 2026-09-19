from __future__ import annotations

import io
import time
from pydantic import BaseModel
from pydantic_stream_file import StreamValidator
from pydantic_stream_file.adapters.csv import CsvAdapter


class BenchmarkItem(BaseModel):
    id: int
    val: float
    name: str


def generate_benchmark_csv(count: int = 15000) -> io.StringIO:
    lines = ["id,val,name"]
    for i in range(count):
        lines.append(f"{i},{i * 2.5},item_{i}")
    return io.StringIO("\n".join(lines) + "\n")


def test_batch_validation_throughput_speedup():
    count = 15000

    # 1. Single-item validation (batch_size=1)
    csv_single = generate_benchmark_csv(count)
    adapter_single = CsvAdapter(source=csv_single)
    validator_single = StreamValidator(adapter=adapter_single, model=BenchmarkItem, batch_size=1)

    start_single = time.perf_counter()
    list(validator_single)
    duration_single = time.perf_counter() - start_single

    # 2. Vectorized batch validation (batch_size=1000)
    csv_batched = generate_benchmark_csv(count)
    adapter_batched = CsvAdapter(source=csv_batched)
    validator_batched = StreamValidator(adapter=adapter_batched, model=BenchmarkItem, batch_size=1000)

    start_batched = time.perf_counter()
    list(validator_batched)
    duration_batched = time.perf_counter() - start_batched

    # Assert that vectorized batching is faster
    assert duration_batched < duration_single, (
        f"Batched duration ({duration_batched:.4f}s) should be faster than single ({duration_single:.4f}s)"
    )
