# Code Map

## Purpose

This document provides a shallow wayfinding navigation map for coding agents and contributors. It highlights key entry points and change surfaces rather than an exhaustive file-by-file inventory.

For a detailed static file-by-file inventory, consult [Compiler File Guide](../compiler-file-guide.md).

If this document conflicts with live code or current specifications under `openspec/specs/`, live implementation and specifications are authoritative.

## Entry Points

| Purpose | Location | Key Symbol |
|---|---|---|
| CLI Application Execution | `src/clinical_compiler/cli.py` | `clinical_compiler.cli:main` |
| Pipeline Orchestration | `src/clinical_compiler/pipeline.py` | `clinical_compiler.pipeline:run` (lines 222–306) |
| Input Parsing & Contract Mapping | `src/clinical_compiler/adapters/` | `structured_feed.parse_feed`, `contract.map_record` |
| Policy Seed Loading | `src/clinical_compiler/adapters/seed.py` | `load_policy_seed` |
| Canonical IR & Domain Types | `src/clinical_compiler/core/` | `SourceFactIR`, `CanonicalClinicalFact`, `CanonicalClinicalIR`, `DocumentIR` |
| Deterministic Rendering | `src/clinical_compiler/renderers/deterministic.py` | `render_document` |
| Conformance Linting | `src/clinical_compiler/linter/conformance.py` | `lint_conformance` |

## Subsystem Map

### Core Domain (`src/clinical_compiler/core/`)
- **Primary files:** `types.py`, `ir.py`, `diagnostics.py`, `policy.py`
- **Role:** Pure dataclasses, enums, diagnostic codes, and static defaults. Zero dependencies on outer layers; intra-core relative imports (e.g. `core.ir` importing `.types`) permitted.
- **Read first:** `ir.py` for IR ladder (`SourceFactIR` -> `CanonicalClinicalFact` -> `CanonicalClinicalIR` -> `DocumentIR`).

### Ingestion & Adapters (`src/clinical_compiler/adapters/`)
- **Primary files:** `contract.py`, `structured_feed.py`, `seed.py`
- **Role:** Translates external JSONL lines and policy seed JSON into structured evaluations.
- **Read first:** `contract.py` for field contracts and vocabulary validation.

### Pipeline Passes (`src/clinical_compiler/passes/`)
- **Primary files:** `input_validation.py`, `semantic_normalization.py`, `admissibility.py`, `document_selection.py`
- **Role:** Sequential pure transformation stages accumulating diagnostics into `StageResult`.
- **Read first:** `semantic_normalization.py` for canonical interpretation and certainty rules.

### Renderers & Linter (`src/clinical_compiler/renderers/`, `src/clinical_compiler/linter/`)
- **Primary files:** `renderers/deterministic.py`, `linter/conformance.py`
- **Role:** Deterministic byte serialization and independent byte/grammar conformance validation.
- **Read first:** `renderers/deterministic.py` for canonical byte formatting rules.

## Critical Flows

### Standard Compilation Flow
```text
CLI (cli.py:main)
  -> Reads JSONL bytes (_read_input)
  -> Evaluates policy seed (_resolve_policy)
  -> Invokes pipeline.run(request)
       -> adapters.structured_feed:parse_feed
       -> passes.input_validation:run_input_validation
       -> passes.semantic_normalization:run_semantic_normalization
       -> passes.admissibility:run_admissibility
       -> passes.document_selection:run_document_selection
       -> [Emission Gate: Fail-Closed check]
       -> renderers.deterministic:render_document
       -> linter.conformance:lint_conformance
  -> CLI emits document to stdout (if no --output), writes atomic output file (if --output), or emits stderr diagnostics on failure
```

## Change Surface Map

### If changing input field definitions or vocabularies
- **Start with:** `src/clinical_compiler/adapters/contract.py`
- **Likely affected:** `src/clinical_compiler/passes/input_validation.py`, `tests/unit/test_adapters_contract.py`
- **Verify:** `uv run --no-sync pytest tests/unit/test_adapters_contract.py`

### If changing canonical normalization or certainty handling
- **Start with:** `src/clinical_compiler/passes/semantic_normalization.py`
- **Likely affected:** `src/clinical_compiler/core/types.py`, `src/clinical_compiler/core/ir.py`, `tests/unit/test_passes_semantic_normalization.py`
- **Verify:** `uv run --no-sync pytest tests/unit/test_passes_semantic_normalization.py`

### If changing policy veto rules or policy seed parsing
- **Start with:** `src/clinical_compiler/adapters/seed.py`, `src/clinical_compiler/passes/admissibility.py`
- **Likely affected:** `src/clinical_compiler/cli.py`, `tests/unit/test_policy.py`, `tests/unit/test_passes_admissibility.py`
- **Verify:** `uv run --no-sync pytest tests/unit/test_passes_admissibility.py tests/unit/test_policy.py`

### If changing document rendering or formatting
- **Start with:** `src/clinical_compiler/renderers/deterministic.py`
- **Likely affected:** `src/clinical_compiler/linter/conformance.py`, `tests/unit/test_renderers_deterministic.py`, `tests/unit/test_integration_golden_determinism.py`
- **Verify:** `uv run --no-sync pytest tests/unit/test_renderers_deterministic.py tests/unit/test_integration_golden_determinism.py`

## Cross-Cutting Locations

- **Test Suite:** `tests/unit/` (mirroring module structure under `src/clinical_compiler/`)
- **Package Configuration:** `pyproject.toml`
- **Domain Specifications:** `openspec/specs/`

## Generated Map Note

No automated repository map generator exists in this repository. In accordance with ACS v1.1 standards, no `CODEMAP.generated.md` placeholder is generated.
