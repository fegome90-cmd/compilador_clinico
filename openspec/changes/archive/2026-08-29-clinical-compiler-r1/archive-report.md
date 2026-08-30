# Archive Report — clinical-compiler-r1

**Change**: `clinical-compiler-r1` (clinical-record-compiler R1)
**Archived**: 2026-08-29 by the sdd-archive phase (artifact store: **hybrid** — this file + Engram `sdd/clinical-compiler-r1/archive-report`)
**Owner authorization**: owner instruction "archiva", 2026-08-29
**Pre-flight**: PASS — all 10 hash-bound bundle files re-hashed at archive time match `state.yaml` `bundle_hashes_sha256` exactly; the bundle manifest recomputes to `7a7d3a28afa749c362a2091f4ea0c60d25745f0ede49ac311b5e8d8511e0737d` (match). Zero bundle drift.

---

## What Was Archived

The completed SDD change `clinical-compiler-r1` — the full R1 build-out of the clinical record compiler: proposal, 7 domain spec deltas, normative design (decisions D1–D10), tasks (5 phases), 5 phase approval records (APPROVAL-PHASE0..4), phase outputs (inventory, closes, quarantine drafts), verify report, and DAG state — merged into the main specs and moved to the archive per the openspec convention.

## Merge Manifest (7 domains → `openspec/specs/`)

First population: all main specs were empty; each delta IS the full domain spec. Copied with an HTML-comment provenance header; content below the header is byte-faithful (verified per-domain with `cmp` against the archived delta).

| # | Domain | Source delta | Main spec created | Action |
|---|--------|--------------|-------------------|--------|
| 1 | cli-surface | `specs/cli-surface/spec.md` | `openspec/specs/cli-surface/spec.md` | Created (first population) |
| 2 | clinical-fact-model | `specs/clinical-fact-model/spec.md` | `openspec/specs/clinical-fact-model/spec.md` | Created (first population) |
| 3 | determinism-rendering | `specs/determinism-rendering/spec.md` | `openspec/specs/determinism-rendering/spec.md` | Created (first population) |
| 4 | diagnostics-policy | `specs/diagnostics-policy/spec.md` | `openspec/specs/diagnostics-policy/spec.md` | Created (first population) |
| 5 | input-contract | `specs/input-contract/spec.md` | `openspec/specs/input-contract/spec.md` | Created (first population) |
| 6 | phase0-verification | `specs/phase0-verification/spec.md` | `openspec/specs/phase0-verification/spec.md` | Created (first population) |
| 7 | pipeline-passes | `specs/pipeline-passes/spec.md` | `openspec/specs/pipeline-passes/spec.md` | Created (first population) |

**Destructive-delta check** (config rule "Warn before merging destructive deltas (large removals)"): **NO destructive content.** All 7 deltas contain only `## Purpose` + `## Requirements` (no ADDED/MODIFIED/REMOVED delta markers); with empty main specs the merge is pure addition by construction. No warning required.

## Final State Snapshot

- **Phases**: sdd-explore ✅ (engram #7234) · sdd-propose ✅ (#7235) · sdd-spec ✅ (#7240, 7 domains) · sdd-design ✅ (#7242, D1–D10) · sdd-tasks ✅ (#7244, 42 tasks / 44 checkbox rows) · sdd-apply ✅ done-pending-owner-commit→resolved (#7256; P1 8/8, P2 11/11, P3 5/5, P4 8/8) · sdd-verify ✅ (#7318) · **sdd-archive ✅ (this report)**
- **Verify verdict**: **PASS_WITH_WARNINGS — archive-ready.** 66/69 scenarios SATISFIED with fresh execution evidence, 1 PARTIAL closed by owner adjudication ADJ-1 (baseline anomaly counting `RECONCILED_NOT_COUNTING`), 2 N/A conditional free-text scenarios (gate decision `STRUCTURED_FEED_ONLY` never activated them), 0 UNSATISFIED, 0 CRITICAL.
  - **WARNING 1**: `tasks.md` checkboxes 0/44 — **deliberate**. The bundle is hash-bound; editing checkboxes would break the approval binding. Completion is tracked in state.yaml + the five phase close reports (all re-verified fresh by sdd-verify). Do not misread the empty boxes as incomplete work.
  - **WARNING 2**: the bundle-manifest SHA-256 is not independently reproducible from the documented "ordered concatenation" formula (three variants tried all differ). No drift exists — all 10 per-file digests match, which independently satisfies the binding requirement's either/or — but the exact manifest recipe should be recorded for future re-verification.
- **Gates**: all 8 proposal success criteria recomputed fresh PASS — 406/406 tests, 100.00% branch coverage (634 stmts / 212 branches / 0 missed, all 22 files), `mypy --strict` clean, `ruff` clean, golden machinery VALID plain + `python -I`, CLI byte-identical across 3 hash seeds and equal to golden digest `e7b5b03f…8abc`, fail-closed corpus FC-01..FC-12 + PC-1/PC-2 with zero silent acceptance, 0 orphan diagnostic codes (8/8 producing + covered), zero runtime dependencies, additive-only core diff (`ir.py +60/−0` vs `c6578b6`), hash-bound approval chain intact.
- **Owner decision ledger**: 22 owner acts (5 approval records, 6 decision-gate resolutions, 7 CRC adjudications, 3 owner-delegated closures, R-3.9c glyph option A).
- **Flags**: 26 recorded minimal-faithful readings, adjudication-pending, none gate-blocking (Phase-2 #1–14, Phase-3 P3-F1..F8, Phase-4 P4-F1..F4) plus naming/placement deviation families (P1/P2/P4-F5). Reviewed by sdd-verify: all conservative, none contradicts a spec scenario.
- **r2_debt** (explicitly deferred to R2, by owner adjudication or frozen scope):
  1. CRC-006 core type narrowing — `ClinicalValue.value` stays `Any`; the RUNTIME value boundary is enforced now (`ENFORCE_BOUNDED_VALUES_AT_RUNTIME`), type-level narrowing deferred (requires separately approved core migration).
  2. Free-text telegraphic adapter — absent in R1 (`STRUCTURED_FEED_ONLY`); free text → `INPUT_CONTRACT_ERROR`.
  3. CLI surface extensions — stdin input, `--json`, `check` verb (frozen R1 surface = `compile INPUT` only).
  4. `NOT_APPLICABLE` interpretation row — unreachable in R1 (no absence marker in the frozen structured contract).
  5. Destination-write fault mapping — currently exit-70 catch-all (P4-F4); exit-2 reclassification would be an owner decision.
- **Final HEAD at archive time**: `60cbc9b` (owner had committed the Phase-3/4 payload: `546acf6`, `cff0baf`, `60cbc9b` — P3-F11 resolved).

## Non-Blocking Residual Owner Acts

1. **P3-F10** — independent-sample authorship (subagent re-derivation under closed rule A) awaits owner ratification as a designated audit path, or substitution by a hand-authored sample (permitted any time; re-verifies against the same digests).
2. **Mimosa re-scan post-P3/P4** — pending; the archived change was verified by sdd-verify but the platform security scan has not yet been re-run after the Phase-3/4 payload.
3. **tasks.md checkboxes 0/44** — deliberate (hash-bound bundle); recorded here so the empty boxes are not misread as incomplete work. No act required unless the owner chooses to re-freeze the bundle.

## Audit Trail

- Archived location: `openspec/changes/archive/2026-08-29-clinical-compiler-r1/` (moved via `git mv`; all tracked files preserved as renames; untracked `verify-report.md` moved alongside).
- Main specs now live at `openspec/specs/{domain}/spec.md` — the single source of truth going forward.
- Archived content is immutable audit trail: nothing deleted or modified beyond this archive report and the state.yaml archive fields.
- Engram mirror: `sdd/clinical-compiler-r1/archive-report` (topic_key upsert, project `compilador_clinico`).
