from __future__ import annotations

import io
import tracemalloc
from pydantic_stream_file.adapters.xml import XmlAdapter


def generate_large_xml(count: int = 5000) -> io.StringIO:
    buf = io.StringIO()
    buf.write('<?xml version="1.0" encoding="utf-8"?>\n<catalog batch_id="BATCH-CONST">\n')
    for i in range(count):
        buf.write(
            f'  <item id="{i}"><name>Product {i}</name><sku>SKU-{i}</sku><price>19.99</price></item>\n'
        )
    buf.write("</catalog>\n")
    buf.seek(0)
    return buf


def test_xml_memory_bounded_streaming():
    xml_stream = generate_large_xml(count=5000)
    adapter = XmlAdapter(source=xml_stream, target_tag="item", context_tags=["catalog"])

    tracemalloc.start()
    records_count = 0
    peak_snapshots: list[int] = []

    for idx, record in enumerate(adapter):
        records_count += 1
        if idx % 1000 == 0:
            current, peak = tracemalloc.get_traced_memory()
            peak_snapshots.append(peak)

    _, final_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert records_count == 5000
    # Peak memory difference between iteration 1000 and 5000 must remain negligible (< 2 MB)
    if len(peak_snapshots) > 1:
        growth = abs(peak_snapshots[-1] - peak_snapshots[1])
        assert growth < 2 * 1024 * 1024, f"Memory grew unexpectedly: {growth} bytes"
