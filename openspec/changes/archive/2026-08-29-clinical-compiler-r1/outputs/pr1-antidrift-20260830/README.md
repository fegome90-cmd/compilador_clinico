# PR-1 FULL_ANTIDRIFT re-verification evidence

- **UTC date of audit:** 2026-08-30 (logs carry `date_utc` stamps)
- **Absolute path:** `/Users/felipe_gonzalez/Developer/compilador_clinico/openspec/changes/archive/2026-08-29-clinical-compiler-r1/outputs/pr1-antidrift-20260830/`
- **Audited target:** `7d0895133d0ca74a889e3f3270f3a4b9f497f4cd` (local HEAD == remote `r1-clinical-compiler` head at audit time; branch `main`)
- **Writer identity:**
  - The pre-existing drift described in the executing brief (uncommitted P0-1..P1-1 repairs on top of `9b04fa2`) was authored by **PREVIOUS_ORCHESTRATOR_EXECUTION** — the prior session's repair agents. It is NOT present as working-tree state anymore: it was committed verbatim as `7d089513…` and pushed to `r1-clinical-compiler` before this session started.
  - THIS directory (evidence + verify-report append) was authored by the **FULL_ANTIDRIFT executor** session of 2026-08-30, working against the committed tree with `modified_files_before = 0`.
- **Baseline note:** the brief's `baseline_sha = 9b04fa2…` is SUPERSEDED — `9b04fa2` is the owner docs commit and the direct parent of the repair commit `7d089513…`. Details in `baseline-head.txt`.

## Target-freeze statement

Every command in `battery/*.log` was executed with `git rev-parse HEAD == 7d0895133d0ca74a889e3f3270f3a4b9f497f4cd` and a clean tracked tree (each log ends with `target_sha:` and `working_tree_status:` lines captured AFTER the command ran). This session made **no source-code changes**: the four defects (P0-1 verbatim injection, P0-2 certainty loss, P0-3 POPULATED-empty, P1-1 exit-70-on-empty-ids) were demonstrated CLOSED against the committed repair, not repaired here. The only repo modifications authored by this session are this evidence directory and the appended `## FULL_ANTIDRIFT RE-VERIFICATION` section of `verify-report.md` (at the change root, one level above).

## Contents

| File | What it proves |
|---|---|
| `preflight.txt` | exact git state captured at evidence-freeze time (toplevel, branch, HEAD, status, diff, untracked, remote PR head) |
| `baseline-head.txt` | target freeze + superseded-baseline honesty record + writer identity |
| `battery/01-pytest-coverage.log` | `uv run --no-sync pytest --cov … --strict-markers -q` → exit 0, **432 passed, 100.00% branch coverage** (gate ≥95) |
| `battery/02-mypy-strict.log` | `uv run --no-sync mypy --strict src` → exit 0, zero errors |
| `battery/03-ruff-check.log` | `uv run --no-sync ruff check src tests` → exit 0, "All checks passed" |
| `battery/04-golden-machinery-verify.log` | golden corpus: `corpus_verified=True`, `overall_integrity=VALID`, `phase3_gate_blocked=False` under plain AND `python -I` interpreters; per-scenario digests MATCH committed document bytes AND manifest under plain / `PYTHONHASHSEED=0` / `python -I` |
| `battery/05-determinism-hashseed.log` | 3 CLI cases × seeds {0, 12345, random} → stdout+stderr `cmp`-identical, identical exits |
| `battery/06-git-diff-check.log` | `git diff --check` → exit 0 (no whitespace/conflict-marker faults) |
| `battery/07-imports-review.log` | dependency rule holds: nothing below `pipeline` imports `pipeline` proper; renderers/linter never import passes; `pipeline_types` leaf hits are sanctioned; only stdlib + `clinical_compiler` imports |
| `battery/08-zero-runtime-deps.log` | `[project].dependencies` absent from pyproject; all src imports stdlib-or-clinical_compiler; uv.lock shows dev-dependencies only |
| `battery/09-determinism-scan.log` | `datetime|locale|random|hash(` scan of src → zero call sites in output paths (docstring/comment hits only; the single `hashlib.sha256` site is the sanctioned deterministic canonical-fact-id derivation) |
| `battery/10-admissibility-explicit-policy.log` | veto terms reach admissibility ONLY as the explicit `veto_terms` parameter; `core.policy` never imported outside core; live re-run of `test_stage_never_reads_the_core_policy_constant` |
| `battery/11-doc-diagnostics-noncoexistence.log` | `CompileResult.__post_init__` makes document+diagnostics (and silent-empty-under-resolved) unrepresentable; behavioral tests scoped-pass (12 passed) |
| `battery/12-exit70-sweep.log` | 27-case invalid-input family sweep → all mapped exits (0/2/3/4/6/9), **ZERO 70** |
| `cli-sweep.md` | human-readable exit-code table: defect reproductions + full sweep + determinism triples |
| `sha256sums.txt` | SHA-256 of every file in this directory except itself |

## Verdict

All gates PASS against `7d089513…`; final verdict recorded in `verify-report.md`
(`## FULL_ANTIDRIFT RE-VERIFICATION (2026-08-30, target 7d089513)`):
**REPAIR_COMMITTED_PENDING_INDEPENDENT_AUDIT**.
