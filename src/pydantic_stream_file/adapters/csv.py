from __future__ import annotations

import csv
from collections.abc import Iterator, Sequence
from contextlib import nullcontext
from pathlib import Path
from typing import Any, TextIO, Union
from pydantic_stream_file.adapters.base import StreamAdapter
from pydantic_stream_file.types import RawRecord, StreamLocation
from pydantic_stream_file.utils import clean_null_values


class CsvAdapter(StreamAdapter):
    """Streaming adapter for delimited text files (CSV, TSV)."""

    def __init__(
        self,
        source: Union[str, Path, TextIO],
        delimiter: str = ",",
        quotechar: str = '"',
        escapechar: Union[str, None] = None,
        null_values: Sequence[str] = ("", "NULL", "N/A"),
        encoding: str = "utf-8",
    ) -> None:
        self.source = source
        self.delimiter = delimiter
        self.quotechar = quotechar
        self.escapechar = escapechar
        self.null_values = set(null_values)
        self.encoding = encoding

    def __iter__(self) -> Iterator[RawRecord]:
        close_needed = False
        if isinstance(self.source, (str, Path)):
            f: TextIO = open(self.source, mode="r", encoding=self.encoding, newline="")
            close_needed = True
        else:
            f = self.source

        try:
            reader_kwargs: dict[str, Any] = {
                "delimiter": self.delimiter,
                "quotechar": self.quotechar,
            }
            if self.escapechar is not None:
                reader_kwargs["escapechar"] = self.escapechar

            reader = csv.reader(f, **reader_kwargs)

            try:
                header_row = next(reader)
            except StopIteration:
                return

            headers = [h.strip() for h in header_row]
            logical_record = 0
            current_start_line = reader.line_num + 1

            for row in reader:
                logical_record += 1
                end_line = reader.line_num
                start_line = current_start_line
                current_start_line = end_line + 1

                # Build dictionary mapping headers to row values
                raw_dict: dict[str, Any] = {}
                for idx, h in enumerate(headers):
                    val = row[idx] if idx < len(row) else None
                    raw_dict[h] = val

                cleaned_dict = clean_null_values(raw_dict, self.null_values)

                location = StreamLocation(
                    logical_record=logical_record,
                    physical_line_start=start_line,
                    physical_line_end=end_line,
                )

                yield RawRecord(data=cleaned_dict, location=location)

        finally:
            if close_needed:
                f.close()
