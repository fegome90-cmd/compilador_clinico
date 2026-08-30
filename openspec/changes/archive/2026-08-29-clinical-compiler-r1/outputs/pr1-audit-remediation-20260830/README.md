# PR #1 — audit remediation evidence (2026-08-30 UTC)

- **Run date (UTC):** 2026-08-30
- **Worktree:** `/Users/felipe_gonzalez/Developer/compilador_clinico-audit-cec43d3` (clean DETACHED worktree frozen at the PR head)
- **Base SHA:** `cec43d39212b46b105dae318e6e5ca96627285b3` (verified by `preflight-first.txt` before any battery command existed)
- **Main tree:** `/Users/felipe_gonzalez/Developer/compilador_clinico` was NEVER touched by this run — its external uncommitted edit is preserved per owner disposition.
- **Commit:** this evidence directory is committed in the same remediation commit it documents; that commit is the direct child of `cec43d3` pushed to `r1-clinical-compiler` (final SHA in the executor's report and in `git log`).
- **Verdict state:** **BLOCKED** (normalized per owner instruction 2026-08-30) — pending independent audit of the new SHA by a reviewer ≠ executor. Nothing here is a PASS/MERGE/ARCHIVE claim.

## Scope

Two code defects from the independent audit, closed via TDD (RED captured before fix):

1. **Linter empty provenance** — `linter/conformance.py`: a matched provenance segment with an
   empty/whitespace-only `source_ref` is now a typed, deterministic `LINT_FAILURE` (line order).
   `not_assessed` lines remain the only provenance-less form (positive pin retained).
2. **Renderer control chars** — `renderers/deterministic.py`: explicit FROZEN module constant
   `CANONICAL_BREAKING_CHARACTERS` (67 literal codepoints: C0 U+0000–U+001F, DEL U+007F,
   C1 U+0080–U+009F incl. NEL U+0085, U+2028, U+2029; NO `unicodedata` — determinism across
   Python versions), enforced on BOTH value glyphs and `source_ref` strings → `RENDER_ERROR`
   fail-closed naming the exact `U+XXXX`; never transformed. Printable/typical unicode
   (`ñ`, `°`, `—`) pinned as still rendering (no over-blocking); golden corpus (plain printable
   ASCII) byte-identical (battery 04/05).

Plus three verify-report corrections appended in `verify-report.md` §AUDIT REMEDIATION
(verdict normalized to BLOCKED; prior run's preflight/battery timestamp inversion documented
honestly; the two defects recorded with evidence pointers).

## Contents

| Path | What |
|---|---|
| `preflight-first.txt` | Freeze proof, captured FIRST — timestamped git state per capture; last TS 2026-08-30T10:51:16Z |
| `repro-before-fix/defects-before-fix.txt` | Both defects reproduced against the pre-fix tree (timestamped) |
| `tdd/red-before-fix.txt` | RED: linter 6 failed/39 passed (new tests fail pre-fix); renderer module ImportError (constant absent) |
| `tdd/green-after-fix.txt` | GREEN: linter 45 passed, renderer 49 passed |
| `battery/01..12-*.log` | Full 12-item battery; each log embeds UTC start/end, command, exit code, target state |
| `cli-sweep.md` | Extended exit-70 sweep write-up: 29/29 mapped, ZERO 70; reachability note for the lint fix |
| `sha256sums.txt` | SHA-256 of every file this run produced/modified (except itself) |

## Battery results (all exit 0; logs embed UTC timestamps strictly after preflight-first)

| # | Item | Result |
|---|---|---|
| 1 | pytest + coverage gate | **464 passed**, 0 failed; stmts 692/0 missed, branches 244/0 missed = **100.00%** (gate ≥95) |
| 2 | `mypy --strict src` | Success — 22 source files |
| 3 | `ruff check src tests` | All checks passed |
| 4 | Golden machinery verify, plain + `python -I` | `overall_integrity=VALID`; all 3 scenario digests MATCH committed docs + manifest |
| 5 | Determinism: 3 cases × PYTHONHASHSEED 0/12345/random | BYTE-IDENTICAL stdout+stderr; golden case == committed golden bytes |
| 6 | `git diff --check` | clean |
| 7 | Imports rule review | dependency rule holds; only `typing.Final` added (stdlib) |
| 8 | Zero runtime deps | `[project].dependencies` absent; stdlib-only imports |
| 9 | datetime/locale/random/hash( scan | zero call sites in output paths; frozen charset adds none (no unicodedata) |
| 10 | Admissibility explicit policy | live re-verified (stage never reads core constant) |
| 11 | Document/diagnostics non-coexistence | construction guard + behavioral tests re-verified live |
| 12 | Extended exit-70 sweep | **29/29 mapped** (27 prior + ws-only-source_ref → exit 10 + U+2028 value → exit 9), stdout empty on every fault, **ZERO 70** |

### Test-count reconciliation (honest arithmetic)

Battery log 01's description carried the pre-run expectation "463 passed"; actual was
**464 = 432 prior + 7 linter + 25 renderer**. The linter delta is 7, not 6: the RED run showed
6 failing new tests plus the new `not_assessed`-form positive pin, which passed pre-fix by
design (it pins a pre-existing correct property). Coverage grew 634→692 stmts, 212→244
branches, still 0 missed.

### Environment note

The worktree had no `.venv`; it was created with `uv sync --group dev` (gitignored, dev
tooling only). The first attempt used `--offline` and failed on one uncached wheel
(pygments 2.21.0); the sync was completed normally for that wheel. This changes nothing
about the system under test: the runtime remains stdlib-only (battery 07/08). `python -I`
legs ran via the project interpreter (bare `python3` on PATH is Xcode 3.9, below the ≥3.11
floor) — same note as the prior run.

## Ordering discipline (corrective, per owner)

The prior run's artifacts showed preflight (10:22:15Z) AFTER battery start (10:17:23Z) —
freeze-before-battery was NOT proven there. This run: `preflight-first.txt` written before
any battery command existed (last captured TS 2026-08-30T10:51:16Z); the battery ran at
`date_utc` 2026-08-30T11:04:43Z (item 01) through 2026-08-30T11:04:51Z (item 12 end) — every
battery log's UTC timestamps strictly after the preflight's last TS, so ordering is provable
from the artifacts alone.
The battery executed PRE-COMMIT on this worktree; byte-identity between battery-tested and
committed content is provable via `sha256sums.txt` (recorded pre-commit) plus the post-commit
fence (clean tree, only the documented files).

---

## CORRECTION (appended 2026-08-30, audit remediation ROUND 2 — append-only note)

Wording correction per independent audit §1: this README's opening bullet describes the run's worktree as "(clean DETACHED worktree frozen at the PR head)" and the battery narrative leans on that cleanliness. The precise preflight state was: **tracked source tree clean; the evidence directory itself intentionally untracked** at preflight time (committed only with the remediation commit it documents). The statement "clean tree / no untracked files" would be FALSE for this run and must not be propagated into future evidence write-ups. The underlying facts (worktree frozen at `cec43d3`, zero modified tracked files, main tree never touched) are unaffected.

Appended at 2026-08-30T11:59:50Z by the ROUND 2 remediation run.
