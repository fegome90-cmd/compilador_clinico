# Design: Clinical Kernel Stage 1 — Characterization and Architecture Gates

## Technical Approach

Add two test-only seams over the live R1 layout: `tests/unit/test_stage1_characterization.py` for C1–C3 and `tests/unit/test_architecture_gates.py` for A1/A2/A3/A5. Keep expected bytes, fault vectors, and context literals independent from implementation helpers. No production module, runtime path, fixture bytes, current main spec, archive, roadmap, or Etapa 0 artifact is changed by this planning batch.

C1 extends `tests/golden/manifest.json` and `tests/golden/independent/MANIFEST.json` with an explicit `compile_context` containing `NURSING_RECORD_TELEGRAPHIC` and the approved-empty `DEFERRED_BY_OWNER_DECISION` policy. The new characterization test reads the independent expected files, constructs that context, calls `clinical_compiler.pipeline.run`, and compares exact bytes plus digest. `tests/golden/golden_machinery.py::{load_manifest,assess_golden_evidence}` remains a self-consistency mechanism, not the independent oracle.

C2 uses an independent `FaultOracleCase` table in the new test module. Each row carries input, policy/context, exact ordered `DiagnosticCode` values, `document_is_none`, and expected exit. Rows cover the current pipeline/CLI corpus and injected render/lint defenses; no expected vector is imported from existing parameter tables. C4/C5 remain no-op after readback unless current evidence is disproved.

C3 runs a fresh child interpreter over the same production chain and emits canonical JSON, never `repr`: document presence/digest, ordered diagnostic codes, canonical fact IDs, `source_fact_refs`, and `(source_kind, source_ref)` provenance. Repeated isolated and seeded processes must produce identical envelopes.

## Architecture Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Independent oracle | Literal manifest bytes/vectors plus explicit context | Prevents implementation-generated self-approval. |
| AST gate | `ast.parse` over `src/clinical_compiler/**/*.py`, normalized import names, explicit denylist | Tests production structure without importing or executing production code. |
| Gate locator | `tests/unit/test_architecture_gates.py::test_production_import_boundaries_are_respected` | Gives A1/A2/A3/A5 one stable documented locator. |
| A4 correction | Point `docs/agent/ARCHITECTURE.md:254` to `tests/unit/test_cli.py::test_pyproject_registers_the_console_script_with_zero_deps`; replace the uncommitted AST-script claim with the new locator at line 255 | Aligns documentation with actual and planned evidence. |

## Data Flow

```text
manifest context + independent bytes
        -> pipeline.run / exact C1-C2 assertions
        -> fresh child observation envelope
        -> AST scan of production imports
        -> scope audit and verification commands
```

## File Changes

| File | Action | Description |
|---|---|---|
| `tests/unit/test_stage1_characterization.py` | Future create | C1–C3 tests and independent fault oracle. |
| `tests/unit/test_architecture_gates.py` | Future create | Production-only AST/import gate for A1/A2/A3/A5. |
| `tests/golden/manifest.json` | Future modify | Add context metadata only; preserve scenario/input/document bytes. |
| `tests/golden/independent/MANIFEST.json` | Future modify | Bind the same context to independent expected bytes. |
| `docs/agent/ARCHITECTURE.md` | Future modify | Two minimal fitness-test locator corrections only. |

## Interfaces / Contracts

The test-only observation envelope is canonical JSON with keys `document_sha256`, `document_is_none`, `diagnostic_codes`, `clinical_fact_ids`, `source_fact_refs`, and `provenance`. Import rules are normalized to absolute module names before denylist comparison; relative intra-core imports remain allowed.

## Testing Strategy

Run targeted characterization and architecture tests first, then:

```bash
uv run --no-sync pytest -q
uv run --no-sync pytest --cov=clinical_compiler --cov-report=term-missing --strict-markers
uv run --no-sync ruff check src tests
uv run --no-sync mypy --strict src
python3 "${ACS_ROOT:-$HOME/.claude/skills/agent-context-system}/scripts/validate_agent_context.py" . --strict-generated
```

No test, build, install, sync, or fixture-regeneration command is run in this planning batch.

## Migration / Rollout

No migration or runtime rollout. Apply test-only gates, correct the two documentation locators, then perform a narrow diff audit that preserves Etapa 0 and all protected paths.

## Open Questions

None; Runtime Bundle is the explicit prerequisite for executable A6 qualification.
