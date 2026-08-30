# APPROVAL-PHASE1 — change: clinical-compiler-r1

OWNER INSTRUCTION (2026-08-29): decision-gate resolutions + `AUTHORIZE_PHASE_1`,
"después de registrar formalmente las anteriores". This record IS that formal
registration. Executor transcription of the owner's chat instruction; decision
content is the owner's verbatim.

## Decision gate resolutions (PHASE_0 decision gate — CLOSED)

| Gate | Resolution |
|---|---|
| `ADJ-1 BASELINE_ANOMALIES_DRIFT_COUNTING` | **RECONCILED / NOT COUNTING → 0** — the C-1 (untracked `tests/conftest.py`), C-2 (`tests/fixtures/` dir) and C-3 (modified `test_ir.py` consumes factories) findings are absorbed as working-tree baseline, not anomalies. |
| `INPUT_CONTRACT_DECISION` | **STRUCTURED_FEED_ONLY** (R1). Free-text deferred to R2. |
| `POLICY_SEED_DECISION` | **DEFERRED_BY_OWNER** — durable state + test-local seeds; empty set is an approved-by-deferral state. |
| `CLI_SURFACE_CONFIRMATION` | **CONFIRM_AS_DESIGNED** — `clinical-compiler compile …`. |
| `ADJ-2 GITIGNORE_SCOPE_WIDENING` | **Widen**: add `.pi/` and `_ctx/` to `.gitignore`. |
| `PHASE_1_AUTHORIZATION` | **AUTHORIZED** — effective upon this record. |

With ADJ-1 reconciled: `BASELINE_ANOMALIES → 0` (effective). Baseline gate
considered PASS under the reconciled counting rule.

## PHASE_1 authorization — WORK-UNIT MODE (normative execution constraints)

Phase 1 authorizes a SEQUENCE of bounded work units — it does NOT authorize
implementing the whole phase in one pass. Owner rules, verbatim:

> Implement exactly one bounded code unit at a time. For each unit: inspect its
> frozen contract, write or update its tests first, implement the minimum code
> required to satisfy that contract, run the scoped verification, inspect the
> diff, and stop. Do not begin the next code unit until the current one has an
> evidence-backed PASS.

> A phase authorizes a sequence of bounded work units; it does not authorize
> implementing the whole phase in one pass.

Phase 1 work-unit sequence (owner-defined):
1. `adapters/contract.py` — freeze the structured-feed contract ONLY (allowed
   fields, types, required/optional, invariants, mapping to `SourceFactIR`).
   Contract tests. Green gate. **No parser yet.**
2. `adapters/structured_feed.py` — `bytes/record → candidate source facts`
   ONLY. No semantic normalization, no policy, no admissibility. Fault cases
   FC. Green gate.
3. `passes/input_validation.py` — validate adapter output against the value
   contract; produce `INPUT_CONTRACT_ERROR` / `TYPE_ERROR` where applicable.
   Mutation-sensitive tests. Green gate.
4. Minimal integration: `structured_feed → input_validation → SourceFactIR`,
   positive + negative cases. No general pipeline, CLI, renderer, or policy
   machinery yet.
5. Phase 1 closes only when that chain is demonstrably stable.

NEXT UNIT: **Unit 1 only — `adapters/contract.py` + its tests. Nothing else.**

## Standing constraints

- Frozen core: the ONLY permitted core change remains the adjudicated additive
  `CanonicalClinicalIR` (D10); Unit 1 must not touch it.
- `uv run --no-sync` everywhere; zero runtime dependencies; mypy strict and
  ruff must stay green; TDD per `openspec/config.yaml` (`apply.tdd: true`).
- Writes allowed: `src/clinical_compiler/adapters/` (incl. missing
  `__init__.py`), its tests, `.gitignore` (ADJ-2), and
  `openspec/changes/clinical-compiler-r1/` records. No commits.

## Receipt

Bound bundle manifest unchanged: `7a7d3a28afa749c362a2091f4ea0c60d25745f0ede49ac311b5e8d8511e0737d`
(verification evidence: `outputs/inventory/`, engram #7256). Decision authority:
Felipe Gonzalez. Reviewer ≠ executor.
