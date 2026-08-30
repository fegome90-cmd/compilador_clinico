# APPROVAL-PHASE4 — change: clinical-compiler-r1

OWNER INSTRUCTION (verbatim, 2026-08-29): **"continuemos con a y luego autorizo fase 4"** —
option A executed first (R-3.9c: glyph closed as `[<source_kind> <source_ref>]`;
independent re-derivation corroborates the goldens byte-for-byte;
EVIDENCE_INTEGRITY = VALID). With that precondition met, PHASE_4 is authorized.

## Approved scope

PHASE_4 of `tasks.md` — **WORK-UNIT MODE** (same discipline as Phases 1-3):
> Implement exactly one bounded code unit at a time. For each unit: inspect its
> frozen contract, write or update its tests first, implement the minimum code
> required to satisfy that contract, run the scoped verification, inspect the
> diff, and stop. Do not begin the next code unit until the current one has an
> evidence-backed PASS.

Unit sequence (derived from tasks.md Phase 4 rows — executors MUST check the
full task list for omissions, R-2.7 lesson):
1. `pipeline.py` — composition root: chain wiring (parse → validate →
   normalize → admit → aggregate → select → render → lint); the `is_resolved`
   policy branch (carried flag: MUST replicate the UNRESOLVED_POLICY gate);
   whole-run fail-closed emission gate (ANY diagnostic → no document bytes);
   exit-code derivation as a PURE function of the diagnostic set (frozen table
   0/2/3-10/70, min-code-present precedence); StageResult re-export from
   pipeline_types (G-1/D10).
2. CLI (`src/clinical_compiler/cli.py` + `[project.scripts]`
   `clinical-compiler = clinical_compiler.cli:main` — pyproject edit in scope):
   stdlib argparse, `compile INPUT [--mode] [--policy-seed] [--output]`,
   diagnostics to stderr, document bytes written ONLY at exit 0, atomic write
   (temp + os.replace + parent-dir fsync per design), exit codes per table.
3. Docs (CRC-009): README.md completed from the owner's draft as base +
   `docs/architecture.md` filled (pipeline, contracts, invariants, exit codes,
   determinism).
4. Final receipt (M10.3 schema: commands/exit codes, failures/recovery, human
   decisions, residual risk, next transition) + final gates (orphan
   DiagnosticCode count = 0, coverage ≥95, determinism, sdd-verify readiness)
   + phase close.

## Standing constraints (unchanged, binding)
- Frozen core (the adjudicated `CanonicalClinicalIR` already landed); zero
  runtime deps; `uv run --no-sync`; mypy strict + ruff; TDD.
- Hash-bound bundle FROZEN. Executor commits prohibited.
- Exit-code determinism: pure function of the diagnostic SET (identical input
  → identical exit code). No time/locale/random in any output path.

## NOT authorized
- `sdd-verify` / `sdd-archive` execution — separate orchestrator phases after
  Phase 4 close (verify will validate the implementation against all specs).

## Receipt
- Bundle manifest (unchanged): `7a7d3a28afa749c362a2091f4ea0c60d25745f0ede49ac311b5e8d8511e0737d`
- PHASE_1..3 done (gates 1.9: 8/8; 2.8: 11/11; 3.9: 5/5 with
  EVIDENCE_INTEGRITY VALID corroborated). Suite at Phase-4 start: 337/337,
  coverage 100%.
- Security scan (post-Phase-2, sealed, static-only): 0 findings.

Decision owner: Felipe Gonzalez. Reviewer ≠ executor.
This record authorizes NOTHING beyond PHASE_4.
