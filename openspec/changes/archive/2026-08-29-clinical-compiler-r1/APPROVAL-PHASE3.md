# APPROVAL-PHASE3 — change: clinical-compiler-r1

OWNER INSTRUCTION (verbatim, 2026-08-29): **"autorizo fase 3"**

## Approved scope

PHASE_3 of `tasks.md` — **WORK-UNIT MODE** (same discipline as Phases 1-2):
> Implement exactly one bounded code unit at a time. For each unit: inspect its
> frozen contract, write or update its tests first, implement the minimum code
> required to satisfy that contract, run the scoped verification, inspect the
> diff, and stop. Do not begin the next code unit until the current one has an
> evidence-backed PASS.

Unit sequence (derived from tasks.md Phase 3 rows; executors MUST check the
full task list for omissions — the R-2.7 lesson):
1. `passes/document_selection.py` — DocumentIR from admissible canonical facts
   (refs + presentation roles ONLY, never values); `DOCUMENT_SELECTION_ERROR`.
2. `renderers/deterministic.py` — canonical byte rendering; `RENDER_ERROR`
   defense-in-depth (dangling-ref injection fixtures).
3. `linter/conformance.py` — `NURSING_RECORD_TELEGRAPHIC` mode rules;
   `LINT_FAILURE` (injection-reachable).
4. Determinism machinery — golden files + cross-run SHA-256 gate +
   `EVIDENCE_INTEGRITY = VALID|DEGRADED|INVALID` (implementation-generated
   goldens are DEGRADED evidence).
5. Independent expected sample under `tests/golden/independent/` — authored
   from the frozen spec/design ONLY by an author independent of the
   implementation (owner may substitute his own hand-authored sample at any
   time). ABSENCE BLOCKS the Phase-3 gate (P1-008/P2-012 repair).
6. Minimal Phase-3 integration (admissibility → document_selection → render →
   lint) + phase gate computation (ALL task-3.x rows verified covered).

## Standing constraints (unchanged, binding)

- Frozen core except the committed adjudicated `CanonicalClinicalIR` (already
  landed in Phase 2 — zero further core changes).
- Certainty rules (CRC-001/002), policy machine (CRC-005), runtime value
  boundary (CRC-006 R1 half), zero runtime deps, `uv run --no-sync`, mypy
  strict + ruff green, TDD per `openspec/config.yaml`.
- Hash-bound bundle (proposal/design/tasks/specs) FROZEN — no edits.
- Determinism invariants: tuple containers, codepoint sort keys, no
  time/locale/random/env dependence, UTF-8 + `\n` only.
- DocumentIR never stores clinical values — refs only (CRC-004 two-sided
  rule: selection impossible-by-construction / renderer defense-in-depth).

## NOT authorized

- Phase 4 (pipeline.py composition root + CLI + docs) — separate record.
  NOTE for Phase 4 (carried flag): pipeline.py MUST replicate the
  `is_resolved` policy branch (today test-helper only).
- Executor commits; commits remain owner-orchestrated acts.

## Receipt

- Bundle manifest (unchanged): `7a7d3a28afa749c362a2091f4ea0c60d25745f0ede49ac311b5e8d8511e0737d`
- PHASE_1 done (gate 1.9 PASS 8/8); PHASE_2 done (gate 2.8 PASS 11/11);
  commits `9d3ab30`→`b376c0c`→`267258b`→`172399b`→`470fef5`.
- Security scan (post-Phase-2, sealed): `scan-2026-08-29T19-08-39.327Z-35f4beb8b43d`,
  seal `sha256:1d4a246f…`, 0 findings, 0 dependency advisories (static-only
  evidence boundary).

Decision owner: Felipe Gonzalez. Reviewer ≠ executor.
This record authorizes NOTHING beyond PHASE_3.
