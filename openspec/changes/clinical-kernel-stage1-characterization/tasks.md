# Tasks: Clinical Kernel Stage 1 — Characterization and Architecture Gates

## Phase 1: Context and Oracle Foundation

- [x] **1.1** Reconfirm branch `codex/wo-001-clinical-kernel-preparation`, HEAD `729134461850a17d240327fb5d8243c9e77f976d`, tree `1dbc33ee1ffc2dc08498a53a1044a13211c7a078`; preserve the active Etapa 0 overlay and record the allowed Stage 1 paths.
- [x] **1.2** Add `compile_context` metadata to `tests/golden/manifest.json` and `tests/golden/independent/MANIFEST.json` without changing any input or expected-document bytes; bind mode and `DEFERRED_BY_OWNER_DECISION` explicitly.

## Phase 2: Characterization Gaps

- [x] **2.1** RED/GREEN: create `tests/unit/test_stage1_characterization.py` with a literal C1 oracle that runs `pipeline.run` under manifest context and directly compares production bytes and SHA-256 to each independent expected file.
- [x] **2.2** Add the independent C2 fault table with exact ordered diagnostic vectors, `document is None`, and exit mapping for the current pipeline/CLI corpus, including multi-diagnostic and render/lint defense cases.
- [x] **2.3** Add C3 fresh-process observations for bytes/digests, diagnostic vectors, canonical IDs, `source_fact_refs`, and provenance; compare canonical JSON envelopes across isolated and seeded interpreters.
- [x] **2.4** Verify existing C4/C5 evidence at their current seams (`test_passes_semantic_normalization.py`, `test_integration_phase3_chain.py`, and `test_pipeline.py`); explicitly leave both as **no-op** unless verification disproves coverage, then stop and record the exact new seam before adding a test.

## Phase 3: Architecture Gates

- [x] **3.1** RED/GREEN: create `tests/unit/test_architecture_gates.py::test_production_import_boundaries_are_respected` using `ast.parse` over production files only; cover A1 core leaf, A2 pure passes, A3 renderer/linter independence, and A5 no reverse host imports.
- [x] **3.2** Retain A4 as the existing `tests/unit/test_cli.py::test_pyproject_registers_the_console_script_with_zero_deps`; add no duplicate dependency test.
- [x] **3.3** Record A6 only as a documentation boundary; do not create an executable qualification test before Runtime Bundle.

## Phase 4: Traceability and Verification

- [x] **4.1** Correct only the two fitness-test locators in `docs/agent/ARCHITECTURE.md:254-255` to the exact A4 and architecture-gate symbols.
- [x] **4.2** Run targeted tests, full `pytest` with branch coverage, `ruff`, `mypy`, and ACS structural validation with `--no-sync`; record failures as blockers, never inferred PASS.
- [x] **4.3** Perform a final scope audit: only the new characterization/architecture tests, manifest context metadata, and two documentation locator lines are allowed; no source/runtime/config/current-spec/archive/roadmap/Etapa 0 mutation.

## Review Workload Forecast

Decision needed before apply: No
Chained PRs recommended: No
400-line budget risk: Low

The work is a bounded test-and-traceability slice; no production implementation or PR chain is planned.
