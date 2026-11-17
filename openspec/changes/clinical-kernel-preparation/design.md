# Design: Clinical Kernel Preparation

## Technical Approach

Etapa 0 is a documentation-only freeze over the live checkout. The verified subject is branch `codex/wo-001-clinical-kernel-preparation`, commit `729134461850a17d240327fb5d8243c9e77f976d`, tree `1dbc33ee1ffc2dc08498a53a1044a13211c7a078`; the archived R1 commit remains historical provenance, not a substitute baseline. `BASELINE_R1.md` records identity, current golden-manifest evidence, the observed R1 flow, and typed evidence (`Observed`, `Computed`, `Pending`). `ARCHITECTURE_DEBT_MAP.md` records D0.1-D0.6 without authorizing refactoring.

```text
00_SOURCE_BASIS.md (read-only) + live Git/code/spec evidence
             -> evidence classification and digest capture
             -> BASELINE_R1.md
             -> debt ownership/import map -> ARCHITECTURE_DEBT_MAP.md
             -> minimal labeled links from canonical agent docs
```

The documented implementation flow is preserved as evidence only:
`feed bytes -> contract/structured_feed -> pipeline.run -> validation -> normalization -> admissibility -> CanonicalClinicalIR -> selection -> render -> lint -> CompileResult`.

## Architecture Decisions

| Decision | Choice | Alternative rejected | Rationale |
|---|---|---|---|
| Baseline authority | Freeze the verified live commit/tree and distinguish workspace overlay from committed identity. | Copy the roadmap or use archived R1 as the current baseline. | Code, current specs, and the live checkout are the R1 ground truth; the archive is historical context. |
| Evidence/debt separation | Use two new documents: one evidence ledger and one debt/ownership map. | Expand `ARCHITECTURE.md` with a second narrative or roadmap tables. | Keeps evidence auditable and preserves one canonical architecture authority. |
| Cross-references | Add only short, scope-labeled links in `ARCHITECTURE.md` and `CODEMAP.md`. | Duplicate contracts, debt rows, or roadmap content. | Prevents competing authority while keeping navigation discoverable. |
| Gate semantics | Record manifest digests and command outcomes as typed evidence; unrun or unavailable checks remain Pending/blocked. | Infer PASS from existing files or historical logs. | Prevents overstated readiness and preserves provenance. |

The debt map rows are: D0.1 `adapters/contract.py` mixed source envelope plus FC/TA fields -> `structured_feed`/contract consumers -> split source/domain seam; D0.2 `passes/document_selection.py` mode/profile selection -> `pipeline -> selection` -> profile seam; D0.3 `pipeline.py` concrete composition-root imports -> adapters/passes/renderer/linter -> assemblable kernel, not urgent; D0.4 `pipeline.py` `CompileRequest`/`CompileResult` -> `cli -> pipeline` -> evolve without duplication; D0.5 `core/` stdlib-only leaf -> outer layers import core -> universal-only abstractions; D0.6 product/roadmap boundary with no runtime-bundle edge -> Etapa 7 Clinical Runtime Bundle, not package management.

## Interfaces / Contracts

- `BASELINE_R1.md`: identity/provenance, manifest and scenario digest references, observed compilation invariants (`CompileRequest`/`CompileResult`, pure `run`, FC/TA contract, one mode, blocking diagnostics, atomic output, byte determinism, zero external runtime dependencies), and a gate matrix.
- `ARCHITECTURE_DEBT_MAP.md`: one row per debt with ID, current owner/path, responsibility, evidenced import edge, deferred seam, and non-authority status.
- Canonical cross-references explicitly state that `docs/agent/ARCHITECTURE.md` remains architecture authority, `openspec/specs/` remains normative behavior authority, and the roadmap is read-only input.

## File Changes

| File | Action | Description |
|---|---|---|
| `docs/agent/BASELINE_R1.md` | Create | Exact live freeze and bounded evidence record. |
| `docs/agent/ARCHITECTURE_DEBT_MAP.md` | Create | D0.1-D0.6 ownership, responsibility, import edges, and deferred seams. |
| `docs/agent/ARCHITECTURE.md` | Modify | Minimal links and scope labels only. |
| `docs/agent/CODEMAP.md` | Modify | Minimal navigation links only. |
| `docs/local/clinical-kernel-staged-reports-v2/00_SOURCE_BASIS.md` | Read only | Roadmap source; never overwrite. |

Current manifest evidence is the committed `tests/golden/manifest.json` (`669e6f72fa48e50ab42d8b37993bdf77f81a0e940b868f7b8b0b07a7490d6ae9`) and `tests/golden/independent/MANIFEST.json` (`1d0b40bad026970a456d810a336da04d0f2307b72b791b9b75697893df151ffa`); scenario digests remain owned by those manifests.

## Verification Strategy

Use read-only, `--no-sync` checks after documentation writes: `uv run --no-sync pytest -q`; `uv run --no-sync pytest --cov=clinical_compiler --cov-report=term-missing --strict-markers`; `uv run --no-sync mypy --strict src`; and `uv run --no-sync ruff check src tests`. Do not install, sync, update goldens, rewrite fixtures, or alter environment state. Classify unavailable/unrun gates as Pending/blocked.

## Migration / Rollout

No migration, rollout, dependency change, or runtime activation is required. Rollback removes only the two new documents and reverts the minimal cross-reference lines.

## Forbidden Mutations

Do not create `kernel/`, move `core/`, add registries/profiles/MCP, change contracts, modes, output, diagnostics, clinical semantics, source, tests, fixtures, runtime, config, dependencies, public APIs, `openspec/specs/`, archive records, or the read-only roadmap.
