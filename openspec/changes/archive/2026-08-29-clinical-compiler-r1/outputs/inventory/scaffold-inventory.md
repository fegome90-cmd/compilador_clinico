# Phase 0 — Zero-Byte Scaffold Inventory (Task 0.4)

Change: `clinical-compiler-r1` | Captured: 2026-08-29 (runs 0/05 sha-manifest, `wc -c` pass) | Repo HEAD: `c6578b6`.

## Enumeration — every file under `src/clinical_compiler/` with byte count

Zero-byte files (all share the empty-file SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`):

| # | Path (under `src/clinical_compiler/`) | Bytes | Category |
|---|---|---|---|
| 1 | `passes/__init__.py` | 0 | package `__init__` |
| 2 | `passes/input_validation.py` | 0 | pass scaffold |
| 3 | `passes/semantic_normalization.py` | 0 | pass scaffold |
| 4 | `passes/admissibility.py` | 0 | pass scaffold |
| 5 | `passes/document_selection.py` | 0 | pass scaffold |
| 6 | `linter/__init__.py` | 0 | package `__init__` |
| 7 | `linter/conformance.py` | 0 | linter scaffold |
| 8 | `renderers/__init__.py` | 0 | package `__init__` |
| 9 | `renderers/deterministic.py` | 0 | renderer scaffold |
| 10 | `core/__init__.py` | 0 | package `__init__` (core is otherwise implemented) |
| 11 | `adapters/README.md` | 0 | placeholder doc in adapters (no Python there) |
| 12 | `py.typed` | 0 | PEP 561 marker — NOT a source file |

Non-zero files under `src/clinical_compiler/`:

| Path | Bytes | Content |
|---|---|---|
| `__init__.py` | 170 | exports `Diagnostic`, `DiagnosticCode` |
| `core/types.py` | (implemented) | `Certainty`/`Missingness`/`Provenance`/`ClinicalValue` |
| `core/ir.py` | (implemented) | `SourceFactIR` → `CanonicalClinicalFact` → `DocumentIR` |
| `core/diagnostics.py` | (implemented) | 8-code `DiagnosticCode` + `Diagnostic` |
| `core/policy.py` | (implemented) | `NEVER_AUTO_TERMS = frozenset()` (empty) |

## Counts

- **Zero-byte files under `src/clinical_compiler/` total: 12** (11 source files + 1 marker).
- **Zero-byte SOURCE files: 11** = 4 passes + `linter/conformance.py` + `renderers/deterministic.py`
  + 4 package `__init__.py` (`passes`, `linter`, `renderers`, `core`) + `adapters/README.md`.
  This **confirms** the proposal baseline claim "11 zero-byte source files" under that counting
  (the claim's enumeration names the 6 pass/linter/renderer files and folds the `__init__.py`
  files and `adapters/README.md` into the count; `py.typed` is a marker and excluded).
- tasks.md 0.4's expected list names 10 items (it omits `core/__init__.py`, which is also
  zero-byte); the observed superset of 11 is enumerated above so the final-gate scaffold count
  (scoped to `{passes,linter,renderers,adapters}` = 9 today: items 1–9 + `adapters/README.md`)
  is unambiguous.
- **`adapters/` contains no Python: CONFIRMED** — sole entry is the zero-byte `README.md`; no
  `__init__.py`; mypy run 0/07 found 15 source files, none under `adapters/`.

## Docs confirmation

- `README.md` — 0 bytes (`wc -c`) — CONFIRMED empty.
- `docs/architecture.md` — 0 bytes (`wc -c`) — CONFIRMED empty.

## Other markers

- `src/clinical_compiler/py.typed` — 0 bytes (intentional PEP 561 marker; registered in
  `pyproject.toml` `[tool.setuptools.package-data]`; NOT part of the scaffold-completion gate).
