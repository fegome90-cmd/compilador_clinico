# Phase 4 Close — Gate 4.7 + R1 FINAL RECEIPT (change: clinical-compiler-r1)

Executor: sdd-apply PHASE_4 CLOSE / FINAL RECEIPT unit (APPROVAL-PHASE4
unit 4). Unit scope: compute the Phase-4 gate from fresh evidence,
consolidate the R1 final receipt (M10.3 schema, tasks.md "Final
Receipt"), write this report. Read-only for `src/`/`tests/`/bundle/
approvals/`state.yaml`; sole writes: this file + one engram save
(topic `sdd/clinical-compiler-r1/apply-progress`). No commit; no
`tasks.md` box edits (hash-bound); no approval-record mutation.

**ADDENDUM (2026-08-29 21:45Z, bounded residuals unit R-4.7a):** the
single enumerated residual was closed under owner authorization —
`src/clinical_compiler/adapters/README.md` deleted (pre-state verified
0 bytes + git-tracked, exactly the design-named placeholder), Gate
4.7 row 3 recomputed → 0 → PASS, quality suite re-run green
(406/406, cov 100.00%, mypy strict, ruff). Edits below are marked
"(post-R-4.7a recompute)"; the 21:33–21:39Z close-time record is
preserved as written. PHASE_4 = done (8/8); R1-apply overall =
done-pending-owner-commit (P3-F11 + P3-F10 note).

All commands run 2026-08-29, UTC range 21:33–21:39Z, every `uv`
invocation `--no-sync` (no environment mutation; no install/sync
attempted; zero `UNKNOWN` outcomes). Every verdict below is computed
from captured evidence — nothing assumed. Gate semantics per
`specs/phase0-verification/spec.md` and the tasks.md result
vocabulary: `UNKNOWN` never yields PASS; a named gate item that is
unmet blocks the gate and is enumerated — never silently passed.

## Phase-4 task rows — EVERY row 4.1–4.7 and its disposition (R-2.7 lesson)

Literal rows are 4.1–4.7 (no 4.8/4.9 exists in `tasks.md`). Code
payload from APPROVAL-PHASE4 units 1–3 (already in the working tree
at close start; verified, not trusted):

| Row | Task (tasks.md verbatim scope) | Disposition | Evidence |
|-----|-------------------------------|-------------|----------|
| 4.1 | `pipeline.py` composition root: fixed stage order; per-fact quarantine; diagnostics accumulator; whole-run emission gate (`document is None` iff any diagnostic); `derive_exit_code` pure (min stage-order code among 3–10; 0 iff empty); exit 70 catch-all; `StageResult` re-export | **DONE** | `src/clinical_compiler/pipeline.py` (269 lines): `parse_feed → run_input_validation → run_semantic_normalization → run_admissibility → CanonicalClinicalIR → run_document_selection → render_document → lint_conformance`, survivors-only; `is_resolved` D7 branch is PRODUCTION code (carried Phase-2 flag closed); `CompileResult.__post_init__` makes `document+diagnostics` and `no-document+no-diagnostics-under-resolved-policy` unrepresentable; `derive_exit_code` iterates the ordered `_STAGE_ORDER_EXIT_CODES` tuple (never set order). Tests: 36 in `tests/unit/test_pipeline.py` incl. `test_any_diagnostic_yields_no_document_and_the_family_exit_code`, `test_unresolved_policy_runs_no_admissibility_and_blocks` (spy), `test_min_stage_order_code_wins_regardless_of_encounter_order`, `test_stage_result_is_reexported_from_the_leaf_module`, `test_blocked_accumulator_never_reaches_render_or_lint` |
| 4.2 | Integration tests `tests/integration/` (in-process `pipeline.run`) | **DONE with placement deviation (P4-F5)** | In-process `pipeline.run` integration coverage lives in `tests/unit/test_pipeline.py` (36) — `tests/integration/` was NOT created; the naming/placement convention carried from Phases 1–2 continues (recorded, not silently accepted) |
| 4.3 | `cli.py`: argparse shell `compile INPUT [--mode MODE] [--policy-seed PATH] [--output PATH]`; diagnostics to stderr one per line `CODE: message (path)`; document bytes ONLY at exit 0; `--output` atomic (temp + `os.replace`); usage errors exit 2, no compile attempted | **DONE** | `src/clinical_compiler/cli.py` (289 lines): `_Parser.error` override (no SystemExit leak); `_atomic_write` = mkstemp-in-destination-dir → write+flush+fsync → `os.replace` → parent-dir fsync, temp removed on any failure; stdin/`--json`/`check` deferred to R2 per the frozen surface |
| 4.4 | `pyproject.toml`: `[project.scripts]` `clinical-compiler = "clinical_compiler.cli:main"`; `[project].dependencies` stays `[]` | **DONE** | Diff vs HEAD: exactly the 3-line `[project.scripts]` block; no `dependencies` key ever declared (⇒ zero runtime deps, PEP 621). Console script is NOT materialized in `.venv/bin` — the no-sync budget forbids the re-sync that would create it; the entry point is registered and tests invoke `main` directly (subprocess with explicit `PYTHONPATH`) |
| 4.5 | CLI subprocess tests: exit 0 on success; exit 2 usage faults; exits 3–10 one per diagnostic category via the FC corpus end-to-end; identical failing input → identical exit code; document stream empty on every non-zero exit | **DONE** | 33 in `tests/unit/test_cli.py` (fresh-interpreter subprocess + in-process arms): `test_fault_corpus_exits_its_family_code_and_never_emits_a_document`, `test_usage_faults_exit_two_without_emitting_anything`, `test_seed_fault_yields_the_unresolved_policy_usage_line`, `test_atomic_write_cleans_the_temp_file_on_write_failure`, `test_output_into_a_missing_directory_fails_closed_at_seventy`, `test_diagnostic_stderr_line_format_is_stable`. Exits 7/9/10 are unreachable through `pipeline.run` by construction (CRC-004 adjudication) — exercised at the CLI seam via injected stage faults, as FC-10/FC-11 prescribe |
| 4.6 | Fill `README.md` and `docs/architecture.md` (both 0 bytes at baseline) | **DONE (CRC-009)** | `README.md` 385 lines (architecture, install, quick start incl. CLI, JSONL input contract, complete Exit-Code Table rows 0/2/3–10/70 at lines 250–260, diagnostics/missingness rules); `docs/architecture.md` 179 lines (pipeline, IR ladder, contracts incl. D7 machine + G-1 leaf, invariants incl. the determinism mechanism #1–#6 and NOT_PRODUCED, module map, CRC-010 lineage, governance) |
| 4.7 | Final gates: compute the full Gate Checklist (rows 1–8 below); enumerate every BLOCKED outcome; emit the Final Receipt | **DONE — 8/8 after R-4.7a closed (post-R-4.7a recompute)** | Evidence table below; residual was enumerated at close, then bounded-recovered and recomputed per R-2.7 precedent |

**No unassigned Phase-4 row.** 4.1–4.6 done; 4.7 computed 7/8 at
close time, row 3's residual R-4.7a then closed by the bounded
residuals unit → recomputed **8/8** — PHASE_4 = `done`
(post-R-4.7a recompute).

## Gate 4.7 — Gate Checklist rows 1–8 (computed, never asserted)

Run IDs `clinical-compiler-r1/4.7/00–13`.

| # | Gate (tasks.md checklist) | Computation + run ID | Exit | Key evidence | Verdict |
|---|---------------------------|----------------------|------|--------------|---------|
| 1 | Phase 0 baseline: `BASELINE_ANOMALIES` | carried from `outputs/inventory/baseline-anomalies.md` + `state.yaml` `decision_gate_phase0.adj1` | — | 2 raw anomalies observed (drift claims) → owner ADJ-1 `RECONCILED_NOT_COUNTING` → effective **0**; zero `UNKNOWN` outcomes across all phases | **PASS** (carried, owner-adjudicated) |
| 2 | Phase 0 decision: owner-stated `INPUT_CONTRACT_DECISION` + seed status | carried from `APPROVAL-PHASE1.md` + `state.yaml` | — | `INPUT_CONTRACT_DECISION = STRUCTURED_FEED_ONLY`, `POLICY_SEED_DECISION = DEFERRED_BY_OWNER`, both owner-authored in the approval record (`4.7/05` re-read) | **PASS** (carried) |
| 3 | Scaffold completion: zero-byte count under `src/clinical_compiler/{passes,linter,renderers,adapters}` | At close (21:33Z, `4.7/04`): count = 1 (`adapters/README.md`, 0 bytes, tracked, design.md File Changes line 342 = **Delete** executed by no unit) → **UNMET, enumerated as R-4.7a**. POST-R-4.7a RECOMPUTE (21:45Z): placeholder DELETED by the bounded residuals unit after pre-state verification (`wc -c` = 0; `git ls-files` tracked; no hook interference) → `fd --type f --size 0b` scan over the four dirs = **0**; supplementary src-wide scan = 2, both outside gate scope and conventional artifacts clean at HEAD (`core/__init__.py` package init, `py.typed` PEP 561 marker); `adapters/` now holds only real modules (`__init__.py` 84 B, contract.py 8.5k, seed.py 12k, structured_feed.py 3.7k) | 0 | close-time count was 1 → UNMET (R-4.7a, enumerated); recomputation after the bounded deletion yields 0 with legitimate artifacts only | **PASS** (post-R-4.7a recompute) |
| 4 | Zero runtime deps: `len([project].dependencies)` | `uv run --no-sync python -c tomllib` parse (`4.7/05`) | 0 | Key ABSENT from `[project]` (absent ⇒ 0 under PEP 621; semantically the proposal's `dependencies == []`); only `[dependency-groups] dev` (pytest/pytest-cov/ruff/mypy) — dev-only, outside `[project].dependencies`; no runtime import outside stdlib | **PASS** |
| 5 | Quality suite | `uv run --no-sync pytest --cov=clinical_compiler` (`4.7/01`) · `uv run --no-sync mypy --strict src` (`4.7/02`) · `uv run --no-sync ruff check src tests` (`4.7/03`) · no-cov re-run (`4.7/12`) | 0 / 0 / 0 / 0 | **406 passed, 0 failed**; `Required test coverage of 95.0% reached. Total coverage: 100.00%` (TOTAL 634 stmts, 212 branches, **0 missed**); every one of the 22 source files 100%. mypy: `Success: no issues found in 22 source files`. ruff: `All checks passed!`. Re-run clean (`406 passed in 1.27s`). Observation (non-blocking): the first cov run emitted one `CoverageWarning: module-not-measured` during collection; the coverage table itself measured all 22 files at 100%, and the warning is absent on re-run — recorded, not suppressed | **PASS** |
| 6 | Determinism: identical fixture set compiled twice in fresh interpreters | scoped golden suite `pytest tests/unit/test_integration_golden_determinism.py tests/golden -q --no-cov` (`4.7/07`) · REAL CLI cross-run `PYTHONHASHSEED=0 / random / 12345` → `main(['compile', …standard_mixed…, '--output', …])` (`4.7/08`) | 0 / 0 | 16/16 golden tests: each scenario compiled 4× (`python -I` ×2, `PYTHONHASHSEED=0`, unseeded) — digests equal AND equal to the committed golden. Live end-to-end: 3 CLI runs at 3 hash seeds → exit 0, `cmp` byte-identical across runs AND vs the golden document; digest `e7b5b03fa6d9f150c081684846fb481b7dfda02ebdd24992a7fba164c88b8abc` | **PASS** |
| 7 | Fail-closed safety: FC-01..FC-12 + PC-1/PC-2, silently-accepted unsafe count == 0 | census `rg --fixed-strings FC-xx tests/` per id (`4.7/10`) · CLI corpus test (`4.7/06` module census) · live fault run (`4.7/09`) | 0 | Every corpus id has test coverage (min 3 refs): FC-01×6, FC-02×6, FC-03×11, FC-04×5, FC-05×7, FC-06×4, FC-07×4, FC-08×3, FC-09×6, FC-10×8, FC-11×9, FC-12×8, PC-1×11, PC-2×13. Live CLI fault (bool `raw_value` + missing provenance) → **exit 3**, two stable-format stderr diagnostics, empty stdout. `test_fault_corpus_exits_its_family_code_and_never_emits_a_document` pins family codes with empty document stream. Silently-accepted unsafe count = **0** | **PASS** |
| 8 | Diagnostics coverage: `DiagnosticCode` members with no producing stage AND no covering test | census per code: `rg -c "DiagnosticCode.<CODE>" src/` + `rg -c "<CODE>" tests/` (`4.7/06`) | 0 | 8/8 members covered — production sites (min 2 each): INPUT_CONTRACT_ERROR 23, TYPE_ERROR 3, SEMANTIC_AMBIGUITY_BLOCK 2, POLICY_VIOLATION 2, PROVENANCE_ERROR 3, DOCUMENT_SELECTION_ERROR 3, RENDER_ERROR 5, LINT_FAILURE 11; test references (min 13 each): 47/23/15/16/13/16/22/45. **Orphan count = 0** (both Phase-0 baseline orphans `TYPE_ERROR`/`PROVENANCE_ERROR` eliminated at gates 1.9/2.8). `UNRESOLVED_POLICY` is a resolution state, not an 8th… not a taxonomy member — correctly outside this census (CLI maps it to exit 2, `4.7/09` family) | **PASS** |

**GATE_4_7 = 8/8 PASS (post-R-4.7a recompute; close-time computation
was 7/8 with row 3 UNMET, enumerated as R-4.7a).**
Every CLI end-to-end leg also verified live (`4.7/08–09`): exit 0
success with byte-identical golden output; exit 2 on unreadable INPUT
(`clinical-compiler: error: cannot read input …`) and on unknown
`--mode` (argparse usage); exit 3 on a contract fault with stable
`CODE: message` stderr lines and empty stdout.

## Unit summary (APPROVAL-PHASE4 work-unit sequence, owner-defined)

Phase-4 payload sits UNCOMMITTED in the working tree (owner-HEAD
`470fef5`, the Phase-2 payload commit; executor commits prohibited).

| Unit | Scope (tasks) | Result | Tests | Files |
|------|---------------|--------|-------|-------|
| P4-U1 | `pipeline.py` composition root + emission gate + `derive_exit_code` + `is_resolved` production branch + `StageResult` re-export (4.1/4.2) | PASS | 36 in `test_pipeline.py` | + module (uncommitted) |
| P4-U2 | CLI shell + `[project.scripts]` + subprocess/exit-code/atomic-write suite (4.3/4.4/4.5) | PASS | 33 in `test_cli.py` | + `cli.py`, pyproject +3 lines (uncommitted) |
| P4-U3 | Docs: README completed from owner draft + `docs/architecture.md` filled, claims verified live (4.6, CRC-009) | PASS | — (docs) | `README.md` (385 lines), `docs/architecture.md` (179 lines) (modified) |
| P4-CLOSE | Gate 4.7 + Gate Checklist + FINAL RECEIPT + this report (4.7) | **DONE — 8/8 after R-4.7a bounded-recovered** | suite 406/406 re-verified | this report |

Test arithmetic: 337 (Phase-3 close) + 36 + 33 = **406** — matches
observed. Suite evolution: 140 (P1) → 251 (P2) → 337 (P3) → 406 (P4);
coverage 100.00% at every close; mypy strict + ruff exit 0 at every
close.

## Consolidated Phase-4 flags (P4-F*, reported per `risk_policy: ask_on_risk`)

| # | Flag | Substance |
|---|------|-----------|
| P4-F1 | `CompileResult.document` is `bytes \| None`, not the design sketch's `str \| None` — the normative sequence diagram + frozen `StageResult[bytes]` stages produce bytes; the sketch predates the Phase-3 freeze | minimal-faithful reading (pipeline.py docstring #1) |
| P4-F2 | `CompileRequest` carries the `PolicyResolution`, not a bare veto set — the D7 branch is indistinguishable on a bare set (resolved-empty vs unresolved) | minimal-faithful reading (#2) |
| P4-F3 | `CompileResult.policy` added beyond the sketch's two fields — `UNRESOLVED_POLICY` is a resolution state, NOT a `DiagnosticCode`; without the field, `document=None, diagnostics=()` would be indistinguishable from success-and-emit-nothing | minimal-faithful reading (#3) |
| P4-F4 | Destination write faults (`--output` OSError) are NOT frozen exit-2 triggers → they reach the exit-70 catch-all (fail-closed, tested) | minimal-faithful reading (cli.py docstring) |
| P4-F5 | Task 4.2 letter names `tests/integration/`; actual suite is `tests/unit/test_pipeline.py` — placement convention carried from P1/P2 naming deviations | recorded deviation |
| P4-F6 | Console script `clinical-compiler` not materialized in `.venv/bin` — `uv sync` prohibited by the side-effect budget; entry point registered in pyproject (4.4's letter is the pyproject edit) and exercised via `PYTHONPATH` subprocess tests | recorded; materializes at the owner's next install |
| **R-4.7a** | **RESOLVED (2026-08-29 21:45Z, bounded residuals unit under owner authorization): placeholder deleted after pre-state verification (0 bytes, git-tracked, design-named); Gate row 3 recomputed → 0 → PASS; suite re-verified 406/406 cov 100%** | closed — was the single open Phase-4 residual |

---

# R1 FINAL RECEIPT (task 4.7 — M10.3 schema)

```text
final_receipt:
  bundle:             clinical-compiler-r1 — bundle manifest SHA-256
                      7a7d3a28afa749c362a2091f4ea0c60d25745f0ede49ac311b5e8d8511e0737d
                      (as bound in APPROVAL-PHASE0.md and re-cited by every
                      subsequent approval record; per-file digests in
                      state.yaml `bundle_hashes_sha256`)

  governance:         ai-work-agent-execution-contract-0.3, selected_profile
                      GOVERNED; reviewer ≠ executor on every approval record;
                      executor commits prohibited throughout; risk_policy
                      ask_on_risk (flags reported, never silently resolved)

  subject:            baseline commit c6578b6 → final HEAD commit 470fef5
                      ("feat(pipeline): canonical aggregate, semantic
                      normalization, admissibility and policy seed resolution"
                      — the owner's Phase-2 payload commit). NOTE (honest
                      subject caveat): the Phase-3 and Phase-4 payloads are
                      UNCOMMITTED in the working tree (7 tracked M + 13
                      untracked entries; P3-F11 carried) — the executor
                      cannot commit; the receipt's final commit act belongs
                      to the owner.

  final_status:       done-pending-owner-commit   (post-R-4.7a recompute)
                      # contract result vocabulary. Every pipeline stage,
                      # the CLI, the docs, and the full quality suite are
                      # evidenced green; R-4.7a was closed by the bounded
                      # residuals unit (deletion + row recompute) and the
                      # remaining open acts are owner-only: the commit of
                      # the Phase-3/4 payload (P3-F11) — the only blocking
                      # owner act — and the P3-F10 authorship ratification
                      # note (carried, non-gate-blocking).
                      # R1-apply OVERALL = done-pending-owner-commit — same
                      # acts; all five phase gates computed PASS.

  phases:             phase 0: done   — read-only verification; BASELINE_ANOMALIES
                                        effective 0 (ADJ-1 RECONCILED_NOT_COUNTING);
                                        decision envelopes + activation
                      phase 1: done   — GATE_1_9 = PASS (8/8); residuals 1.4/1.8
                                        closed; 1.6 ADJUDICATED_ACCEPT_DEVIATION;
                                        wire format JSONL_CONFIRMED_BY_DESIGN
                      phase 2: done   — GATE_2_8 = PASS (11/11; R-2.7 closed by
                                        residuals unit with live mutation kills)
                      phase 3: done   — GATE_3_9 = PASS (5/5 recomputed after
                                        R-3.9a/b; R-3.9c RESOLVED_BY_OWNER_ADJUDICATION
                                        option A; EVIDENCE_INTEGRITY = VALID,
                                        3/3 byte-MATCH corroboration)
                      phase 4: done    — GATE_4_7 = 8/8 (post-R-4.7a recompute;
                                        close-time 7/8, row 3 UNMET →
                                        R-4.7a closed by bounded residuals unit;
                                        suite re-verified green)

  commands:           (all uv invocations --no-sync; every run exit 0 unless noted)
                      per-phase gate suites:
                        P1: pytest 140 passed cov 100.00% · mypy 19 files · ruff
                        P2: pytest 251 passed cov 100.00% · mypy 20 files · ruff
                            (R2.7/02-03 mutation kills: exit 1 BY DESIGN — a kill
                            is the test failing under mutation, core byte-untouched)
                        P3: pytest 337 passed cov 100.00% · mypy 20 files · ruff ·
                            golden machinery verify exit 0 plain AND python -I
                        P4 close (this unit):
                        4.7/01 pytest --cov → 406 passed, 100.00% (634 stmts,
                            212 branches, 0 missed), exit 0
                        4.7/02 mypy --strict src → 22 source files, exit 0
                        4.7/03 ruff check src tests → All checks passed!, exit 0
                        4.7/07 golden determinism scoped → 16 passed, exit 0
                        4.7/08 CLI cross-run (PYTHONHASHSEED 0/random/12345) →
                            exit 0 ×3; bytes mutually identical AND equal to the
                            golden standard_mixed document (e7b5b03f…8abc)
                        4.7/09 CLI fault legs → contract fault exit 3 (2 stderr
                            lines, empty stdout); unreadable INPUT exit 2; unknown
                            --mode exit 2 (argparse)
                        4.7/12 pytest no-cov re-run → 406 passed in 1.27s, exit 0
                        R-4.7a close (post-R-4.7a recompute, 21:45Z):
                        pre-state check → wc -c = 0 bytes AND git ls-files
                            tracked (design-named placeholder confirmed)
                        deletion → rm executed, no hook interference;
                            git status shows ` D src/.../adapters/README.md`
                        row-3 recompute → fd zero-byte scan over the four
                            gate dirs = 0; src-wide = 2 (core/__init__.py +
                            py.typed, both clean at HEAD, outside gate scope)
                        suite re-run → pytest --cov 406 passed cov 100.00%
                            (634/212/0 missed) · mypy --strict 22 files exit 0 ·
                            ruff src tests exit 0

  e2e_matrix:         Gate Checklist rows 1–8 (table above):
                        1 baseline: PASS (carried, ADJ-1)   5 quality: PASS
                        2 decision: PASS (carried)          6 determinism: PASS
                        3 scaffold: PASS (post-R-4.7a       7 fail-closed: PASS
                          recompute, 0 zero-byte            8 diagnostics: PASS
                          in gate scope)                                        (orphans = 0)
                        4 deps: PASS (0 runtime)

  evidence_integrity: VALID — golden corpus (3 scenarios, manifest + document and
                      input digests) verified by 16/16 tests; the independently
                      authored expected sample is PRESENT, self-consistent, and
                      CORROBORATES the implementation goldens byte-for-byte
                      (post-R-3.9c option-A re-derivation; 3/3 cmp MATCH,
                      machinery verify VALID exit 0 plain AND python -I).
                      Carried caveat: authorship ratification (P3-F10) remains
                      an owner act; a substituted hand-authored sample would
                      re-verify against the same digests.

  failures_recovery:  (complete ledger, in order)
                      F1 Phase 0 — contract-conformance audit FAIL (1×P0, 5×P1,
                         12×P2): RECOVERED engram #7247 (18/18 findings, 5 files)
                         + post-repair consistency check PASS.
                      F2 Phase 0 — CRC ticket audit: RECOVERED by mini-customs
                         closure (engram #7250 fixes + #7251 owner 6/6
                         adjudications; post-adjudication consistency PASS).
                      F3 Phase 0 — baseline drift anomalies (conftest.py,
                         fixtures/, golden/, uncommitted pyproject+test_ir):
                         RECONCILED_NOT_COUNTING by owner ADJ-1 → effective 0.
                      F4 Phase 1 — gate 1.9 first computed with residuals
                         (1.8 .gitignore, 1.4 docstrings, 1.6 letter deviation):
                         1.8/1.4 RECOVERED by the bounded residuals unit; 1.6
                         owner-ADJUDICATED_ACCEPT_DEVIATION (inline corpus).
                      F5 Phase 1 — owner-draft conflict (Unit 1): owner draft
                         files quarantined, never overwritten
                         (outputs/quarantine-unit1-conflict/*.owner-draft.md).
                      F6 Phase 2 — R-2.7: task 2.7 executed by no Phase-2 unit →
                         gate first 10/11 BLOCKED; RECOVERED by the bounded
                         residuals unit (tautology deleted; frozen-empty-default
                         pin + in-place-mutation pin; live mutation kills M1/M2;
                         core/policy.py byte-untouched) → recomputed 11/11.
                      F7 Phase 3 — gate 3.9 first 4/5 BLOCKED: R-3.9a (3 stale
                         U4 tests) + R-3.9b (machinery multi-scenario manifest
                         reader) RECOVERED by the residuals unit; R-3.9c glyph
                         divergence RESOLVED_BY_OWNER_ADJUDICATION (option A,
                         bracket form [<source_kind> <source_ref>]; independent
                         sample re-derived; 3/3 byte-MATCH).
                      F8 Phase 4 — R-4.7a (close-time record): adapters/
                         README.md deletion (design.md File Changes row)
                         executed by no unit → gate row 3 = 1 ≠ 0 →
                         ENUMERATED. RESOLVED post-close (21:45Z) by the
                         bounded residuals unit under owner authorization
                         (R-2.7 precedent): pre-state verified (0 bytes +
                         tracked), deletion executed (no hook interference),
                         row recomputed → 0 → PASS; suite re-verified green.
                      M5.2 crash/restart: never triggered (no executor crash);
                      the single-executor/idempotent-recompute policy held —
                      every gate in R1 was recomputable from repository state.

  human_decisions:    (consolidated ledger — 22 recorded owner decision acts,
                      grouped; none executor-authored)
                      APPROVAL RECORDS ×5: PHASE_0 ("sdd apply ahora"),
                      PHASE_1, PHASE_2, PHASE_3, PHASE_4 ("continuemos con a y
                      luego autorizo fase 4", precondition = option A executed;
                      APPROVAL-PHASE4.md) — each naming exactly its phase,
                      work-unit mode, reviewer ≠ executor.
                      PHASE-0 DECISION GATE ×6 (closed in APPROVAL-PHASE1,
                      mirrored in state.yaml): ADJ-1 baseline-drift counting →
                      RECONCILED_NOT_COUNTING; INPUT_CONTRACT_DECISION =
                      STRUCTURED_FEED_ONLY; POLICY_SEED_DECISION =
                      DEFERRED_BY_OWNER; CLI surface → CONFIRM_AS_DESIGNED;
                      ADJ-2 gitignore widening (.pi/ + _ctx/) → APPLIED;
                      PHASE_1_AUTHORIZATION = AUTHORIZED_WORK_UNIT_MODE.
                      CRC MINI-CUSTOMS ×7 (owner adjudications 2026-08-28,
                      engram #7251 6/6 applied + CRC-004 via ticket coverage):
                      CRC-001 taxonomy RETAIN_FOR_COMPATIBILITY, auto mapping
                      (monitor/lab→CONFIRMED) REJECTED, PROBABLE/LIKELY/UNLIKELY
                      NOT_PRODUCED; CRC-002 BOTH_SEPARATED authority model;
                      CRC-003 CanonicalClinicalIR additive core/ir.py aggregate
                      (D10); CRC-004 dangling-ref absorption (impossible-by-
                      construction + renderer defense-in-depth); CRC-005
                      UNRESOLVED_POLICY fail-closed (no silent empty set);
                      CRC-006 DEFER_CORE_TYPE_NARROWING_TO_R2 +
                      ENFORCE_BOUNDED_VALUES_AT_RUNTIME; CRC-010 lineage
                      SUCCESSOR_OF_V0_5.
                      OWNER-DELEGATED ADJUDICATIONS ×3 (2026-08-29, Phase-1
                      closure): task 1.6 → ADJUDICATED_ACCEPT_DEVIATION
                      (ACCEPT_INLINE_CORPUS); WIRE_FORMAT →
                      JSONL_CONFIRMED_BY_DESIGN (FC-03 authority; README
                      corrected); .mimosa tracked-file index-untracking
                      APPROVED (staged).
                      GLYPH RULING ×1 (2026-08-29): R-3.9c option A —
                      provenance bracket form [<source_kind> <source_ref>]
                      (implementation form upheld; no golden re-freeze;
                      independent sample re-derived under the closed rule).

  protected_surfaces: core diff vs c6578b6 (verified 4.7/13): EXACTLY
                      core/ir.py +60/−0 — the adjudicated additive
                      CanonicalClinicalIR (CRC-003/D10, the only permitted core
                      change); core/{types,diagnostics,policy}.py untouched;
                      working tree adds ZERO further core change vs HEAD.
                      core retains 100% coverage (4/4 files). Side-effect
                      budget: BEFORE/AFTER snapshots of this close unit
                      identical (4.7/00 vs 4.7/13) — no venv, no installs, no
                      network, no process starts; every uv --no-sync; zero
                      UNKNOWN outcomes across R1.

  regression:         branch coverage: 100.00% (212 branches, 0 missed) —
                      ≥ 95.0 gate and ≥ baseline core 100% (core files
                      individually 100%). Suite growth 140 → 251 → 337 → 406
                      (+269 test cases over R1), all green at each close.
                      Changed files at receipt: 20 working-tree entries
                      (7 tracked M: README.md, docs/architecture.md,
                      state.yaml, pyproject.toml, linter/conformance.py,
                      passes/document_selection.py, renderers/deterministic.py;
                      13 untracked incl. cli.py, pipeline.py, 5 new/changed
                      test files, golden corpus + independent sample,
                      APPROVAL-PHASE3/4, phase3-close) — the Phase-3/4 payload
                      awaiting the owner's commit (P3-F11).

  residual_risk:      (still-open owner items — none suppresses evidence;
                      R-4.7a DROPPED from this list: closed 21:45Z by the
                      bounded residuals unit, see F8 and Gate row 3)
                      1. P3-F10: independent-sample authorship (subagent
                         re-derivation under closed rule A) awaits owner
                         ratification as a designated audit path, or
                         substitution by a hand-authored sample (permitted
                         any time; re-verifies against the same digests).
                      2. P3-F11: Phase-3/4 payload entirely uncommitted — the
                         receipt's subject commit is the owner's act; until
                         then the final HEAD does not reference phases 3–4.
                         The ONLY blocking owner act for R1-apply completion.
                      3. Accumulated minimal-faithful readings (adjudication-
                         pending, none gate-blocking): Phase-2 flags #1–#14
                         (14) + Phase-3 flags P3-F1..F8 (8) + Phase-4 flags
                         P4-F1..F4 (4) = 26 readings, plus the recorded
                         naming/placement deviation families (P1/P2/P4-F5).
                      4. Golden corpus pins the glyph rule (option A): a
                         future owner glyph change ⇒ golden re-freeze +
                         independent re-derivation (documented path).
                      5. One-time CoverageWarning (module-not-measured) in the
                         first cov run of 4.7/01 — absent on re-run; coverage
                         table itself measured all 22 files at 100%. Recorded
                         as an observation, not a risk.

  r2_debt:            (explicitly deferred to R2, by owner adjudication or
                      frozen scope)
                      - CRC-006 core type narrowing: ClinicalValue.value stays
                        Any; the RUNTIME value boundary is enforced now
                        (ENFORCE_BOUNDED_VALUES_AT_RUNTIME), the TYPE-level
                        narrowing is deferred.
                      - Free-text telegraphic adapter: absent in R1 (input
                        contract STRUCTURED_FEED_ONLY); free text →
                        INPUT_CONTRACT_ERROR.
                      - CLI surface extensions: stdin input, --json, check
                        verb (frozen R1 surface = compile INPUT only).
                      - NOT_APPLICABLE interpretation row: unreachable in R1
                        (no absence marker in the frozen structured contract).
                      - Destination-write fault mapping: currently exit-70
                        catch-all (P4-F4); an exit-2 reclassification would be
                        an owner decision.

  next_transition:    1) DONE 21:45Z — R-4.7a closed by the bounded residuals
                         unit (deletion + Gate 4.7 row 3 recompute → 8/8 →
                         PHASE_4 done), per R-2.7 precedent under owner
                         authorization.
                      2) sdd-verify (spec conformance across all 7 domains) —
                         authorized AFTER Phase-4 close, per APPROVAL-PHASE4
                         NOT-authorized clause.
                      3) Owner commit of the Phase-3/4 payload (P3-F11) —
                         pinned as the receipt's final subject commit; the
                         commit set now also includes the R-4.7a deletion.
                      4) sdd-archive (R1 close) → R2 intake (r2_debt above).
```

## Phase report (contract vocabulary: done|partial|blocked|failed)

```text
phase_report:
  phase: 4
  status: done
  executive_summary: Phase-4 units 1-3 verified done (pipeline.py composition root with the production is_resolved D7 branch + fail-closed emission gate + pure derive_exit_code; cli.py frozen argparse surface with atomic --output and stable stderr diagnostics; README 385 lines + architecture.md 179 lines incl. the complete 0/2/3-10/70 exit-code table and determinism mechanism; [project.scripts] registered, dependencies still zero) and gate 4.7 CLOSED: computed 7/8 at close time with row 3 UNMET (adapters/README.md 0-byte tracked placeholder whose design.md File Changes row records DELETE, enumerated residual R-4.7a) — then R-4.7a was closed by the bounded residuals unit 21:45Z under owner authorization (pre-state verified 0 bytes + git-tracked; deletion executed, no hook interference; row recomputed via fd zero-byte scan over the four gate dirs = 0; supplementary src-wide scan = 2 conventional artifacts clean at HEAD, outside gate scope) → GATE_4_7 = 8/8, PHASE_4 = done; suite re-verified post-deletion (pytest 406/406 cov 100.00% 634/212/0, mypy strict 22 files, ruff clean); R1 FINAL RECEIPT (M10.3) final_status = done-pending-owner-commit — the only blocking owner act is the payload commit (P3-F11, now including the R-4.7a deletion) plus the P3-F10 authorship-ratification note; R1-apply overall = done-pending-owner-commit.
  artifacts: [openspec/changes/clinical-compiler-r1/outputs/phase4-close.md]
  evidence: [4.7/00 BEFORE git status 21:33:03Z · 4.7/01 pytest --cov 406 passed cov 100.00% (634 stmts/212 branches/0 missed) exit 0 · 4.7/02 mypy --strict "Success: no issues found in 22 source files" exit 0 · 4.7/03 ruff "All checks passed!" exit 0 · 4.7/04 zero-byte scan at close → exactly 1 (adapters/README.md, tracked, design says Delete) · 4.7/05 pyproject tomllib parse → [project].dependencies ABSENT (⇒ 0), scripts {"clinical-compiler": "clinical_compiler.cli:main"} · 4.7/06 DiagnosticCode census → 8/8 codes: production sites 23/3/2/2/3/3/5/11, test refs 47/23/15/16/13/16/22/45, orphans 0 · 4.7/07 golden scoped pytest 16 passed exit 0 · 4.7/08 CLI cross-run seeds 0/random/12345 → exit 0 ×3, cmp byte-identical across runs and vs golden (e7b5b03fa6d9f150c081684846fb481b7dfda02ebdd24992a7fba164c88b8abc) · 4.7/09 CLI fault legs → exit 3 (INPUT_CONTRACT_ERROR + DOCUMENT_SELECTION_ERROR on stderr, empty stdout), unreadable INPUT exit 2, unknown --mode exit 2 · 4.7/10 FC/PC census → FC-01..FC-12 (3–11 refs each) + PC-1×11 + PC-2×13 · 4.7/11 docs census → README 385 lines with exit-code rows 0/2/3-10/70 (lines 250-260), architecture.md 179 lines with determinism mechanism + NOT_PRODUCED · 4.7/12 pytest no-cov re-run 406 passed in 1.27s exit 0 (no warning) · 4.7/13 core diff vs c6578b6 = ir.py +60 only; working tree adds no core change; AFTER git status == BEFORE · R-4.7a close (21:45:41Z) pre-state: wc -c = 0 bytes, git ls-files tracked, design-named placeholder confirmed · deletion: rm ok, no hook; git status ` D src/clinical_compiler/adapters/README.md` · row-3 recompute: fd --size 0b over {passes,linter,renderers,adapters} = 0; src-wide = 2 (core/__init__.py, py.typed — clean at HEAD, outside gate scope); adapters/ = __init__.py 84 B + contract.py 8.5k + seed.py 12k + structured_feed.py 3.7k · suite re-run: pytest --cov 406 passed cov 100.00% (634/212/0 missed) in 1.35s + mypy --strict exit 0 (22 files) + ruff exit 0]
  failures_recovery: [R-4.7a ENUMERATED at close (21:33Z), RESOLVED 21:45Z by the bounded residuals unit under owner authorization (R-2.7 precedent): pre-state verified → deletion executed (no hook interference) → gate row recomputed 0 → PASS → suite re-verified green; all other Phase-4 gates computed without failure; historical F1-F8 ledger consolidated in the Final Receipt]
  human_decisions: [APPROVAL-PHASE4.md — PHASE_4 authorized work-unit mode (option-A precondition verified: 3/3 cmp MATCH, EVIDENCE_INTEGRITY VALID), units 1-4, executor commits prohibited, sdd-verify/archive NOT authorized by this record; owner authorization for the bounded R-4.7a residuals unit per the R-2.7 precedent; full 22-act owner decision ledger consolidated in the Final Receipt (5 approval records, 6 decision-gate resolutions, 7 CRC adjudications, 3 owner-delegated closures, R-3.9c glyph option A)]
  residual_risk: [P3-F10 independent-authorship ratification · P3-F11 Phase-3/4 payload uncommitted (final HEAD 470fef5 predates phases 3-4; commit set now includes the R-4.7a deletion) — the ONLY blocking owner act · 26 accumulated minimal-faithful readings adjudication-pending (P2 #1-14, P3 F1-F8, P4 F1-F4) + naming/placement deviation families · glyph-rule-A pin on the golden corpus · one-time CoverageWarning observation (absent on re-run, coverage table complete)]
  next_recommended: sdd-verify (all 7 specs) → owner commit of the Phase-3/4 payload incl. the R-4.7a deletion (P3-F11, the receipt's final subject commit) → sdd-archive → R2 intake (r2_debt)
```

---

**GATE_4_7 = 8/8 PASS (post-R-4.7a recompute). PHASE_4 = done — the
close-time 7/8 was honestly partial, then R-4.7a was bounded-recovered
under owner authorization and the row recomputed from fresh evidence.
R1-apply OVERALL = done-pending-owner-commit, blocked on exactly one
owner act (P3-F11 commit of the Phase-3/4 payload, now including the
R-4.7a deletion) plus the P3-F10 ratification note; every pipeline,
CLI, docs, determinism, fail-closed, and quality property of R1 is
evidenced green at 406/406 with 100.00% branch coverage, mypy strict,
ruff clean, byte-identical cross-run goldens, zero orphan diagnostics,
and a VALID corroborated golden evidence chain.**
