from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator, Sequence
import io
from pathlib import Path
from typing import Any, BinaryIO, Optional, TextIO, Union
import xml.etree.ElementTree as ET

from pydantic_stream_file.adapters.base import StreamAdapter
from pydantic_stream_file.types import RawRecord, StreamLocation


def _strip_ns(tag: str) -> str:
    if tag.startswith("{"):
        idx = tag.find("}")
        if idx != -1:
            return tag[idx + 1 :]
    return tag


def _elem_to_dict(
    elem: ET.Element,
    strip_namespaces: bool = True,
    attr_prefix: str = "@",
    text_key: str = "#text",
) -> Any:
    """Convert an ElementTree Element into a dictionary representation."""
    result: dict[str, Any] = {}

    # 1. Attributes
    for attr_name, attr_val in elem.attrib.items():
        clean_attr = _strip_ns(attr_name) if strip_namespaces else attr_name
        result[f"{attr_prefix}{clean_attr}"] = attr_val

    # 2. Group children by tag
    children_by_tag: dict[str, list[ET.Element]] = defaultdict(list)
    for child in list(elem):
        tag = _strip_ns(child.tag) if strip_namespaces else child.tag
        children_by_tag[tag].append(child)

    for tag, child_list in children_by_tag.items():
        converted_children = [
            _elem_to_dict(
                c,
                strip_namespaces=strip_namespaces,
                attr_prefix=attr_prefix,
                text_key=text_key,
            )
            for c in child_list
        ]
        if len(converted_children) > 1:
            result[tag] = converted_children
        else:
            result[tag] = converted_children[0]

    # 3. Inner text
    text = elem.text.strip() if elem.text else ""
    if text:
        if not result:
            return text
        result[text_key] = text

    return result


class XmlAdapter(StreamAdapter):
    """Streaming XML adapter with O(1) RAM subtree pruning and parent context injection."""

    def __init__(
        self,
        source: Union[str, Path, BinaryIO, TextIO],
        target_tag: str,
        context_tags: Sequence[str] = (),
        strip_namespaces: bool = True,
        attr_prefix: str = "@",
        text_key: str = "#text",
    ) -> None:
        self.source = source
        self.target_tag = target_tag
        self.context_tags = set(context_tags)
        self.strip_namespaces = strip_namespaces
        self.attr_prefix = attr_prefix
        self.text_key = text_key

    def __iter__(self) -> Iterator[RawRecord]:
        context_stack: list[tuple[str, dict[str, str]]] = []
        parent_stack: list[ET.Element] = []
        logical_record = 0

        # Handle file paths vs file-like objects
        close_needed = False
        if isinstance(self.source, (str, Path)):
            stream: Any = open(self.source, "rb")
            close_needed = True
        else:
            stream = self.source

        try:
            # We listen for both 'start' and 'end' events
            context = ET.iterparse(stream, events=("start", "end"))

            for event, elem in context:
                raw_tag = elem.tag
                tag_name = _strip_ns(raw_tag) if self.strip_namespaces else raw_tag

                if event == "start":
                    parent_stack.append(elem)
                    if tag_name in self.context_tags:
                        context_stack.append((tag_name, dict(elem.attrib)))

                elif event == "end":
                    if tag_name == self.target_tag:
                        logical_record += 1

                        # Convert target element to dict
                        record_dict = _elem_to_dict(
                            elem,
                            strip_namespaces=self.strip_namespaces,
                            attr_prefix=self.attr_prefix,
                            text_key=self.text_key,
                        )
                        if not isinstance(record_dict, dict):
                            record_dict = {self.text_key: record_dict}

                        # Inject parent context attributes
                        for ctx_tag, ctx_attribs in context_stack:
                            for attr_k, attr_v in ctx_attribs.items():
                                clean_k = _strip_ns(attr_k) if self.strip_namespaces else attr_k
                                # Inject prefixed context key: e.g. warehouse_code
                                prefixed_key = f"{ctx_tag}_{clean_k}"
                                record_dict[prefixed_key] = attr_v
                                # Also inject bare key if not already present
                                if clean_k not in record_dict and f"{self.attr_prefix}{clean_k}" not in record_dict:
                                    record_dict[clean_k] = attr_v

                        # Build location
                        xpath_desc = f"XPath: {tag_name}[{logical_record}]"
                        location = StreamLocation(
                            logical_record=logical_record,
                            xpath=xpath_desc,
                        )

                        yield RawRecord(data=record_dict, location=location)

                        # Constant-memory cleanup:
                        elem.clear()
                        if len(parent_stack) > 1:
                            parent = parent_stack[-2]
                            parent.remove(elem)

                    if tag_name in self.context_tags and context_stack and context_stack[-1][0] == tag_name:
                        context_stack.pop()

                    if parent_stack and parent_stack[-1] is elem:
                        parent_stack.pop()

        finally:
            if close_needed:
                stream.close()
