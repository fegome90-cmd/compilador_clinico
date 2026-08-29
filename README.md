# Clinical Record Compiler — `compilador_clinico`

> **One-line purpose:** Compile scattered per-source clinical facts into a single deterministic, fail-closed, fully traceable clinical document.

Compiler of clinical records (`clinical-record-compiler` v0.1.0). Turns scattered per-source clinical readings — `TA 120/80`, `FC 72`, lab values, nursing notes, expressed as **structured JSONL facts** (R1 accepts no free text) — into a safe `NURSING_RECORD_TELEGRAPHIC` document without losing the three things that make a clinical document trustworthy: **certainty**, **missingness** (assessed-absent vs never-assessed), and **provenance**.

> **Status: WIP — R1 under SDD.** Phases 0–3 are gated and closed (input contract → passes → renderer/linter/determinism); Phase 4 (runner, CLI, docs) is landing. The end-to-end `compile` CLI is implemented and verified against the committed goldens (suite: 337 passed, 100% branch coverage, `mypy --strict`, `ruff` clean at Phase-4 start). API and contracts below reflect the committed implementation.

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

**Policy (D7):** `admissibility` takes `veto_terms: frozenset[str]` explicitly; the runner loads it from `--policy-seed PATH` (`{"terms": [...]}`). The flag **absent** resolves to the approved-empty policy, citing the durable owner decision (`APPROVAL-PHASE1.md`, `POLICY_SEED_DECISION = DEFERRED_BY_OWNER`) — the FC-12 production path, an empty set that always traces to a recorded ruling. A **given** seed that is missing, unreadable, malformed, or wrongly shaped resolves `UNRESOLVED_POLICY` → CLI usage exit 2 — never empty-set-and-continue, and never an uncited empty set (an approved-empty policy without a `DEFERRED_BY_OWNER` citation is unrepresentable by construction).

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
│   ├── structured_feed.py    # JSONL bytes → per-record contract evaluations (branch A)
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
                              # integration suites (test_pipeline, test_cli, test_integration_*)

openspec/changes/clinical-compiler-r1/  # SDD bundle: proposal → design → tasks → specs
docs/architecture.md           # architecture record (pipeline, contracts, invariants, lineage)
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

### 3. CLI — `clinical-compiler compile` (implemented, frozen surface)

```bash
# happy path — deterministic document to stdout (exit 0); --mode defaults
# to NURSING_RECORD_TELEGRAPHIC, the only R1 mode
clinical-compiler compile input.jsonl --mode NURSING_RECORD_TELEGRAPHIC --output out.txt

# with an owner-authored policy seed (veto terms that must never be auto-confirmed)
clinical-compiler compile input.jsonl --policy-seed policy.json
# policy.json shape: {"terms": ["<term-a>", "<term-b>"]}

# no --policy-seed at all runs the approved-empty policy (durable owner
# deferral recorded in APPROVAL-PHASE1.md) — same clean compile
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

Precedence when multiple categories are present: **minimum code among 3–10 in stage order** (documented order above, not enum declaration order). The mapping is a pure, order-independent function of the diagnostic SET — identical failing input always yields the identical exit code.

Enumeration is **full, never fail-fast**: a feed-level or record-level fault still runs every later stage on the (possibly empty) survivor set, so one run can report several categories. A `raw_value: true` for `FC`, for example, yields both `TYPE_ERROR` and — because no fact survives to selection — `DOCUMENT_SELECTION_ERROR` on stderr, and exits `4` (the minimum stage-order code).

---

## Configuration

| Concern | Mechanism | Notes |
|---------|-----------|-------|
| Document mode | `--mode` | R1: only `NURSING_RECORD_TELEGRAPHIC` (the default; unknown mode → exit 2 before any compile) |
| Clinical policy | `--policy-seed PATH` | Owner-authored JSON `{"terms": [...]}`; flag absent → approved-empty policy citing the recorded `DEFERRED_BY_OWNER` (APPROVAL-PHASE1.md); a given-but-invalid seed → `UNRESOLVED_POLICY`, exit 2 |
| Output | `--output PATH` or stdout | File writes are atomic (`temp + fsync + os.replace` + dir fsync), never partial |
| Input | `INPUT` path | JSONL feed — one fact-record object per line, blank lines ignored; a top-level JSON array is rejected (`INPUT_CONTRACT_ERROR`, FC-03) and non-UTF-8 bytes fault the whole feed; `-`/stdin deferred to R2 |

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
uv run pytest tests/unit/test_integration_golden_determinism.py -v
```

Conventions: `pytest.mark.unit` / `integration` / `slow`; factories in `tests/conftest.py`; golden corpus in `tests/golden/` (`manifest.json` + `scenarios/` — each fixture set's input and document SHA-256) with independently authored expected samples under `tests/golden/independent/` (implementation-generated goldens alone are `DEGRADED` evidence; the committed corpus is `EVIDENCE_INTEGRITY = VALID`, corroborated by the independent sample).

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

`CONTRACT: Mapping[str, FieldContract]` (R1: `FC → (int, float)`, `TA → (str,)` — exact runtime types), `REQUIRED_RECORD_KEYS` / `OPTIONAL_RECORD_KEYS` / `ALLOWED_RECORD_KEYS`, `REQUIRED_PROVENANCE_KEYS` (exactly `source_kind` + `source_ref`), `ALLOWED_SOURCE_KINDS` (`monitor`, `lab`, `clinical_note`), `map_record(record) -> ContractEvaluation` (fact XOR diagnostic), `StructuredFeedFact` (mapped `SourceFactIR` + verbatim `source_asserted_certainty`).

### `clinical_compiler.adapters.seed` and `clinical_compiler.pipeline_types`

`PolicyResolution` (state `POPULATED` / `APPROVED_EMPTY_BY_DEFERRAL` / `UNRESOLVED_POLICY`, construction-time legal-shape invariants), `load_policy_seed(path)`, `approved_empty_by_deferral(citation)` (requires a `DEFERRED_BY_OWNER` citation), `PolicySeedFault` (typed fault reasons). `pipeline_types.StageResult[_T]` — the leaf stage contract (`admitted` + `diagnostics` tuples), re-exported by `pipeline.py`.

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

- **R1 (current):** Phases 0–4 — input contract freeze → 4 passes → renderer/linter/determinism → runner/CLI/docs. Phases 0–3 are gated and closed; Phase 4 is landing. Single mode `NURSING_RECORD_TELEGRAPHIC`, no stdin, no `--json`, no conflict resolution (ambiguity blocks).
- **R2 candidates (not in scope):** free-text telegraphic micro-grammar (branch B), stdin/`--json` diagnostics, `check`-only subcommand, new document modes, bounded `ClinicalValue.value` type narrowing (`r2_debt` — `Any` stays in R1), CI.

---

## Contributing

This repository follows SDD: changes land as `openspec/changes/<name>/` bundles (proposal → design → tasks → specs) with hash-bound approval before execution. Keep `core` additive-only with recorded justification; preserve zero runtime dependencies, `mypy --strict`, and branch coverage ≥ 95.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `INPUT_CONTRACT_ERROR` on valid-looking JSON | Unknown/extra key, `bool` `raw_value`, missing `provenance` sub-key | Validate against `adapters/contract.py` — `ALLOWED_RECORD_KEYS` is closed; `bool` is intentionally rejected |
| `SEMANTIC_AMBIGUITY_BLOCK` with two facts for same `field_id` | Equal-authority conflict, no disambiguator — R1 never picks | Provide a single authoritative fact or a disambiguator (R1 has no resolution rule) |
| `POLICY_VIOLATION` despite low certainty | Veto is certainty-independent — even `CONFIRMED` is blocked | Remove term from input or update owner-approved `--policy-seed` |
| `UNRESOLVED_POLICY` / exit 2 with a seed given | The given seed file is missing, unreadable, malformed JSON, or not exactly `{"terms": [...]}` with string terms | Fix or point `--policy-seed` at a valid owner-authored seed; omitting the flag entirely runs the approved-empty policy (recorded owner deferral) |
| Determinism gate fails | Unsorted iteration, locale formatting, `hash()`-dependent ordering | Use `tuple` + explicit codepoint sort key, locale-free `str(int)`, canonical JSON |

---

## License

No license file is committed yet. All rights reserved until a license is chosen and added.
