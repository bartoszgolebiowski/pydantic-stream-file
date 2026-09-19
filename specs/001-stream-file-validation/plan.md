# Implementation Plan: Stream File Validation (`pydantic-stream-file`)

**Branch**: `001-stream-file-validation` | **Date**: 2026-09-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-stream-file-validation/spec.md`

## Summary

Build `pydantic-stream-file`, an optimized Python library acting as the glue layer between streaming file I/O (CSV, XML) and Pydantic validation. The architecture guarantees $O(1)$ constant memory usage across arbitrary file sizes, provides pluggable sync/async adapters, implements vectorized batch validation using Pydantic's Rust core, and delivers robust error routing via a Dead Letter Queue (`StreamResult`) pattern.

## Technical Context

**Language/Version**: Python >= 3.10  
**Primary Dependencies**: `pydantic>=2.5.0` (zero other mandatory runtime dependencies). Optional extras: `lxml` (accelerated XML), `aiocsv` (async CSV).  
**Storage**: N/A (in-memory streaming, local files, file-like objects, network streams).  
**Testing**: `pytest>=8.0.0`, `pytest-asyncio>=0.23.0`  
**Target Platform**: Cross-platform (Linux, macOS, Windows); optimized for serverless (AWS Lambda, Cloud Run) and memory-constrained containers.  
**Project Type**: Python library (`src/pydantic_stream_file/`).  
**Performance Goals**:
- Constant $O(1)$ memory footprint across file sizes from 10 MB to 50+ GB.
- Vectorized batching (`batch_size >= 1000`) achieves $\ge 30\%$ throughput gain over single-record validation loops.
- Library framework overhead $\le 15-20\%$ compared to direct Pydantic validation.  
**Constraints**:
- Single-record malformations must not crash the entire stream pipeline when using `YIELD_RESULT` or `SKIP` policies.
- 100% type safety and IDE autocompletion (`py.typed`).
- Zero mandatory dependencies other than Pydantic.  
**Scale/Scope**: Streaming files up to 50 GB and 100+ million records.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / Gate | Assessment | Status |
| :--- | :--- | :---: |
| **I. Library-First** | The codebase is structured purely as a standalone, reusable, independently testable Python library with clear abstractions (`StreamAdapter`, `StreamValidator`). | **PASS** |
| **II. Clean Interface** | Public exports are clean, cohesive, type-hinted, and decoupled (`pydantic_stream_file`). | **PASS** |
| **III. Test-First (TDD)** | Comprehensive unit, contract, and benchmark suites designed before implementation. | **PASS** |
| **IV. Integration & Parity** | Verification covers sync/async parity, large file benchmarks, and multi-format contracts. | **PASS** |
| **V. Simplicity & Minimal Deps** | Standard library `csv` and `xml.etree` used by default; optional parsers gated behind extras. No framework bloat. | **PASS** |

## Project Structure

### Documentation (this feature)

```text
specs/001-stream-file-validation/
├── spec.md              # Feature specification
├── plan.md              # Implementation plan (this document)
├── research.md          # Technical research & architecture decisions (Phase 0)
├── data-model.md        # Domain entities, types & invariants (Phase 1)
├── contracts/           # Public API signatures & contracts (Phase 1)
│   └── python-api.md
├── quickstart.md        # End-to-end runnable validation guide (Phase 1)
└── checklists/
    └── requirements.md  # Specification quality checklist
```

### Source Code (repository root)

```text
src/
└── pydantic_stream_file/
    ├── __init__.py          # Top-level exports (StreamValidator, StreamResult, ErrorPolicy)
    ├── py.typed             # PEP 561 marker
    ├── types.py             # ErrorPolicy, StreamLocation, RawRecord, StreamResult
    ├── engine.py            # StreamValidator, StreamValidatorAsync, BatchValidator core
    ├── utils.py             # Sentinel coercion, string formatting helpers
    └── adapters/
        ├── __init__.py      # Adapter exports (CsvAdapter, XmlAdapter, Base adapters)
        ├── base.py          # Abstract StreamAdapter and AsyncStreamAdapter
        ├── csv.py           # Delimited CSV adapter with multiline and line tracking
        └── xml.py           # Constant-memory XML adapter with subtree pruning & parent context

tests/
├── conftest.py              # Shared fixtures, temporary files, test models
├── unit/
│   ├── test_location.py     # StreamLocation formatting and tracking
│   ├── test_types.py        # StreamResult, ErrorPolicy invariants
│   ├── test_csv_adapter.py  # CSV multiline, delimiters, sentinels, line numbers
│   └── test_xml_adapter.py  # XML subtree clearing, parent context, namespaces, attributes
├── integration/
│   ├── test_stream_validator.py  # RAISE, SKIP, YIELD_RESULT policies and DLQ behavior
│   ├── test_batching.py          # Batch vectorized validation and error isolation
│   ├── test_async_parity.py      # StreamValidatorAsync parity with sync engine
│   └── test_polymorphic.py       # Discriminated union stream routing
└── benchmarks/
    ├── test_memory_profile.py    # O(1) RAM assertion on large synthetic files
    └── test_batch_throughput.py  # Throughput comparison (batch_size=1 vs batch_size=5000)
```

**Structure Decision**: Standard modern Python library layout with `src/` directory packaging, full type annotations, and stratified unit/integration/benchmark test suites.

## Complexity Tracking

> **No Constitution violations detected. All features follow minimal footprint and zero external dependency principles.**
