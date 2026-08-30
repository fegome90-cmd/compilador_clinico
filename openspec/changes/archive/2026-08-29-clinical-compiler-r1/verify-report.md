# Verify Report — clinical-compiler-r1

**Change**: `clinical-compiler-r1`
**Spec version**: bundle manifest `7a7d3a28…37d` (per-file digests in `state.yaml` / `APPROVAL-PHASE0.md`)
**Verification date**: 2026-08-29 (all commands executed fresh by the sdd-verify agent)
**Verification method**: real execution — full suite with coverage, mypy strict, ruff, golden machinery verify (plain + `python -I`), live CLI round trips and fault legs, per-code orphan sweep, core-diff and hash-binding checks. Nothing asserted without output.

---

## Verification commands + exit codes (fresh evidence)

| # | Command | Result |
|---|---------|--------|
| 1 | `uv run --no-sync pytest --cov=clinical_compiler --cov-report=term-missing --cov-fail-under=95 --strict-markers` | exit 0 — **406 passed**, 0 failed, 0 skipped; TOTAL 634 stmts / 212 branches / **0 missed** = **100.00%** (every one of 22 source files 100%) |
| 2 | `uv run --no-sync mypy --strict src` | exit 0 — `Success: no issues found in 22 source files` |
| 3 | `uv run --no-sync ruff check src tests` | exit 0 — `All checks passed!` |
| 4 | `uv run --no-sync python tests/golden/golden_machinery.py verify` | exit 0 — `corpus_verified=True`, `independent_sample_present=True`, `overall_integrity=VALID`, `phase3_gate_blocked=False` |
| 5 | same under `python -I` (isolated interpreter, randomized hash seed) | exit 0 — identical output, `VALID` |
| 6 | `.venv/bin/clinical-compiler compile tests/golden/scenarios/standard_mixed.input.jsonl --output …` × 2 | exit 0 ×2; both outputs `cmp`-identical to each other AND to the committed golden document; SHA-256 `e7b5b03fa6d9f150c081684846fb481b7dfda02ebdd24992a7fba164c88b8abc` = manifest digest |
| 7 | `PYTHONHASHSEED=random / 0 / 12345` CLI compiles | exit 0 ×3, byte-identical across seeds (`HASHSEED_CROSSRUN=IDENTICAL`) |
| 8 | FC-05 fault (`raw_value: true` for `FC`) via CLI | exit **4**, stdout **0 bytes**, 2 stable stderr lines (`TYPE_ERROR: …`, `DOCUMENT_SELECTION_ERROR: …`) |
| 9 | FC-01 fault (missing `field_id`) via CLI | exit **3**, stdout **0 bytes**, 2 stderr lines |
| 10 | unreadable INPUT via CLI | exit **2**, `clinical-compiler: error: cannot read input …`, no compile |
| 11 | `--policy-seed <missing>` via CLI | exit **2**, `UNRESOLVED_POLICY: … not found — no seed and no durable owner decision present`, stdout 0 bytes |
| 12 | valid seed (`{"terms": ["sepsis"]}`) via CLI | exit 0, output byte-identical to golden (FC-12 production path + populated veto) |
| 13 | orphan sweep: `rg -c "DiagnosticCode.<CODE>"` src/ + `rg -c "<CODE>"` tests/ per code | 8/8 codes have producing sites (2–23 constructs each) and covering tests (13–47 refs each) — **orphans = 0** |
| 14 | `git diff c6578b6 --numstat -- src/clinical_compiler/core/` | exactly `60 0 core/ir.py` (additive `CanonicalClinicalIR` only); working tree adds zero further core change |
| 15 | `shasum -a 256` over the 10 bundle files | **all 10 per-file digests match** `state.yaml` / `APPROVAL-PHASE0.md` — no bundle drift |
| 16 | `fd --type f --size 0b` over `{passes,linter,renderers,adapters}` | **0** zero-byte files (src-wide: only `core/__init__.py` + `py.typed`, both conventional, outside gate scope) |
| 17 | `git merge-base --is-ancestor 9d3ab30 b376c0c` | true — contract-freeze commit precedes adapter commit (freeze-before-build) |
| 18 | `rg -i "sepsis\|dolor\|infecc\|…"` over `src/` | **0 matches** — no executor-authored clinical content |

Note: the owner has committed the Phase 3–4 payload since the Phase-4 close (commits `546acf6`, `cff0baf`, `60cbc9b` after `d7731c8`); the working tree is clean, the console script `clinical-compiler` is now materialized in `.venv/bin`, and residual P3-F11 is resolved. The R-4.7a `adapters/README.md` deletion is in commit `cff0baf` ("drop adapters placeholder").

---

## Completeness

| Metric | Value |
|--------|-------|
| Tasks total (tasks.md rows) | 44 checkbox rows across phases 0–4 |
| Tasks complete (checkbox `[x]`) | **0** |
| Tasks incomplete (checkbox `[ ]`) | 44 |

**WARNING (non-blocking, explained):** every checkbox in `tasks.md` is unchecked — deliberately. The bundle is hash-bound (`APPROVAL-PHASE0.md` binds `tasks.md` at `086e7884…`), so editing checkboxes would break the approval binding. Phase/task completion is instead tracked in `state.yaml` (`sdd-apply: done_pending_owner_commit`) and the five phase close reports (`outputs/phase{0..4}-close.md` / `inventory/`), whose claims I re-verified fresh above — all task payloads 0.1–4.7 are present and green. No incomplete task content found.

---

## Spec Compliance Matrix — scenario-by-scenario (7 domains, 69 scenarios)

Classification: **SATISFIED** = passing test / live command / code+governance evidence exists. **PARTIAL** = scenario met only via a recorded owner adjudication. **N/A** = conditional scenario whose activation condition is false by recorded owner decision.

### Domain 1 — cli-surface (8/8 SATISFIED)

| Requirement | Scenario | Evidence (test / command) | Status |
|---|---|---|---|
| Pipeline Runner | End-to-end success | `test_pipeline.py::test_happy_path_emits_document_with_empty_diagnostics_and_exit_zero`; live CLI round trip #6 (exit 0, golden bytes) | SATISFIED |
| Pipeline Runner | Diagnostics enumerate on failure | live #8/#9 (all diagnostics on stderr, stdout empty); `test_pipeline.py::test_mixed_feed_enumerates_every_quarantine_and_takes_the_minimum` | SATISFIED |
| Zero-Dependency CLI | Script entry registered, deps still zero | `pyproject.toml` `[project.scripts]` present, no `[project].dependencies` key; `test_cli.py::test_pyproject_registers_the_console_script_with_zero_deps`; console script materialized and exercised live | SATISFIED |
| Zero-Dependency CLI | CLI compiles | live #6: `.venv/bin/clinical-compiler compile …` exit 0 | SATISFIED |
| Strict Exit-Code Mapping | Non-zero on diagnostics (`SEMANTIC_AMBIGUITY_BLOCK`) | FC-06 → exit 5 pinned by `test_fault_corpus_exits_its_family_code_and_never_emits_a_document[FC-06…]`; live FC-01→3, FC-05→4 | SATISFIED |
| Strict Exit-Code Mapping | Deterministic exit codes | `test_cli.py::test_identical_failing_input_yields_identical_bytes_and_exit`; `derive_exit_code` is a pure min-stage-order function (`test_min_stage_order_code_wins_regardless_of_encounter_order`) | SATISFIED |
| Documentation | Docs filled | `README.md` 385 lines, `docs/architecture.md` 179 lines (pipeline, contracts, invariants, exit-code table); `.gitignore` covers `.coverage` + `.mimosa/` (read) | SATISFIED |
| Final Quality Gates | Computable quality gate | fresh runs #1–#3: 406/0, cov 100.00% ≥ 95.0, mypy exit 0, ruff exit 0 | SATISFIED |

### Domain 2 — clinical-fact-model (15/15 SATISFIED)

| Requirement | Scenario | Evidence | Status |
|---|---|---|---|
| Core Baseline Immutability | Additive-only diff | `git diff c6578b6 -- core` = `ir.py +60/−0` only (`CanonicalClinicalIR`, CRC-003/D10 justification in design.md File Changes) | SATISFIED |
| Core Baseline Immutability | Non-additive change escalated | no non-additive core change was merged (diff is the proof); escalation path recorded in design §Rollback / proposal | SATISFIED |
| Missingness Non-Conflation | Unassessed survives compilation | PC-1 golden `FC: unknown [not_assessed]` (live golden doc); `test_renderers_deterministic.py::test_pc1_unassessed_field_renders_explicit_unknown`; `test_fact_carrying_not_assessed_renders_unknown_unassessed` | SATISFIED |
| Missingness Non-Conflation | Assessed absence requires a source assertion | PC-2 golden + `test_integration_phase3_chain.py::test_pc2_assessed_absence_traces_to_source_assertion`; absence marker is an explicit input record (`raw_value: null`) | SATISFIED |
| Certainty Preservation | Fail-closed certainty assignment | `test_certainty_is_unresolved_for_every_admissible_input[FC-72 / FC-72.5 / TA-120/80 / TA-None]`; normalizer hard-assigns `Certainty.UNRESOLVED` (semantic_normalization.py) | SATISFIED |
| Certainty Preservation | Source-asserted certainty stored as provenance, distinct | `test_source_asserted_certainty_is_preserved_verbatim[confirmed/candidate/unresolved]`, `test_certainty_never_lands_on_the_source_fact_ir`, `test_declared_certainty_never_becomes_compiler_certainty` (CRC-002 BOTH_SEPARATED) | SATISFIED |
| Certainty Preservation | Adjudicated clinical_note semantics stay fail-closed | `test_every_source_kind_yields_unresolved_certainty[monitor/lab/clinical_note]`; no source_kind→certainty mapping exists in code | SATISFIED |
| Certainty Preservation | Reserved states NOT_PRODUCED in R1 | `test_reserved_certainty_states_are_not_produced`; enum members retained, never produced | SATISFIED |
| Provenance Traceability | Full chain resolution | `test_passes_admissibility.py::test_resolvable_refs_admit`; golden lines carry `[monitor m-3]` provenance; PC-2 chain test | SATISFIED |
| Provenance Traceability | Missing provenance blocks | `test_unresolvable_refs_yield_provenance_error`, `test_absent_refs_yield_provenance_error`, `test_partially_unresolvable_refs_still_block` | SATISFIED |
| CanonicalClinicalIR | Duplicate fact ids fail construction | `test_ir.py::test_canonical_ir_duplicate_fact_ids_fail_construction` (`__post_init__` raises) | SATISFIED |
| CanonicalClinicalIR | Lineage validation boundary | `test_canonical_ir_lineage_invalid_fact_fails_construction[no-refs/empty-ref]` | SATISFIED |
| CanonicalClinicalIR | No document prose / no document_mode | `test_canonical_ir_carries_clinical_facts_only` | SATISFIED |
| CanonicalClinicalIR | Deterministic representation | `test_canonical_ir_representation_is_deterministic` (canonical `(field_id, clinical_fact_id)` sort in `__post_init__`) | SATISFIED |
| Single Authority Per Fact | Document references identifiers | `test_document_ir_contains_no_clinical_values`, `test_document_ir_references_facts_instead_of_storing_values`; `DocumentIR` stores refs + roles only (core/ir.py read) | SATISFIED |

### Domain 3 — determinism-rendering (6/6 SATISFIED)

| Requirement | Scenario | Evidence | Status |
|---|---|---|---|
| Byte-Identical Determinism | Cross-run digest equality | `test_cross_run_digests_equal_and_match_committed_golden[×3]` (python -I ×2, seeded, unseeded); live #7 (3 hash seeds identical) | SATISFIED |
| Byte-Identical Determinism | Golden digest match | live #6: CLI output SHA-256 = `e7b5b03f…8abc` = committed manifest digest; machinery verify #4/#5 exit 0 | SATISFIED |
| Byte-Identical Determinism | Render failure | `test_fc10_dangling_ref_yields_render_error_and_no_partial_document`; `test_injected_render_fault_exits_nine_with_no_document`; `test_injected_render_fault_blocks_the_run_before_lint` | SATISFIED |
| Golden Files | Golden regression detection | `test_mutated_golden_byte_is_detected_as_drift`, `test_tampered_manifest_digest_is_detected`, `test_output_affecting_input_change_breaks_the_golden_comparison` | SATISFIED |
| Conformance Linter | Lint failure blocks | 26 conformance tests (`test_linter_conformance.py`) incl. `test_injected_lint_failure_exits_ten_with_no_document` (exit 10, no document) | SATISFIED |
| Conformance Linter | Clean document accepted | `test_clean_rendered_document_lints_clean_and_is_accepted`; golden corpus is the lint-clean accepted path | SATISFIED |

### Domain 4 — diagnostics-policy (6/6 SATISFIED)

| Requirement | Scenario | Evidence | Status |
|---|---|---|---|
| Fail-Closed Fault Corpus | Zero silent acceptance | corpus census (fresh rg): FC-01..FC-12 + PC-1/PC-2 all have 3+ test refs each; `test_any_diagnostic_yields_no_document_and_the_family_exit_code[FC-01/02/03×2/05/06/07/09]`; live fault legs #8/#9 mapped codes with empty stdout; silently-accepted = 0 | SATISFIED |
| Taxonomy Coverage | No orphan codes | fresh orphan sweep #13: 8/8 codes — producing sites in passes/adapters/renderer/linter, 13–47 test refs each; both baseline orphans eliminated (TYPE_ERROR at input_validation, PROVENANCE_ERROR at admissibility) | SATISFIED |
| Policy Content Governance | Executor proposes no clinical content | `rg` clinical terms over `src/` = 0 (#18); `core/policy.py` NEVER_AUTO_TERMS is the frozen empty default (`test_policy.py::test_never_auto_terms_is_the_frozen_empty_default`); veto terms in tests are test-local placeholders (`test-veto-term-alpha`) | SATISFIED |
| Policy Content Governance | Exact seed fidelity | `test_owner_seed_file_loads_populated`, `test_loaded_seed_feeds_admissibility_veto`, `test_load_is_deterministic`, `test_duplicate_terms_normalize_to_a_set` (set-level fidelity per D7) | SATISFIED |
| Policy Resolution State Machine | UNRESOLVED_POLICY blocks — never empty-set-and-continue | live #11 (exit 2 + UNRESOLVED_POLICY, empty stdout); `test_unresolved_policy_blocks_gate_with_no_silent_empty_set`; `PolicyResolution.__post_init__` makes uncited approved-empty unrepresentable; `approved_empty_by_deferral` requires the DEFERRED_BY_OWNER citation | SATISFIED |
| Mutation-Sensitive Policy Tests | Mutation detected | `test_never_auto_terms_is_the_frozen_empty_default` + `test_never_auto_terms_membership_cannot_be_mutated_in_place` (membership mutation → failure); enforcement mutation kills `test_vetoed_term_is_quarantined_with_policy_violation` / `test_stage_never_reads_the_core_policy_constant`; Phase-2 close records live mutation kills M1/M2 (R-2.7) | SATISFIED |

### Domain 5 — input-contract (8 SATISFIED, 2 N/A-conditional)

| Requirement | Scenario | Evidence | Status |
|---|---|---|---|
| Frozen Input Contract | Freeze before build | `git merge-base --is-ancestor 9d3ab30 b376c0c` → true (contract commit `9d3ab30` precedes adapter commit `b376c0c`) | SATISFIED |
| Frozen Input Contract | Contract violation | live FC-01 exit 3; `test_missing_required_key_is_input_contract_error[×4]`, `test_unknown_key_is_input_contract_error` | SATISFIED |
| Type Validation | Wrong value type | live FC-05 exit 4; `test_bool_raw_value_for_numeric_field_is_type_error` (exact-type check, `bool` never passes for numeric FC) | SATISFIED |
| Type Validation | Arbitrary object rejected at runtime boundary | `test_arbitrary_object_raw_value_is_type_error` at BOTH the adapter (contract.py) and the defense-in-depth stage (input_validation.py) — CRC-006 ENFORCE_BOUNDED_VALUES_AT_RUNTIME | SATISFIED |
| Type Validation | Orphan eliminated after Phase 1 | orphan sweep: TYPE_ERROR produced by `adapters/contract.py` + `passes/input_validation.py`, 23 test refs | SATISFIED |
| Driving Adapter | Verbatim ingestion | golden `standard_mixed` ("TA 120/80" → `TA: 120/80 [present] [monitor m-9]`); `test_valid_feed_bytes_map_to_candidate_source_facts` | SATISFIED |
| Driving Adapter | Source-declared certainty captured as provenance | `test_source_asserted_certainty_is_preserved_verbatim[×3]` + `test_integration_feed_validation.py::test_declared_certainty_is_preserved_alongside_admitted_facts` (verbatim, optional, never invented) | SATISFIED |
| Conditional Free-Text | In-grammar note | condition false: gate recorded `INPUT_CONTRACT_DECISION = STRUCTURED_FEED_ONLY` (APPROVAL-PHASE1) | N/A (conditional) |
| Conditional Free-Text | Out-of-grammar note | condition false — same recorded decision | N/A (conditional) |
| Conditional Free-Text | Free-text deferred | `test_free_text_line_is_input_contract_error`, `test_quoted_free_text_line_is_input_contract_error` — free text rejected with `INPUT_CONTRACT_ERROR`, never guessed | SATISFIED |

### Domain 6 — phase0-verification (13 SATISFIED, 1 PARTIAL, 1 vacuous-SATISFIED)

| Requirement | Scenario | Evidence | Status |
|---|---|---|---|
| Read-Only Phase 0 | No mutation outside declared writes | `outputs/inventory/evidence-before.md` + `evidence-after.md` captured before/after snapshots; declared writes = `outputs/inventory/` only | SATISFIED |
| Read-Only Phase 0 | Environment change required | 0 UNKNOWN outcomes recorded across all phases (`baseline-anomalies.md` §UNKNOWN = 0); rule (UNKNOWN → terminal, gate-blocking) encoded in the anomaly computation | SATISFIED (vacuous — never triggered) |
| Baseline Verification Gate | Clean baseline (`BASELINE_ANOMALIES == 0`) | raw compute was **3 drift contradictions + 0 UNKNOWN → BLOCKED**, then owner ADJ-1 `RECONCILED_NOT_COUNTING` (APPROVAL-PHASE1 / state.yaml) → effective 0. The zero was NOT computed directly; it was adjudicated. | **PARTIAL** (owner-adjudicated) |
| Baseline Verification Gate | Contradicted claim | the 3 drift contradictions WERE enumerated (C-1..C-3 in `baseline-anomalies.md`) and the gate blocked at compute time — mechanism worked | SATISFIED |
| Baseline Verification Gate | Unverifiable claim blocks | rule documented + encoded (UNKNOWN counts as blocking anomaly); 0 UNKNOWNs occurred | SATISFIED (vacuous) |
| Evidence-Based Dossiers | Options without selection | `input-contract-dossier.md` present; `decision-gate.md`: every `owner_decision: ________  # BLANK`, `selection_mode: OPEN` — no executor selection | SATISFIED |
| Evidence-Based Dossiers | Structure-only policy dossier | `policy-seed-dossier.md` present; repo-wide search shows zero executor-authored clinical content (#18); seed loader validates structure only (seed.py read) | SATISFIED |
| Hygiene Inventory | Findings enumerated | `hygiene-inventory.md` lists the tautological test, both orphan codes (TYPE_ERROR, PROVENANCE_ERROR), and both `.gitignore` gaps (verified by rg) | SATISFIED |
| Phase 0 Decision Gate | Decisions recorded | `APPROVAL-PHASE1.md` lines 13–14: `INPUT_CONTRACT_DECISION = STRUCTURED_FEED_ONLY`, `POLICY_SEED_DECISION = DEFERRED_BY_OWNER`; "Felipe Gonzalez. Reviewer ≠ executor." — owner-authored | SATISFIED |
| Phase 0 Decision Gate | Missing decision blocks | `decision-gate.md` decision fields BLANK; APPROVAL-PHASE0 "NOT authorized: Phases 1–4 … contingent on the Phase 0 decision gate" | SATISFIED |
| Phase 0 Decision Gate | Executor-authored decision invalid | all decision fields blank in the executor-authored skeleton (read); decisions exist only in the owner record | SATISFIED |
| Hash-Bound Activation Gate | No record, no execution | 5 sequential approval records gate every phase; APPROVAL-PHASE0 explicitly authorizes "PHASE_0 ONLY" and blocks the rest | SATISFIED |
| Hash-Bound Activation Gate | Phase-explicit activation | each APPROVAL-PHASEn names exactly its phase (PHASE_0: "This record authorizes NOTHING beyond PHASE_0"; PHASE_4 record names PHASE_4 work-units) | SATISFIED |
| Hash-Bound Activation Gate | Bundle drift invalidates the record | fresh `shasum -a 256` (#15): all 10 per-file digests match the record — no drift. (Manifest-hash recomputation caveat → SUGGESTION below) | SATISFIED |
| Hash-Bound Activation Gate | Unevidenced readiness activates nothing | APPROVAL-PHASE0 §Validation receipt references engram #7246/#7247/#7250/#7251 audits on the bound hashes | SATISFIED |

### Domain 7 — pipeline-passes (9/9 SATISFIED)

| Requirement | Scenario | Evidence | Status |
|---|---|---|---|
| Scaffold Completion | Computable scaffold gate | fresh `fd --size 0b` over the four gate dirs = **0** (#16); `adapters/README.md` placeholder deleted (commit `cff0baf`, R-4.7a closed) | SATISFIED |
| Fixed Stage Order | Blocked fact stops downstream | `test_pipeline.py::test_blocked_upstream_fact_is_never_consumed_downstream`; stages consume only `admitted` tuples (pipeline.py read) | SATISFIED |
| Fixed Stage Order | No silent omission | live fault legs enumerate ALL diagnostics incl. downstream `DOCUMENT_SELECTION_ERROR`; `test_mixed_feed_enumerates_every_quarantine_and_takes_the_minimum`; renderer omission arm (`test_omitted_fact_yields_render_error`) | SATISFIED |
| Semantic Normalization | Unambiguous normalization | `test_present_int_value_maps_to_present`, `test_absence_marker_maps_to_missing_with_provenance`, `test_provenance_carried_through` | SATISFIED |
| Semantic Normalization | Ambiguity blocks | `test_conflicting_equal_authority_facts_block`, `test_no_canonical_fact_is_created_for_a_conflicted_field`; live/tested FC-06 → exit 5 | SATISFIED |
| Admissibility Veto | Veto overrides certainty | `test_veto_is_certainty_independent[confirmed + 6 more]` (FC-07 at test-constructed CONFIRMED); FC-07 → exit 6 via corpus tests + live seed leg | SATISFIED |
| Admissibility Veto | Empty approved set | live #12: deferral-empty policy compiles golden clean (FC-12); `test_deferral_empty_set_feeds_admissibility_clean`, `test_empty_veto_set_is_a_pure_no_op` | SATISFIED |
| Document Selection | Assembly from admitted facts | `test_entries_reference_canonical_fact_ids_in_canonical_order`, `test_every_entry_carries_the_presentation_role` | SATISFIED |
| Document Selection | Selection failure | `test_fc09_all_facts_blocked_upstream_then_selection_requested`, `test_unknown_mode_yields_document_selection_error_no_document`; live FC-01 run also surfaced `DOCUMENT_SELECTION_ERROR` | SATISFIED |

**Compliance summary: 66/69 SATISFIED, 1 PARTIAL (owner-adjudicated baseline anomaly counting), 2 N/A (conditional free-text scenarios not activated by the recorded gate decision), 0 UNSATISFIED, 0 UNVERIFIABLE.**

---

## The 8 Proposal Success Criteria (recomputed fresh)

| # | Gate | Fresh computation | Verdict |
|---|------|-------------------|---------|
| 1 | Phase 0 baseline | raw 3 drift contradictions + 0 UNKNOWN; owner ADJ-1 `RECONCILED_NOT_COUNTING` → effective **0** | PASS (owner-adjudicated, recorded) |
| 2 | Phase 0 decision | `INPUT_CONTRACT_DECISION = STRUCTURED_FEED_ONLY` + `POLICY_SEED_DECISION = DEFERRED_BY_OWNER`, both owner-stated in `APPROVAL-PHASE1.md` (reviewer ≠ executor) | PASS |
| 3 | Scaffold completion | zero-byte count over `{passes,linter,renderers,adapters}` = **0** | PASS |
| 4 | Zero runtime deps | `[project].dependencies` key absent from `pyproject.toml` (⇒ 0, PEP 621); dev-group only; console script registered | PASS |
| 5 | Quality suite | **406 passed / 0 failed**, branch coverage **100.00%** (634/212/0) ≥ 95.0; `mypy --strict` exit 0 (22 files); `ruff check` exit 0 | PASS |
| 6 | Determinism | golden machinery verify exit 0 plain AND `python -I`; CLI byte-identical across 3 hash seeds AND equal to golden digest `e7b5b03f…8abc`; EVIDENCE_INTEGRITY = VALID (independent sample present + self-consistent) | PASS |
| 7 | Fail-closed safety | FC-01..FC-12 + PC-1/PC-2 all yield mapped codes (tests + live legs); silently-accepted unsafe = **0** | PASS |
| 8 | Diagnostics coverage | orphan sweep: 8/8 codes have producing stage + covering tests → **0 orphans** | PASS |

**8/8 PASS.**

---

## Contract-conformance spot-check (v0.3 essentials)

| Check | Evidence | Result |
|---|---|---|
| Computable gates, never assumed | all 8 gates recomputed fresh in this report (#1–#18) | HOLD |
| Fail-closed behavior | live fault legs: exit 3/4/2 with empty stdout; `CompileResult.__post_init__` makes document+diagnostics coexistence unrepresentable; exit-70 catch-all tested (`test_unexpected_exception_is_fail_closed_exit_seventy`, `test_unrepresentable_empty_outcome_never_exits_zero`) | HOLD |
| Single activation gate, hashes still bound | 5 phase-explicit approval records; all 10 bundle per-file SHA-256s still match (fresh #15) — no drift; each record names exactly its phase | HOLD |
| No runtime dependencies | pyproject read: no `[project].dependencies` key; stdlib-only imports verified across `src/` (argparse/json/hashlib/pathlib/dataclasses/re/types) | HOLD |
| Executor-authored clinical content = 0 | `rg` clinical vocabulary over `src/` = 0; NEVER_AUTO_TERMS frozen-empty; presentation role `telegraphic_entry` is a style name, not clinical semantics (flagged by the implementer itself) | HOLD |
| Core immutability | `git diff c6578b6 -- core` = `ir.py +60/−0` only (adjudicated additive `CanonicalClinicalIR`); `types/diagnostics/policy` untouched | HOLD |

---

## Correctness (static — structural evidence)

| Area | Status | Notes |
|---|---|---|
| Fixed stage order (D1) | Implemented | pipeline.py: parse → validate → normalize → (D7 gate) → admit → aggregate → select → render → lint; survivors-only throughout |
| Exit-code table (D3) | Implemented | `_STAGE_ORDER_EXIT_CODES` ordered tuple; min-code precedence; 0 iff empty; 2/70 at the CLI boundary |
| CLI surface (D4) | Implemented | `clinical-compiler compile INPUT [--mode] [--policy-seed] [--output]`; argparse stdlib; atomic write (mkstemp + fsync + os.replace + dir fsync) |
| Module map / D5 | Implemented | `pipeline_types.py` leaf holds `StageResult` (G-1); passes never import pipeline; core imports nothing new |
| Determinism mechanism (D6) | Implemented | tuple containers, codepoint sorts, exact-type value glyphs, UTF-8/LF, no time/locale/random/env (verified by cross-run goldens) |
| Policy seed injection (D7) | Implemented | `veto_terms` explicit parameter; core constant never read (`test_stage_never_reads_the_core_policy_constant`); resolution state machine in `adapters/seed.py` |
| Contract table (D8) | Implemented | `adapters/contract.py` single source of truth consumed by adapter + validation |
| CRC-006 runtime boundary | Implemented | exact-type checks at adapter AND defense-in-depth validation stage |
| CRC-003 aggregate (D10) | Implemented | `CanonicalClinicalIR` in `core/ir.py`, frozen dataclass, construction-time invariants, canonical ordering |

## Coherence (design decisions D1–D10)

| Decision | Followed? | Notes |
|---|---|---|
| D1 blocking granularity | Yes | per-fact quarantine + whole-run emission gate; all 8 codes blocking |
| D2 fault corpus | Yes | corpus design-authored; every FC has 3+ test refs |
| D3 exit codes | Yes | frozen table; deterministic min-code precedence (tested incl. PROVENANCE rank-7 case) |
| D4 CLI surface | Yes | exactly one verb; stdin/--json/check deferred |
| D5 dependency rule | Yes | verified by import inspection + `test_stage_result_is_reexported_from_the_leaf_module` |
| D6 determinism | Yes | golden corpus + cross-run gate green |
| D7 seed injection | Yes | runtime injection; UNRESOLVED_POLICY never degrades to empty-and-continue |
| D8 contract location | Yes | single frozen table, freeze-before-build proven by commit ancestry |
| D9 CRC-006 | Yes | annotation deferred, runtime boundary enforced |
| D10 CRC-003 | Yes | additive aggregate in core/ir.py, only core change |

Recorded minimal-faithful readings (26 flagged in phase closes) were reviewed: all are conservative (bytes instead of str for `CompileResult.document`; `PolicyResolution` on the request; extra `policy` field on the result; exit-70 for destination-write faults; substring veto matching; explicit `source_fact_ids` parameter). None contradicts a spec scenario; none silently weakens fail-closed behavior.

---

## Issues Found

**CRITICAL** (must fix before archive): **None.**

**WARNING** (should fix / record):
1. `tasks.md` checkbox completeness is 0/44 — deliberate (hash-bound bundle; box edits prohibited), with completion tracked in `state.yaml` + close reports; archive should note this explicitly so the empty checkboxes are not misread as incomplete work.
2. The bundle-manifest SHA-256 (`7a7d3a28…`) is not independently reproducible from the documented formula ("ordered concatenation of those ten digests") — three recomputation variants (digest-concat without newlines, full shasum-line concat, glob-sorted) all yield different digests. No drift exists (all 10 per-file digests match, which independently satisfies the binding requirement's "either/or"), but the manifest recipe should be recorded for future re-verification.

**SUGGESTION** (nice to have):
1. Design §CLI Surface declares stderr format `CODE: message (path)`, but no producing site ever sets `Diagnostic.path`, so production lines render `CODE: message` only (suffix is conditional in `cli._format_diagnostic`; both forms are test-pinned). Cosmetic design-letter deviation; behavior remains stable and deterministic.
2. Task 4.2 names `tests/integration/`; in-process runner coverage lives in `tests/unit/test_pipeline.py` (recorded deviation P4-F5) — placement-only, all prescribed scenarios are covered.
3. The one-time `CoverageWarning: module-not-measured` during coverage collection (observed again in this verification's first run, absent on re-run; coverage table complete at 100%) — recorded observation, previously noted in the Phase-4 receipt.

---

## Verdict

**PASS WITH WARNINGS.**

All 69 spec scenarios across the 7 domains are accounted for: 66 SATISFIED with fresh execution evidence, 1 PARTIAL closed by a recorded owner adjudication (baseline anomaly counting, ADJ-1), 2 N/A conditional scenarios whose gate decision (STRUCTURED_FEED_ONLY) never activated them. Zero CRITICAL findings. All 8 proposal success criteria recomputed PASS from fresh commands: 406/406 tests, 100.00% branch coverage, mypy strict + ruff clean, byte-identical cross-run goldens equal to the committed digest, fail-closed corpus with zero silent acceptance, zero orphan diagnostic codes, zero runtime dependencies, additive-only core diff, and an intact hash-bound approval chain. The two WARNINGs are documentation/hygiene items that do not block archive. **Archive-ready.**

---

## CORRECTION ADDENDUM (2026-08-30, PR-repair audit)

An independent verification agent audited the post-archive PR #1 repair (four defects: P0-1 verbatim-string document injection, P0-2 `source_asserted_certainty` lost at `run()`, P0-3 `{"terms": []}` → resolved POPULATED-empty policy, P1-1 empty `fact_id` → unhandled ValueError/exit 70). The repairs live in the **uncommitted working tree on HEAD 9b04fa2** (to be committed by the orchestrator). Everything above this addendum is preserved verbatim; the two claims below are re-evaluated because their original SATISFIED evidence did not prove the property at the required boundary. Fresh battery after repair: 432 passed, 100.00% branch coverage, `mypy --strict` clean, `ruff check` clean, golden machinery `corpus_verified=True / integrity=VALID` under plain and `python -I` interpreters, scenario digests byte-identical across `python -I` / `PYTHONHASHSEED=0` / `PYTHONHASHSEED=random` and equal to the committed files' SHA-256; independent CLI adversarial sweep (11 cases × 2 hash seeds) mapped every fault to its family exit code with **zero exit-70 outcomes**.

### Claim 1 (Domain 2, Certainty Preservation row): "Source-asserted certainty stored as provenance, distinct"

- **Original claim (line 75, quoted):** "`test_source_asserted_certainty_is_preserved_verbatim[confirmed/candidate/unresolved]`, `test_certainty_never_lands_on_the_source_fact_ir`, `test_declared_certainty_never_becomes_compiler_certainty` (CRC-002 BOTH_SEPARATED) | SATISFIED".
- **Why it was false:** the load-bearing citation `test_certainty_never_lands_on_the_source_fact_ir` was an **absence-proving test** — it pinned the `SourceFactIR` field list *without* any certainty slot, i.e. it asserted exactly the loss the requirement forbids. The verbatim capture existed only on the adapter wrapper, which `pipeline.run()` discarded at its composition boundary (`run_input_validation(tuple(fact.fact ...))`), so no observable run outcome carried the declaration. The remaining citations covered only the wrapper hop. Absence of a contradiction in the cited scope was accepted as presence of the property across the required boundary.
- **Corrected status: SATISFIED** — with new, presence-proving evidence at the required boundary (all run by this audit, 52 scoped tests passing):
  - `test_declared_certainty_lands_only_in_the_dedicated_ir_slot` — pins the IR field list **with** the additive `source_asserted_certainty` slot and the verbatim value on it (replaces the removed wrong test; `rg` confirms the old name no longer exists anywhere).
  - `test_pipeline.py::test_source_asserted_certainty_is_traceable_across_the_run` — **run() level**: declared CONFIRMED/PROBABLE in, the same per-fact values out on `CompileResult.source_asserted_certainties`, codepoint-sorted, never merged.
  - `test_undeclared_facts_contribute_no_certainty_entry`, `test_corroborating_facts_keep_their_own_declarations`, `test_both_certainty_authorities_stay_distinct_at_the_run_boundary` (plus the retained normalizer pin `test_certainty_is_unresolved_for_every_admissible_input`).
- **Repair shape (working tree):** additive `SourceFactIR.source_asserted_certainty: Certainty | None = None` (owner-pre-authorized 2026-08-30 — the second recorded core-change exception, recorded in `core/ir.py`'s docstring) + additive `CompileResult.source_asserted_certainties`; `StructuredFeedFact` delegates via a setter-less property so there is exactly one storage location.

### Claim 2 (Domain 4, Policy Resolution State Machine row) + the coherence line "None contradicts a spec scenario"

- **Original claims (quoted):** row "Policy Resolution State Machine | UNRESOLVED_POLICY blocks — never empty-set-and-continue | live #11 …; `test_unresolved_policy_blocks_gate_with_no_silent_empty_set`; `PolicyResolution.__post_init__` makes uncited approved-empty unrepresentable; `approved_empty_by_deferral` requires the DEFERRED_BY_OWNER citation | SATISFIED"; and "None contradicts a spec scenario; none silently weakens fail-closed behavior."
- **Why they were false:** the cited evidence never exercised the zero-term-seed path, and a committed test (`test_empty_terms_seed_is_populated`, pre-repair `tests/unit/test_adapters_seed.py`) actively **pinned** the contradiction: `{"terms": []}` loaded as `POPULATED` with `frozenset()` and `is_resolved=True` — a RESOLVED empty veto set reached by a non-deferral route, violating the diagnostics-policy spec's letter that the empty set is *only ever* an APPROVED-BY-DEFERRAL state. `seed.py` had itself flagged this exact seam as under-specified, and the coherence line's "none contradicts a spec scenario" was false for that flag. This was the same failure mode as Claim 1: coverage-shaped evidence accepted where a spec-scenario contradiction existed outside the cited scope.
- **Corrected status: SATISFIED** — with new, presence-proving evidence at construction and CLI boundaries (run by this audit):
  - `test_empty_terms_seed_is_unresolved` (flipped from the wrong pin): loader returns `UNRESOLVED_POLICY` with typed `PolicySeedFault.EMPTY_TERMS`, `is_resolved` false.
  - `test_resolved_empty_policy_is_unrepresentable_except_by_deferral`: **construction level** — `populated_policy(frozenset())` raises and raw `PolicyResolution(state=POPULATED, terms=frozenset(), …)` raises ("non-empty"), while the citation-checked deferral path still yields the one legitimate resolved-empty state.
  - `test_cli.py::test_empty_terms_seed_is_a_usage_exit`: exit 2, `UNRESOLVED_POLICY:` stderr, empty stdout — re-confirmed live by this audit's sweep (deterministic across hash seeds).
- **Repair shape (working tree):** `PolicySeedFault.EMPTY_TERMS` + zero-term rejection in `load_policy_seed` + `PolicyResolution.__post_init__` POPULATED⇒non-empty invariant; the seed.py FLAGGED item (1) converted to REPAIRED FLAG citing the 2026-08-30 owner instruction.

### Audit scope note

P0-1 (multiline verbatim injection) and P1-1 (empty `fact_id` → exit 70) post-date this report and are closed in the same working tree: renderer fail-closed line-break refusal (RENDER_ERROR, exit 9) + linter hardening (one-line-per-field, provenance-required on assessed lines), and non-empty `fact_id`/`source_ref` at the contract with the mirrored validation check (INPUT_CONTRACT_ERROR, exit 3, never 70) — each backed by run()-level, byte-level, and CLI-corpus tests verified by this audit. The optional contract-level narrowing of `\n` (which would require a recorded owner decision under the input-contract spec) was deliberately NOT taken; the frozen contract's string space is unchanged.

---

## FULL_ANTIDRIFT RE-VERIFICATION (2026-08-30, target 7d089513)

**Status of the sections above this line: SUPERSEDED pending independent audit of `7d089513`.** The original report's `PASS WITH WARNINGS … Archive-ready` verdict and the CORRECTION ADDENDUM were issued against evidence gathered on the **pre-commit working tree** (the addendum itself says so: "repairs live in the **uncommitted working tree** on HEAD 9b04fa2"). Those verdicts are preserved verbatim as history, but they are no longer the operative status: the operative status is THIS section, which re-proves the same properties against the committed SHA.

- **Exact SHA audited:** `7d0895133d0ca74a889e3f3270f3a4b9f497f4cd` — the repair commit "fix: close PR-1 audit defects P0-1..P1-1", direct child of `9b04fa2` (the brief's superseded baseline — `9b04fa2` is the owner docs commit, not a repair state).
- **Tree state at audit:** CLEAN — zero modified tracked files; only untracked `.claude/` session-runtime files (out of scope, not committed). Local HEAD == remote `r1-clinical-compiler` head at audit time.
- **Prior addendum → committed, confirmed:** the working-tree repairs the addendum described are what commit `7d089513` contains (`git diff --stat 9b04fa2..7d089513`: contract.py, seed.py, core/ir.py additive-only +25/−2 with the recorded owner-pre-authorized CORE CHANGE RECORD, linter, input_validation, pipeline.py, renderer + test changes; 815 insertions / 249 deletions over 16 files). The two wrong pins the addendum condemned (`test_certainty_never_lands_on_the_source_fact_ir`, `test_empty_terms_seed_is_populated`) are ABSENT from the committed tree (`rg` = 0 matches); the presence-proving replacements it cited are PRESENT and passing.
- **Full battery re-run at this SHA (all logs committed under `outputs/pr1-antidrift-20260830/battery/`):** 432 passed / 0 failed, **100.00% branch coverage** (gate ≥95) — `01`; `mypy --strict` exit 0 — `02`; `ruff check src tests` exit 0 — `03`; golden machinery `corpus_verified=True / overall_integrity=VALID / phase3_gate_blocked=False` under plain AND `python -I`, with per-scenario digests MATCH under plain / `PYTHONHASHSEED=0` / `python -I` and equal to the committed document bytes and manifest — `04`; 3 CLI cases byte-identical (`cmp`) across `PYTHONHASHSEED` 0 / 12345 / random, golden case digest `e7b5b03f…` equal to the committed golden — `05`; `git diff --check` clean — `06`; dependency-rule import review clean (pipeline_types leaf sanctioned) — `07`; `[project].dependencies` absent, stdlib-only imports — `08`; determinism scan: zero time/locale/random/hash call sites in output paths — `09`; admissibility explicit-`veto_terms`-parameter re-verified live (`test_stage_never_reads_the_core_policy_constant` executed against the current tree; `core.policy` imported nowhere outside core) — `10`; document+diagnostics non-coexistence re-verified live (both `__post_init__` guards raise; 12 scoped behavioral tests pass) — `11`; 27-case invalid-input family CLI sweep, every case mapped (0/2/3/4/6/9), **ZERO exit 70** — `12`.

### Affected requirements — re-evaluated ONLY where the addendum touched them

| Requirement (domain) | Status | Evidence at 7d089513 (all fresh, this session) |
|---|---|---|
| Certainty preservation / both authorities (Domain 2, CRC-002) | **SATISFIED** | CLI + run()-boundary reproduction: corroborating facts declaring `confirmed`/`probable` yield `CompileResult.source_asserted_certainties == (("p02-a", CONFIRMED), ("p02-b", PROBABLE))` (per-fact, codepoint-sorted, never merged) while canonical `ClinicalValue.certainty` stays `UNRESOLVED`; `SourceFactIR` carries the declaration (wrapper delegates); unknown certainty name → `INPUT_CONTRACT_ERROR`. 29 scoped adversarial tests pass incl. `test_source_asserted_certainty_is_traceable_across_the_run`, `test_both_certainty_authorities_stay_distinct_at_the_run_boundary`, `test_declared_certainty_lands_only_in_the_dedicated_ir_slot`. (cli-sweep.md §Phase A; battery 01) |
| Policy state machine (Domain 4, D7/CRC-005) | **SATISFIED** | `{"terms": []}` seed → CLI exit 2, `UNRESOLVED_POLICY` with typed `EMPTY_TERMS` detail, empty stdout; `populated_policy(frozenset())` and direct POPULATED-empty construction raise `ValueError`; `approved_empty_by_deferral` rejects uncited citations and the canonical deferral citation yields the only resolved-empty state; absent flag runs the deferral path (exit 0). (cli-sweep.md; battery 12, 01) |
| Canonical representation / injection / lint (Domains 3+5, P0-1) | **SATISFIED** | All four injection variants (LF/CR in `raw_value`, LF/CR in `source_ref`) → exit 9, `RENDER_ERROR`, stdout EMPTY, no fabricated second line; valid baseline still renders exit 0; duplicate-rendered-field and present-without-provenance linter tests pass. (cli-sweep.md; battery 01, 12) |
| Mapped diagnostics — no exit 70 (Domains 1+4, P1-1 + sweep) | **SATISFIED** | `fact_id=""` and `source_ref=""` → exit 3 `INPUT_CONTRACT_ERROR` (never ValueError/70); nothing invalid reaches `CanonicalClinicalIR` (adapter + defense-in-depth quarantine). Full 27-case family sweep: zero exit-70. (cli-sweep.md; battery 12) |

No other requirement re-evaluated; nothing in this section's fresh evidence contradicts the superseded sections' remaining claims, and no new defect was found.

### Residual risk — verified repairs vs not-demonstrated properties

- **Verified repairs (demonstrated against the committed SHA):** P0-1 (injection fail-closed at render, all 4 LF/CR variants), P0-2 (certainty traceability at the run() boundary with the compiler axis untouched), P0-3 (empty-seed → UNRESOLVED_POLICY; resolved-empty only by cited deferral; unrepresentable by direct construction), P1-1 (empty identifiers → mapped exit 3).
- **Not-demonstrated here (honest limits):** (1) the golden corpus remains VALID only because the committed independent sample is self-consistent — its clinical correctness is the owner's authorship, not re-derived by this audit; (2) `mypy --strict src` being clean does not prove absence of every latent type edge — it proves the current code passes; (3) the exit-70 catch-all path itself was not triggered by any sweep case (by design — sweep proves zero 70; the 70 *mechanism* is covered by `test_cli.py::test_unexpected_exception_is_fail_closed_exit_seventy` in battery 01, not re-triggered live); (4) this audit is executor-side — an **independent audit of 7d089513** (reviewer ≠ executor) is still the governance requirement before this SHA is treated as owner-accepted.
- **Owner-review flags carried forward unchanged:** the pre-existing FLAGGED items in `pipeline.py` (bytes-not-str document; PolicyResolution on request; extra `policy`/`source_asserted_certainties` fields), `admissibility.py` (explicit `source_fact_ids` param; substring veto matching), `seed.py` (set-level dedupe; empty-term rejection; fault/usage split deferred to CLI). These remain owner decisions, not defects.

**Verdict of this section: REPAIR_COMMITTED_PENDING_INDEPENDENT_AUDIT** — all four defects closed at `7d0895133d0ca74a889e3f3270f3a4b9f497f4cd`; evidence frozen in `outputs/pr1-antidrift-20260830/` (SHA-256 manifest in `sha256sums.txt`); awaiting independent audit before the SUPERSEDED marker above is lifted and the change is re-affirmed archive-ready at this SHA.

---

## AUDIT REMEDIATION (2026-08-30, worktree of cec43d3 → new commit)

Executed from a CLEAN DETACHED WORKTREE of the PR head `cec43d39212b46b105dae318e6e5ca96627285b3` (`compilador_clinico-audit-cec43d3`); the main tree was never touched (its external uncommitted edit is preserved per owner disposition). This section appends three corrections; nothing above is altered. All fresh evidence lives in `outputs/pr1-audit-remediation-20260830/` (12 battery logs, each embedding its own UTC timestamp, target state and exit code).

### Correction 1 — verdict normalization: the operative state is **BLOCKED**

The FULL_ANTIDRIFT section above closes with the verdict "REPAIR_COMMITTED_PENDING_INDEPENDENT_AUDIT". Per owner instruction (2026-08-30) that label is **normalized to BLOCKED**: the PR remains in state BLOCKED pending independent audit — until a reviewer ≠ executor certifies the target SHA, no PASS / MERGE_READY / ARCHIVE_READY state exists for this change, whatever the batteries say. The prior label is preserved above as history; this is a re-labeling per owner disposition, not a re-scoring of the evidence.

### Correction 2 — the prior evidence run did NOT prove freeze-before-battery

Honest record: in the prior run (`outputs/pr1-antidrift-20260830/`), the preflight capture (`preflight.txt`, 2026-08-30T10:22:15Z) POSTDATES the battery start (`battery/01-pytest-coverage.log`, 2026-08-30T10:17:23Z). Because of this timestamp inversion, those artifacts do not prove that the tree was frozen before the battery ran — they prove only that the tree was clean at 10:22:15Z. Implication: the battery could in principle have executed against a different tree state than the one the preflight later froze; the run's per-log digests and exit codes still support its conclusions, but the ordering discipline itself was not demonstrated by the artifacts. Corrective discipline in THIS run: preflight FIRST — `preflight-first.txt` (last captured TS 2026-08-30T10:51:16Z, HEAD exactly `cec43d3`, zero modified files) was written before any battery command existed, and every battery log in `outputs/pr1-audit-remediation-20260830/battery/` embeds its own UTC timestamp strictly greater than that preflight's last TS, so capture-before-battery ordering is provable from the artifacts alone.

### Correction 3 — two new defects (independent audit findings), fixed and evidenced

1. **Linter accepted an EMPTY provenance `source_ref`.** `_LINE_RE`'s provenance group used `source_ref=.*`, so the hand-injectable line `TA: 72 [present] [monitor ]` (empty ref) linted CLEAN — while a clinical line carrying a present/missing/not_applicable marker must carry non-empty provenance. Repro before fix (all four byte forms PASSED, the defect): `repro-before-fix/defects-before-fix.txt`. Fix (`src/clinical_compiler/linter/conformance.py`, `_check_line`): a matched provenance segment with an empty/whitespace-only `source_ref` is a typed `LINT_FAILURE` with a deterministic message, enumerated in line order; `[not_assessed]` lines remain the ONLY provenance-less form (positive pin retained). Defense-in-depth only: the pipeline already rejects empty refs at the frozen contract (7d08951), so this fault is unreachable from real input end-to-end — covered here via direct lint tests and documented honestly in `cli-sweep.md`. Tests: `test_empty_source_ref_yields_lint_failure` (5 parametrized forms incl. whitespace-only), `test_empty_source_ref_violations_enumerate_in_line_order_deterministically`, `test_not_assessed_lines_remain_the_only_provenance_less_form` — RED (6 failed) before the fix, GREEN (45 passed) after (`tdd/red-before-fix.txt`, `tdd/green-after-fix.txt`).
2. **Renderer refused only LF/CR — the rest of the canonical-breaking alphabet rendered verbatim.** U+0000, TAB U+0009, DEL U+007F, NEL U+0085, C1 U+0080–U+009F, LINE SEPARATOR U+2028 and PARAGRAPH SEPARATOR U+2029 all reached the canonical bytes untransformed (U+2028 fabricates a second visual line inside one physical line). Repro before fix (8 cases RENDERED VERBATIM): `repro-before-fix/defects-before-fix.txt`. Fix (`src/clinical_compiler/renderers/deterministic.py`): new module constant `CANONICAL_BREAKING_CHARACTERS` — the EXPLICIT FROZEN 67-codepoint set (C0 U+0000–U+001F, DEL U+007F, C1 U+0080–U+009F incl. NEL, U+2028, U+2029) written as literal codepoints with NO `unicodedata` runtime dependency (determinism across Python versions), enforced on BOTH value glyphs and `source_ref` strings → `RENDER_ERROR` fail-closed naming the exact `U+XXXX`; values are never transformed. Boundary pins: printable ASCII and typical unicode (`ñ`, `°`, `—`) still render verbatim (no over-blocking); the LF/CR tests are kept and the golden corpus (plain printable ASCII) stays byte-identical (battery items 04/05). Tests: `test_canonical_breaking_charset_is_explicit_frozen_and_complete`, 7 parametrized value cases, 7 parametrized source_ref cases, 10 boundary cases — RED (module collection failure: constant absent) before, GREEN (49 passed) after.

**Spec compliance delta:** canonical-representation/lint requirement was PARTIAL-by-audit (these two gaps) → **SATISFIED at the new commit** produced by this remediation, pending independent confirmation (reviewer ≠ executor). All other requirement statuses are unaffected by this diff. Battery discipline: preflight-first proven (Correction 2); 12-item battery with ZERO exit-70 across the extended sweep; results in `outputs/pr1-audit-remediation-20260830/battery/` and `cli-sweep.md`.

---

## AUDIT REMEDIATION ROUND 2 (2026-08-30, worktree of aff8b21 → new commit)

Executed from a CLEAN DETACHED WORKTREE [CORRECTION 2026-08-30: read as "tracked source tree clean; evidence directory intentionally untracked" — see INDEPENDENT AUDIT CERTIFICATION] of the PR head `aff8b219e197c4f04ff464f5ffe5a6b6e6bc05c8` (`compilador_clinico-audit-cec43d3`); the main tree was never touched (its external uncommitted edit is preserved per owner disposition). This section closes the two BLOCKERS of the independent audit round 2 and applies the four non-blocking dispositions. Nothing above is altered. All fresh evidence lives in `outputs/pr1-audit-remediation-r2-20260830/` (preflight, repro-before-fix, RED/GREEN logs, battery logs each embedding UTC timestamps + target SHA + tree status, post-commit fence). Target state: **C1** — the code+report commit carrying this section (its exact SHA is frozen by the commit itself and recorded in the evidence README, the fence, and the PR body; the post-commit battery runs in a SEPARATE clean detached checkout of C1, not in the authoring worktree).

### BLOCKER 1 — linter canonical-character parity (defense-in-depth, closed)

- **Root cause:** the renderer's frozen 67-codepoint `CANONICAL_BREAKING_CHARACTERS` refuses C0 U+0000–U+001F, DEL U+007F, C1 U+0080–U+009F, U+2028, U+2029 in values AND source_refs (RENDER_ERROR), but the linter — the net AFTER render — globally blocked only CR. 65 of the 67 codepoints, embedded mid-line, linted CLEAN: bytes the renderer declares impossible could pass the final gate. Repro before fix (4 auditor examples + full 67-codepoint sweep, 65 CLEAN): `repro-before-fix/defects-before-fix.txt`.
- **Fix** (`src/clinical_compiler/linter/conformance.py`): new own module constant `LINTER_CANONICAL_BREAKING_CHARACTERS` — the SAME 67 literal codepoints, deliberately DUPLICATED (never imported from the renderer: an independent net must not import the renderer it polices; same pattern as `_FIXED_GLYPHS`), parity pinned TEST-side (`test_linter_charset_parity_with_the_renderer_frozen_set` — tests may import both). Every decoded line is scanned (fixed order: the scan runs LAST within a line so every pre-existing enumeration is preserved byte-for-byte; first/leftmost violating char named) → typed `LINT_FAILURE` with a deterministic `U+XXXX` message in line order. U+000A is structurally excluded from a decoded line (it IS the separator; split-line fragments are blocked by the existing grammar + one-line-per-field rules); U+000D keeps its dedicated global LF-only invariant (no double-enumeration). All prior rules (CR global, grammar, vocabulary, duplicates, provenance, empty-ref) intact — the rule only APPENDS diagnostics.
- **Tests** (`tests/unit/test_linter_conformance.py`): completeness pin parametrized over the WHOLE frozen set (67/67 → LINT_FAILURE, never admitted); message pin over the 65 in-line characters (exactly one diagnostic naming `U+XXXX`, line 1); the auditor's four named position cases (TAB in value, TAB in ref, U+0085 in ref, U+2028 in value); frozen-set shape pin (67 codepoints, explicit ords); charset-parity cross-pin; determinism pin; printable-unicode positive boundaries (ñ, °, —, emoji-class values and refs stay lint-clean — no over-blocking). Mutation-sensitive: removing the check or shrinking the set fails the parametrized pins. RED (collection ImportError: constant absent) → GREEN (193 passed) in `tdd/red-blocker1-linter.txt` / `tdd/green-blocker1-linter.txt`.
- **Post-fix sweep:** 0 of 67 lint-clean (was 65) — captured in the battery's adversarial-linter log.

### BLOCKER 2 — FC-11 presentation_role → LINT_FAILURE (closed, auditor's option A)

- **Root cause:** FC-11 ("DocumentIR entry with `presentation_role` outside the mode's allowed set → LINT_FAILURE") was UNREACHABLE: `render_document` ignored `presentation_role` entirely and the linter receives only bytes — the role vanished between render and lint. Injected invalid roles ("INVALID", "", wrong-mode role) rendered clean bytes. Repro before fix: `repro-before-fix/defects-before-fix.txt`.
- **Fix (option A — validate BEFORE information loss)** (`src/clinical_compiler/renderers/deterministic.py`): new frozen literal `MODE_ALLOWED_PRESENTATION_ROLES` (mode → frozenset of allowed roles) defined LOCALLY in the renderer — renderers must not import `passes` (D5); duplication rationale recorded in-code; parity pinned TEST-side against `passes.document_selection`'s `SUPPORTED_MODES`/`TELEGRAPHIC_ENTRY_ROLE` (`test_renderer_role_vocabulary_parity_with_document_selection`). Each entry's role is validated against `DocumentIR.document_mode`'s allowed set at the top of the entries loop (the LAST point where the role exists) → **`LINT_FAILURE`** (FC-11's prescribed code) per invalid entry, in entry order, fail-closed (any diagnostic ⇒ no document). An unknown mode carries an EMPTY allowed set → every entry fails closed (defense-in-depth; selection already blocks unknown modes). `derive_exit_code` maps the diagnostic CODE, not the emitting stage, so the set maps to exit 10 — pinned by `test_fc11_role_diagnostic_maps_to_exit_ten`. No renderer signature gap: `DocumentIR` carries `document_mode` (core/ir.py), so no OWNER_DECISION_REQUIRED was needed.
- **Tests**: renderer unit — invalid roles ("INVALID", "", "narrative_entry") → `LINT_FAILURE` + no bytes + message naming role and mode; per-entry D1 enumeration in entry order; valid-role bytes pinned unchanged; unknown-mode fail-closed; exit-10 mapping. Integration (`tests/unit/test_integration_phase3_chain.py`) — a test-constructed `DocumentIR` with an invalid role (and one stamped with an unknown mode) through the render boundary → `LINT_FAILURE`, `admitted == ()`, `derive_exit_code == 10`, no document bytes. RED (collection ImportError: constant absent) → GREEN (258 passed across renderer/chain/linter) in `tdd/red-blocker2-renderer.txt` / `tdd/green-blocker2-renderer.txt`. Goldens byte-identical (battery item 4/5; valid inputs untouched).

### Dispositions applied (non-blocking)

1. **Evidence wording (audit §1):** this round's preflight (`outputs/pr1-audit-remediation-r2-20260830/preflight-first.txt`, captured FIRST, before any battery command) describes the state as **tracked source tree clean; evidence directory intentionally untracked** — never "clean tree / no untracked". An append-only CORRECTION note to that effect was added to the PREVIOUS run's README (`outputs/pr1-audit-remediation-20260830/README.md`).
2. **Test comment fix (audit §3):** `test_empty_source_ref_yields_lint_failure`'s docstring no longer claims "the pipeline already rejects empty refs": it now distinguishes `""` (contract-REJECTED → INPUT_CONTRACT_ERROR, 7d08951) from `" "` (contract-ADMISSIBLE — flows through the real pipeline today; this linter rule is the only net rejecting it). The whitespace-only parametrized form was swapped from TAB (now a canonical-char-parity case) to NBSP U+00A0 (whitespace-only per `.strip()`, NOT in the breaking set) so exactly the empty-ref rule fires.
3. **This section** is the verify-report append; the operative verdict remains **BLOCKED pending independent re-audit** (never MERGE_READY).
4. **PR body:** updated after the final push, Verification section only (stale PASS_WITH_WARNINGS/archive-ready text superseded) — evidence in `outputs/pr1-audit-remediation-r2-20260830/pr-body-update.txt`.

### Battery + fence discipline

The full battery runs POST-COMMIT in a SEPARATE detached worktree created from C1 (`compilador_clinico-postcommit-C1`), porcelain verified EMPTY before and after (the real fence): pytest+cov, `mypy --strict`, `ruff`, golden verify (plain + `python -I`), adversarial linter tests scoped, determinism (2 cases × 2 seeds byte-compare), exit-70 sweep (≥10 cases including the new lint paths). Logs live in `outputs/pr1-audit-remediation-r2-20260830/battery/` (each: command, UTC timestamps, exit code, target_sha=C1, tree status), committed as **C2** (evidence-only; no tested-file changes between C1 and C2).

### Verdict

Two audit BLOCKERS closed at C1 with repro-before → RED → GREEN → post-commit-clean-checkout evidence; four dispositions applied. **Operative verdict: BLOCKED — pending independent re-audit of C1 by a reviewer ≠ executor.** No PASS / MERGE_READY / ARCHIVE_READY state exists for this change until that certification.

## INDEPENDENT AUDIT CERTIFICATION (2026-08-30)

The independent auditor (reviewer ≠ executor) completed the re-audit of PR #1 @ `7edbaa6085c44b6e513993cc7d6ab41c41605198` — code frozen at **C1** `b8c0c46b99290863faa6c4c42c10d947c40c6e51`, followed only by evidence commit C2 — and certified: **MERGE_READY**. The prior **BLOCKED** verdict is WITHDRAWN. This is the operative verdict of the change.

### Auditor's final gate (all PASS)

| # | Gate | Result |
|---|------|--------|
| 1 | Subject remoto (reviewer ≠ executor) | PASS |
| 2 | C1→C2 isolation (evidence-only commit; no tested-file changes between C1 and C2) | PASS |
| 3 | Linter 67-char parity | PASS |
| 4 | Renderer 67-char closure | PASS |
| 5 | FC-11 exact scenario | PASS |
| 6 | Fail-closed / exit 10 | PASS |
| 7 | Full post-commit battery (622 passed, 707 stmts, 252 branches, 0 misses) | PASS |
| 8 | Post-commit fence (HEAD==C1, porcelain empty) | PASS |
| 9 | PR claim hygiene | PASS |
| 10 | Nuevo drift técnico | NONE FOUND |

### Residual observations (both non-blocking)

1. **Wording drift inside the ROUND 2 report intro:** it re-uses "CLEAN DETACHED WORKTREE" while its own preflight correctly says "tracked source tree clean; evidence directory intentionally untracked" — raw state correctly recorded, and the battery ran in the truly-clean worktree-2. **Disposition: CORRECTED in this update** — a one-line `[CORRECTION 2026-08-30: …]` note is inserted immediately after the phrase above (surgical insert, history visible; nothing above rewritten).
2. **CI absent:** GitHub Actions does not run for this repository → the PR is manual-independent-audit verified, not CI-certified. **Disposition: OPEN, non-blocking** — CI as first R2 item remains the right improvement.

### Caveat (auditor's clause)

The MERGE_READY verdict applies unless a new commit at head touches `src/`, `tests/`, normative specs (`openspec/specs/`) or the fault corpus (design docs). **This documentary commit (C3) touches none of those** — it modifies only this verify-report (this append plus the one bracketed correction note in the ROUND 2 intro), leaving the certified code SHA C1 `b8c0c46b99290863faa6c4c42c10d947c40c6e51` intact.
