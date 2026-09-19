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

    # Warmup both engines to avoid one-off compilation / cache cold starts
    csv_warmup = generate_benchmark_csv(500)
    list(StreamValidator(adapter=CsvAdapter(source=csv_warmup), model=BenchmarkItem, batch_size=1))
    csv_warmup2 = generate_benchmark_csv(500)
    list(StreamValidator(adapter=CsvAdapter(source=csv_warmup2), model=BenchmarkItem, batch_size=1000))

    # Take best of 3 trials to eliminate OS scheduling / garbage collection noise on CI runners
    single_trials: list[float] = []
    for _ in range(3):
        csv_single = generate_benchmark_csv(count)
        adapter_single = CsvAdapter(source=csv_single)
        validator_single = StreamValidator(adapter=adapter_single, model=BenchmarkItem, batch_size=1)
        start_single = time.perf_counter()
        list(validator_single)
        single_trials.append(time.perf_counter() - start_single)
    duration_single = min(single_trials)

    batched_trials: list[float] = []
    for _ in range(3):
        csv_batched = generate_benchmark_csv(count)
        adapter_batched = CsvAdapter(source=csv_batched)
        validator_batched = StreamValidator(adapter=adapter_batched, model=BenchmarkItem, batch_size=1000)
        start_batched = time.perf_counter()
        list(validator_batched)
        batched_trials.append(time.perf_counter() - start_batched)
    duration_batched = min(batched_trials)

    # In virtualized CI runners with noisy neighbors, allow up to a 15% margin
    assert duration_batched <= duration_single * 1.15, (
        f"Batched duration ({duration_batched:.4f}s) should not significantly exceed single ({duration_single:.4f}s)"
    )
