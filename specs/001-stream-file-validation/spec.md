# Feature Specification: Stream File Validation (`pydantic-stream-file`)

**Feature Branch**: `001-stream-file-validation`  
**Created**: 2026-09-19  
**Status**: Draft  
**Input**: User description: "Product Requirements Document: pydantic-stream-file"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Flat-File (CSV) Streaming with Dead Letter Queue Routing (Priority: P1)

As a data engineer building ETL pipelines in memory-constrained environments, I want to stream large delimited flat files line-by-line or in batches through a schema validator, converting empty or sentinel values to nulls and capturing malformed records into a structured result object without halting the stream, so that corrupt data can be routed to a dead letter queue while valid records proceed downstream.

**Why this priority**: Core value proposition of the library. Flat file validation with error tolerance and constant memory usage is the primary use case for data pipelines.

**Independent Test**: Can be fully tested by processing a CSV file containing valid rows, multiline quoted fields, and intentionally corrupted rows; verifying that valid rows produce validated entities, invalid rows yield detailed error objects with source payloads and line locations, and process memory stays constant.

**Acceptance Scenarios**:

1. **Given** a CSV file with 1,000,000 records containing multiline text within quotation marks, **When** the stream is processed with error handling set to result-yielding mode, **Then** all multiline records are parsed without record truncation and validated as cohesive entities.
2. **Given** a CSV file containing sentinel strings such as `""`, `"NULL"`, or `"N/A"`, **When** the data is streamed into fields configured for nullability, **Then** these sentinel values are converted to null representations prior to validation.
3. **Given** a stream containing malformed records with invalid types, **When** error handling is set to result-yielding mode, **Then** the stream yields a result containing the validation failure reason, the raw unvalidated row dictionary, and the physical/logical line position, without throwing an uncaught exception.
4. **Given** a stream containing malformed records, **When** error handling is set to skip mode, **Then** invalid records are silently omitted and only valid entities are emitted.
5. **Given** a stream containing malformed records, **When** error handling is set to raise mode, **Then** processing immediately halts and raises a validation error on the first non-conforming record.

---

### User Story 2 - Memory-Bounded Hierarchical XML Stream Extraction & Validation (Priority: P1)

As an integration engineer ingesting massive XML feeds (such as product catalogs or order feeds), I want to extract nested records, automatically transform XML tag structures into flat or nested records, inject parent contextual attributes (such as batch IDs), and immediately purge processed XML tree nodes, so that memory usage remains strictly flat ($O(1)$) regardless of whether the file is 10 megabytes or 50 gigabytes.

**Why this priority**: XML feeds frequently cause out-of-memory crashes in serverless and containerized systems due to DOM tree accumulation; streaming garbage collection is critical.

**Independent Test**: Can be fully tested by processing a multi-gigabyte XML file on a system with a strict 256 MB memory limit; verifying that all target entities are validated, parent attributes are injected into every child item, and memory consumption remains flat throughout execution.

**Acceptance Scenarios**:

1. **Given** a multi-gigabyte XML document with deeply nested item elements, **When** the stream processor iterates over each item tag, **Then** each item's subtree is pruned and discarded from memory immediately after conversion.
2. **Given** XML elements containing attributes (e.g., `id="123"`), inner text content, and repeated sibling child tags, **When** adapted for validation, **Then** attributes are mapped with an attribute identifier prefix, inner text is mapped to a standard text key, and repeated sibling tags are grouped into homogeneous collections.
3. **Given** an XML feed containing namespaces and URI-prefixed tags, **When** the stream is parsed, **Then** namespace prefixes and URIs are stripped from tag names so that keys match target schema field names.
4. **Given** a parent element containing contextual metadata (such as `<orders batch_id="B42">`), **When** nested `<order>` records are streamed, **Then** the parent context attribute `batch_id` is automatically injected into each extracted child record prior to validation.

---

### User Story 3 - High-Throughput Vectorized Validation & Batching (Priority: P2)

As a pipeline architect processing tens of millions of records, I want to group streamed raw records into configurable batch sizes for validation while preserving per-item result reporting, so that validation throughput is maximized while maintaining dead letter queue compatibility.

**Why this priority**: Validating records one-by-one introduces significant overhead. Batching allows high validation throughput while still preserving item-level failure isolation.

**Independent Test**: Can be tested by running benchmark comparisons between batch sizes of 1 and batch sizes of 5,000 on a 500,000-record dataset, verifying that overall throughput increases significantly while each record's validity and location remain accurately reported.

**Acceptance Scenarios**:

1. **Given** a stream configured with a batch size of 5,000, **When** the stream is iterated, **Then** records are accumulated into batches for validation before being emitted individually or in batch collections.
2. **Given** a batch containing 4,999 valid records and 1 invalid record in result-yielding mode, **When** the batch is evaluated, **Then** the 4,999 valid records are marked valid with their validated objects, and the 1 invalid record is marked invalid with its specific error and raw data.
3. **Given** a stream whose total record count is not an exact multiple of the batch size, **When** reaching the end of the stream, **Then** the trailing partial batch is processed and yielded without data loss.

---

### User Story 4 - Non-Blocking Asynchronous Stream Validation (Priority: P3)

As a web service or cloud engineer handling incoming HTTP uploads or cloud storage streams, I want to validate streaming data using asynchronous iteration with identical validation rules and error policies as the synchronous engine, so that I/O operations do not block the application event loop.

**Why this priority**: Modern web services and serverless runtimes require asynchronous I/O to handle concurrent data ingress without thread starvation.

**Independent Test**: Can be tested by consuming an asynchronous stream source inside an asynchronous event loop; verifying that identical validation results, ordering, and error reports are produced as in synchronous mode without blocking.

**Acceptance Scenarios**:

1. **Given** an asynchronous data stream source, **When** iterated using asynchronous iteration syntax, **Then** validated records and error results are yielded sequentially as chunks arrive.
2. **Given** identical input data and schema definitions, **When** processed through either the synchronous or asynchronous validation stream, **Then** both streams produce the exact same sequence of valid objects, errors, and metadata.

---

### User Story 5 - Polymorphic Event Stream Multiplexing (Priority: P3)

As an event-driven system developer processing multi-type message logs or files containing mixed record types (e.g., login events, transaction events, error events), I want the stream validator to validate records against a discriminated union of schemas, so that different event types can be inspected, matched, and routed dynamically in a single pass.

**Why this priority**: Real-world audit logs and CDC feeds often mix multiple entity types in a single chronological stream.

**Independent Test**: Can be tested with a stream containing alternating event types with a discriminator field, verifying that each record resolves to its specific concrete type.

**Acceptance Scenarios**:

1. **Given** a stream containing mixed event payloads distinguished by a discriminator tag or field, **When** processed by the stream validator, **Then** each record is instantiated as its specific schema variant.
2. **Given** a record whose discriminator does not match any known variant or fails the specific variant's schema, **When** in result-yielding mode, **Then** it yields a failure result containing the raw unvalidated payload and error details.

---

### Edge Cases

- **Corrupted Delimiters / Malformed Rows in CSV**: When unescaped quotes or mismatched delimiters appear mid-stream, the adapter reports the physical line number where corruption was detected and handles the row per the active error policy.
- **Empty Files and Header-Only Streams**: When a stream contains zero bytes, or only column headers with no data rows, the stream completes cleanly with zero iterations and without raising false errors.
- **Extremely Large Single Cells**: Cells exceeding standard buffer sizes are buffered without truncation up to configurable limits.
- **Deeply Nested XML with Cyclic or Infinite References**: Parser enforces maximum depth and tag resolution limits to prevent memory exhaustion.
- **XML Nodes with Identical Names at Multiple Hierarchy Levels**: Context extraction distinguishes between parent context and child tags by requiring explicit tag matching rules.
- **Partial or Truncated Chunks in Async Streaming**: If an async stream terminates abruptly mid-record, an explicit stream truncation error is reported with the last known position.
- **Mixed Presence of XML Child Tags**: If a child element appears once in some parents and multiple times in others, schema casting handles both scalar and list expectations gracefully.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide an extensible source adapter interface that decouples underlying file format parsing from the core validation engine.
- **FR-002**: System MUST include a Delimited Flat-File (CSV) adapter supporting configurable delimiters, quote characters, and escape characters.
- **FR-003**: CSV adapter MUST correctly buffer and preserve multiline cells containing embedded newlines within quoted fields.
- **FR-004**: CSV adapter MUST support configurable sentinel value coercion (such as `""`, `"NULL"`, `"N/A"`) into null values prior to schema validation.
- **FR-005**: CSV adapter MUST track and report both physical file line numbers and logical record numbers for every emitted item.
- **FR-006**: System MUST include a Hierarchical XML adapter operating in constant memory ($O(1)$ RAM) by purging parsed subtrees and detaching parent references immediately after item extraction.
- **FR-007**: XML adapter MUST transform XML nodes into structured dictionaries by prefixing node attributes (e.g., `@id`), mapping text content to a standard key (e.g., `#text`), and collecting repeated child elements into collections.
- **FR-008**: XML adapter MUST support automatic namespace stripping to eliminate URI prefixes from element tags and attribute keys.
- **FR-009**: XML adapter MUST support parent context extraction, injecting specified attributes or text values from ancestor elements into extracted descendant records.
- **FR-010**: System MUST support configurable error handling policies:
  - `RAISE`: Terminate stream iteration immediately upon encountering the first validation or I/O error.
  - `SKIP`: Discard invalid records silently and yield only successfully validated entities.
  - `YIELD_RESULT`: Yield a comprehensive result envelope for every processed record, capturing both successes and failures without halting iteration.
- **FR-011**: In `YIELD_RESULT` mode, each emitted result envelope MUST expose:
  - `is_valid` (boolean status indicator)
  - `item` (validated entity or null)
  - `raw_data` (raw dictionary representation from the source adapter)
  - `error` (detailed validation failure information or null)
  - `location` (precise location descriptor such as line number or document path)
- **FR-012**: Validation engine MUST support a configurable batch size parameter to perform bulk vectorized schema validation, reducing per-item overhead while maintaining item-level error attribution.
- **FR-013**: System MUST provide both synchronous and asynchronous stream validator interfaces with identical validation rules, error handling strategies, and output schemas.
- **FR-014**: System MUST support polymorphic validation against union schemas, resolving to the specific matching variant based on record contents or discriminator tags.
- **FR-015**: The core system MUST have zero required third-party runtime dependencies other than the schema validation framework (`pydantic`), with optional optimized parsers provided via opt-in package extras.

### Key Entities

- **StreamAdapter**: Abstract boundary responsible for chunking raw source I/O (files, streams, network data) into standard dictionaries accompanied by location metadata.
- **StreamValidator**: Core processing engine binding a `StreamAdapter` to a target schema model, orchestrating batching, applying error policies, and emitting results.
- **StreamValidatorAsync**: Asynchronous counterpart of `StreamValidator` for non-blocking stream sources.
- **StreamResult**: Immutable result record encapsulating validity status, the validated entity (if valid), the raw source dictionary, validation error details (if invalid), and file/stream location information.
- **StreamLocation**: Structured location indicator containing line numbers (physical and logical), column numbers, or structural paths (e.g., XPath or record indices).
- **ErrorPolicy**: Enumeration defining stream behavior upon encounter of invalid data (`RAISE`, `SKIP`, `YIELD_RESULT`).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Peak resident memory usage remains flat ($O(1)$ RAM) when streaming files of arbitrary size (from 10 MB to 50 GB+), with memory growth remaining under 10% between small and massive datasets under the same batch configuration.
- **SC-002**: 100% of malformed records are safely isolated without process termination when operating in `YIELD_RESULT` or `SKIP` mode across all supported file formats.
- **SC-003**: In `YIELD_RESULT` mode, 100% of failed records retain their original raw dictionary payload and exact stream location to allow complete dead letter queue reproduction and debugging.
- **SC-004**: Vectorized batch validation (`batch_size >= 1000`) provides at least a 30% reduction in total validation elapsed time compared to single-item validation on datasets of 100,000+ records.
- **SC-005**: Core library overhead (adapter parsing, dictionary mapping, and flow control) introduces no more than 20% latency overhead compared to direct, unbuffered schema validation loops.
- **SC-006**: 100% feature and validation parity between synchronous and asynchronous validation engines: for identical inputs, both engines emit identical records, ordering, error messages, and metadata.

## Assumptions

- Target applications run on Python 3.10+ environments.
- Memory constraints assume standard streaming where caller code does not accumulate yielded items into an unbounded in-memory list.
- Standard CSV files adhere to RFC 4180 or specify custom delimiter/quote configurations compatible with standard tabular parsing.
- XML files are well-formed XML documents suitable for incremental tree parsing (`iterparse`).
- Downstream dead letter queue persistence and storage systems are managed by the consuming application; the library provides the standard structured payload for handoff.
