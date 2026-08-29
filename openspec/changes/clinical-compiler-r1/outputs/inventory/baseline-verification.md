# Phase 0 — Baseline Re-Verification (Task 0.2)

Change: `clinical-compiler-r1` | Environment: the EXISTING provisioned venv (CPython 3.14.2, `uv 0.11.2`).
Every command ran with `uv run --no-sync`. NO install, NO sync, NO venv creation occurred. No command
required an environment change — therefore there are **no UNKNOWN outcomes** in this re-verification.

Side-effect prevention applied to each run (semantically neutral cache/write suppression, declared in
`evidence-before.md`): `PYTHONDONTWRITEBYTECODE=1`; pytest additionally `-p no:cacheprovider` and
`COVERAGE_FILE` redirected INTO the declared writes (`outputs/inventory/.coverage-run-0-06`) so the
pre-existing root `.coverage` baseline artifact (2026-08-28) was neither overwritten nor deleted;
mypy `--cache-dir=/dev/null`; ruff `--no-cache`. Branch coverage is enabled by repository config
(`pyproject.toml`: `addopts = "--cov=clinical_compiler --cov-report=term-missing --strict-markers"`,
`[tool.coverage.run] branch = true`), so the plain `pytest` invocation measures branch coverage.

## Run 0/06 — `uv run --no-sync pytest -p no:cacheprovider`

- UTC timestamp: **2026-08-29T13:17:30Z**
- Exit code: **0**
- Result: **29 passed** in 0.04s; **branch coverage 100.00%** (49 statements, 0 missed, 0 partial branches; required 95.0% reached)

Raw output (verbatim):

```text
============================= test session starts ==============================
platform darwin -- Python 3.14.2, pytest-9.1.1, pluggy-1.6.0
rootdir: /Users/felipe_gonzalez/Developer/compilador_clinico
configfile: pyproject.toml
testpaths: tests
plugins: cov-7.1.0
collected 29 items

tests/unit/test_diagnostics.py ............                              [ 41%]
tests/unit/test_ir.py .......                                            [ 65%]
tests/unit/test_policy.py ..                                             [ 72%]
tests/unit/test_types.py ........                                        [100%]

================================ tests coverage ================================
_______________ coverage: platform darwin, python 3.14.2-final-0 _______________

Name                                                     Stmts   Miss Branch BrPart  Cover   Missing
----------------------------------------------------------------------------------------------------
src/clinical_compiler/__init__.py                            2      0      0      0   100%
src/clinical_compiler/core/__init__.py                       0      0      0      0   100%
src/clinical_compiler/core/diagnostics.py                   14      0      0      0   100%
src/clinical_compiler/core/ir.py                            10      0      0      0   100%
src/clinical_compiler/core/policy.py                         2      0      0      0   100%
src/clinical_compiler/core/types.py                         21      0      0      0   100%
src/clinical_compiler/linter/__init__.py                     0      0      0      0   100%
src/clinical_compiler/linter/conformance.py                  0      0      0      0   100%
src/clinical_compiler/passes/__init__.py                     0      0      0      0   100%
src/clinical_compiler/passes/admissibility.py                0      0      0      0   100%
src/clinical_compiler/passes/document_selection.py           0      0      0      0   100%
src/clinical_compiler/passes/input_validation.py             0      0      0      0   100%
src/clinical_compiler/passes/semantic_normalization.py       0      0      0      0   100%
src/clinical_compiler/renderers/__init__.py                  0      0      0      0   100%
src/clinical_compiler/renderers/deterministic.py             0      0      0      0   100%
----------------------------------------------------------------------------------------------------
TOTAL                                                       49      0      0      0   100%
Required test coverage of 95.0% reached. Total coverage: 100.00%
============================== 29 passed in 0.04s ==============================
```

Observation note (fact, no adjudication): the coverage table reports zero branch arcs
(`Branch` column all 0) because the implemented core contains no conditional branches — the
"100% branch coverage of implemented core" figure is therefore 100% of a currently
branch-free core. Per-file test counts: test_diagnostics 12, test_ir 7, test_policy 2, test_types 8
= 29 collected, 29 passed.

## Run 0/07 — `uv run --no-sync mypy --cache-dir=/dev/null src`

- UTC timestamp: **2026-08-29T13:17:36Z**
- Exit code: **0**
- Result: **Success: no issues found in 15 source files** (strict mode comes from repository config: `[tool.mypy] strict = true`)

Raw output (verbatim):

```text
Success: no issues found in 15 source files
```

## Run 0/08 — `uv run --no-sync ruff check --no-cache src tests`

- UTC timestamp: **2026-08-29T13:17:44Z**
- Exit code: **0**
- Result: **All checks passed!**

Raw output (verbatim):

```text
All checks passed!
```

## Summary

| Run ID | Command | Exit | Outcome |
|---|---|---|---|
| `clinical-compiler-r1/0/06` | `uv run --no-sync pytest` (branch coverage via config) | 0 | 29/29 pass, coverage 100.00% |
| `clinical-compiler-r1/0/07` | `uv run --no-sync mypy src` (strict via config) | 0 | clean |
| `clinical-compiler-r1/0/08` | `uv run --no-sync ruff check src tests` | 0 | clean |

UNKNOWN outcomes: **0** (no verification command required an install/sync or any environment change;
all ran in the existing provisioned environment). These raw results feed `baseline-anomalies.md` (task 0.3).
