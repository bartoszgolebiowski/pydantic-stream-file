# CSV & Delimited Files Adapter (`CsvAdapter`)

`CsvAdapter` streams delimited flat files (CSV, TSV, PSV) line-by-line while handling the most common real-world flat-file edge cases.

---

## Key Features

1. **Multiline Cells in Quotes**: Preserves records where cells contain embedded `\n` line breaks enclosed in quotes, preventing corrupted field splits.
2. **Sentinel Null Coercion**: Automatically cleans string representations of nulls (`""`, `"NULL"`, `"N/A"`, `"None"`, `"\\N"`) into Python `None` before schema validation.
3. **Dual Coordinate Tracking**: Reports both physical line numbers (including multiline spans) and logical row indices.
4. **Flexible Stream Sources**: Reads from file paths (`str`, `Path`), file-like objects (`io.StringIO`), standard input (`sys.stdin`), or decoded text streams (such as `io.TextIOWrapper` over a network socket).

---

## Constructor Parameters

```python
adapters.CsvAdapter(
    source: Union[str, Path, TextIO],
    delimiter: str = ",",
    quotechar: str = '"',
    escapechar: Optional[str] = None,
    null_values: Sequence[str] = ("", "NULL", "N/A"),
    encoding: str = "utf-8",
)
```

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `source` | `str \| Path \| TextIO` | *Required* | File path, file-like object, or standard input stream. |
| `delimiter` | `str` | `","` | Character used to separate fields (e.g. `","`, `";"`, `"\t"`, `"\|"`). |
| `quotechar` | `str` | `'"'` | Character used to quote fields containing delimiters or line breaks. |
| `escapechar` | `Optional[str]` | `None` | One-character string used to escape quotes/delimiters. |
| `null_values` | `Sequence[str]` | `("", "NULL", "N/A")` | Strings converted to `None` prior to schema validation. |
| `encoding` | `str` | `"utf-8"` | Character encoding when opening file paths. |

---

## Examples

### 1. Handling Multiline Quotes and Semicolon Separators

```python
from pydantic import BaseModel
from pydantic_stream_file import StreamValidator, adapters

class SupportTicket(BaseModel):
    ticket_id: int
    customer: str
    message: str

# Semicolon delimited file with multiline message cells
adapter = adapters.CsvAdapter(
    source="tickets.csv",
    delimiter=";",
    quotechar='"'
)

for ticket in StreamValidator(adapter, SupportTicket):
    print(ticket.ticket_id, ticket.message)
```

If row 5 has a message spanning lines 5 through 8:
- The ticket is read as a single record.
- In `yield_result` mode, its location is accurately reported as `Lines: 5-8 (Record: 4)`.

---

### 2. Custom Null Values for Legacy Database Dumps

Legacy SQL dumps often represent nulls as `\N` or `'None'`:

```python
adapter = adapters.CsvAdapter(
    source="database_dump.tsv",
    delimiter="\t",
    null_values=["\\N", "None", "NULL", ""]
)
```

Fields defined as `Optional[T] = None` in your Pydantic model will receive `None` instead of failing with string parsing errors.

---

### 3. Streaming directly from AWS S3 (`boto3`)

Because `CsvAdapter` requires text lines, wrap binary stream bodies (such as `StreamingBody`) using `io.TextIOWrapper`:

```python
import io
import boto3
from pydantic_stream_file import StreamValidator, adapters

s3 = boto3.client("s3")
obj = s3.get_object(Bucket="my-bucket", Key="huge_dataset.csv")

# Decode the binary stream into text lines
text_stream = io.TextIOWrapper(obj["Body"], encoding="utf-8")

adapter = adapters.CsvAdapter(
    source=text_stream
)

for record in StreamValidator(adapter, MyModel):
    process(record)
```
