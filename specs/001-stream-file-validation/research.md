# Research & Technical Decisions: `pydantic-stream-file`

**Feature**: `001-stream-file-validation`  
**Date**: 2026-09-19  

## 1. Constant Memory XML Streaming ($O(1)$ RAM)

### Context & Challenge
Standard XML parsing methods (`xml.etree.ElementTree.parse` or naive `iterparse`) accumulate parsed elements into a tree rooted at the document root. Even when calling `elem.clear()`, the parent element retains references to cleared child elements in its internal children list, causing memory to scale linearly $O(N)$ with file size (frequently causing OOM errors on 100 MB–50 GB files).

### Decision
Use `xml.etree.ElementTree.iterparse` with dual `'start'` and `'end'` events, accompanied by explicit parent-reference cleanup and optional `lxml` acceleration.

1. **Parent Context Tracking**: On `'start'` events of configured parent tags, push tag name and attributes onto an internal context stack (`list[tuple[str, dict[str, str]]]`).
2. **Subtree Extraction & Pruning**: On `'end'` events of target record tags:
   - Extract the record dictionary.
   - Inject required parent context attributes from the context stack.
   - Call `elem.clear()`.
   - Clear parent references:
     - For standard library `xml.etree.ElementTree`: Maintain a stack of parent elements during traversal and explicitly remove the processed element from its immediate parent (`parent.remove(elem)`).
     - For `lxml` extra: Apply the high-performance idiom:
       ```python
       elem.clear()
       while elem.getprevious() is not None:
           del elem.getparent()[0]
       ```
3. On `'end'` events of ancestor context tags: pop from context stack.

### Alternatives Considered
- `xmltodict`: Buffers the entire XML document into memory unless paired with streaming, but lacks parent-context injection and requires full tree buffering for non-trivial subtrees.
- SAX Parser (`xml.sax`): Extremely low memory, but writing state-machine handlers for nested structures with variable repeated tags is error-prone, fragile, and slower in pure Python than C-accelerated `iterparse`.

---

## 2. Vectorized Batch Validation & Dead Letter Queue Error Isolation

### Context & Challenge
Calling `model.model_validate(row)` in a pure Python loop incurs overhead for each item entering and exiting Pydantic's Rust engine (`pydantic-core`). Grouping records into batches (`TypeAdapter(list[Model]).validate_python(batch)`) delegates batch looping to compiled Rust, yielding 30–50% throughput gains. However, when a batch contains one or more invalid records, Pydantic raises a single `ValidationError` for the entire batch.

### Decision
Implement a **Fast-Path Batch / Fallback Item Isolation** pattern:

1. **Happy Path (All Valid)**: The engine submits the collected batch of `N` raw dictionaries to `TypeAdapter(list[Model]).validate_python(batch, from_attributes=False)`. If successful, all `N` items are marked `is_valid=True` and emitted (or yielded).
2. **Faulted Path (Errors Encountered)**:
   - In `RAISE` mode: The `ValidationError` is raised immediately.
   - In `SKIP` or `YIELD_RESULT` mode:
     - Pydantic v2 `ValidationError.errors()` provides a `loc` tuple where the first element is the integer index of the failing record within the batch (e.g., `loc = (4, 'amount')`).
     - We group errors by batch index. Items with no corresponding error are validated as `is_valid=True`.
     - For items with errors, we attach the specific `ValidationError` (or reconstructed error details), their original `raw_data`, and their `StreamLocation`.
     - If unexpected batch-level validation failure occurs, the engine falls back to per-item validation for that single batch to ensure 100% deterministic error isolation.

### Alternatives Considered
- *Strict Per-Item Validation Only*: Simpler to implement, but loses all Rust vectorization performance advantages.
- *Discard Entire Batch on Single Failure*: Inacceptable for Dead Letter Queue architectures; violating tenet #4 ("A single malformed row must not crash or discard valid data").

---

## 3. Delimited Flat-File (CSV) Adaptation & Location Tracking

### Context & Challenge
CSVs present multiline cells with embedded `\n` within quotes, heterogeneous sentinel representations of null (`""`, `"NULL"`, `"None"`, `"\\N"`), and discrepancies between physical line numbers (file lines) and logical record numbers (data rows).

### Decision
1. Delegate character and quote handling to Python's standard `csv.reader` / `csv.DictReader`, which handles RFC 4180 quoted multiline cells natively without line truncation.
2. Track `reader.line_num` before and after reading each record:
   - `physical_start_line`: Line number at start of record.
   - `physical_end_line`: `reader.line_num` after consuming the record.
   - `record_number`: Monotonically increasing logical record counter.
3. Pre-validation cleaning step: A lightweight transformation pipeline replaces configured sentinel strings with `None` across dictionary values before passing them to the validation engine.

### Alternatives Considered
- Manual line-by-line `.readline()` splitting: Fails on multiline cells inside quotes.
- Polars streaming reader: Extremely fast, but requires heavy third-party dependency (`polars`) and adds schema rigidity; better suited as an optional future adapter extra.

---

## 4. Sync and Async Dualism Architecture

### Context & Challenge
Pipelines operate in synchronous scripts (data migration jobs, CLI scripts) and asynchronous environments (FastAPI file uploads, streaming downloads from S3 with `aiobotocore` / `httpx`). Duplicating validation logic across sync and async implementations creates maintenance debt.

### Decision
Decouple the architecture into three orthogonal components:

1. **Source Adapters**:
   - `StreamAdapter[T]`: Implements `__iter__() -> Iterator[RawRecord]`
   - `AsyncStreamAdapter[T]`: Implements `__aiter__() -> AsyncIterator[RawRecord]`
2. **Validation Engine Core (`EngineCore`)**:
   - Pure, synchronous batch validator function/class that accepts a `list[RawRecord]` and returns a `list[StreamResult[T]]`.
   - Handles batching logic, Pydantic `TypeAdapter` execution, error parsing, and `StreamResult` packaging.
3. **Execution Controllers**:
   - `StreamValidator`: Consumes `StreamAdapter` via synchronous generator.
   - `StreamValidatorAsync`: Consumes `AsyncStreamAdapter` via asynchronous generator, delegating batch validation chunks to the shared `EngineCore`.

### Alternatives Considered
- Running sync generators in `asyncio.to_thread`: Introduces unnecessary thread switching overhead and cannot consume true non-blocking streams (like chunked HTTP responses).
- Maintaining two completely separate validation engines: Duplicates error handling, sentinel mapping, and batch slicing code.

---

## 5. XML-to-Dictionary Normalization Rules

### Context & Challenge
XML trees contain attributes, text nodes, mixed child elements, and repeated tags. A standardized mapping to Python dictionaries is required so Pydantic models can validate them predictably.

### Decision
Standardize on the following transformation contract:
1. **Attributes**: Mapped to keys with an `@` prefix (e.g., `id="42"` $\rightarrow$ `{"@id": "42"}`).
2. **Element Text**:
   - If an element has attributes and text content, text is mapped to `#text` (e.g., `<item id="1">Shoes</item>` $\rightarrow$ `{"@id": "1", "#text": "Shoes"}`).
   - If an element has only text and no attributes or child elements, it is simplified to a scalar string value (e.g., `<name>Shoes</name>` $\rightarrow$ `{"name": "Shoes"}`).
3. **Repeated Sibling Tags**: When multiple child tags share the same tag name, they are automatically aggregated into a `list` (e.g., `<tag>A</tag><tag>B</tag>` $\rightarrow$ `{"tag": ["A", "B"]}`).
4. **Namespace Stripping**: Enabled by default; regular expression `re.sub(r"^{[^}]+}", "", tag)` strips XML namespace prefixes so models do not require namespace-aware field aliases unless configured.
