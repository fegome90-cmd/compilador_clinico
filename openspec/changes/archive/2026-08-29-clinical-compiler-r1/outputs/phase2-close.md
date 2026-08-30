# Phase 2 Close — Gate 2.8 Report (change: clinical-compiler-r1)

Executor: sdd-apply unit (PHASE_2 CLOSE). Unit scope: compute gate 2.8
with fresh evidence and write this report. Read-only for src/tests; sole
writes: this file + one engram save (topic
`sdd/clinical-compiler-r1/apply-progress`). No commit; no tasks.md /
state.yaml / approval-record mutation; hash-bound bundle untouched.

ADDENDUM (2026-08-29, sdd-apply R-2.7 RESIDUALS unit): the single
gate-blocking item computed below (item 2 — RESIDUAL R-2.7) was closed
by the bounded residuals unit (sole src/tests write:
`tests/unit/test_policy.py`); item 2 and the gate verdict were
RECOMPUTED from fresh evidence (run IDs `R2.7/*`) and this report now
records the final state — `GATE_2_8 = PASS`, `PHASE_2 = done`. The
original close-time findings are preserved verbatim; addendum-marked
sections record what changed.

All commands run 2026-08-29 (UTC below), every `uv` invocation
`--no-sync` (no environment mutation; no install/sync attempted; zero
`UNKNOWN` outcomes). Every verdict below is computed from captured
evidence — nothing assumed, nothing inherited from unit reports without
re-verification where the gate demands it.

Gate semantics per `specs/phase0-verification/spec.md` and the tasks.md
result vocabulary: `UNKNOWN` never yields PASS; a named gate item that is
unmet blocks the gate and is enumerated — never silently passed.

## Gate 2.8 — item-by-item evidence table

Literal gate definition: tasks.md task 2.8 (11 named items).

| # | Gate item (tasks.md 2.8) | Command(s) + run ID | Exit | Key evidence | Verdict |
|---|--------------------------|---------------------|------|--------------|---------|
| 1 | `PROVENANCE_ERROR` orphan eliminated (producing stage + covering test) | `rg -n "PROVENANCE_ERROR" src/clinical_compiler/{passes,adapters}` (`2.8/02`, 2026-08-29T18:51Z) · `rg -c "PROVENANCE_ERROR" tests/unit/` (`2.8/03`) | 0 | Producing stage: `passes/admissibility.py:136` (unresolvable refs arm) + `:147` (absent-refs arm) — `DiagnosticCode.PROVENANCE_ERROR`. Covering tests: `tests/unit/test_passes_admissibility.py` 7 occurrences — `test_unresolvable_refs_yield_provenance_error` (FC-08), `test_partially_unresolvable_refs_still_block`, `test_absent_refs_yield_provenance_error`, `test_fact_with_both_faults_emits_both_codes_and_quarantines_once`. Baseline orphan (task 0.7 finding: `PROVENANCE_ERROR` with no producing stage) eliminated. | PASS |
| 2 | tautology replaced | scoped `pytest tests/unit/test_policy.py -v` (`R2.7/01`, 2026-08-29T18:58:17Z) · mutation-kill runs (`R2.7/02-03`) · full suite (`R2.7/04`) | 0 / 1 / 1 / 0 | Tautology `test_never_auto_terms_vetoes_membership` DELETED and replaced by 3 content-bearing tests in `tests/unit/test_policy.py` (R-2.7 closure): `test_never_auto_terms_is_an_immutable_string_set` (frozenset-of-str type pin, kept as-is), `test_never_auto_terms_is_the_frozen_empty_default` (`NEVER_AUTO_TERMS == frozenset()` — the D7 frozen empty default), `test_never_auto_terms_membership_cannot_be_mutated_in_place` (`.add` must raise `AttributeError` — no in-place membership mutation). LIVE mutation kills, in-memory shadow of the module binding (`core/policy.py` byte-untouched, diff empty at `R2.7/07`): M1 populated default → frozen-empty pin FAILED (exit 1); M2 plain-`set` binding (empty, so set equality passes and only type/immutability pins can catch it) → type pin AND in-place pin FAILED (exit 1). Veto-ENFORCEMENT mutation kill already evidenced (U3 suite + Unit-5 live kill, engram #7256) — complemented, not duplicated. Suite 251 passed (2 tests replaced 1). | **PASS (recomputed 2026-08-29T18:58Z after R-2.7 closure; was UNMET at first computation 18:51Z)** |
| 3 | executor-authored clinical policy content == 0 | `rg -n "\"terms\"\|terms:" src/ tests/fixtures/` + `rg -ni "consent\|resuscitat\|do-not\|dnr\|next-of-kin" src/ tests/fixtures/` (`2.8/06`) | 0 | Sole term content in executor artifacts: `tests/fixtures/policy-seed-sample.json` = `{"terms": ["test-veto-term-alpha", "test-veto-term-beta"]}` — self-evidently synthetic test placeholders, not clinical content. Clinical-term sweep: zero matches in src/tests/fixtures. `core/policy.py` untouched (`git diff` empty, `2.8/07`); `NEVER_AUTO_TERMS` stays the frozen empty default. | PASS |
| 4 | no `UNRESOLVED_POLICY` state passes the gate (no silent empty-set path) | scoped run `pytest test_adapters_seed.py::test_unresolved_never_carries_terms_or_continues test_integration_phase2_chain.py::test_unresolved_policy_blocks_gate_with_no_silent_empty_set …` (`2.8/08`) · code read `adapters/seed.py` | 0 | `PolicyResolution.__post_init__` invariants (seed.py:149-176): `UNRESOLVED_POLICY` carries NO terms + REQUIRED typed fault; approved-empty exists ONLY via `approved_empty_by_deferral(decision_record)` which rejects citations not naming `DEFERRED_BY_OWNER` (seed.py:212-217) — uncited empty policy unrepresentable even via direct construction (`test_direct_construction_cannot_forge_approved_empty`). Scoped tests passed; full suite green. Loader faults (missing/unreadable/malformed/wrong-shape/non-string/empty-term) all resolve `UNRESOLVED_POLICY`, never populated-empty (6 dedicated tests). | PASS |
| 5 | `compiler_assigned_certainty` is `UNRESOLVED` for every canonical fact | scoped run (`2.8/08`): `test_certainty_is_unresolved_for_every_admissible_input`, `test_every_source_kind_yields_unresolved_certainty` (parametrized over the full `source_kind` vocabulary), integration `test_declared_assertions_never_upgrade_compiler_certainty_across_chain` | 0 | `passes/semantic_normalization.py:145` — the ONLY certainty construction site: `certainty=Certainty.UNRESOLVED` (hardcoded, unconditional; no code path reads `source_kind` for certainty). 20/20 scoped cases passed. | PASS |
| 6 | rejected automatic mapping (`monitor/lab → CONFIRMED`, `clinical_note → PROBABLE`) appears nowhere as executable semantics | `rg -n "source_kind" src/` (`2.8/05`) · `rg -n "PROBABLE\|LIKELY\|UNLIKELY" src/{passes,adapters}` (`2.8/04`) · `rg -n "CONFIRMED" src/{passes,adapters}` | 0 | Every `source_kind` hit is provenance validation (contract.py:184-195 vocabulary check; input_validation.py:64-72) or docstring. `PROBABLE`/`LIKELY`/`UNLIKELY`/`CONFIRMED` appear in passes/adapters ONLY inside module docstrings (semantic_normalization.py:13-14; admissibility.py:22,111) — zero executable references. No mapping table exists anywhere in src. | PASS |
| 7 | NOT_PRODUCED invariant for `PROBABLE`/`LIKELY`/`UNLIKELY` covered by tests | scoped run (`2.8/08`): `test_reserved_certainty_states_are_not_produced` + integration `test_declared_assertions_never_upgrade_compiler_certainty_across_chain` | 0 | Dedicated unit test asserts the reserved states are never produced for any admissible input; the integration test pins the whole-chain NOT_PRODUCED set (declared "probable" in input stays a verbatim wrapper assertion, never a compiler assignment). Passed. | PASS |
| 8 | certainty authority model holds — `BOTH_SEPARATED` distinct fields with covering tests (CRC-002) | `rg -n "source_asserted_certainty" src/` (`2.8/09`) · scoped run (`2.8/08`): `test_declared_certainty_never_becomes_compiler_certainty` | 0 | Two distinct fields on distinct types: `source_asserted_certainty: Certainty \| None` on the adapter wrapper `StructuredFeedFact` (contract.py:102, captured verbatim, never overwritten) vs the compiler axis `ClinicalValue.certainty` assigned only by the normalizer. Wrapper certainty never enters `run_semantic_normalization` (input type is `tuple[SourceFactIR, ...]`). Covering tests green (unit + chain). | PASS |
| 9 | `CanonicalClinicalIR` additive `core/ir.py` aggregate, all construction-time invariants covered by tests (CRC-003) | `git diff --stat HEAD -- src/clinical_compiler/core/` (`2.8/07`) · read `core/ir.py:75-132` · `pytest tests/unit/test_ir.py --collect-only` (`2.8/10`) | 0 | Diff: `core/ir.py` +60/−0 (purely additive; `types.py`/`policy.py`/`diagnostics.py` untouched). Invariants in `__post_init__`: duplicate `clinical_fact_id` → ValueError; lineage boundary (no refs / empty-string ref → ValueError); canonical `(field_id, clinical_fact_id)` sort at construction. Covering tests (8 new cases in `test_ir.py`, collected 15 = 7 baseline + 8): duplicate-ids, lineage ×2 params, facts-only/no-`document_mode` (+ constructor rejects the kwarg), deterministic representation (forward==backward), frozen, empty-set valid, MINIMAL plain frozen dataclass. | PASS |
| 10 | runtime value boundary holds — no value outside the frozen field contract becomes an admissible canonical value (CRC-006) | `rg -n "def test_.*(boundary\|arbitrary)" tests/unit/test_passes_input_validation.py tests/unit/test_adapters_contract.py` (`2.8/12`) · full-suite run (`2.8/13`) | 0 | Boundary enforcement at adapters + validation (Phase-1 CRC-006 tests still present and green: `test_arbitrary_object_raw_value_is_type_error` in both test_adapters_contract.py:220 and test_passes_input_validation.py:208). Phase-2 adds NO value-admission path: `run_semantic_normalization` consumes only validation survivors (`tuple[SourceFactIR, ...]`) and copies `first.raw_value` verbatim; admissibility filters, never constructs values; `CanonicalClinicalIR` carries facts unchanged. | PASS |
| 11 | quality suite green | `uv run --no-sync pytest` (`2.8/13`, 2026-08-29T18:52Z) · `uv run --no-sync mypy src` (`2.8/14`) · `uv run --no-sync ruff check src tests` (`2.8/15`) | 0 / 0 / 0 | `250 passed in 0.17s`; `Required test coverage of 95.0% reached. Total coverage: 100.00%` (TOTAL 346 stmts, 120 branches, 0 missed). `Success: no issues found in 20 source files` (strict). `All checks passed!`. | PASS |

**GATE_2_8 = PASS** (recomputed 2026-08-29T18:58Z, R-2.7 residuals
unit) — 11 of 11 named items computed PASS from fresh evidence. At the
first computation (2026-08-29T18:51Z, close unit) the gate was BLOCKED
at 10/11 with item 2 ("tautology replaced") UNMET and reported as
RESIDUAL R-2.7 per the honest-arithmetic rule (an item referencing work
Phase 2 assigned but not done is neither silently passed nor silently
failed). The residuals unit below closed R-2.7 exactly as the recovery
specified, and item 2 was recomputed PASS from fresh mutation-kill
evidence (`R2.7/01-04`). No other item was touched: items 1, 3-11 stand
on the close unit's evidence unchanged, and item 11's quality suite was
re-run green at the new 251-test count (100.00% branch coverage, mypy
strict, ruff clean) — `R2.7/04-06`.

## Residual R-2.7 (the single gate-blocking item) — RESOLVED 2026-08-29T18:58Z

- **What**: task 2.7 — "Replace the tautological test in
  `tests/unit/test_policy.py` with content-bearing, mutation-sensitive
  tests" — was not executed by any Phase-2 unit (it does not appear in
  the APPROVAL-PHASE2 owner-defined unit sequence, and no unit report
  claims it). `test_never_auto_terms_vetoes_membership`
  (test_policy.py:12-19) remains in the suite: a vacuous test that
  cannot fail.
- **Substance already present** (why this is MEDIUM, not HIGH): the
  mutation-sensitivity the task exists for is delivered elsewhere and
  evidenced — (a) veto-ENFORCEMENT mutation is killed by
  `test_passes_admissibility.py` (dedicated POLICY_VIOLATION
  assertions) and was demonstrated live by Unit 5 (veto-disabling
  mutation → integration test FAILED, byte-exact revert; engram #7256);
  (b) core-constant CONSULTATION mutation is killed by design pin
  `test_stage_never_reads_the_core_policy_constant` (monkeypatches
  `NEVER_AUTO_TERMS` to `{"estable"}`, asserts no behavior change — D7:
  the injected parameter is the only veto source); (c) effective-set
  fidelity is pinned by `test_adapters_seed.py`
  (`test_owner_seed_file_loads_populated`,
  `test_loaded_seed_feeds_admissibility_veto`).
- **Gap that remains**: (a) a vacuous test still runs in the suite
  (hygiene debt, flagged as an anomaly by task 0.7 hygiene inventory);
  (b) NO test pins the frozen-empty default itself — mutating
  `NEVER_AUTO_TERMS` membership (adding a term) is caught by nothing,
  so the diagnostics-policy spec scenario "mutation of policy
  membership → ≥1 test failure" holds only via the D7 design reading
  (constant unread ⇒ membership mutation is behavior-dead), not via a
  membership assertion.
- **Severity**: MEDIUM (substance covered; letter unmet; suite carries
  a known-vacuous test).
- **Recovery** (bounded, ~5 lines, Phase-1 residuals-unit precedent):
  replace `test_never_auto_terms_vetoes_membership` with a
  content-bearing pin, e.g. `assert NEVER_AUTO_TERMS == frozenset()`
  (frozen empty default per D7) — that single assertion is
  membership-mutation-sensitive and simultaneously satisfies the spec
  scenario literally; keep the type-shape test as-is or fold it in.
  Then recompute item 2 → expected GATE_2_8 = PASS. This unit is
  read-only for tests, so the write is NOT performed here.

### R-2.7 RESOLUTION (bounded residuals unit, 2026-08-29T18:58Z)

- **Write performed**: exactly the recovery specified above — sole
  src/tests write `tests/unit/test_policy.py`. Tautology
  `test_never_auto_terms_vetoes_membership` deleted; replaced by
  `test_never_auto_terms_is_the_frozen_empty_default`
  (`assert NEVER_AUTO_TERMS == frozenset()` — the frozen empty default
  per D7) plus
  `test_never_auto_terms_membership_cannot_be_mutated_in_place`
  (`pytest.raises(AttributeError)` on `.add` — the in-place mutation
  operator itself is unavailable); type-shape test
  `test_never_auto_terms_is_an_immutable_string_set` kept as-is (the
  note's "keep as-is" option). 2 tests replaced 1 → suite 250 → 251.
  The placeholder term used in the in-place test is synthetic
  (`test-veto-term-placeholder`), matching the fixture precedent — no
  executor-authored clinical content.
- **Mutation kills evidenced live** (in-memory shadow of the module
  binding inside a short-lived interpreter — `core/policy.py`
  byte-untouched throughout; `git diff HEAD -- core/policy.py` empty at
  `R2.7/07`):
  - M1 populated default `frozenset({'test-veto-term-alpha'})` →
    `test_never_auto_terms_is_the_frozen_empty_default` FAILED
    (`R2.7/02`, 2026-08-29T18:58:25Z, exit 1). This closes the gap
    named above: membership mutation now fails a test DIRECTLY, no
    longer only via the D7 constant-unread design reading.
  - M2 mutable plain-`set` binding — deliberately EMPTY, since
    `set() == frozenset()` is True and only the type/immutability pins
    can catch it → BOTH `test_never_auto_terms_is_an_immutable_string_set`
    and the in-place pin FAILED (`R2.7/03`, 18:58:30Z, exit 1).
    (M3 populated plain set is killed by the union of M1's equality
    pin and M2's type pins.)
  - Veto-ENFORCEMENT mutants: killed by the U3/U5 evidence already on
    record (U3 POLICY_VIOLATION suite + Unit-5 live kill, engram #7256)
    — complemented, not duplicated.
- **Verification** (`R2.7/04-06`, all `--no-sync`): `pytest` →
  `251 passed in 0.13s`, `Required test coverage of 95.0% reached.
  Total coverage: 100.00%` (346 stmts, 120 branches, 0 missed), exit 0;
  `mypy src` → `Success: no issues found in 20 source files`, exit 0;
  `ruff check src tests` → `All checks passed!`, exit 0.
- **Spec scenario "Mutation detected"**: satisfied literally —
  policy-membership mutation fails ≥1 test (`R2.7/02-03`); veto-
  enforcement mutation fails ≥1 test (Phase-2 record, U3/U5).
- **Scope discipline**: BEFORE snapshot (`R2.7/00`, captured pre-write
  and bounded by the first stamped command `R2.7/01` 18:58:17Z) and
  AFTER snapshot (`R2.7/07`, 18:58:46Z) identical except
  `tests/unit/test_policy.py` (+ the addendum edits to this report
  file). No core/ write, no other src/tests file, no bundle /
  APPROVAL-* / state.yaml touch, no commit, no env mutation.

## Unit summary (APPROVAL-PHASE2 work-unit sequence, owner-defined)

All Phase-2 code sits UNCOMMITTED in the working tree (commits are
owner-orchestrated acts; APPROVAL-PHASE2 "NOT authorized: any git
mutation by executors"). HEAD remains `267258b`.

| Unit | Scope (tasks) | Result | Test cases (collected) | Files |
|------|---------------|--------|------------------------|-------|
| P2-U1 | `CanonicalClinicalIR` additive aggregate + construction invariants (2.1a/2.2a) | PASS | 8 new in `test_ir.py` (file total 15) | `core/ir.py` +60/−0, `tests/unit/test_ir.py` |
| P2-U2 | `passes/semantic_normalization.py` — interpretation table, `SEMANTIC_AMBIGUITY_BLOCK`, no certainty invention (2.1/2.2) | PASS | 33 in `test_passes_semantic_normalization.py` | + module (uncommitted) |
| P2-U3 | `passes/admissibility.py` — injected veto (D7) + provenance resolution, `POLICY_VIOLATION`/`PROVENANCE_ERROR` (2.3/2.6) | PASS | 28 in `test_passes_admissibility.py` | + module (uncommitted) |
| P2-U4 | `adapters/seed.py` — seed loader + `UNRESOLVED_POLICY` state machine, `DEFERRED_BY_OWNER` (2.4/2.5) | PASS | 34 in `test_adapters_seed.py` | + module + `tests/fixtures/policy-seed-sample.json` (uncommitted) |
| P2-U5 | Phase-2 chain integration (2.5/2.6) | PASS | 7 in `test_integration_phase2_chain.py` | + test file (uncommitted); engram #7256 |
| CLOSE | gate 2.8 compute + this report (2.8) | BLOCKED on item 2 (R-2.7) | — | this file |
| R-2.7 | Residuals: replace test_policy.py tautology + recompute gate item 2 (2.7/2.8) | PASS | 3 in `test_policy.py` (2 replace 1; suite 251) | `tests/unit/test_policy.py` + this report |

Phase-2 test arithmetic: 8 + 33 + 28 + 34 + 7 = 110 new cases; suite
250 = 140 (Phase-1 close) + 110 — matches observed `250 passed` at the
close computation. After R-2.7 closure (+2 replacement tests, −1
tautology, net +1 in `test_policy.py`): suite 251 = 140 + 110 + 1 —
matches the recomputed `251 passed` (`R2.7/04`).
Interpretation table + covering tests: U2 (33 cases; FC-06 conflict,
PC-2 assessed absence, fail-closed certainty, corroboration merge,
determinism). Injected veto demonstrated: U3 signature
`run_admissibility(facts, veto_terms, source_fact_ids)` — veto arrives
only as a parameter; `core.NEVER_AUTO_TERMS` never read (design pin
test); FC-07 veto-at-CONFIRMED covered by
`test_veto_is_certainty_independent` (parametrized over the full
Certainty enum).

## Consolidated owner-review flags (adjudication-pending, accumulated across Phase-2 unit reports + this close)

None of these blocks gate 2.8 beyond R-2.7 (which is listed as #15);
they are implementation readings of under-specified seams that the
owner should ratify or redirect (risk_policy: ask_on_risk).

| # | Flag | Origin | Substance |
|---|------|--------|-----------|
| 1 | Sort-at-construction | U1 | `CanonicalClinicalIR` canonically orders facts `(field_id, clinical_fact_id)` at construction (deterministic representation choice) |
| 2 | Structural lineage only | U1/U3 | Aggregate validates lineage STRUCTURALLY (non-empty, no empty strings); resolution against surviving `SourceFactIR` lives in admissibility (FC-08) |
| 3 | Id scheme sha256 | U2 | `clinical_fact_id = "{field_id}:{sha256(canonical-JSON [field_id, sorted refs])}"` — deterministic identity scheme of the executor's design |
| 4 | `NOT_APPLICABLE` unreachable | U2 | the interpretation table's `NOT_APPLICABLE` row has no marker in the frozen R1 structured contract — unreachable in Phase 2 (inventing one would be executor-authored clinical semantics) |
| 5 | Merged-provenance first-contributor | U2 | corroborated group's `ClinicalValue.provenance` = FIRST-encountered contributor's (equal authority ⇒ no precedence rule exists) |
| 6 | Corroboration merge by interpretation pair | U2 | merge decided by `(missingness, value)` pair equality; `72` and `72.0` are one interpretation (never a false conflict) |
| 7 | Per-fact ambiguity diagnostics | U2 | a conflicted group emits one `SEMANTIC_AMBIGUITY_BLOCK` PER quarantined fact (not one per field) |
| 8 | `source_fact_ids` required param | U3 | admissibility adds a required, default-less 3rd parameter (ids of surviving source facts) — the frozen design signature `run_admissibility(facts, veto_terms)` does not prescribe how sources reach the stage |
| 9 | Veto substring semantics | U3 | veto match = substring containment in a string value (spec's "containing" wording; equality is the edge case); non-string values never match |
| 10 | Naming divergences | U2/U3/U4 | tasks 2.2/2.6 name `test_semantic_normalization.py`/`test_admissibility.py`; actual files are `test_passes_semantic_normalization.py`, `test_passes_admissibility.py`, `test_adapters_seed.py` (Phase-1 naming convention continued) |
| 11 | Zero-term seed corner | U4 | an owner-authored `{"terms": []}` seed loads `POPULATED` with an empty set (emptiness then traces to the owner's own artifact); stricter reading would reject at the boundary |
| 12 | Seed faults all `UNRESOLVED_POLICY` | U4 | no split between resolution faults and usage errors at the loader layer; exit-2 CLI mapping deferred to the composition root per the frozen Exit-Code Table |
| 13 | Task-2.6 DocumentIR leg deferred | U5 | full-chain scenario's reachable legs (canonical refs → surviving SourceFactIR with original provenance) covered; the `DocumentIR` leg awaits Phase 3 (no DocumentIR producer exists in Phase 2) |
| 14 | `is_resolved` gate is test-only | U5 | the `UNRESOLVED_POLICY`-blocks-the-run branch exists only in the integration test helper; production `pipeline.py` MUST implement the same branch (Phase 4, D7) |
| 15 | **R-2.7 tautology not replaced — RESOLVED 2026-08-29T18:58Z** | CLOSE → R-2.7 residuals unit | closed by the bounded residuals unit exactly per the specified recovery (see R-2.7 RESOLUTION: frozen-empty-default pin + in-place-mutation-rejection pin + live mutation kills M1/M2; suite 251) — no owner adjudication needed |

## Side-effect budget note

- BEFORE snapshot (`2.8/00`, 2026-08-29T18:50:10Z) and AFTER snapshot
  (`2.8/16`, 18:54:09Z) IDENTICAL — both show exactly the pre-existing
  Phase-2 unit writes (5 tracked M: state.yaml, core/ir.py,
  admissibility.py, semantic_normalization.py, test_ir.py; 7 untracked:
  APPROVAL-PHASE2.md, seed.py, policy-seed-sample.json, 4 test files)
  and nothing else. `__pycache__` is gitignored. This unit created no
  src/tests writes, no venv, no installs, no network, no process
  starts; `uv` always `--no-sync` (no failures ⇒ no `UNKNOWN`).
- Executor writes this unit: this report file + one engram save.
- Note (reported, not acted on): the 5 tracked modifications and 7
  untracked files are the complete Phase-2 code payload, awaiting the
  owner's commit decision — the gate does not require a commit
  (APPROVAL-PHASE2 bars executor git mutation), but the Phase-2 work is
  unreferenced by any commit until the owner acts.

## Phase report (contract vocabulary: done|partial|blocked|failed)

```text
phase_report:
  phase: 2
  status: done
  executive_summary: Gate 2.8 computed from fresh evidence across the close unit and the R-2.7 residuals unit: 11/11 named items PASS (PROVENANCE_ERROR orphan eliminated; tautology REPLACED with live mutation-kill evidence — populated-default and mutable-binding mutants each fail ≥1 test with core/policy.py byte-untouched; clinical-policy-content search == 0; no silent empty-set path; UNRESOLVED-everywhere certainty; rejected mapping non-executable; NOT_PRODUCED + BOTH_SEPARATED + CRC-006 covered; CanonicalClinicalIR additive with all invariants tested; 251 passed at 100.00% branch coverage, mypy strict 20 files, ruff clean) → GATE_2_8 = PASS; PHASE_2 = done (first computation 2026-08-29T18:51Z was 10/11 BLOCKED on R-2.7; closed 18:58Z by the bounded residuals unit per the Phase-1 precedent).
  artifacts: [openspec/changes/clinical-compiler-r1/outputs/phase2-close.md]
  evidence: [close unit 2.8/00-16 (first computation 18:51Z — see item table) · R2.7/00 BEFORE git status pre-write, bounded by R2.7/01 at 18:58:17Z, identical to 2.8/16 · R2.7/01 scoped pytest tests/unit/test_policy.py 3 passed exit 0 18:58:17Z · R2.7/02 mutation-kill M1 populated default → frozen-empty-default pin FAILED exit 1 18:58:25Z · R2.7/03 mutation-kill M2 empty plain-set binding → type pin + in-place pin FAILED exit 1 18:58:30Z · R2.7/04 full pytest "251 passed in 0.13s" coverage 100.00% (346 stmts, 120 branches, 0 missed) exit 0 18:58:35Z · R2.7/05 mypy "Success: no issues found in 20 source files" exit 0 18:58:39Z · R2.7/06 ruff "All checks passed!" exit 0 18:58:39Z · R2.7/07 AFTER git status 18:58:46Z = BEFORE + tests/unit/test_policy.py only; core/policy.py diff empty]
  failures_recovery: [R-2.7: task 2.7 not executed by any Phase-2 unit (absent from the owner unit sequence) — RECOVERED by the bounded residuals unit: sole test write test_policy.py (tautology deleted; frozen-empty-default pin + in-place-mutation-rejection pin added; type pin kept); live mutation kills M1/M2 evidenced; suite 250→251]
  human_decisions: [APPROVAL-PHASE2.md — PHASE_2 authorized work-unit mode, units 1-5 + close; owner CRC adjudications 2026-08-28 (CRC-001/002/003/005/006) via engram #7251; APPROVAL-PHASE1.md POLICY_SEED_DECISION=DEFERRED_BY_OWNER cited by seed.py deferral constant; flags table #1-#14 remain adjudication-pending (none gate-blocking); R-2.7 (flag #15) RESOLVED — no adjudication needed]
  residual_risk: [Phase-2 payload entirely uncommitted (6 tracked M + 7 untracked, now including test_policy.py) pending owner commit; is_resolved gate exists only in test code until Phase-4 pipeline.py; DocumentIR leg of the full-chain scenario deferred to Phase 3; NOT_APPLICABLE row unreachable in R1; per-fact ambiguity diagnostics cadence and interpretation-pair merge semantics await owner ratification]
  next_recommended: owner review → commit decision for the Phase-2 payload (6 tracked M + 7 untracked files); Phase 3 activation then requires an updated owner approval record naming Phase 3 per the activation rule — never activation by implication
```

**GATE_2_8 = PASS (11/11; item 2 recomputed 2026-08-29T18:58Z after
R-2.7 closure — mutation kills M1/M2 evidenced live, core/policy.py
byte-untouched). PHASE_2 = done.** Faithful per the result vocabulary —
the path from BLOCKED to `done` runs through a computed recompute with
fresh mutation-kill evidence, not a silent edit.
