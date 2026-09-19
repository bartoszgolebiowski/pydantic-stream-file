from __future__ import annotations

import io
from pathlib import Path
import pytest
from pydantic_stream_file.adapters.xml import XmlAdapter


def test_xml_adapter_basic_parsing():
    xml_data = """<?xml version="1.0" encoding="utf-8"?>
    <catalog>
        <item id="1">
            <name>Keyboard</name>
            <price>99.99</price>
        </item>
        <item id="2">
            <name>Mouse</name>
            <price>49.99</price>
        </item>
    </catalog>
    """
    adapter = XmlAdapter(source=io.StringIO(xml_data), target_tag="item")
    records = list(adapter)

    assert len(records) == 2
    assert records[0].data == {
        "@id": "1",
        "name": "Keyboard",
        "price": "99.99",
    }
    assert records[0].location.logical_record == 1
    assert "XPath: catalog/item[1]" in records[0].location.xpath or "item" in records[0].location.xpath

    assert records[1].data == {
        "@id": "2",
        "name": "Mouse",
        "price": "49.99",
    }
    assert records[1].location.logical_record == 2


def test_xml_adapter_repeated_child_tags():
    xml_data = """<store>
        <product id="P1">
            <tag>electronics</tag>
            <tag>sale</tag>
            <image url="img1.jpg"/>
            <image url="img2.jpg"/>
        </product>
    </store>"""
    adapter = XmlAdapter(source=io.StringIO(xml_data), target_tag="product")
    records = list(adapter)

    assert len(records) == 1
    assert records[0].data["@id"] == "P1"
    assert records[0].data["tag"] == ["electronics", "sale"]
    assert records[0].data["image"] == [{"@url": "img1.jpg"}, {"@url": "img2.jpg"}]


def test_xml_adapter_text_and_attributes_mapping():
    xml_data = """<items>
        <item id="100" active="true">Special Edition</item>
    </items>"""
    adapter = XmlAdapter(source=io.StringIO(xml_data), target_tag="item")
    records = list(adapter)

    assert len(records) == 1
    assert records[0].data == {
        "@id": "100",
        "@active": "true",
        "#text": "Special Edition",
    }


def test_xml_adapter_namespace_stripping():
    xml_data = """<root xmlns:h="http://www.w3.org/TR/html4/" xmlns:f="https://www.w3schools.com/furniture">
        <f:table id="T1">
            <f:name>Coffee Table</f:name>
            <f:width>80</f:width>
        </f:table>
    </root>"""
    adapter = XmlAdapter(source=io.StringIO(xml_data), target_tag="table", strip_namespaces=True)
    records = list(adapter)

    assert len(records) == 1
    assert records[0].data == {
        "@id": "T1",
        "name": "Coffee Table",
        "width": "80",
    }


def test_xml_adapter_parent_context_extraction():
    xml_data = """<warehouse code="WH-EU" region="Europe">
        <batch number="B101">
            <order id="O-1">
                <total>250</total>
            </order>
            <order id="O-2">
                <total>500</total>
            </order>
        </batch>
    </warehouse>"""
    adapter = XmlAdapter(
        source=io.StringIO(xml_data),
        target_tag="order",
        context_tags=["warehouse", "batch"],
    )
    records = list(adapter)

    assert len(records) == 2
    assert records[0].data["@id"] == "O-1"
    assert records[0].data["total"] == "250"
    assert records[0].data["warehouse_code"] == "WH-EU"
    assert records[0].data["warehouse_region"] == "Europe"
    assert records[0].data["batch_number"] == "B101"

    assert records[1].data["@id"] == "O-2"
    assert records[1].data["warehouse_code"] == "WH-EU"
    assert records[1].data["batch_number"] == "B101"
