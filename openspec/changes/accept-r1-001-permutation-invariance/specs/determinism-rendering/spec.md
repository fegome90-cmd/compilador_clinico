# Determinism and Rendering — delta for `accept-r1-001-permutation-invariance`

## ADDED Requirements

### Requirement: Equivalent Fact-Set Permutation Invariance

Compiling equivalent validated fact sets SHALL produce identical canonical
facts, provenance, diagnostics, and rendered bytes regardless of input record
order. This is distinct from cross-run determinism: it compares equivalent
inputs whose records are permuted, rather than rerunning one identical fixture
set in fresh interpreters.

#### Scenario: Equivalent fact-set permutation

- GIVEN two feeds containing the same validated fact records in different
  orders
- WHEN both feeds are normalized and compiled
- THEN their canonical facts, conflict messages, provenance, source references,
  diagnostics, and rendered documents are identical

## Lineage

- R1 baseline: `clinical-compiler-r1` archived 2026-08-29 at `openspec/changes/archive/2026-08-29-clinical-compiler-r1/` (state `sdd-archive: done`, `state.yaml` bundle hashes)
- Finding: post-R1 ACCEPT-R1-001 — permutation invariance missing from current authority, implementation already on PR #3 but spec authority misplaced to archive
- Repair: restore archive verbatim to `origin/main` (`NO DIFF`), promote delta to `openspec/specs/determinism-rendering/spec.md` (this file's normative target), retain `semantic_normalization` implementation and regression tests

## Non-Goals (explicit)

- No duplicate `fact_id` uniqueness redesign — see proposal Finding OUT_OF_SCOPE
- No R2, no framework, no IR layer, no provenance engine

