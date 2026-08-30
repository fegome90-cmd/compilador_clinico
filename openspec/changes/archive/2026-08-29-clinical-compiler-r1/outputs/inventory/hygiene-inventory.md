# Phase 0 — Hygiene Inventory (Task 0.7)

Change: `clinical-compiler-r1` | Captured: 2026-08-29 (runs 0/01–0/05 + file reads + `rg` searches) | Repo HEAD: `c6578b6`.

## 1. Tautological test in `tests/unit/test_policy.py` (CONFIRMED)

`test_policy.py::test_never_auto_terms_vetoes_membership` — both branches of the `if/else`
assign `vetoed` from the identical membership expression, so the final assertion compares the
expression with itself (an `x is x` tautology). No mutation of veto membership or enforcement can
fail it. Quoted verbatim:

```python
def test_never_auto_terms_vetoes_membership() -> None:
    """Membership in NEVER_AUTO_TERMS must be a hard veto predicate."""
    term = "next-of-kin-consent"
    if term in NEVER_AUTO_TERMS:
        vetoed = True
    else:
        vetoed = term in NEVER_AUTO_TERMS
    assert vetoed is (term in NEVER_AUTO_TERMS)
```

(The sibling test `test_never_auto_terms_is_an_immutable_string_set` is content-bearing but, with
the set empty, weak.) Scheduled replacement: tasks 2.7 — content-bearing, mutation-sensitive
tests (any mutation of veto membership OR enforcement → ≥1 failure).

## 2. Orphan diagnostic codes (CONFIRMED)

`rg` over `src/` finds each code ONLY at its enum declaration in `core/diagnostics.py`; every
module that could produce them is zero-byte:

- `TYPE_ERROR` — sole occurrence: `src/clinical_compiler/core/diagnostics.py:15` (declaration). No producing stage. Elimination: Phase 1 (`passes/input_validation.py`, task 1.5).
- `PROVENANCE_ERROR` — sole occurrence: `src/clinical_compiler/core/diagnostics.py:21` (declaration). No producing stage. Elimination: Phase 2 (`passes/admissibility.py`, task 2.3).

Baseline gate 8 (diagnostics coverage) counts members with neither producing stage nor covering
test; both orphans are pre-declared baseline gaps, not new findings.

## 3. `.gitignore` gaps (CONFIRMED)

Current `.gitignore` (verbatim, 137 bytes):

```text
# Local Pi runtime state
.atl/
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
dist/
build/
*.egg-info/
.DS_Store
```

- `.coverage` — NOT ignored. A 53 KB `.coverage` data file (from the 2026-08-28 baseline verification run) currently sits UNTRACKED at the repo root (run 0/01).
- `.mimosa/` — NOT ignored. The directory exists untracked (AI-runtime artifact).
- Scheduled fix: task 1.8 appends `.coverage` and `.mimosa/` (cli-surface Documentation requirement, pulled forward per design Phase Mapping row 1).

## 4. Untracked working-tree inventory (beyond the two gaps)

From run 0/01 (`git status --porcelain`): untracked entries are `.coverage`, `.mimosa/`, `.pi/`,
`_ctx/`, `openspec/`, `tests/conftest.py`.

- `tests/conftest.py` — the KNOWN DRIFT item (G-2): 51 lines, `make_provenance` +
  `make_clinical_value` factories; design File Changes reconciles it as "Modify — extend existing".
- `.pi/` — pre-declared as G-4: the spec-named `.gitignore` additions cover only `.coverage` and
  `.mimosa/`; `.pi/` is OUT of R1 scope unless the owner widens the list at the Phase 0 gate.
- `_ctx/` — ADDITIONAL observation (not named in G-4 or any baseline claim): untracked
  AI-runtime telemetry directory (`_ctx/telemetry/events.jsonl`, `_ctx/telemetry/last_run.json`).
  Same status as `.pi/`: out of R1 scope unless the owner widens the `.gitignore` list at the gate.
- `openspec/` — this change directory itself (bundle + contracts mirror); expected and in-scope.

## 5. Uncommitted working-tree modifications vs `c6578b6` (G-3; verified, not fixed)

Two tracked files differ from the baseline commit (full diff in `evidence-before.md` section 2):

- `pyproject.toml` (+7/-1): adds `--strict-markers` to pytest `addopts` and registers `unit` /
  `integration` / `slow` markers. No dependency, packaging, or core change.
- `tests/unit/test_ir.py` (+38 lines rewritten): four tests now inject the `conftest.py`
  factories (`make_provenance`, `make_clinical_value`) instead of building values inline; the
  local `make_clinical_value` helper is removed. Test count unchanged (7); suite green (run 0/06).

Both modifications are uncommitted at Phase 0 start; neither is mentioned in the proposal
baseline — enumerated here and in `baseline-anomalies.md` (drift family C-1/C-3) for owner
adjudication at the gate.

## 6. Empty-directory observations

`tests/fixtures/` and `tests/golden/` exist as EMPTY directories (untracked-in-git; invisible to
`git status` and to file-only listings — shown via directory listing, run 0/05 prep). Part of
KNOWN DRIFT G-2 (`baseline-anomalies.md` C-2).
