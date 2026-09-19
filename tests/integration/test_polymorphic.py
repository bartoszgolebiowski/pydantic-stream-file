from __future__ import annotations

import io
from typing import Annotated, Literal, Union
import pytest
from pydantic import BaseModel, Field, TypeAdapter
from pydantic_stream_file import StreamValidator, StreamResult
from pydantic_stream_file.adapters.csv import CsvAdapter


class LoginEvent(BaseModel):
    type: Literal["login"]
    user_id: int
    ip: str


class PurchaseEvent(BaseModel):
    type: Literal["purchase"]
    user_id: int
    amount: float


Event = Annotated[Union[LoginEvent, PurchaseEvent], Field(discriminator="type")]


def test_polymorphic_event_stream_routing():
    csv_data = (
        "type,user_id,ip,amount\n"
        "login,101,192.168.1.1,\n"
        "purchase,101,,49.95\n"
        "login,102,10.0.0.1,\n"
        "unknown_event,999,,\n"
        "purchase,102,,bad_amount\n"
    )
    adapter = CsvAdapter(source=io.StringIO(csv_data))
    validator = StreamValidator(
        adapter=adapter,
        model=TypeAdapter(Event),
        on_error="yield_result",
        batch_size=2,
    )

    results = list(validator)
    assert len(results) == 5

    # 1. LoginEvent
    assert results[0].is_valid is True
    assert isinstance(results[0].item, LoginEvent)
    assert results[0].item.user_id == 101
    assert results[0].item.ip == "192.168.1.1"

    # 2. PurchaseEvent
    assert results[1].is_valid is True
    assert isinstance(results[1].item, PurchaseEvent)
    assert results[1].item.amount == 49.95

    # 3. LoginEvent
    assert results[2].is_valid is True
    assert isinstance(results[2].item, LoginEvent)
    assert results[2].item.user_id == 102

    # 4. Unknown event discriminator
    assert results[3].is_valid is False
    assert results[3].item is None
    assert results[3].error is not None
    assert results[3].raw_data["type"] == "unknown_event"

    # 5. Malformed purchase amount
    assert results[4].is_valid is False
    assert results[4].item is None
    assert results[4].error is not None
    assert results[4].raw_data["amount"] == "bad_amount"
