# APPROVAL-PHASE2 — change: clinical-compiler-r1

OWNER INSTRUCTION (verbatim, 2026-08-29): **"autorizo, paso 1 y 2"** — following the
two acts presented to the owner: (1) Phase-1 closure commit; (2) PHASE_2
authorization. Act (1) executed as commit `267258b`. This record authorizes act (2).

## Approved scope

PHASE_2 of `tasks.md` — **WORK-UNIT MODE** (same discipline as Phase 1):
> Implement exactly one bounded code unit at a time. For each unit: inspect its
> frozen contract, write or update its tests first, implement the minimum code
> required to satisfy that contract, run the scoped verification, inspect the
> diff, and stop. Do not begin the next code unit until the current one has an
> evidence-backed PASS.

Unit sequence (owner-defined, refined by adjudication ADJ-4):
1. `CanonicalClinicalIR` — the adjudicated additive lightweight aggregate in
   `core/ir.py` (D10; the ONLY permitted core change in R1) + construction-time
   invariants + tests (tasks 2.1a/2.2a).
2. `passes/semantic_normalization.py` — interpretation table; quarantine
   semantics; `SEMANTIC_AMBIGUITY_BLOCK`; no certainty invention.
3. `passes/admissibility.py` — veto terms + provenance resolution;
   `POLICY_VIOLATION` / `PROVENANCE_ERROR`.
4. `adapters/seed.py` — policy-seed loader + `UNRESOLVED_POLICY` state machine
   (D7); `DEFERRED_BY_OWNER` durable state (closed at the Phase-0 decision gate,
   recorded in APPROVAL-PHASE1.md) + test-local seeds.
5. Minimal integration (Phase-2 chain) + phase gate.

## Standing constraints (adjudicated, binding)

- Certainty authority (CRC-002 BOTH_SEPARATED): `source_asserted_certainty`
  preserved verbatim, never overwritten; `compiler_assigned_certainty` is
  non-clinical processing state; absent an approved deterministic rule →
  `UNRESOLVED`. The compiler MUST NOT produce `PROBABLE`/`LIKELY`/`UNLIKELY`
  in R1 (CRC-001 NOT_PRODUCED) and MUST NOT infer certainty from `source_kind`.
- Policy (CRC-005): missing seed without a durable owner decision →
  `UNRESOLVED_POLICY` → gate BLOCKED; empty set only via `DEFERRED_BY_OWNER`.
- Runtime value boundary (CRC-006 R1 half): bounded validation enforced at
  adapters + P1/P2; `Any` narrowing deferred to R2 (`r2_debt`).
- Zero runtime dependencies; `uv run --no-sync` everywhere; mypy strict +
  ruff green; TDD per `openspec/config.yaml`.
- Hash-bound bundle (proposal/design/tasks/specs) is FROZEN — no edits.

## NOT authorized

- Phases 3–4 (renderer/linter/CLI/docs) — require a separate approval record.
- Any git mutation by executors; commits remain owner-orchestrated acts.

## Receipt

- Bundle manifest (unchanged, verified post-Phase-1-closure):
  `7a7d3a28afa749c362a2091f4ea0c60d25745f0ede49ac311b5e8d8511e0737d`
- Gate 1.9 PASS (8/8 evidence); PHASE_1 = done (`outputs/phase1-close.md`).
- Phase-1 commits: `9d3ab30` (contract) → `b376c0c` (adapter+stage+integration)
  → `267258b` (closure).

Decision owner: Felipe Gonzalez. Reviewer ≠ executor.
This record authorizes NOTHING beyond PHASE_2.
