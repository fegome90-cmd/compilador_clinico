# Phase 0 — BASELINE_ANOMALIES (Task 0.3)

Change: `clinical-compiler-r1` | Computed: 2026-08-29 (runs 0/01–0/08) | Repo HEAD: `c6578b6`.

## Gate formula (per proposal Success Criterion 1 / phase0-verification spec / tasks 0.3)

```text
BASELINE_ANOMALIES = (number of proposal "Current Baseline" claims CONTRADICTED by observation)
                   + (number of claims whose verification outcome is UNKNOWN)
```

`0` → PASS; `>0` → BLOCKED (contradictions and UNKNOWNs enumerated separately). Per tasks.md 0.3,
the KNOWN DRIFT items below are verified and documented, NOT fixed, and **whether the drift counts
toward `BASELINE_ANOMALIES` is adjudicated by the decision owner at the gate**
(`risk_policy: ask_on_risk`). Both the strict computed value and the adjudication dependency are
reported — the executor asserts neither a PASS nor an adjudication.

## Claim-by-claim verification

Proposal "Current Baseline (verified 2026-08-28)" claims, each checked against direct observation
(runs 0/01–0/08; file reads; `rg`/`wc`/`eza`/`fd` inspections; evidence in
`evidence-before.md` + `baseline-verification.md` + `hygiene-inventory.md`):

| # | Proposal claim | Observation | Verdict |
|---|---|---|---|
| 1a | Core green: 29/29 tests pass | run 0/06: collected 29, 29 passed, exit 0 | **CONFIRMED** |
| 1b | 100% branch coverage of implemented core | run 0/06: core modules 100% (49 stmts, 0 miss, 0 branch arcs — core is branch-free today) | **CONFIRMED** |
| 1c | `mypy --strict` clean | run 0/07: exit 0, "no issues found in 15 source files" (strict via pyproject) | **CONFIRMED** |
| 1d | `ruff` clean | run 0/08: exit 0, "All checks passed!" | **CONFIRMED** |
| 1e | `core/{types,ir,diagnostics,policy}.py` complete, documented, annotated | all four non-empty with docstrings/annotations (types.py 70+ lines; policy.py, diagnostics.py, ir.py verified by read/hash) | **CONFIRMED** |
| 2a | Scaffold empty: 11 zero-byte source files | 11 zero-byte source files observed under `src/clinical_compiler/`: 4 passes + `linter/conformance.py` + `renderers/deterministic.py` + 4 package `__init__.py` (`passes`, `linter`, `renderers`, `core`) + `adapters/README.md` (a 12th zero-byte file, `py.typed`, is a PEP 561 marker, not a source file) | **CONFIRMED** (counting reconciliation documented in `scaffold-inventory.md`) |
| 2b | `adapters/` has no Python at all, not a package | `adapters/` contains only zero-byte `README.md`; no `__init__.py`; mypy counted 15 source files (none in adapters) | **CONFIRMED** |
| 3 | No runtime glue: no pipeline runner, no CLI, no `[project.scripts]` | no `pipeline.py`/`cli.py` in manifest; `pyproject.toml` has no `[project.scripts]` | **CONFIRMED** |
| 4a | No test infrastructure: **no `conftest.py`** | `tests/conftest.py` EXISTS (untracked; 51 lines; `make_provenance` + `make_clinical_value` factories) — KNOWN DRIFT G-2 | **CONTRADICTED (C-1)** |
| 4b | No test infrastructure: **no `tests/fixtures/`** | `tests/fixtures/` EXISTS as an empty directory (untracked-in-git; empty dirs are invisible to git, so the claim holds vs commit `c6578b6` but not vs the working tree) — KNOWN DRIFT G-2 | **CONTRADICTED (C-2)** |
| 4c | No test infrastructure: no golden files | `tests/golden/` exists EMPTY — zero golden files present | **CONFIRMED** (empty-dir existence noted) |
| 4d | No test infrastructure: no integration tests | only `tests/unit/` test files exist | **CONFIRMED** |
| 4e | No test infrastructure: **inline literals only** | `tests/unit/test_ir.py` is MODIFIED vs `c6578b6` (uncommitted) to consume the `conftest.py` factories — shared fixture infrastructure beyond inline literals exists in the working tree — KNOWN DRIFT G-2/G-3 family | **CONTRADICTED (C-3)** |
| 5 | Docs empty: `README.md` and `docs/architecture.md` 0 bytes | both 0 bytes (`wc -c` = 0; empty-file SHA-256 `e3b0c442…`) | **CONFIRMED** |
| 6a | `NEVER_AUTO_TERMS` is an empty frozenset | `core/policy.py` line 3: `NEVER_AUTO_TERMS: frozenset[str] = frozenset()` | **CONFIRMED** |
| 6b | `TYPE_ERROR` and `PROVENANCE_ERROR` have no producing stage | `rg` in `src/`: both appear ONLY as enum members in `core/diagnostics.py` (lines 15, 21); every pass/linter/renderer module is 0 bytes | **CONFIRMED** |
| 6c | `test_policy.py` contains a tautological test | `test_never_auto_terms_vetoes_membership` — both if/else branches assign `vetoed` from the identical membership test; the assertion reduces to `x is x` (quoted in `hygiene-inventory.md`) | **CONFIRMED** |
| 6d | `.gitignore` misses `.coverage` and `.mimosa/` | `.gitignore` read: neither entry present (both paths currently untracked) | **CONFIRMED** |
| 6e | No CI | no `.github/`/`.gitlab/` anywhere in the repository | **CONFIRMED** |
| 7 | Zero runtime dependencies (dev-only: pytest, pytest-cov, ruff, mypy) | `pyproject.toml` `[project]` declares NO `dependencies` key; venv site-packages contains only the dev toolchain + transitive deps + the editable project itself | **CONFIRMED** |

## Contradictions (enumerated separately)

- **C-1 — "no `conftest.py`" is contradicted.** `tests/conftest.py` exists in the working tree (untracked at `c6578b6`; 51 lines defining `make_provenance` and `make_clinical_value` factory fixtures). Pre-declared as KNOWN DRIFT G-2 in tasks.md; `design.md` File Changes already reconciles it ("`tests/conftest.py` — Modify — extend existing factories").
- **C-2 — "no `tests/fixtures/`" is contradicted (working-tree reading).** `tests/fixtures/` exists as an empty directory. Git cannot track empty directories, so against the commit `c6578b6` the claim is true while against the working tree it is false. `tests/golden/` exists equally empty (claim 4c "no golden files" remains literally true — zero golden files).
- **C-3 — "inline literals only" is contradicted.** The uncommitted modification to `tests/unit/test_ir.py` (vs `c6578b6`: 4 test signatures changed to inject `make_provenance`/`make_clinical_value`, local builder removed, `--strict-markers` + markers added to `pyproject.toml`) means the working-tree suite already depends on shared fixture infrastructure. Same drift family as C-1 (the conftest is its counterpart).

Related drift NOT rising to a claim contradiction (documented for the gate): untracked `.pi/`,
`_ctx/` (AI-runtime artifacts; G-4 covers `.pi/`; `_ctx/` additionally observed), `.mimosa/`,
`.coverage`, and the whole `openspec/` tree — no baseline claim speaks about them, so they are
observations, not contradictions.

## UNKNOWN outcomes (enumerated separately)

**None.** All three verification commands ran to completion in the existing provisioned
environment with `--no-sync` (exits 0/0/0 — `baseline-verification.md`). No command required an
install or environment change; no evidence item was unobtainable (the installed-package listing
was captured via an allowlisted read-only site-packages directory enumeration instead of a
non-allowlisted venv-query command — evidence obtained, method documented).

## Computed gate value

```text
contradicted_claims = 3   (C-1, C-2, C-3)
unknown_outcomes    = 0
BASELINE_ANOMALIES  = 3 + 0 = 3      → 3 > 0  →  Phase 0 baseline gate: BLOCKED (as computed)
```

### Adjudication dependency (fail-closed presentation)

All three counted contradictions are the pre-declared KNOWN DRIFT (tasks.md G-2/G-3), which
tasks.md 0.3 explicitly reserves for owner adjudication at the gate. Therefore:

- **Strict computed reading (fail-closed default):** `BASELINE_ANOMALIES = 3` → gate **BLOCKED**;
  the enumerated list above is the adjudication material.
- **If the owner adjudicates the known drift as reconciled/not-counting** (e.g. accepting
  `design.md` File Changes' "Modify — extend existing conftest" as the controlling description,
  and the empty-dir/inline-literal wording as superseded): the remaining count is
  `0 + 0 = 0` → gate PASS.

The executor records both readings and claims NEITHER. Under the fail-closed default the gate
stands BLOCKED until the owner adjudicates. Every non-drift claim (1a–1e, 2a–2b, 3, 4c, 4d, 5,
6a–6e, 7) was independently re-verified CONFIRMED this run.
