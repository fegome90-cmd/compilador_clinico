# PR #1 — audit remediation ROUND 2 evidence (2026-08-30 UTC)

- **Run date (UTC):** 2026-08-30
- **Worktree-1 (authoring):** `/Users/felipe_gonzalez/Developer/compilador_clinico-audit-cec43d3` — detached at the PR head `aff8b219e197c4f04ff464f5ffe5a6b6e6bc05c8` when the run started
- **C1 (the code SHA audited):** `b8c0c46b99290863faa6c4c42c10d947c40c6e51` — "fix(linter,renderer): canonical-char parity in linter and FC-11 presentation-role validation", direct child of `aff8b21`; carries BOTH audit-round-2 BLOCKER fixes, the verify-report ROUND 2 section, the previous evidence README's append-only wording correction, and the disposition-2 test comment fix
- **C2 (evidence-only commit):** the commit carrying THIS directory — **no tested-file changes** between C1 and C2 (nothing under `src/` or `tests/`), so C1 remains the tested target
- **Worktree-2 (battery):** `/Users/felipe_gonzalez/Developer/compilador_clinico-postcommit-C1` — a SEPARATE detached worktree created from C1 AFTER C1 was committed; the full battery ran THERE, never in the authoring tree (audit §6 prescription: post-commit battery from a clean checkout)
- **Preflight state wording (audit §1):** tracked source tree clean; evidence directory intentionally untracked (committed as C2) — never "clean tree / no untracked files"
- **Main tree** `/Users/felipe_gonzalez/Developer/compilador_clinico`: NEVER touched by this run — its external uncommitted edit is preserved per owner disposition
- **Verdict state:** **BLOCKED** — pending independent re-audit of C1 by a reviewer ≠ executor. Nothing here is a PASS/MERGE/ARCHIVE claim.

## Scope — two BLOCKERS closed (TDD, RED before GREEN)

1. **BLOCKER 1 — linter canonical-character parity (P0 defense-in-depth).** The renderer's frozen 67-codepoint `CANONICAL_BREAKING_CHARACTERS` refuses C0/DEL/C1/U+2028/U+2029 in values AND source_refs, but the linter (the net AFTER render) blocked only CR: 65 of 67 codepoints linted CLEAN mid-line — bytes the renderer declares impossible passed the final gate. Fix: `linter/conformance.py` defines its OWN literal frozen set `LINTER_CANONICAL_BREAKING_CHARACTERS` (deliberate duplication — the net never imports the renderer it polices; parity pinned TEST-side) and scans every decoded line → typed `LINT_FAILURE` naming the exact `U+XXXX` in deterministic line order. The scan runs LAST within a line so every pre-existing enumeration is preserved byte-for-byte; U+000A is the line separator itself (split fragments blocked by existing rules), U+000D keeps its dedicated global invariant. All prior rules intact. Post-fix sweep: **0 of 67 lint-clean**.
2. **BLOCKER 2 — FC-11 `presentation_role` → `LINT_FAILURE` (auditor's option A).** `render_document` ignored `presentation_role`; the linter sees only bytes — the role vanished, and injected invalid roles rendered clean bytes. Fix: frozen literal `MODE_ALLOWED_PRESENTATION_ROLES` defined LOCALLY in the renderer (renderers must not import passes — D5; duplication rationale in-code, parity pinned TEST-side against `passes.document_selection`); each entry's role validated against `DocumentIR.document_mode`'s allowed set at the renderer boundary (the LAST point where the role exists) → **`LINT_FAILURE`** per invalid entry, in entry order, fail-closed; unknown mode ⇒ empty allowed set ⇒ every entry fails closed. `derive_exit_code` maps the diagnostic CODE (not the emitting stage) → exit 10, pinned by test. No signature gap (`DocumentIR` carries `document_mode`) — no OWNER_DECISION_REQUIRED needed.

## Contents

| Path | What |
|---|---|
| `preflight-first.txt` | Captured FIRST (2026-08-30T11:48:14Z), before any fix/test/battery command; HEAD `aff8b21`, porcelain = exactly the one untracked evidence dir; carries the audit §1 wording block (appended 11:59:42Z, still before any battery command existed) |
| `repro-before-fix/defects-before-fix.txt` | BOTH blockers reproduced against the pre-fix tree: 4 auditor examples lint-CLEAN + 65/67-codepoint sweep CLEAN; invalid roles ("INVALID", "", "narrative_entry") and unknown mode rendered clean bytes |
| `tdd/red-blocker1-linter.txt` | RED: `ImportError: cannot import name 'LINTER_CANONICAL_BREAKING_CHARACTERS'` (collection failure) |
| `tdd/green-blocker1-linter.txt` | GREEN: 193 passed (linter unit file) |
| `tdd/red-blocker2-renderer.txt` | RED: `ImportError: cannot import name 'MODE_ALLOWED_PRESENTATION_ROLES'` (renderer+chain collection failure) |
| `tdd/green-blocker2-renderer.txt` | GREEN: 258 passed (renderer + chain + linter files) |
| `battery/01..09-*.log/.txt` | Post-commit battery at C1 in worktree-2 — every log embeds target_sha=C1, UTC start/end, command, exit code, and before/after porcelain line counts |
| `fence-post-commit.txt` (= `battery/09-…`) | REAL fence: HEAD == C1, porcelain EMPTY after the battery, with an honest precision note about git-ignored runtime caches |
| `pr-body-update.txt` | The exact PR-body Verification-section replacement + apply command (body applied after push; `gh pr view` capture delivered in the executor's report) |
| `sha256sums.txt` | SHA-256 of every file this run produced/modified (except itself) |

## Battery results (all exit 0; run at C1 in worktree-2, never in the authoring tree)

| # | Item | Result |
|---|---|---|
| 1 | pytest + coverage gate | **622 passed**, 0 failed; 707 stmts / 0 missed, 252 branches / 0 missed = **100.00%** (gate ≥95) |
| 2 | `mypy --strict src` | Success — 22 source files |
| 3 | `ruff check src tests` | All checks passed |
| 4 | Golden verify, plain | `overall_integrity=VALID`, `phase3_gate_blocked=False` |
| 5 | Golden verify, `python -I` (isolated, fresh hash seed) | same — VALID |
| 6 | Adversarial tests scoped (linter + renderer + chain units) | all passed |
| 7 | Determinism: 2 golden scenarios × `PYTHONHASHSEED` 0 vs 12345 | stdout+stderr byte-identical (`cmp`); `standard_mixed` digest `e7b5b03f…` equals the committed golden; NOTE: a first attempt used a wrong CLI flag and exited 2 vacuously — the log was restarted with correct positional usage before any conclusion was drawn (documented in-log) |
| 8 | Exit-70 sweep — 20 cases: 13 CLI (valid, missing file, malformed JSONL, missing provenance, bool value, empty fact_id, empty ref, whitespace-only ref, U+2028 value, TAB value, NEL ref, empty-terms seed, veto seed) + 7 stage-level NEW lint paths (TAB-in-value/ref bytes, U+0085/U+2028 bytes, whitespace-ref bytes, invalid-role IR, unknown-mode IR) | **20/20 mapped — ZERO 70**; the new lint paths all map to exit 10 (LINT_FAILURE). Honest notes: through the real pipeline the U+2028/TAB/NEL-in-feed cases are rejected EARLIER by the contract/type layers (exits 3/4) — the render/lint arms are exercised by the stage-level cases S01–S07, which is where injected bytes/IR can exist. First harness attempt crashed on a missing `.encode()` (harness bug, not a system exit) — documented in-log |
| 9 | Post-commit fence (REAL) | HEAD == `b8c0c46…` (C1) AND porcelain EMPTY after the battery; git-ignored caches (`.venv/`, `__pycache__/`, `.*_cache/`) exist by design and are noted honestly in the fence |

## Test-count arithmetic (honest)

464 (end of round 1) → **622**: +67 completeness parametrize, +65 message parametrize, +2 charset pins (frozen-shape + parity cross-pin), +4 auditor named cases, +1 linter determinism pin, +11 printable-boundary params, −1+1 empty-ref param (TAB form swapped for NBSP) on the linter side; +1 parity cross-pin, +3 invalid-role params, +2 enumeration/mixed pins, +1 valid-role pin, +1 unknown-mode pin, +1 exit-10 pin on the renderer side; +2 FC-11 integration cases on the chain side.

## Dispositions (non-blocking) — applied

1. **Evidence wording (§1):** this README + `preflight-first.txt` use "tracked source tree clean; evidence directory intentionally untracked"; append-only CORRECTION note added to the PREVIOUS run's README (`../pr1-audit-remediation-20260830/README.md`).
2. **Test comment fix (§3):** `test_empty_source_ref_yields_lint_failure` now distinguishes `""` (contract-REJECTED → INPUT_CONTRACT_ERROR, 7d08951) from `" "` (contract-ADMISSIBLE — flows through the real pipeline today; battery item 8 case C08 proves it end-to-end: exit 10 at the linter). TAB form moved to the canonical-char parity cases; NBSP U+00A0 keeps the whitespace-only-ref pin.
3. **verify-report.md:** `## AUDIT REMEDIATION ROUND 2 (2026-08-30)` appended — both blockers with evidence pointers; operative verdict stays **BLOCKED pending independent re-audit**.
4. **PR body (§7):** Verification section replaced (state BLOCKED / Target C1 / executor battery / audit remediated + re-audit pending / prior PASS_WITH_WARNINGS superseded); everything else byte-preserved. Applied after the final push; `pr-body-update.txt` carries the exact body.

## Ordering discipline

Preflight (`11:48:14Z`) → repro-before-fix → RED logs → fixes → GREEN logs → dispositions → C1 commit → worktree-2 created from C1 → battery items 1–9 (12:00–12:04Z, every log self-timestamped, target_sha=C1, porcelain before/after recorded) → fence → evidence README/sha256sums → C2 → push → PR body edit. Provable from the artifacts alone.
