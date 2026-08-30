# Clinical Record Compiler — `compilador_clinico`

> **One-line purpose:** Compile scattered per-source clinical facts into a single deterministic, fail-closed, fully traceable clinical document.

Compiler of clinical records (`clinical-record-compiler` v0.1.0). Turns scattered per-source clinical readings — `TA 120/80`, `FC 72`, lab values, nursing notes, expressed as **structured JSONL facts** (R1 accepts no free text) — into a safe `NURSING_RECORD_TELEGRAPHIC` document without losing the three things that make a clinical document trustworthy: **certainty**, **missingness** (assessed-absent vs never-assessed), and **provenance**.

---

## Why this exists

Manual or lossy scripts that compile clinical sources typically drop:

1. **How certain** each value is (`CONFIRMED` vs `UNRESOLVED` vs `CANDIDATE` — not guessed from `source_kind`).
2. **Whether a missing value was assessed absent** (`MISSING`/`NOT_APPLICABLE`) or **never assessed** (`UNKNOWN`/`NOT_ASSESSED`) — conflating them is a safety error.
3. **Where each value came from** — every rendered value traces back to its `SourceFactIR`(s) via `source_fact_refs`.

This compiler enforces those invariants by construction: per-fact quarantine, whole-run fail-closed gating (one invalid fact blocks document emission), deterministic byte-identical output, zero runtime dependencies.

---

## Architecture Overview

The compiler follows a pure functional core and imperative shell architecture:

```text
bytes (JSONL) ──▶ adapters/contract + structured_feed ──▶ SourceFactIR
                                                         │
                              input_validation ──────────┤── INPUT_CONTRACT_ERROR / TYPE_ERROR
                            semantic_normalization ──────┤── SEMANTIC_AMBIGUITY_BLOCK
                                   admissibility ────────┤── POLICY_VIOLATION / PROVENANCE_ERROR
                              document_selection ────────┤── DOCUMENT_SELECTION_ERROR
                                                         ▼
                                              emission gate (fail-closed)
                                                         │
                                    renderers/deterministic ── RENDER_ERROR
                                         linter/conformance ── LINT_FAILURE
                                                         │
                                                         ▼
                                              Document bytes (UTF-8,
)
                                              diagnostics on stderr (one per line)
```

The canonical architecture narrative, component boundaries, state ownership, invariants, and evolution policies are documented in [Canonical Architecture](docs/agent/ARCHITECTURE.md).

---

## Project structure

```text
src/clinical_compiler/
├── core/                     # frozen leaf — stdlib only
│   ├── types.py              # Certainty | Missingness | Provenance | ClinicalValue
│   ├── ir.py                 # SourceFactIR → CanonicalClinicalFact → DocumentIR
│   ├── diagnostics.py        # DiagnosticCode (8) | Diagnostic
│   └── policy.py             # NEVER_AUTO_TERMS
├── adapters/
│   ├── contract.py           # frozen declarative input-contract table (single source of truth)
│   ├── structured_feed.py    # JSONL bytes → per-record contract evaluations
│   ├── seed.py               # --policy-seed loader (structural validation only)
│   └── free_text.py          # NOT built — Phase 0 recorded STRUCTURED_FEED_ONLY
├── passes/
│   ├── input_validation.py
│   ├── semantic_normalization.py
│   ├── admissibility.py
│   └── document_selection.py
├── renderers/deterministic.py
├── linter/conformance.py
├── pipeline_types.py         # StageResult[_T] leaf (passes import this, never pipeline)
├── pipeline.py               # composition root + emission gate + exit-code derivation
└── cli.py                    # argparse shell — clinical-compiler compile

tests/
├── conftest.py               # make_provenance / make_clinical_value / IR factories
├── fixtures/                 # corpus fixtures (12 fault classes + 2 positive controls)
├── golden/                   # golden documents + SHA-256 digests (incl. independent/)
│   └── scenarios/            # named fixture sets: input.jsonl + document.txt + manifest digests
└── unit/                     # per-pass, adapter, renderer/linter tests + runner/CLI/determinism

docs/
├── agent/                    # Agent Context System v1.1 canonical documents
│   ├── CONTEXT.md            # Domain purpose, actors, constraints, and non-goals
│   ├── ARCHITECTURE.md       # Sole canonical architecture authority
│   ├── CODEMAP.md            # Shallow wayfinding navigation map
│   └── RUNTIME.md            # CLI commands, runtime topology, and exit behavior
├── architecture.md           # Compatibility stub redirecting to docs/agent/ARCHITECTURE.md
└── compiler-file-guide.md    # Static file inventory and wayfinding

openspec/
├── specs/                    # Normative domain specifications (single source of truth)
└── changes/archive/2026-08-29-clinical-compiler-r1/  # Archived R1 design and audit trail
```

---

## Prerequisites

- Python **3.11+**
- [uv](https://docs.astral.sh/uv/) (recommended) or `pip`
- No runtime dependencies — `src` is stdlib-only. Dev deps: `pytest`, `pytest-cov`, `ruff`, `mypy`.

---

## Installation

```bash
# clone
git clone https://github.com/fegome90-cmd/compilador_clinico.git
cd compilador_clinico

# install (editable) + dev tools — the only supported setup path
uv sync --group dev

# verify baseline (must be green before any change)
uv run pytest --cov=clinical_compiler --cov-report=term-missing
uv run mypy --strict src
uv run ruff check src tests
```

`pyproject.toml` declares `tool.setuptools.packages.find.where = ["src"]` and `tool.pytest.ini_options.pythonpath = ["src"]`. `[project].dependencies` is `[]` — the runtime is stdlib-only; only `pytest`, `pytest-cov`, `ruff`, `mypy` come from the `dev` dependency group. `[project.scripts]` registers the `clinical-compiler` console script (`clinical_compiler.cli:main`), so after `uv sync` the examples below run as plain `clinical-compiler …` or via `uv run clinical-compiler …`.

---

## Quick start

### 1. Core types

```python
from clinical_compiler.core.types import Certainty, ClinicalValue, Missingness, Provenance
from clinical_compiler.core.ir import SourceFactIR, CanonicalClinicalFact, DocumentIR, DocumentEntry
from clinical_compiler.core.diagnostics import DiagnosticCode, Diagnostic
from clinical_compiler.core import policy

# Every value carries certainty + missingness + provenance — never conflated
provenance = Provenance(source_kind="lab", source_ref="lab-2026-081")
value = ClinicalValue(
    value=72,
    certainty=Certainty.UNRESOLVED,   # R1: no deterministic certainty rule is approved — always UNRESOLVED
    missingness=Missingness.PRESENT,   # vs MISSING / UNKNOWN / NOT_ASSESSED / NOT_APPLICABLE
    provenance=provenance,
)

# IR ladder is frozen and immutable
fact = SourceFactIR(fact_id="fact-1", field_id="FC", raw_value=72, provenance=provenance)
canonical = CanonicalClinicalFact(
    clinical_fact_id="canon-1",
    field_id="FC",
    value=value,
    source_fact_refs=("fact-1",),
)
doc_ir = DocumentIR(document_mode="NURSING_RECORD_TELEGRAPHIC", entries=(
    DocumentEntry(clinical_fact_ref="canon-1", presentation_role="vital_sign"),
))

# Policy veto — frozen empty default, injected at runtime in R1
assert policy.NEVER_AUTO_TERMS == frozenset()
```

### 2. Input contract (frozen, `adapters/contract.py`)

Input is a **JSONL feed**: one fact-record object per non-blank line. The frozen contract is a declarative table (`CONTRACT`) plus the pure `map_record` — the single source of truth enforced by both the adapter and `input_validation`:

```python
from clinical_compiler.adapters.contract import (
    CONTRACT,                     # field_id → FieldContract (per-field raw-value types)
    REQUIRED_RECORD_KEYS,         # {"fact_id", "field_id", "raw_value", "provenance"}
    OPTIONAL_RECORD_KEYS,         # {"source_asserted_certainty"}
    ALLOWED_SOURCE_KINDS,         # {"monitor", "lab", "clinical_note"}
)

# CONTRACT admits exactly two fields in R1:
#   FC → raw_value: int | float        TA → raw_value: str
# raw_value: null is admitted for every field — it is the structured
# branch's assessed-absence marker (PC-2) and normalizes to MISSING.
```

A conformant record (the exact bytes the pipeline accepts):

```json
{"fact_id": "pc1-ta-1", "field_id": "TA", "raw_value": "120/80",
 "provenance": {"source_kind": "monitor", "source_ref": "m-9"}}
```

Rules (all violations → diagnostics, never exceptions):
- `fact_id`, `field_id`, `raw_value`, `provenance` required; only `source_asserted_certainty` is optional; unknown keys → `INPUT_CONTRACT_ERROR`.
- `field_id` must be in `CONTRACT` (R1: `FC`, `TA`); `source_kind` must be in `ALLOWED_SOURCE_KINDS`; `provenance` must declare exactly `source_kind` + `source_ref`.
- `raw_value` type is checked by **exact runtime type** against the field's declared types — a `bool` is rejected for `FC` even though `bool <: int` in Python (`TYPE_ERROR`); an arbitrary object can never become an admissible value.
- Optional `source_asserted_certainty` must name a `Certainty` taxonomy member; it is captured verbatim (authority `PRESERVED`) and never overwrites or upgrades the compiler-assigned certainty (`UNRESOLVED` in R1).

### 3. CLI — `clinical-compiler compile`

```bash
# happy path — deterministic document to stdout (exit 0); --mode defaults
# to NURSING_RECORD_TELEGRAPHIC, the only R1 mode
clinical-compiler compile input.jsonl --mode NURSING_RECORD_TELEGRAPHIC --output out.txt

# with an owner-authored policy seed (veto terms that must never be auto-confirmed)
clinical-compiler compile input.jsonl --policy-seed policy.json

# no --policy-seed runs the approved-empty policy (durable owner deferral)
```

A real round trip, using the committed golden fixture (`tests/golden/scenarios/pc1_unassessed_fc.input.jsonl`):

```console
$ cat input.jsonl
{"fact_id": "pc1-ta-1", "field_id": "TA", "raw_value": "120/80", "provenance": {"source_kind": "monitor", "source_ref": "m-9"}}
$ clinical-compiler compile input.jsonl
FC: unknown [not_assessed]
TA: 120/80 [present] [monitor m-9]
```

`FC` has no fact — it renders the explicit unassessed line `FC: unknown [not_assessed]` (never dropped, never rewritten as assessed absence). Every fact line carries its provenance: `{field}: {value} [{missingness}] [{source_kind} {source_ref}]`.

Diagnostics always go to **stderr**, one per line: `CODE: message (path)` (the ` (path)` suffix only when the diagnostic carries one). A failed run writes **nothing** to the document stream — no partial document, and `--output` is written atomically (`temp` + `fsync` + `os.replace`) so no partial file is ever visible.

---

## Diagnostics taxonomy

All 8 codes are **blocking** in R1 (no warnings). One invalid fact blocks the document — fail-closed whole-run.

| Code | Producing stage | Meaning |
|------|----------------|---------|
| `INPUT_CONTRACT_ERROR` | `input_validation` / adapter | Missing/unknown key, malformed JSON, undecodable bytes |
| `TYPE_ERROR` | `input_validation` | Conformant record, wrong `raw_value` type for `field_id` |
| `SEMANTIC_AMBIGUITY_BLOCK` | `semantic_normalization` | >1 admissible interpretation, no disambiguator |
| `POLICY_VIOLATION` | `admissibility` | Vetoed term (even at `CONFIRMED` — invariant is certainty-independent) |
| `PROVENANCE_ERROR` | `admissibility` | `source_fact_refs` unresolvable |
| `DOCUMENT_SELECTION_ERROR` | `document_selection` | No admissible entries for requested mode |
| `RENDER_ERROR` | `renderers/deterministic` | Internal inconsistency (defense-in-depth, injected fixtures) |
| `LINT_FAILURE` | `linter/conformance` | Rendered bytes violate mode rules |

---

## Exit codes

| Code | Class | Condition |
|------|-------|-----------|
| 0 | Success | Document emitted, diagnostics empty |
| 2 | Usage | argparse failure, missing/unreadable INPUT, unknown `--mode`, invalid `--policy-seed` |
| 3 | Input contract | `INPUT_CONTRACT_ERROR` present |
| 4 | Type | `TYPE_ERROR` present |
| 5 | Semantic ambiguity | `SEMANTIC_AMBIGUITY_BLOCK` present |
| 6 | Policy | `POLICY_VIOLATION` present |
| 7 | Provenance | `PROVENANCE_ERROR` present |
| 8 | Document selection | `DOCUMENT_SELECTION_ERROR` present |
| 9 | Render | `RENDER_ERROR` present |
| 10 | Lint | `LINT_FAILURE` present |
| 70 | Internal | Unexpected exception — fail-closed catch-all, never 0 |

Precedence when multiple categories are present: **minimum code among 3–10 in stage order**.

---

## Configuration

| Concern | Mechanism | Notes |
|---------|-----------|-------|
| Document mode | `--mode` | R1: only `NURSING_RECORD_TELEGRAPHIC` (the default; unknown mode → exit 2 before any compile) |
| Clinical policy | `--policy-seed PATH` | Owner-authored JSON `{"terms": [...]}`; flag absent → approved-empty policy citing recorded deferral; a given-but-invalid seed → `UNRESOLVED_POLICY`, exit 2 |
| Output | `--output PATH` or stdout | File writes are atomic (`temp + fsync + os.replace` + dir fsync), never partial |
| Input | `INPUT` path | JSONL feed — one fact-record object per line, blank lines ignored; a top-level JSON array is rejected (`INPUT_CONTRACT_ERROR`) and non-UTF-8 bytes fault the whole feed; `-`/stdin deferred to R2 |

No environment variables, no config files, no network, no secrets.

---

## Testing

```bash
# full suite with branch coverage (gate: ≥ 95.0, frozen core keeps 100%)
uv run pytest --cov=clinical_compiler --cov-report=term-missing --strict-markers
# strict typing
uv run mypy --strict src
# lint
uv run ruff check src tests

# determinism gate: byte-identical output across fresh interpreters
uv run pytest tests/unit/test_integration_golden_determinism.py -v
```

---

## SDD / OpenSpec

- Normative domain specifications live under `openspec/specs/` (`clinical-fact-model`, `input-contract`, `pipeline-passes`, `diagnostics-policy`, `determinism-rendering`, `cli-surface`, `phase0-verification`).
- Archived historical R1 design and audit records reside in `openspec/changes/archive/2026-08-29-clinical-compiler-r1/`.

---

## Contributing

This repository follows SDD: changes land as `openspec/changes/<name>/` bundles (proposal → design → tasks → specs) with hash-bound approval before execution. Keep `core` additive-only with recorded justification; preserve zero runtime dependencies, `mypy --strict`, and branch coverage ≥ 95.

---

## License

No license file is committed yet. All rights reserved until a license is chosen and added.
