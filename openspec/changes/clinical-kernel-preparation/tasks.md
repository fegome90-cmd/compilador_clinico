# Tasks: Clinical Kernel Preparation

## Phase 1: Baseline

- [x] **1.1** Before any documentation write, verify the live checkout is branch `codex/wo-001-clinical-kernel-preparation`, commit `729134461850a17d240327fb5d8243c9e77f976d`, tree `1dbc33ee1ffc2dc08498a53a1044a13211c7a078`; stop on drift or unverifiable identity.
- [x] **1.2** Create `docs/agent/BASELINE_R1.md` with observed/computed/pending evidence, provenance, the committed manifest hashes `669e6f72fa48e50ab42d8b37993bdf77f81a0e940b868f7b8b0b07a7490d6ae9` and `1d0b40bad026970a456d810a336da04d0f2307b72b791b9b75697893df151ffa`, and scenario anchors `pc1_unassessed_fc`, `pc2_assessed_absence_ta`, and `standard_mixed` with manifest-owned digests and evidence-integrity status.
- [x] **1.3** Record read-only outcomes for `CompileRequest`/`CompileResult`, pure `pipeline.run`, stdlib-only `core`, FC/TA-only `CONTRACT`, one mode, blocking diagnostics, atomic output, byte determinism, and no network/DB/daemon/runtime dependencies; unrun or unavailable gates remain Pending/blocked, never inferred PASS.

## Phase 2: Debt / Authority

- [x] **2.1** Create `docs/agent/ARCHITECTURE_DEBT_MAP.md` with D0.1–D0.6, each naming current owner/path, responsibility, evidenced import edge, deferred seam, and non-authority status; do not authorize refactoring.
- [x] **2.2** Add only minimal, scope-labeled cross-reference lines to `docs/agent/ARCHITECTURE.md` and `docs/agent/CODEMAP.md`; preserve those documents as canonical architecture/navigation authority, `openspec/specs/` as normative authority, and `docs/local/clinical-kernel-staged-reports-v2/00_SOURCE_BASIS.md` as read-only roadmap input.

## Phase 3: Verification / Closeout

- [x] **3.1** Perform structural readback and an exact diff guard: changes may contain only the two new documents and the approved cross-reference lines; assert no changes under `src/`, `tests/`, `fixtures/`, `pyproject.toml`, `uv.lock`, `openspec/config.yaml`, `openspec/specs/`, `openspec/changes/archive/`, or the staged roadmap. Do not modify tests or fixtures.
- [x] **3.2** Document these read-only, `--no-sync` checks and their outcomes: `uv run --no-sync pytest -q`; `uv run --no-sync pytest --cov=clinical_compiler --cov-report=term-missing --strict-markers`; `uv run --no-sync mypy --strict src`; `uv run --no-sync ruff check src tests`. No installs, syncs, golden regeneration, fixture rewrites, or environment mutation.
- [x] **3.3** Strict TDD is not applicable to this documentation-only change; no RED/GREEN/REFACTOR source cycle is authorized. Roll back only the new documents and cross-reference lines if the scope guard fails.

## Dependencies, Order, and Boundaries

Execute `1.1 → 1.2 → 1.3 → 2.1 → 2.2 → 3.1 → 3.2 → 3.3`; baseline identity and evidence precede debt mapping and canonical links. Non-goals: kernel/core moves, registries, profiles, contracts, modes, MCP, outputs, diagnostics, clinical semantics, source/runtime/API/dependency/config/main-spec changes, archive edits, or roadmap edits.

## Review Workload Forecast

Decision needed before apply: No
Chained PRs recommended: No
400-line budget risk: Low
No PR chain is planned.
