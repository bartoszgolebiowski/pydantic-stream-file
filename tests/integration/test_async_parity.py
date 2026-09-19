from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from typing import Optional
import pytest
from pydantic import BaseModel
from pydantic_stream_file import (
    StreamValidator,
    StreamValidatorAsync,
    ErrorPolicy,
    StreamResult,
)
from pydantic_stream_file.adapters.base import AsyncStreamAdapter, StreamAdapter
from pydantic_stream_file.types import RawRecord, StreamLocation


class SensorData(BaseModel):
    sensor_id: str
    temperature: float
    reading_time: int


class MockSyncAdapter(StreamAdapter):
    def __init__(self, records: list[dict]):
        self.records = records

    def __iter__(self) -> Iterator[RawRecord]:
        for idx, rec in enumerate(self.records, 1):
            yield RawRecord(data=rec, location=StreamLocation(logical_record=idx, physical_line_start=idx))


class MockAsyncAdapter(AsyncStreamAdapter):
    def __init__(self, records: list[dict]):
        self.records = records

    async def __aiter__(self) -> AsyncIterator[RawRecord]:
        for idx, rec in enumerate(self.records, 1):
            await asyncio.sleep(0.0001)
            yield RawRecord(data=rec, location=StreamLocation(logical_record=idx, physical_line_start=idx))


@pytest.fixture
def mixed_sensor_records() -> list[dict]:
    return [
        {"sensor_id": "S1", "temperature": "21.5", "reading_time": "1000"},
        {"sensor_id": "S2", "temperature": "bad_temp", "reading_time": "1005"},
        {"sensor_id": "S3", "temperature": "-5.0", "reading_time": "1010"},
    ]


@pytest.mark.asyncio
async def test_async_parity_yield_result(mixed_sensor_records: list[dict]):
    sync_adapter = MockSyncAdapter(mixed_sensor_records)
    async_adapter = MockAsyncAdapter(mixed_sensor_records)

    sync_validator = StreamValidator(sync_adapter, SensorData, on_error="yield_result", batch_size=2)
    async_validator = StreamValidatorAsync(async_adapter, SensorData, on_error="yield_result", batch_size=2)

    sync_results = list(sync_validator)
    async_results = [r async for r in async_validator]

    assert len(sync_results) == len(async_results) == 3

    for s, a in zip(sync_results, async_results):
        assert s.is_valid == a.is_valid
        assert s.raw_data == a.raw_data
        assert s.location == a.location
        if s.is_valid:
            assert s.item == a.item
        else:
            assert s.error is not None and a.error is not None


@pytest.mark.asyncio
async def test_async_parity_skip(mixed_sensor_records: list[dict]):
    sync_adapter = MockSyncAdapter(mixed_sensor_records)
    async_adapter = MockAsyncAdapter(mixed_sensor_records)

    sync_validator = StreamValidator(sync_adapter, SensorData, on_error="skip", batch_size=2)
    async_validator = StreamValidatorAsync(async_adapter, SensorData, on_error="skip", batch_size=2)

    sync_items = list(sync_validator)
    async_items = [r async for r in async_validator]

    assert len(sync_items) == len(async_items) == 2
    for s, a in zip(sync_items, async_items):
        assert s.sensor_id == a.sensor_id
        assert s.temperature == a.temperature
