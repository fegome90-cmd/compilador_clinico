# Architecture

## Architectural Intent

The clinical record compiler compiles structured clinical observation feeds into deterministic, fail-closed, and traceable nursing record documents (`NURSING_RECORD_TELEGRAPHIC`).

The fundamental architectural design follows a functional core and imperative shell pattern. Pure transformation passes consume and produce immutable representations, while I/O, policy resolution, filesystem operations, and process exit code mapping remain isolated in driving and driven adapters.

Key structural properties preserved across all layers:
- Strict separation between source-declared certainty, compiler-assigned certainty, missingness, and provenance.
- Absolute byte determinism: zero ambient environment leakage (locale, timestamps, hash seeds, or platform variations).
- Whole-run fail-closed emission: any diagnostic emitted across any stage completely blocks document emission.
- Zero runtime dependencies: stdlib-only implementation.

## Architectural Drivers

| Driver | Architectural consequence |
|---|---|
| Deterministic byte generation | Fixed pipeline ordering, immutable tuples, canonical JSON encoding, and explicit codepoint sorting (`field_id`, `clinical_fact_id`). |
| Clinical safety & fail-closed execution | Diagnostics accumulate across passes without silent fact discarding; any diagnostic yields non-zero exit and suppresses document emission. |
| Certainty axis separation | Source certainty (`source_asserted_certainty`) is preserved verbatim and never conflated with compiler certainty (`ClinicalValue.certainty`). |
| Auditable data lineage | Normalized canonical facts retain backward references (`source_fact_refs`) to constituent raw observations. |
| Zero runtime dependencies | Implemented purely with Python standard library modules without external web frameworks, ORMs, or CLI packages. |

## System Composition

### Structural Overview

```text
+-----------------------------------------------------------------------------------+
| IMPERATIVE SHELL (CLI & Adapters)                                                 |
|                                                                                   |
|  clinical_compiler.cli:main / _execute                                             |
|   - _read_input: Reads JSONL input into bytes                                     |
|   - _resolve_policy: Evaluates policy seed via load_policy_seed                       |
|   - _atomic_write: Atomic file replacement for --output                           |
|   - _emit: Emits UTF-8 bytes to stdout or diagnostics to stderr                    |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| COMPOSITION ROOT (pipeline.py: run / CompileRequest -> CompileResult)             |
+-----------------------------------------------------------------------------------+
                                          |
       +----------------------------------+----------------------------------+
       |                                                                     |
       v                                                                     v
+-------------------------------------+   +-----------------------------------------+
| DRIVING ADAPTERS                    |   | FUNCTIONAL PASSES                       |
|  - adapters.structured_feed:        |   |  - passes.input_validation:             |
|    parse_feed (FeedEvaluation)      |   |    run_input_validation (_violation)    |
|  - adapters.contract:               |   |  - passes.semantic_normalization:       |
|    map_record (ContractEvaluation)  |   |    run_semantic_normalization           |
|  - adapters.seed:                   |   |    (_interpret, _clinical_fact_id)      |
|    load_policy_seed                 |   |  - passes.admissibility:                |
|    (PolicyResolution)               |   |    run_admissibility                    |
|                                     |   |    (_vetoed_term, _unresolvable_refs)   |
|                                     |   |  - passes.document_selection:           |
|                                     |   |    run_document_selection               |
+-------------------------------------+   +-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| CORE DOMAIN LEAF (Pure Immutable IR & Types)                                      |
|  - core.types: Certainty, Missingness, Provenance, ClinicalValue                  |
|  - core.ir: SourceFactIR, CanonicalClinicalFact, CanonicalClinicalIR              |
|             DocumentEntry, DocumentIR                                             |
|  - core.diagnostics: DiagnosticCode, Diagnostic                                    |
|  - core.policy: NEVER_AUTO_TERMS (frozen empty default)                           |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| DRIVEN RENDERERS & LINTER                                                         |
|  - renderers.deterministic: render_document (Canonical formatting, LF, glyphs)   |
|  - linter.conformance: lint_conformance (Independent byte/grammar validation)      |
+-----------------------------------------------------------------------------------+
```

### Components

#### CLI Shell (`clinical_compiler.cli`)
**Responsibility:** Command-line argument parsing, policy resolution invocation, file I/O, process exit codes, and standard stream management.
**Owns:** Argument parsing (`_build_parser`), stdin/file reading (`_read_input`), policy seed loading (`_resolve_policy`), atomic output writes (`_atomic_write`), stream emission (`_emit`), and entry point (`main`, `_execute`).
**Does not own:** Pipeline execution logic, fact transformation, or document formatting.
**Depends on:** `pipeline`, `adapters.seed`, `core.diagnostics`.
**Used by:** External invocation / console script `clinical-compiler`.
**Interfaces:** CLI options (`INPUT`, `--mode`, `--policy-seed`, `--output`), standard input/output/error streams, exit codes (`0`, `2`, `3-10`, `70`).

#### Pipeline Composition Root (`clinical_compiler.pipeline`)
**Responsibility:** Orchestrating the sequential execution of input validation, semantic normalization, admissibility, document selection, emission gating, deterministic rendering, and conformance linting.
**Owns:** `CompileRequest`, `CompileResult`, `derive_exit_code`, `run`.
**Does not own:** Individual pass transformation logic or file system writes.
**Depends on:** `adapters.structured_feed`, `passes.input_validation`, `passes.semantic_normalization`, `passes.admissibility`, `passes.document_selection`, `renderers.deterministic`, `linter.conformance`, `core.ir`, `core.diagnostics`, `pipeline_types`.
**Used by:** `clinical_compiler.cli`.
**Interfaces:** `run(request: CompileRequest) -> CompileResult`.

#### Input & Structured Feed Adapters (`clinical_compiler.adapters`)
**Responsibility:** Parsing raw JSONL lines into structured fact objects, validating closed field schemas, verifying provenance vocabularies, and loading policy seeds.
**Owns:** `parse_feed`, `FeedEvaluation`, `map_record`, `ContractEvaluation`, `FieldContract`, `CONTRACT`, `REQUIRED_RECORD_KEYS`, `OPTIONAL_RECORD_KEYS`, `ALLOWED_RECORD_KEYS`, `ALLOWED_SOURCE_KINDS`, `load_policy_seed`, `PolicyResolution`, `PolicyResolutionState`, `PolicySeedFault`, `DEFERRED_BY_OWNER_DECISION`, `approved_empty_by_deferral`.
**Does not own:** Canonical normalization or policy veto execution.
**Depends on:** `core.ir`, `core.diagnostics`, `pipeline_types`.
**Used by:** `clinical_compiler.pipeline`, `clinical_compiler.cli`.

#### Semantic Normalization Pass (`clinical_compiler.passes.semantic_normalization`)
**Responsibility:** Transforming validated source facts into canonical clinical facts with explicit certainty, missingness, and provenance representations.
**Owns:** `run_semantic_normalization`, `_interpret`, `_clinical_fact_id`.
**Does not own:** Policy veto enforcement or document structuring.
**Depends on:** `core.types`, `core.ir`, `core.diagnostics`, `pipeline_types`.
**Used by:** `clinical_compiler.pipeline`.

#### Policy Admissibility Pass (`clinical_compiler.passes.admissibility`)
**Responsibility:** Enforcing clinical policy veto terms and verifying that fact references point strictly to surviving source facts.
**Owns:** `run_admissibility`, `_vetoed_term`, `_unresolvable_refs`.
**Does not own:** Policy seed loading or file parsing.
**Depends on:** `core.ir`, `core.diagnostics`, `pipeline_types`.
**Used by:** `clinical_compiler.pipeline`.

#### Document Selection Pass (`clinical_compiler.passes.document_selection`)
**Responsibility:** Selecting admissible canonical clinical facts and assembling structural document entries for the target mode.
**Owns:** `run_document_selection`, `NURSING_RECORD_TELEGRAPHIC`, `SUPPORTED_MODES`, `TELEGRAPHIC_ENTRY_ROLE`.
**Does not own:** Byte rendering or string formatting.
**Depends on:** `core.ir`, `core.diagnostics`, `pipeline_types`.
**Used by:** `clinical_compiler.pipeline`.

#### Deterministic Renderer (`clinical_compiler.renderers.deterministic`)
**Responsibility:** Converting `DocumentIR` and `CanonicalClinicalIR` into bit-deterministic UTF-8 encoded bytes.
**Owns:** `render_document`.
**Does not own:** Byte grammar validation or conformance checking.
**Depends on:** `core.ir`, `core.types`, `core.diagnostics`, `pipeline_types`.
**Used by:** `clinical_compiler.pipeline`.

#### Conformance Linter (`clinical_compiler.linter.conformance`)
**Responsibility:** Independently verifying generated document bytes against document mode grammar, vocabulary, and encoding rules without relying on renderer internal state.
**Owns:** `lint_conformance`.
**Does not own:** Document rendering.
**Depends on:** `core.diagnostics`, `pipeline_types`.
**Used by:** `clinical_compiler.pipeline`.

#### Core Domain Leaf (`clinical_compiler.core`)
**Responsibility:** Defining foundational types, immutable IR dataclasses, diagnostic definitions, and static policy defaults.
**Owns:** `Certainty`, `Missingness`, `Provenance`, `ClinicalValue`, `SourceFactIR`, `CanonicalClinicalFact`, `CanonicalClinicalIR`, `DocumentEntry`, `DocumentIR`, `DiagnosticCode`, `Diagnostic`, `NEVER_AUTO_TERMS`.
**Does not own:** File I/O, parsing, pass logic, rendering, or CLI execution.
**Depends on:** Standard library only (`dataclasses`, `enum`, `typing`). Leaf domain module importing standard library only, with relative intra-core imports (e.g. `core.ir` importing `.types`). Zero dependencies on outer compiler layers.
**Used by:** All compiler passes, adapters, renderers, linter, and pipeline.

## Dependency Rules

**Architectural Layer Hierarchy:**
`cli` -> `pipeline` -> `{passes, renderers, linter}` -> `{adapters, pipeline_types}` -> `core` -> `types`

**Direct Module Permissions & Import Edges:**
- `cli`: Imports `pipeline`, `adapters.seed`, `passes.document_selection`, and `core.diagnostics`.
- `pipeline` (composition root): Imports all passes, renderers, linter, adapters, `pipeline_types`, and `core`.
- `passes.input_validation`, `renderers.deterministic`, `linter.conformance`: Direct import of `adapters.contract` permitted for field contracts, vocabulary definitions, and allowed constants.
- `passes.semantic_normalization`, `passes.admissibility`, `passes.document_selection`: Pure passes importing only `core` and `pipeline_types` (never `adapters`).
- `adapters.structured_feed`: Imports `adapters.contract` and `core.diagnostics`. `adapters.seed` is self-contained.
- `pipeline_types`: Leaf contract container importing only `core.diagnostics`.
- `core`: Pure leaf domain layer importing standard library only (`core.ir` imports `core.types`).

**Forbidden Edges:**
- `core` must never import `adapters`, `passes`, `renderers`, `linter`, `pipeline`, or `cli`.
- `pipeline_types` must never import `pipeline` or passes.
- Passes must never import `pipeline`, `cli`, `renderers`, or `linter`.
- `renderers` and `linter` must never import `pipeline` or `passes`.
- `adapters` must never import `pipeline`, `passes`, `renderers`, `linter`, or `cli`.

## State Ownership

| State | Owner | Writers | Readers | Persistence |
|---|---|---|---|---|
| Raw Observation Record | `SourceFactIR` | `adapters.contract:map_record` | `passes.input_validation`, `passes.semantic_normalization` | In-memory during run |
| Canonical Clinical Fact | `CanonicalClinicalFact` | `passes.semantic_normalization` | `passes.admissibility`, `renderers.deterministic` | In-memory during run |
| Canonical Fact Aggregate | `CanonicalClinicalIR` | `pipeline:run` | `passes.document_selection`, `renderers.deterministic` | In-memory during run |
| Document Structure | `DocumentIR` | `passes.document_selection` | `renderers.deterministic` | In-memory during run |
| Clinical Policy Terms | `PolicyResolution` | `adapters.seed:load_policy_seed` | `passes.admissibility` | In-memory during run |
| Compilation Result | `CompileResult` | `pipeline:run` | `clinical_compiler.cli:_emit`, `_atomic_write` | In-memory / derived bytes |

`DocumentIR` holds references (`clinical_fact_ref`) and presentation roles only; it never duplicates clinical values or becomes the value authority.

## External and Trust Boundaries

- **Input Ingestion Boundary:** External JSONL input is parsed via `adapters.structured_feed` and strictly validated against `adapters.contract`. Unknown fields, malformed JSON, and invalid types produce diagnostics immediately and are quarantined.
- **Policy Ingestion Boundary:** `--policy-seed` must be valid JSON matching `{"terms": ["term_a"]}`. An invalid seed yields `PolicyResolutionState.UNRESOLVED_POLICY` (with typed fault reasons such as `PolicySeedFault.WRONG_SHAPE` or `PolicySeedFault.MALFORMED_JSON`) and blocks execution with exit code 2. If `--policy-seed` is omitted, the empty policy state is authorized strictly via `DEFERRED_BY_OWNER_DECISION`.
- **Pure Core Boundary:** All passes operate on immutable data structures and return typed `StageResult[T]` containers with zero filesystem or network side effects.
- **Atomic Output Boundary:** Output files are written to a temporary file in the destination directory, flushed, fsynced, and atomically replaced (`os.replace`). Failed runs produce zero output files.

## Runtime Scenarios

### Successful Compilation (`exit 0`)
1. User invokes `clinical-compiler compile input.jsonl --output out.txt`.
2. CLI reads input file bytes and verifies policy deferral.
3. Pipeline executes validation, normalization, admissibility, selection, rendering, and linting sequentially.
4. Zero diagnostics are produced.
5. Renderer generates deterministic UTF-8 bytes.
6. Linter validates byte conformance against mode grammar.
7. CLI atomically writes bytes to `out.txt` and exits with code 0.

### Quarantined Fact Compilation (Fail-Closed Diagnostic Exit)
1. Input feed contains three records: one non-conforming record (e.g. `bool` for `FC`) and two valid records.
2. Ingestion / validation quarantines the non-conforming record with a `TYPE_ERROR` diagnostic while accepting the two valid facts.
3. Because diagnostics are accumulated across the run, `pipeline.run` sets `document=None`, suppressing document emission entirely.
4. `derive_exit_code` selects the minimum stage-order code among present diagnostics in the 3–10 range (exit 4 for `TYPE_ERROR` in this scenario) rather than exit 0 or a partial document.
5. CLI emits accumulated diagnostics to stderr and exits with the derived exit code.

### Unresolved Policy Failure (CLI Usage Exit 2)
1. User provides `--policy-seed bad_seed.json` with malformed structure.
2. CLI fails policy resolution with a typed fault (such as `PolicySeedFault.WRONG_SHAPE` or `PolicySeedFault.MALFORMED_JSON`) and state `PolicyResolutionState.UNRESOLVED_POLICY`.
3. Execution blocks immediately before admissibility.
4. CLI prints diagnostic to stderr and exits with usage exit code 2.

## Cross-Cutting Concepts

- **Diagnostic Accumulation:** Every pass receives surviving facts, processes them, returns survivors, and accumulates `Diagnostic` records in `StageResult`.
- **Fail-Closed Emission Gate:** Before reaching rendering, `pipeline.run` evaluates accumulated diagnostics. Any diagnostic forces `CompileResult.document = None` and triggers diagnostic exit code mapping.
- **Determinism:** All collections utilize tuples and are explicitly sorted by `(field_id, clinical_fact_id)` codepoint order. No reliance on dictionary insertion order, hash randomization, locale settings, or timestamps.

## Architectural Invariants

- **INV-001 (Zero Dependencies):** The compiler runtime has zero third-party dependencies, relying exclusively on the Python standard library.
- **INV-002 (Certainty Separation):** Source-asserted certainty (`source_asserted_certainty`) is preserved verbatim and never converted into or derived from `source_kind`.
- **INV-003 (R1 Certainty State):** Normalized clinical facts evaluate compiler certainty strictly to `Certainty.UNRESOLVED`.
- **INV-004 (Missingness Distinction):** Assessed absence (`raw_value: null`) normalizes to `Missingness.MISSING`; unassessed data renders `unknown [not_assessed]`.
- **INV-005 (DocumentIR Reference Shape):** `DocumentEntry` stores `clinical_fact_ref` and `presentation_role` only. Values reside exclusively in `CanonicalClinicalFact`.
- **INV-006 (Byte Determinism):** Rendered outputs are bit-identical across all executions with LF line endings and UTF-8 encoding.
- **INV-007 (Independent Linting):** Conformance linting verifies byte grammar and vocabulary independently of renderer implementation.
- **INV-008 (Fail-Closed Delivery):** Any diagnostic emitted during compilation suppresses document emission completely.
- **INV-009 (Strict Exit Codes):** Process exit codes strictly reflect run outcome (`0`, `2`, `3-10`, `70`).

## Risk-Driven Complexity Control

Architectural complexity is admitted only when demanded by explicit clinical safety, determinism, or traceability requirements.

Guidelines governing architectural changes:
1. Identify the concrete clinical safety or determinism constraint.
2. Verify whether the existing functional-core architecture can accommodate the requirement.
3. Compare against simpler alternatives before introducing new abstractions.
4. Reject speculative features: no plugin systems, no generic dynamic dispatchers, no database layers, no asynchronous task queues.
5. Preserve reversibility: keep core domain models minimal and pure.

## Architecture Conformance and Evolution

Architectural drift is prohibited. Any intentional modification to component responsibilities, dependency directions, state boundaries, or domain types must proceed through:
1. Identification of observed constraint or requirement.
2. Proposal of architectural delta with trade-off analysis.
3. Formal specification update under `openspec/specs/`.
4. Updating this canonical architecture narrative (`docs/agent/ARCHITECTURE.md`).
5. Implementation with strict TDD and test coverage verification.

## Architectural Fitness Functions

| Invariant | Verification Mechanism |
|---|---|
| Zero runtime dependencies | `tests/unit/test_cli.py:test_runtime_dependencies_are_empty` inspecting `pyproject.toml` |
| Import & dependency direction | AST static import analysis script validating forbidden module import edges |
| Byte determinism | `tests/unit/test_integration_golden_determinism.py` testing across multiple invocations |
| Test coverage threshold | `pytest --cov=clinical_compiler --cov-report=term-missing` requiring >= 95.0% branch coverage |
| Static typing & linting | `mypy --strict src` and `ruff check src tests` exiting with code 0 |

## Architectural Non-Goals

- No relational, document, or key-value database persistence.
- No background workers, queues, or distributed communication.
- No agent orchestrator, LLM inference client, or MCP integration in the compiler runtime.
- No web server, HTTP API endpoints, or socket listeners.
- No dynamic plugin architecture or runtime code evaluation (`eval`, `exec`).
- No multi-mode document generation beyond `NURSING_RECORD_TELEGRAPHIC` in R1.

## Known Architecture Risks

- **Type Narrowing Debt:** `ClinicalValue.value` is typed as `Any` at the dataclass level, although field contracts restrict it at runtime. Narrowing the static type definition is tracked for R2.
- **Policy Authoring Boundary:** Clinical policy terms must be authored by clinical domain owners via `--policy-seed` and never hardcoded into the compiler core.
