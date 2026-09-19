from __future__ import annotations

from pathlib import Path
from typing import Optional
import pytest
from pydantic import BaseModel, Field


class SimpleUser(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    is_active: bool = True


class OrderItem(BaseModel):
    batch_id: Optional[str] = None
    item_id: str
    amount: float
    description: Optional[str] = None


@pytest.fixture
def sample_csv_content() -> str:
    return (
        "id,name,email,is_active\n"
        "1,Alice,alice@example.com,true\n"
        '2,"Bob\nSmith",NULL,false\n'
        "3,Charlie,,true\n"
        "4,Dave,dave@example.com,invalid_bool\n"
    )


@pytest.fixture
def sample_csv_file(tmp_path: Path, sample_csv_content: str) -> Path:
    csv_file = tmp_path / "test_users.csv"
    csv_file.write_text(sample_csv_content, encoding="utf-8")
    return csv_file


@pytest.fixture
def sample_xml_content() -> str:
    return """<?xml version="1.0" encoding="utf-8"?>
<batch id="BATCH-999" timestamp="2026-09-19">
    <items>
        <item id="ITM-1">
            <amount>49.99</amount>
            <description>Item 1 description</description>
        </item>
        <item id="ITM-2">
            <amount>120.00</amount>
            <description>Item 2 description</description>
        </item>
        <item id="ITM-3">
            <amount>invalid_amount</amount>
            <description>Item 3 corrupt</description>
        </item>
    </items>
</batch>
"""


@pytest.fixture
def sample_xml_file(tmp_path: Path, sample_xml_content: str) -> Path:
    xml_file = tmp_path / "test_orders.xml"
    xml_file.write_text(sample_xml_content, encoding="utf-8")
    return xml_file
