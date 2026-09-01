# Proposal: accept-r1-001 — Permutation Invariance Repair (post-R1)

## Change Metadata

| Field | Value |
|-------|-------|
| Change ID | `accept-r1-001-permutation-invariance` |
| Date | 2026-08-31 |
| Repository | `compilador_clinico` |
| Base | `main@16edc21` (R1 archive `clinical-compiler-r1` closed 2026-08-29, `sdd-archive: done`) |
| Status | IMPLEMENTED — verified |
| Lineage | `R1 archived baseline → post-R1 ACCEPT-R1-001 finding → bounded determinism repair → current normative spec + implementation + regression tests` |
| Scope | `openspec/specs/determinism-rendering/spec.md` (normative), `src/clinical_compiler/passes/semantic_normalization.py` (already on PR #3), `tests/unit/test_passes_semantic_normalization.py`, `tests/unit/test_pipeline.py` |
| Non-Scope | Archive mutation, duplicate `fact_id` redesign, R2 features |

## Problem / Why

PR #3 correctly implemented permutation invariance (canonical `field_id`/contributor ordering, structural tie-breaks) but placed the normative contract in the historical archive:

`openspec/changes/archive/2026-08-29-clinical-compiler-r1/specs/determinism-rendering/spec.md`

That path is immutable historical evidence (`state.yaml` `bundle_hashes_sha256`). Mutating it breaks archive hash provenance and leaves `openspec/specs/determinism-rendering/spec.md` (current authority per `AGENTS.md`) without the new contract.

## Proposed Change

Bounded lineage/spec-authority repair, no compiler redesign:

1. **Restore archive verbatim** to `origin/main` bytes (already done in this work unit — archive returns to `NO DIFF`).
2. **Promote requirement to current authority** `openspec/specs/determinism-rendering/spec.md` as `Requirement: Equivalent Fact-Set Permutation Invariance` + scenario (byte-identical to PR #3 delta, relocated).
3. **Preserve implementation** in `semantic_normalization.py` (canonical ordering, `_stable_raw_value_key`, `_contributor_sort_key`, structural representative) — already directionally correct per audit.
4. **Preserve regression tests** covering 2-corroborant reverse, `72` vs `72.0`, 3! permutations, conflict reverse, multi-field permutations, pipeline identical-doc.

## Scope Boundaries

| Area | Impact |
|------|--------|
| `openspec/specs/determinism-rendering/spec.md` | ADD requirement (this change's delta) |
| `openspec/changes/archive/...` | RESTORE to `origin/main` (no hash update) |
| `src/clinical_compiler/passes/semantic_normalization.py` | RETAIN (no redesign) |
| `tests/unit/*` | RETAIN |
| `openspec/changes/accept-r1-001-permutation-invariance/` | NEW — this bounded change record |

Explicit non-goals: no `fact_id` uniqueness redesign (see Finding below), no pass manager, no IR layer, no provenance engine, no R2 work.

## Finding — Duplicate `fact_id` (OUT_OF_SCOPE)

Duplicate `SourceFactIR.fact_id` values can be ordered deterministically but may remain lineage-ambiguous because `source_fact_refs` resolve through `fact_id`.

Disposition: **OUT_OF_SCOPE for ACCEPT-R1-001.** Requires separate owner/design adjudication before changing the input contract or source identity model. Do not silently enforce uniqueness unless an existing normative contract already requires it. Recorded here for successor triage.

## Risks

- Archive byte-mismatch if restore incomplete → verified via `git diff origin/main...HEAD -- openspec/changes/archive/` = empty.
- Current spec drift if requirement misplaced → verified via `rg -n "Permutation Invariance" openspec/specs/`.

## Success Criteria

- AC1 archive integrity: no PR diff for closed R1 archive.
- AC2 current authority contains permutation-invariance contract.
- AC3 honest lineage via this change record.
- AC4–AC6 functional invariants + regression suite pass.
- AC7 full verification (pytest, cov≥95, ruff, mypy) pass.

