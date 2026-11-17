# Architecture Debt Map — Etapa 0

## Scope and authority

This map records observable R1 seams only. It is non-authoritative planning
evidence and does **not** authorize implementation or refactoring.

- `docs/agent/ARCHITECTURE.md` remains the sole architecture authority.
- `openspec/specs/` remains normative behavior authority.
- `docs/local/clinical-kernel-staged-reports-v2/00_SOURCE_BASIS.md` and the
  staged roadmap are read-only inputs, not architecture authority.
- No row below permits a `kernel/` move, a `core/` expansion, a registry,
  profile interface, contract/mode/output change, or runtime mutation.

## Ownership table

| Debt | Current owner/path | Current responsibility | Authority status |
|---|---|---|---|
| D0.1 | `src/clinical_compiler/adapters/contract.py` | External record envelope, provenance vocabulary, raw-value types, and the R1 field table | Observed implementation ownership; not a future domain authority |
| D0.2 | `src/clinical_compiler/passes/document_selection.py` | Target mode validation and presentation-entry selection | Observed R1 pass ownership; not a profile contract |
| D0.3 | `src/clinical_compiler/pipeline.py` | Composition-root wiring and whole-run emission gate | Observed R1 composition root; not an assemblable-kernel mandate |
| D0.4 | `src/clinical_compiler/pipeline.py` | `CompileRequest` / `CompileResult` UAPI boundary | Observed current UAPI; not permission to duplicate or redesign it |
| D0.5 | `src/clinical_compiler/core/` | Immutable domain types, IR, diagnostics, and policy default | Frozen leaf boundary; not a generic abstraction bucket |
| D0.6 | Product/roadmap boundary | Future separation of kernel codebase from exact runtime-bundle composition | Roadmap/product hypothesis; no current runtime owner is asserted |

## Debt register and deferred seams

| ID | Responsibility today | Evidenced import/dependency edge | Deferred seam / roadmap target | Non-authority status |
|---|---|---|---|---|
| D0.1 | `contract.py` combines the external structured-feed envelope and the R1 domain fields `FC`/`TA`, including source-kind and raw-value rules. | `adapters/structured_feed.py` imports `.contract`; `passes/input_validation.py` and `renderers/deterministic.py` consume `CONTRACT`; `pipeline.py` consumes the structured-feed adapter. | Split source/envelope contract from domain-module contract, deferred to the roadmap's **Etapa 2 — Preparación de Namespaces y Contratos**. | This row describes a seam; it does not prescribe a move or a new contract. |
| D0.2 | `document_selection.py` owns `SUPPORTED_MODES`, `NURSING_RECORD_TELEGRAPHIC`, `TELEGRAPHIC_ENTRY_ROLE`, and target selection. | `pipeline.py` imports `run_document_selection`; `cli.py` imports the mode vocabulary; the selection pass imports only `core` and `pipeline_types`. | Establish a profile boundary, deferred to **Etapa 3 — Profile Seam**. | The current one-mode behavior remains authoritative; no second mode is authorized. |
| D0.3 | `pipeline.py` directly wires feed parsing, validation, normalization, admissibility, selection, rendering, and linting. | `pipeline.py` imports `adapters.structured_feed`, all functional passes, `renderers.deterministic`, `linter.conformance`, `pipeline_types`, and `core`. | Make composition assemblable only when the roadmap reaches **Etapa 5 — Formación del Kernel**; current R1 wiring is not urgent. | This is a deferred architecture seam, not permission to introduce dependency injection now. |
| D0.4 | `pipeline.py` owns the existing `CompileRequest` / `CompileResult` boundary, including bytes, diagnostics, policy, and source-certainty carriers. | `cli.py` imports `CompileRequest`, `CompileResult`, `run`, and `derive_exit_code`; the console entry point calls the CLI shell. | Evolve the existing boundary without duplication, deferred to **Etapa 9 — UAPI Estable**. | The current types remain the only observed UAPI; no replacement interface is declared. |
| D0.5 | `core/` is a stdlib-only leaf containing immutable types, IR, diagnostics, and the frozen empty policy default. | `core.ir` imports only intra-core `.types`; outer adapters, passes, renderer, linter, and pipeline import core; core imports no outer layer. | Admit only universal abstractions after evidence, primarily during **Etapa 5 — Formación del Kernel**. | The leaf is deliberately frozen; no generic kernel module or core move is authorized. |
| D0.6 | R1 is a bounded compiler product; a separately modeled runtime bundle is not present in the current source/package boundary. | No runtime-bundle or package-manager edge is modeled in the current source. The CLI is a single local process with stdlib runtime closure. | Address the product/runtime composition seam at **Etapa 7 — Clinical Runtime Bundle**, not through package-management work in Etapa 0. | This is a product/roadmap boundary, not evidence for a current runtime defect or implementation task. |

## Current import/dependency edge table

| Current edge | Evidence | Boundary interpretation |
|---|---|---|
| `cli` → `pipeline`, `adapters.seed`, `passes.document_selection`, `core.diagnostics` | `src/clinical_compiler/cli.py:62-78` | Imperative shell drives the pure composition root and reads the mode vocabulary. |
| `pipeline` → adapters, passes, renderer, linter, `pipeline_types`, `core` | `src/clinical_compiler/pipeline.py:71-84` | Composition root owns fixed stage order and fail-closed orchestration. |
| `structured_feed` → `adapters.contract`, `core.diagnostics` | `src/clinical_compiler/adapters/structured_feed.py:30-35` | Feed parsing delegates record acceptance to the frozen contract. |
| `input_validation` → `adapters.contract`, `core`, `pipeline_types` | `src/clinical_compiler/passes/input_validation.py:25-29` | Defense-in-depth value validation uses the same R1 contract. |
| `document_selection` → `core`, `pipeline_types` | `src/clinical_compiler/passes/document_selection.py:66-72` | Selection stays a pure pass and does not import `pipeline`. |
| `renderer` → `adapters.contract`, `core`, `pipeline_types` | `src/clinical_compiler/renderers/deterministic.py:89-97` | Renderer resolves the field vocabulary while remaining I/O-free. |
| `linter` → `core`, `pipeline_types`, contract vocabulary | `src/clinical_compiler/linter/conformance.py:107+` and current architecture rules | Independent byte validation is downstream of rendering and does not import the renderer. |
| Outer layers → `core`; `core` → stdlib and permitted intra-core imports only | `src/clinical_compiler/core/*.py`; AST scan `2026-09-07T10:52:45Z` | The current core leaf has no reverse edge into adapters, passes, renderer, linter, pipeline, or CLI. |
| Runtime package → no third-party dependency | `pyproject.toml:[project]`; AST scan | `project.dependencies=[]`; development tools are not runtime dependencies. |

The table is an evidence map, not a proposed target architecture. Any future
change to an edge requires a separately approved specification and an update
to the canonical architecture document.
