from __future__ import annotations

import io
from typing import Optional
import pytest
from pydantic import BaseModel
from pydantic_stream_file import StreamValidator, StreamResult
from pydantic_stream_file.adapters.csv import CsvAdapter


class MetricRecord(BaseModel):
    id: int
    val: float


def generate_mixed_csv(count: int, error_indices: set[int]) -> io.StringIO:
    lines = ["id,val"]
    for i in range(count):
        if i in error_indices:
            lines.append(f"{i},not_a_float")
        else:
            lines.append(f"{i},{i * 1.5}")
    return io.StringIO("\n".join(lines) + "\n")


def test_batch_all_valid_with_trailing_flush():
    # 25 items with batch_size=10 -> batches of 10, 10, and trailing batch of 5
    csv_stream = generate_mixed_csv(count=25, error_indices=set())
    adapter = CsvAdapter(source=csv_stream)
    validator = StreamValidator(adapter=adapter, model=MetricRecord, batch_size=10)

    items = list(validator)
    assert len(items) == 25
    assert [m.id for m in items] == list(range(25))


def test_batch_mixed_records_yield_result():
    # 20 items with batch_size=5 -> error at index 3 and 12
    error_indices = {3, 12}
    csv_stream = generate_mixed_csv(count=20, error_indices=error_indices)
    adapter = CsvAdapter(source=csv_stream)
    validator = StreamValidator(
        adapter=adapter,
        model=MetricRecord,
        on_error="yield_result",
        batch_size=5,
    )

    results = list(validator)
    assert len(results) == 20

    for idx, r in enumerate(results):
        if idx in error_indices:
            assert r.is_valid is False
            assert r.item is None
            assert r.error is not None
            assert r.raw_data["val"] == "not_a_float"
            assert f"Line: {idx + 2}" in r.location
        else:
            assert r.is_valid is True
            assert r.item is not None
            assert r.item.id == idx
            assert r.error is None


def test_batch_mixed_records_skip():
    csv_stream = generate_mixed_csv(count=20, error_indices={2, 7, 18})
    adapter = CsvAdapter(source=csv_stream)
    validator = StreamValidator(
        adapter=adapter,
        model=MetricRecord,
        on_error="skip",
        batch_size=5,
    )

    items = list(validator)
    assert len(items) == 17
    assert 2 not in [m.id for m in items]
    assert 7 not in [m.id for m in items]
    assert 18 not in [m.id for m in items]
