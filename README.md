# Clinical Record Compiler — `compilador_clinico`

> **One-line purpose:** Compile scattered per-source clinical facts into a single deterministic, fail-closed, fully traceable clinical document.

Compiler of clinical records (`clinical-record-compiler` v0.1.0). Turns telegraphic Spanish notes and machine readings scattered across sources — `TA 120/80`, `FC 72`, lab values, nursing notes — into a safe `NURSING_RECORD_TELEGRAPHIC` document without losing the three things that make a clinical document trustworthy: **certainty**, **missingness** (assessed-absent vs never-assessed), and **provenance**.

> **Status: WIP — R1 under SDD.** Core is frozen green (29/29 tests, 95%+ branch coverage, `mypy --strict`, `ruff` clean). Pipeline passes, renderer, linter and CLI are scaffolded and being implemented under `openspec/changes/clinical-compiler-r1`. API and contracts below reflect the *current* committed core plus the *frozen design* for R1 — runnable end-to-end `compile` ships at Phase 4.

---

## Why this exists

Manual or lossy scripts that compile clinical sources typically drop:

1. **How certain** each value is (`CONFIRMED` vs `UNRESOLVED` vs `CANDIDATE` — not guessed from `source_kind`).
2. **Whether a missing value was assessed absent** (`MISSING`/`NOT_APPLICABLE`) or **never assessed** (`UNKNOWN`/`NOT_ASSESSED`) — conflating them is a safety error.
3. **Where each value came from** — every rendered value traces back to its `SourceFactIR`(s) via `source_fact_refs`.

This compiler enforces those invariants by construction: per-fact quarantine, whole-run fail-closed gating (one invalid fact blocks document emission), deterministic byte-identical output, zero runtime dependencies.

---

## Architecture

```
bytes (JSON) ──▶ adapters/contract + structured_feed ──▶ SourceFactIR
                                                        │
                              input_validation ──────────┤── INPUT_CONTRACT_ERROR / TYPE_ERROR
                            semantic_normalization ──────┤── SEMANTIC_AMBIGUITY_BLOCK
                                   admissibility ───────┤── POLICY_VIOLATION / PROVENANCE_ERROR
                              document_selection ────────┤── DOCUMENT_SELECTION_ERROR
                                                         ▼
                                              emission gate (fail-closed)
                                                         │
                                    renderers/deterministic ── RENDER_ERROR
                                         linter/conformance ── LINT_FAILURE
                                                         │
                                                         ▼
                                              Document bytes (UTF-8, \n)
                                              diagnostics on stderr (one per line)
```

**IR ladder (frozen core, `src/clinical_compiler/core/`):**

| IR | Module | Role |
|----|--------|------|
| `SourceFactIR` | `core/ir.py` | Fact verbatim from one source (`fact_id`, `field_id`, `raw_value`, `provenance`) |
| `CanonicalClinicalFact` | `core/ir.py` | Normalized fact (`ClinicalValue` + `source_fact_refs`) |
| `CanonicalClinicalIR` | `core/ir.py` | Aggregate `facts: tuple[CanonicalClinicalFact, ...]` (R1 additive, CRC-003) |
| `DocumentIR` | `core/ir.py` | Ordered `DocumentEntry`s referencing canonical facts by ID + `document_mode` |
| `ClinicalValue` | `core/types.py` | `value: Any` + `Certainty` + `Missingness` + `Provenance` |
| `Diagnostic` | `core/diagnostics.py` | `code: DiagnosticCode` + `message` + optional `path` |
| `NEVER_AUTO_TERMS` | `core/policy.py` | `frozenset[str]` — veto set injected at runtime, never auto-confirmed |

Every stage is a **pure function** `tuple[In, ...] -> StageResult[Out]` (`pipeline_types.StageResult` — `admitted` + `diagnostics`). All I/O lives at the edges (`adapters/`, `renderers/`, `cli.py`); `pipeline.py` composes stages in fixed taxonomy order.

**Determinism (frozen):** `tuple` containers, explicit codepoint sort key `(field_id, clinical_fact_id)`, locale-free formatting, UTF-8/`\n`-only, canonical `json.dumps(sort_keys=True, ...)`, cross-run SHA-256 gate, golden files under `tests/golden/` (with `tests/golden/independent/` for independently authored expected output).

**Policy (D7):** `admissibility` takes `veto_terms: frozenset[str]` explicitly; the runner loads it from `--policy-seed PATH` (`{"terms": [...]}`). Missing seed without a recorded owner decision `DEFERRED_BY_OWNER` → `UNRESOLVED_POLICY` → gate BLOCKED (never silently empty).

---

## Project structure

```
src/clinical_compiler/
├── core/                     # frozen leaf — stdlib only
│   ├── types.py              # Certainty | Missingness | Provenance | ClinicalValue
│   ├── ir.py                 # SourceFactIR → CanonicalClinicalFact → DocumentIR
│   ├── diagnostics.py        # DiagnosticCode (8) | Diagnostic
│   └── policy.py             # NEVER_AUTO_TERMS
├── adapters/
│   ├── contract.py           # frozen declarative input-contract table (single source of truth)
│   ├── structured_feed.py    # bytes → SourceFactIR (branch A)
│   ├── seed.py               # --policy-seed loader (structural validation only)
│   └── free_text.py          # only if Phase 0 selects free-text branch
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
├── unit/                     # per-pass admitted/quarantined + interpretation table
└── integration/              # pipeline.run + cli.main via subprocess (exit codes)

openspec/changes/clinical-compiler-r1/  # SDD bundle: proposal → design → tasks → specs
docs/architecture.md           # pipeline, contracts, invariants (filled at Phase 4)
```

Dependency rule: `cli → pipeline → {passes, renderers, linter} → {adapters(contract), pipeline_types} → core{ir, diagnostics, policy} → types`. `core` never imports from new packages.

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

# install (editable) + dev tools
uv sync --group dev
# or
uv pip install -e ".[dev]"  # if you add [project.optional-dependencies]

# verify baseline (must be green before any change)
uv run pytest --cov=clinical_compiler --cov-report=term-missing
uv run mypy --strict src
uv run ruff check src tests
```

`pyproject.toml` declares `tool.setuptools.packages.find.where = ["src"]` and `tool.pytest.ini_options.pythonpath = ["src"]`.

---

## Quick start

### 1. Core types (available today)

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

Structured facts at the boundary are `TypedDict`s — validated verbatim, never normalized by the adapter:

```python
from clinical_compiler.adapters.contract import (
    StructuredFactInput, ProvenanceInput,
    REQUIRED_FACT_KEYS, ALLOWED_FACT_KEYS,
)

record: StructuredFactInput = {
    "fact_id": "fact-1",
    "field_id": "FC",
    "raw_value": 72,                          # RawScalar = str | int | float | None (bool excluded)
    "provenance": ProvenanceInput(source_kind="monitor", source_ref="mon-001"),
    # optional: "source_asserted_certainty": "probable"  # preserved verbatim, never overwrites compiler certainty
}
```

Rules: `fact_id`, `field_id`, `raw_value`, `provenance` required; only `source_asserted_certainty` is optional; unknown keys → `INPUT_CONTRACT_ERROR`; `raw_value: bool` is rejected (even though `bool <: int` in Python).

### 3. CLI — `clinical-compiler compile` (ships at Phase 4, frozen surface)

```bash
# happy path — deterministic document to stdout (exit 0)
uv run clinical-compiler compile input.json --mode NURSING_RECORD_TELEGRAPHIC --output out.txt

# with owner-authored policy seed (veto terms that must never be auto-confirmed)
uv run clinical-compiler compile input.json --policy-seed policy.json --output out.txt
# policy.json shape: {"terms": ["<term-a>", "<term-b>"]}

# diagnostics always on stderr, one per line:  CODE: message (path)
# failed run writes NOTHING to the document stream — no partial document
```

`input.json` is a JSON array of `StructuredFactInput` records. See `tests/fixtures/` for the frozen fault corpus (12 fault classes + 2 positive controls) once Phase 1 lands.

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

## Exit codes (frozen, `cli-surface`)

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

Precedence when multiple categories are present: **minimum code among 3–10 in stage order** (documented order above, not enum declaration order).

---

## Configuration

| Concern | Mechanism | Notes |
|---------|-----------|-------|
| Document mode | `--mode` | R1: only `NURSING_RECORD_TELEGRAPHIC` |
| Clinical policy | `--policy-seed PATH` | Owner-authored JSON `{"terms": [...]}`; absent seed with no recorded `DEFERRED_BY_OWNER` → `UNRESOLVED_POLICY` (BLOCKED) |
| Output | `--output PATH` or stdout | File writes are atomic (`temp + os.replace`), never partial |
| Input | `INPUT` path | JSON array of `StructuredFactInput`; `-`/stdin deferred to R2 |

No environment variables, no config files, no network, no secrets.

---

## Testing

```bash
# full suite with branch coverage (gate: ≥ 95.0, frozen core keeps 100%)
uv run pytest --cov=clinical_compiler --cov-report=term-missing --strict-markers
# strict typing
uv run mypy --strict
# lint
uv run ruff check src tests

# determinism gate (Phase 3): byte-identical output across fresh interpreters
# python -I + PYTHONHASHSEED=0 vs random — SHA-256 equality vs committed golden digest
uv run pytest tests/integration/test_determinism.py -v
```

Conventions: `pytest.mark.unit` / `integration` / `slow`; factories in `tests/conftest.py`; golden digests in `tests/golden/` (implementation-generated goldens are `DEGRADED` evidence — at least one sample under `tests/golden/independent/` must be independently authored by the decision owner).

---

## API reference (core — stable)

### `clinical_compiler.core.types`

| Symbol | Kind | Notes |
|--------|------|-------|
| `Certainty` | `StrEnum` | `CANDIDATE`, `UNRESOLVED`, `LIKELY`, `UNLIKELY`, `CONFIRMED`, `PROBABLE`, `AMBIGUOUS` — R1 production: only `UNRESOLVED` is produced; others retained for compatibility (`RETAIN_FOR_COMPATIBILITY`) |
| `Missingness` | `StrEnum` | `UNKNOWN`, `PRESENT`, `MISSING`, `NOT_ASSESSED`, `NOT_APPLICABLE` — `UNKNOWN`/`NOT_ASSESSED` are unassessed, never conflated with assessed absence |
| `Provenance` | `@dataclass(frozen=True)` | `source_kind: str`, `source_ref: str` |
| `ClinicalValue` | `@dataclass(frozen=True)` | `value: Any`, `certainty: Certainty`, `missingness: Missingness`, `provenance: Provenance` |

### `clinical_compiler.core.ir`

| Symbol | Kind | Notes |
|--------|------|-------|
| `SourceFactIR` | frozen dataclass | `fact_id`, `field_id`, `raw_value: object`, `provenance` |
| `CanonicalClinicalFact` | frozen dataclass | `clinical_fact_id`, `field_id`, `value: ClinicalValue`, `source_fact_refs: tuple[str, ...]` |
| `CanonicalClinicalIR` | frozen dataclass | `facts: tuple[CanonicalClinicalFact, ...]` — explicit aggregate (R1 additive, CRC-003) |
| `DocumentIR` | frozen dataclass | `document_mode: str`, `entries: tuple[DocumentEntry, ...]` — never stores values |
| `DocumentEntry` | frozen dataclass | `clinical_fact_ref: str`, `presentation_role: str` |

### `clinical_compiler.core.diagnostics`

| Symbol | Kind |
|--------|------|
| `DiagnosticCode` | `StrEnum` — 8 members (see taxonomy table) |
| `Diagnostic` | `@dataclass(frozen=True, slots=True)` — `code`, `message`, `path: str \| None` |

### `clinical_compiler.core.policy`

| Symbol | Kind |
|--------|------|
| `NEVER_AUTO_TERMS` | `frozenset[str]` — frozen empty default; R1 injects via `admissibility(..., veto_terms)` |

### `clinical_compiler.adapters.contract`

`StructuredFactInput` / `ProvenanceInput` (`TypedDict`), `RawScalar = str | int | float | None`, `REQUIRED_FACT_KEYS` / `OPTIONAL_FACT_KEYS` / `ALLOWED_FACT_KEYS` / `REQUIRED_PROVENANCE_KEYS` / `ALLOWED_PROVENANCE_KEYS`.

---

## SDD / OpenSpec

R1 executes under `openspec/changes/clinical-compiler-r1/` with the **AI Work Agent Execution Contract 0.3** (`openspec/contracts/clinical-compiler-handoff-drive-mirror-20260828/`, `GOVERNED` profile).

- `proposal.md` — scope + decision envelope
- `design.md` — normative technical design (fault corpus, exit codes, determinism, policy state machine, module map)
- `tasks.md` — derived execution plan
- `specs/*` — seven domain specs (`clinical-fact-model`, `input-contract`, `pipeline-passes`, `diagnostics-policy`, `determinism-rendering`, `cli-surface`, `phase0-verification`)
- `outputs/inventory/` — Phase 0 baseline verification + input-contract + policy-seed dossiers

Activation: no phase executes without a durable hash-bound approval record (`APPROVAL-PHASE0.md`) naming the exact bundle SHA-256s, the approved phase(s), and the decision owner — executor is blocked otherwise.

---

## Roadmap

- **R1 (current):** Phases 0–4 — input contract freeze → 4 passes → renderer/linter/determinism → runner/CLI/docs. Single mode `NURSING_RECORD_TELEGRAPHIC`, no stdin, no `--json`, no conflict resolution (ambiguity blocks).
- **R2 candidates (not in scope):** free-text telegraphic micro-grammar (branch B), stdin/`--json` diagnostics, `check`-only subcommand, new document modes, bounded `ClinicalValue.value` type narrowing (`r2_debt` — `Any` stays in R1), CI.

---

## Contributing

This repository follows SDD: changes land as `openspec/changes/<name>/` bundles (proposal → design → tasks → specs) with hash-bound approval before execution. Keep `core` additive-only with recorded justification; preserve zero runtime dependencies, `mypy --strict`, and branch coverage ≥ 95.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `INPUT_CONTRACT_ERROR` on valid-looking JSON | Unknown/extra key, `bool` `raw_value`, missing `provenance` sub-key | Validate against `adapters/contract.py` — `ALLOWED_FACT_KEYS` is closed; `bool` is intentionally rejected |
| `SEMANTIC_AMBIGUITY_BLOCK` with two facts for same `field_id` | Equal-authority conflict, no disambiguator — R1 never picks | Provide a single authoritative fact or a disambiguator (R1 has no resolution rule) |
| `POLICY_VIOLATION` despite low certainty | Veto is certainty-independent — even `CONFIRMED` is blocked | Remove term from input or update owner-approved `--policy-seed` |
| `UNRESOLVED_POLICY` / gate BLOCKED with no seed | No owner decision recorded (`APPROVED` or `DEFERRED_BY_OWNER`) | Record decision in approval file; do not run with silently empty set |
| Determinism gate fails | Unsorted iteration, locale formatting, `hash()`-dependent ordering | Use `tuple` + explicit codepoint sort key, locale-free `str(int)`, canonical JSON |

---

## License

No license file is committed yet. All rights reserved until a license is chosen and added.
