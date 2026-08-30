# AGENTS.md

Repository-level instructions for Codex / Pi agents working in `compilador_clinico` (`clinical-record-compiler` v0.1.0).

---

## ⚠️ CRITICAL: READ FIRST — DO NOT PROCEED WITHOUT THESE (10 min total)

Assuming anything about input format, policy, or pipeline order without these files is a breach of the SDD contract.

**Read in this order:**

0. **`README.md` ← START HERE (3 min)**
   - What: Project purpose, IR ladder, contracts, frozen CLI surface.
   - Contains: Why certainty/missingness/provenance are never conflated; determinism invariants.
   - Skip → you will break the fail-closed gate or reintroduce guessed certainty.

1. **`openspec/changes/clinical-compiler-r1/design.md` (5 min)**
   - What: Normative technical design — fault corpus (12+2), exit-code table, determinism mechanism, policy state machine, module map.
   - Contains: Decisions D1–D10, pipeline sequence diagram, `StageResult` contract.
   - Skip → you will implement the wrong blocking granularity or violate the dependency rule `cli → pipeline → passes → core`.

2. **`openspec/changes/clinical-compiler-r1/tasks.md` (2 min)**
   - What: Derived execution plan — phase gates, file-level writes per phase.
   - Contains: Phase 0–4 gates (computed PASS, never asserted), side-effect budget.
   - Skip → you will write outside the allowed phase or miss the approval gate.

### If You Skip

⛔ YOU WILL:
- Mutate the frozen core (`src/clinical_compiler/core/` is additive-only with recorded justification — only `CanonicalClinicalIR` is allowed) and invalidate the `c6578b6` baseline.
- Add a runtime dependency and break the `dependencies == []` gate.
- Ship a silently-empty `NEVER_AUTO_TERMS` without `DEFERRED_BY_OWNER` and violate D7 (`UNRESOLVED_POLICY` must BLOCK).
- Emit a non-deterministic document (locale, `hash()` order, `datetime.now`) and fail the SHA-256 determinism gate.

✅ INSTEAD: Read the 3 files (10 min), then start. Reference them for every edit.

---

## Build and Test

All commands are verified against `pyproject.toml` / `uv.lock`. Do not invent `npm` scripts — this repo has none.

```bash
# install (editable) + dev tools — stdlib-only runtime, dev: pytest/pytest-cov/ruff/mypy
uv sync --group dev

# tests — branch coverage gate ≥ 95.0 (frozen core keeps 100%)
uv run pytest --cov=clinical_compiler --cov-report=term-missing --strict-markers
uv run pytest -q                          # fast feedback without coverage

# lint / typecheck — both must exit 0
uv run ruff check src tests
uv run mypy --strict src
```

Success criteria before completion: `pytest` 0 failed + coverage ≥95 + `mypy --strict` 0 + `ruff check` 0. A non-zero is BLOCKED, never PASS.

## Working Rules

- Modify only files needed for the task and allowed by the current phase (`tasks.md` + `design.md` §File Changes). Phase 0 is read-only.
- Keep changes minimal and reversible. Prefer pure functions returning `StageResult[Out]` (`pipeline_types.StageResult` — passes never import `pipeline`).
- Respect the dependency rule: `cli → pipeline → {passes, renderers, linter} → {adapters(contract), pipeline_types} → core{ir, diagnostics, policy} → types`. Nothing imports `cli`/`pipeline` except `__main__`.
- Preserve invariants: zero runtime dependencies; `tuple` containers; explicit codepoint sort `(field_id, clinical_fact_id)`; UTF-8 / `\n` only; no `datetime`/`random`/`locale` in output paths.
- Never add `NEVER_AUTO_TERMS` entries without an owner-authored `--policy-seed` (`{"terms": [...]}`) or a recorded `DEFERRED_BY_OWNER`.
- Validate changes before claiming completion — run the four checks above and show output.
- Do not create venvs, install packages, write outside the repo, or use network — see Side-Effect Budget in `proposal.md`.

## Architecture

- **Pattern:** Functional core, imperative shell. Hexagonal target — `core` is a stdlib-only leaf; I/O lives at `adapters/` (driving) and `renderers/`+`linter`+`cli` (driven); `pipeline.py` is the composition root.
- **IR ladder:** `SourceFactIR → CanonicalClinicalFact → CanonicalClinicalIR → DocumentIR → bytes`. `DocumentIR.entries` store IDs + `presentation_role` only — single authority per fact.
- **Pipeline order (fixed):** `input_validation → semantic_normalization → admissibility → document_selection` → emission gate (fail-closed whole-run: ANY diagnostic blocks document emission) → `deterministic render → conformance lint`. Every stage runs on survivors only, quarantines per-fact, accumulates diagnostics.
- **Contracts:** `adapters/contract.py` is the single source of truth (`REQUIRED_FACT_KEYS`, `ALLOWED_FACT_KEYS`, `RawScalar = str|int|float|None`, `bool` excluded). `source_asserted_certainty` is preserved verbatim, never overwrites `compiler_assigned_certainty` (R1: always `UNRESOLVED`).
- **SDD governance:** `GOVERNED` profile (contract 0.3). No execution without a hash-bound approval record (`APPROVAL-PHASE0.md`) binding the 10 bundle file SHA-256s and naming the approved phase(s). Executor never authors policy content or input-format selection.

## Red Flags

| Violation | Why It's Wrong | Fix |
|-----------|----------------|-----|
| `bool` `raw_value` passing as numeric | `bool <: int` in Python — contract explicitly excludes `bool` | Reject in `input_validation`; map to `TYPE_ERROR` |
| Inferring `CONFIRMED`/`PROBABLE` from `source_kind` | CRC-001/002: `source_kind` informs provenance only, certainty stays `UNRESOLVED` in R1 | Keep adjudicated interpretation table; retain enum members without producing them |
| Mutating `core/policy.NEVER_AUTO_TERMS` at import time | D7: veto set is runtime-injected `frozenset[str]` | Pass `veto_terms` to `admissibility()`; load via `adapters/seed.py` |
| Unsorted `dict`/`set` iteration reaching output | Latent nondeterminism across `PYTHONHASHSEED` | Use `tuple` + codepoint sort; verify with cross-run `python -I` gate |
| Writing a partial document on failure | Violates `diagnostics on stderr, document only at exit 0` | Gate emission on empty diagnostic set; write atomically (`temp + os.replace`) |

## References

- `README.md` — overview, install, quick start, diagnostics/exit-code tables
- `docs/architecture.md` — pipeline, contracts, invariants (filled at Phase 4; currently 0 bytes — do not duplicate here)
- `openspec/changes/clinical-compiler-r1/` — `proposal.md` (scope/budget) → `design.md` (normative) → `tasks.md` (plan) → `specs/*` (7 domain specs)
- `openspec/contracts/clinical-compiler-handoff-drive-mirror-20260828/` — execution contract 0.3 + lineage
- `src/clinical_compiler/core/` — frozen baseline; `src/clinical_compiler/adapters/contract.py` — frozen input contract

Progressive disclosure: keep this file <150 lines. Link to docs above instead of embedding them. Re-audit when `pyproject.toml`, `design.md`, or the module map changes.
