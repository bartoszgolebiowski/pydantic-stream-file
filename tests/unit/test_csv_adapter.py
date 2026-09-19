from __future__ import annotations

import io
from pathlib import Path
import pytest
from pydantic_stream_file.adapters.csv import CsvAdapter


def test_csv_adapter_basic_reading():
    csv_data = "id,name\n1,Alice\n2,Bob\n"
    adapter = CsvAdapter(source=io.StringIO(csv_data))
    records = list(adapter)

    assert len(records) == 2
    assert records[0].data == {"id": "1", "name": "Alice"}
    assert records[0].location.logical_record == 1
    assert records[0].location.physical_line_start == 2
    assert records[0].location.physical_line_end == 2

    assert records[1].data == {"id": "2", "name": "Bob"}
    assert records[1].location.logical_record == 2
    assert records[1].location.physical_line_start == 3
    assert records[1].location.physical_line_end == 3


def test_csv_adapter_custom_delimiter_and_quotechar():
    csv_data = "id;name;notes\n10;'Widget';'Best;ever'\n"
    adapter = CsvAdapter(source=io.StringIO(csv_data), delimiter=";", quotechar="'")
    records = list(adapter)

    assert len(records) == 1
    assert records[0].data == {"id": "10", "name": "Widget", "notes": "Best;ever"}


def test_csv_adapter_multiline_cells():
    csv_data = (
        'id,description,status\n'
        '1,"First line\nSecond line\nThird line",active\n'
        '2,"Single line",pending\n'
    )
    adapter = CsvAdapter(source=io.StringIO(csv_data))
    records = list(adapter)

    assert len(records) == 2
    assert records[0].data["id"] == "1"
    assert records[0].data["description"] == "First line\nSecond line\nThird line"
    assert records[0].location.logical_record == 1
    assert records[0].location.physical_line_start == 2
    assert records[0].location.physical_line_end == 4

    assert records[1].data["id"] == "2"
    assert records[1].location.logical_record == 2
    assert records[1].location.physical_line_start == 5
    assert records[1].location.physical_line_end == 5


def test_csv_adapter_null_coercion():
    csv_data = "id,opt1,opt2,opt3\n1,,NULL,N/A\n2,val,None,\\N\n"
    adapter = CsvAdapter(
        source=io.StringIO(csv_data),
        null_values=["", "NULL", "N/A", "None", "\\N"]
    )
    records = list(adapter)

    assert len(records) == 2
    assert records[0].data == {"id": "1", "opt1": None, "opt2": None, "opt3": None}
    assert records[1].data == {"id": "2", "opt1": "val", "opt2": None, "opt3": None}


def test_csv_adapter_from_file_path(tmp_path: Path):
    file = tmp_path / "temp.csv"
    file.write_text("x,y\n10,20\n", encoding="utf-8")

    adapter = CsvAdapter(source=str(file))
    records = list(adapter)
    assert len(records) == 1
    assert records[0].data == {"x": "10", "y": "20"}
