from __future__ import annotations

import io
from pathlib import Path
from typing import Optional
import pytest
from pydantic import BaseModel
from pydantic_stream_file import (
    StreamValidator,
    StreamValidatorAsync,
    ErrorPolicy,
    adapters,
)
from pydantic_stream_file.adapters.base import AsyncStreamAdapter, StreamAdapter
from pydantic_stream_file.types import RawRecord, StreamLocation


class Transaction(BaseModel):
    id: int
    amount: float
    description: str
    note: Optional[str] = None


class Order(BaseModel):
    batch_id: str
    order_id: str
    amount: float


def test_quickstart_scenario_1_csv_dlq():
    csv_data = (
        'id,amount,description,note\n'
        '1,10.5,"Groceries\nand supplies",NULL\n'
        '2,invalid_amount,"Hardware store",\n'
        '3,99.00,"Online course",Valid note\n'
    )
    csv_stream = adapters.CsvAdapter(
        source=io.StringIO(csv_data),
        delimiter=",",
        null_values=["", "NULL"],
    )

    validator = StreamValidator(
        adapter=csv_stream,
        model=Transaction,
        on_error=ErrorPolicy.YIELD_RESULT,
        batch_size=10,
    )

    results = list(validator)
    assert len(results) == 3

    # Row 1: Valid multiline
    assert results[0].is_valid is True
    assert "\n" in results[0].item.description
    assert results[0].item.note is None

    # Row 2: Invalid row routed to DLQ
    assert results[1].is_valid is False
    assert results[1].item is None
    assert results[1].error is not None
    assert results[1].raw_data["amount"] == "invalid_amount"
    assert "Line:" in results[1].location

    # Row 3: Valid
    assert results[2].is_valid is True
    assert results[2].item.note == "Valid note"


def test_quickstart_scenario_2_xml_parent_context():
    xml_data = """<?xml version="1.0" encoding="utf-8"?>
    <orders batch_id="BATCH-001">
        <order order_id="ORD-1">
            <amount>150.00</amount>
        </order>
        <order order_id="ORD-2">
            <amount>275.50</amount>
        </order>
    </orders>
    """
    xml_stream = adapters.XmlAdapter(
        source=io.StringIO(xml_data),
        target_tag="order",
        context_tags=["orders"],
        attr_prefix="",
    )

    validator = StreamValidator(
        adapter=xml_stream,
        model=Order,
        on_error="raise",
    )

    orders = list(validator)
    assert len(orders) == 2
    for ord_item in orders:
        assert ord_item.batch_id == "BATCH-001"
    assert orders[0].order_id == "ORD-1"
    assert orders[1].order_id == "ORD-2"


class SimpleItem(BaseModel):
    id: int
    val: float


class MockSync(StreamAdapter):
    def __init__(self, data: list[dict]):
        self.data = data

    def __iter__(self):
        for idx, d in enumerate(self.data, 1):
            yield RawRecord(data=d, location=StreamLocation(logical_record=idx, physical_line_start=idx))


class MockAsync(AsyncStreamAdapter):
    def __init__(self, data: list[dict]):
        self.data = data

    async def __aiter__(self):
        for idx, d in enumerate(self.data, 1):
            yield RawRecord(data=d, location=StreamLocation(logical_record=idx, physical_line_start=idx))


@pytest.mark.asyncio
async def test_quickstart_scenario_4_async_parity():
    raw_data = [
        {"id": "1", "val": "10.0"},
        {"id": "2", "val": "not_float"},
        {"id": "3", "val": "30.0"},
    ]
    sync_res = list(StreamValidator(MockSync(raw_data), SimpleItem, on_error="yield_result"))
    async_res = [r async for r in StreamValidatorAsync(MockAsync(raw_data), SimpleItem, on_error="yield_result")]

    assert len(sync_res) == len(async_res) == 3
    for s, a in zip(sync_res, async_res):
        assert s.is_valid == a.is_valid
        assert s.raw_data == a.raw_data
        assert s.location == a.location
