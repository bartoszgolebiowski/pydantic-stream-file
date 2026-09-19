from __future__ import annotations

import pytest
from pydantic import ValidationError, BaseModel
from pydantic_stream_file.types import ErrorPolicy, StreamLocation, StreamResult, RawRecord


class DummyModel(BaseModel):
    name: str
    age: int


def test_error_policy_values():
    assert ErrorPolicy.RAISE.value == "raise"
    assert ErrorPolicy.SKIP.value == "skip"
    assert ErrorPolicy.YIELD_RESULT.value == "yield_result"
    assert ErrorPolicy("raise") == ErrorPolicy.RAISE
    assert ErrorPolicy("skip") == ErrorPolicy.SKIP
    assert ErrorPolicy("yield_result") == ErrorPolicy.YIELD_RESULT


def test_stream_result_valid_invariant():
    item = DummyModel(name="Alice", age=30)
    result = StreamResult[DummyModel](
        is_valid=True,
        item=item,
        raw_data={"name": "Alice", "age": "30"},
        error=None,
        location="Line: 1",
    )
    assert result.is_valid is True
    assert result.item == item
    assert result.error is None
    assert result.raw_data["name"] == "Alice"
    assert result.location == "Line: 1"


def test_stream_result_invalid_invariant():
    error_mock = None
    try:
        DummyModel.model_validate({"name": "Bob", "age": "not_an_int"})
    except ValidationError as err:
        error_mock = err

    assert error_mock is not None

    result = StreamResult[DummyModel](
        is_valid=False,
        item=None,
        raw_data={"name": "Bob", "age": "not_an_int"},
        error=error_mock,
        location="Line: 2",
    )
    assert result.is_valid is False
    assert result.item is None
    assert result.error is error_mock
    assert result.raw_data["age"] == "not_an_int"
    assert result.location == "Line: 2"


def test_raw_record_creation():
    loc = StreamLocation(logical_record=1, physical_line_start=10)
    record = RawRecord(data={"col1": "val1"}, location=loc)
    assert record.data == {"col1": "val1"}
    assert record.location.logical_record == 1
    assert record.location.physical_line_start == 10
