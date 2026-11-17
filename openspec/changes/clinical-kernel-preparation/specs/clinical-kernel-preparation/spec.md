# Clinical Kernel Preparation Documentation Specification

## Purpose

This capability defines Etapa 0 documentation for freezing R1 and recording preparation debt. It is artifact-only and MUST NOT introduce or modify runtime normative behavior.

## Requirements

### Requirement: Freeze exact baseline identity and provenance

The baseline record MUST name branch `codex/wo-001-clinical-kernel-preparation`, commit `729134461850a17d240327fb5d8243c9e77f976d`, and tree `1dbc33ee1ffc2dc08498a53a1044a13211c7a078`. It MUST identify these as live-checkout values captured before documentation writes, distinct from archived reference `c6578b685c9dd66bba8958f75749e0d02c061ed1` (tree `94b213e0ecb99f4c3083984b35f5fe75d67b814b`).

#### Scenario: Verified live identity
- GIVEN the live checkout matches the required branch, commit, and tree
- WHEN the freeze record is written
- THEN it records the exact identity and provenance

#### Scenario: Baseline drift
- GIVEN any identity component differs or cannot be verified
- WHEN freeze preparation runs
- THEN the baseline claim is BLOCKED and no substituted historical identity is accepted

### Requirement: Preserve typed, read-only verification evidence

The record MUST classify every gate or invariant as **Observed**, **Computed**, or **Pending**, with subject, source/command, result, and provenance. It MUST cover: `CompileRequest`/`CompileResult` and pure `pipeline.run`, stdlib-only `core`, FC/TA-only `CONTRACT`, one mode, blocking diagnostics, atomic output, byte determinism, and no network/DB/daemon/runtime dependencies. Collection MUST NOT install, sync, rewrite fixtures, alter environment state, or claim PASS from an unrun gate.

#### Scenario: Bounded evidence
- GIVEN read-only repository and specification evidence
- WHEN the record is assembled
- THEN facts are Observed, derived identity/hashes are Computed, and unrun gates remain Pending

#### Scenario: Mutating or unavailable gate
- GIVEN a gate would mutate the environment or cannot produce evidence
- WHEN it is considered for the record
- THEN that gate is Pending/blocked rather than PASS

### Requirement: Register D0.1-D0.6 ownership and deferred seams

The debt map MUST contain one row per debt, naming ownership, responsibility, import edge, and deferred seam:
- D0.1 — owner `adapters/contract.py`; mixed envelope and FC/TA fields; edge to `structured_feed` and contract consumers; seam: split source/domain.
- D0.2 — owner `passes/document_selection.py`; mode/profile target selection; edge `pipeline -> selection`; seam: profile boundary.
- D0.3 — owner `pipeline.py`; composition root; concrete adapter/pass/renderer/linter imports; seam: assemblable kernel, not urgent.
- D0.4 — owner `pipeline.py`; `CompileRequest`/`CompileResult` UAPI; edge `cli -> pipeline`; seam: evolve without duplication.
- D0.5 — owner `core/`; stdlib-only leaf; outer layers import it; seam: universal-only abstractions.
- D0.6 — owner product/roadmap boundary; no modeled runtime-bundle edge; seam: Etapa 7 Clinical Runtime Bundle, not package management.
It MUST NOT authorize implementation.

#### Scenario: Complete debt register
- GIVEN the six observable debts and current architecture are available
- WHEN the map is published
- THEN all six rows have auditable ownership, edges, and deferred seams

#### Scenario: Uncertain edge
- GIVEN an ownership or import edge is not evidenced
- WHEN the row is written
- THEN it is marked unresolved/pending and no speculative refactor is prescribed

### Requirement: Preserve canonical authority through minimal cross-references

`docs/agent/ARCHITECTURE.md` MUST remain architecture authority and `openspec/specs/` normative behavior authority. `docs/agent/CODEMAP.md` and the architecture document MAY add minimal links to the new artifacts, but MUST NOT duplicate or supersede contracts; the staged roadmap remains read-only input.

#### Scenario: Non-competing references
- GIVEN the new baseline and debt artifacts exist
- WHEN canonical docs are updated
- THEN they link to the artifacts with scope labels and retain existing authority

### Requirement: Enforce preparation and no-runtime-change boundaries

This phase MUST declare no kernel or `core/` move, registry, profile interface, contract or mode change, MCP, output/diagnostic/clinical-semantic change, or source/test/fixture/runtime/config/dependency/public-API/main-spec change. Later artifacts MUST remain documentation-only and preserve the existing behavior contract.

#### Scenario: Documentation-only delivery
- GIVEN the candidate diff contains only authorized documentation and cross-references
- WHEN scope is checked
- THEN it is accepted with no modified runtime capability

#### Scenario: Forbidden mutation
- GIVEN a prohibited path or behavior change appears
- WHEN scope is checked
- THEN the change is BLOCKED and the runtime/main specifications remain untouched
