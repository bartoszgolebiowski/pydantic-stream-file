from __future__ import annotations

from pydantic_stream_file.types import StreamLocation


def test_location_single_line_csv():
    loc = StreamLocation(logical_record=5, physical_line_start=12, physical_line_end=12)
    str_repr = str(loc)
    assert "Line: 12" in str_repr
    assert "Record: 5" in str_repr


def test_location_multiline_csv():
    loc = StreamLocation(logical_record=3, physical_line_start=10, physical_line_end=14)
    str_repr = str(loc)
    assert "Lines: 10-14" in str_repr
    assert "Record: 3" in str_repr


def test_location_xml_xpath():
    loc = StreamLocation(logical_record=42, xpath="/catalog/item[42]")
    str_repr = str(loc)
    assert "XPath: /catalog/item[42]" in str_repr
    assert "Record: 42" in str_repr


def test_location_minimal():
    loc = StreamLocation(logical_record=1)
    assert str(loc) == "Record: 1"
