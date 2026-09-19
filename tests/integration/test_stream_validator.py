from __future__ import annotations

import io
from typing import Optional
import pytest
from pydantic import BaseModel, ValidationError
from pydantic_stream_file import StreamValidator, ErrorPolicy, StreamResult
from pydantic_stream_file.adapters.csv import CsvAdapter


class UserRecord(BaseModel):
    id: int
    name: str
    age: Optional[int] = None


@pytest.fixture
def mixed_csv_data() -> str:
    return (
        "id,name,age\n"
        "1,Alice,30\n"
        "2,Bob,invalid_age\n"
        "3,Charlie,25\n"
    )


def test_validator_raise_policy(mixed_csv_data: str):
    adapter = CsvAdapter(source=io.StringIO(mixed_csv_data))
    validator = StreamValidator(adapter=adapter, model=UserRecord, on_error=ErrorPolicy.RAISE)

    it = iter(validator)
    item1 = next(it)
    assert isinstance(item1, UserRecord)
    assert item1.name == "Alice"

    with pytest.raises(ValidationError) as exc_info:
        next(it)
    assert "Input should be a valid integer" in str(exc_info.value)


def test_validator_skip_policy(mixed_csv_data: str):
    adapter = CsvAdapter(source=io.StringIO(mixed_csv_data))
    validator = StreamValidator(adapter=adapter, model=UserRecord, on_error="skip")

    valid_items = list(validator)
    assert len(valid_items) == 2
    assert [u.name for u in valid_items] == ["Alice", "Charlie"]


def test_validator_yield_result_policy(mixed_csv_data: str):
    adapter = CsvAdapter(source=io.StringIO(mixed_csv_data))
    validator = StreamValidator(adapter=adapter, model=UserRecord, on_error="yield_result")

    results: list[StreamResult[UserRecord]] = list(validator)
    assert len(results) == 3

    # Row 1: Valid
    assert results[0].is_valid is True
    assert isinstance(results[0].item, UserRecord)
    assert results[0].item.id == 1
    assert results[0].error is None
    assert results[0].raw_data["name"] == "Alice"
    assert "Line: 2" in results[0].location

    # Row 2: Invalid (routed to DLQ)
    assert results[1].is_valid is False
    assert results[1].item is None
    assert isinstance(results[1].error, ValidationError)
    assert results[1].raw_data["age"] == "invalid_age"
    assert "Line: 3" in results[1].location

    # Row 3: Valid
    assert results[2].is_valid is True
    assert isinstance(results[2].item, UserRecord)
    assert results[2].item.id == 3
    assert results[2].error is None


def test_validator_empty_stream():
    adapter = CsvAdapter(source=io.StringIO("id,name,age\n"))
    validator = StreamValidator(adapter=adapter, model=UserRecord, on_error="yield_result")
    assert list(validator) == []
