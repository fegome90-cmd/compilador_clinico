# Proposal: Clinical Kernel Preparation

## Intent

Freeze the verified live R1 baseline before future kernel refactoring and make Etapa 0 debt auditable. This is documentation-only: it records evidence and ownership without changing executable behavior, normative runtime contracts, or clinical semantics.

## Scope

### In Scope

- Freeze the verified live baseline: branch `codex/wo-001-clinical-kernel-preparation`, HEAD `729134461850a17d240327fb5d8243c9e77f976d`, tree `1dbc33ee1ffc2dc08498a53a1044a13211c7a078`.
- Produce the baseline freeze/evidence record at `docs/agent/BASELINE_R1.md`, separating observed evidence, inference, and pending gates.
- Produce the Etapa 0 architecture debt map at `docs/agent/ARCHITECTURE_DEBT_MAP.md` for D0.1–D0.6, including current ownership, responsibility, import edges, and future seam/defer point.
- Treat existing `docs/local/clinical-kernel-staged-reports-v2/00_SOURCE_BASIS.md` as read-only roadmap input; never overwrite it.
- Add minimal cross-references in canonical `docs/agent/ARCHITECTURE.md` and `docs/agent/CODEMAP.md` so staged reports do not become a competing architecture authority.
- Preserve the seven `openspec/specs/*/spec.md` files as the normative behavior authority.

### Out of Scope

No kernel move, registry, profile, mode, contract, MCP, output, diagnostics, or clinical semantic changes. Also excluded: source, tests, fixtures, runtime, configuration, main-spec, dependency, and public-API changes.

## Capabilities

No runtime normative capability is introduced or modified.

### New Capabilities

- `clinical-kernel-preparation-documentation`: artifact-only baseline, debt, ownership, import-map, and canonical cross-reference documentation.

### Modified Capabilities

- None; current main specifications remain unchanged.

## Approach

Verify Git identity before recording it; use live code and current specs as ground truth. Align Etapa 0 documents with the roadmap, keep `docs/agent/ARCHITECTURE.md` canonical, and label every gate as observed, computed, or pending rather than assuming PASS.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `docs/agent/BASELINE_R1.md`, `docs/agent/ARCHITECTURE_DEBT_MAP.md` | Documentation | New baseline evidence and D0.1–D0.6 ownership/import map |
| `docs/agent/ARCHITECTURE.md`, `docs/agent/CODEMAP.md` | Cross-reference only | Point to the new artifacts without duplicating authority |
| `docs/local/clinical-kernel-staged-reports-v2/00_SOURCE_BASIS.md` | None | Read-only roadmap input; never overwritten |
| `openspec/specs/` | None | Read-only normative reference |

## Risks

| Risk | Mitigation |
|---|---|
| Baseline drift | Record exact SHA/tree and recheck before documentation writes |
| Conflicting architecture narratives | Use canonical-doc cross-references only |
| Overstated verification | Separate evidence, inference, and pending work |

## Rollback Plan

Revert or remove only the new documentation artifacts and cross-references; restore prior canonical-doc bytes and leave source, tests, fixtures, runtime, configuration, roadmap input, and main specs untouched.

## Dependencies

Verified live Git state, the Etapa 0 roadmap, canonical architecture/codemap docs, and current main specifications.

## Success Criteria

- [ ] `docs/agent/BASELINE_R1.md` records the exact verified SHA/tree and bounded gate evidence.
- [ ] `docs/agent/ARCHITECTURE_DEBT_MAP.md` maps D0.1–D0.6 to ownership, paths, import edges, and deferred seams.
- [ ] Canonical architecture and codemap references are minimal and non-competing.
- [ ] Diff contains no behavior or normative capability changes; the only capability is artifact-only documentation.
