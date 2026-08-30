<!-- PROVENANCE
Domain: cli-surface
Origin: delta spec of change `clinical-compiler-r1` — merged into the main spec on 2026-08-29 by the sdd-archive phase (artifact store: hybrid).
This was the FIRST population of openspec/specs/ (main specs were empty). Content below this comment is byte-faithful to the approved delta; its SHA-256 is recorded in the archived change state.yaml under bundle_hashes_sha256 (change now at openspec/changes/archive/2026-08-29-clinical-compiler-r1/).
-->
# CLI Surface Specification

## Purpose

Runtime glue: the pipeline runner, the zero-dependency CLI and packaging, strict exit codes, documentation, and the final quality gates. The CLI command name and exact argument surface are OPEN — frozen in `design.md`, owner-reviewed at bundle approval — and are not assumed here.

## Requirements

### Requirement: Pipeline Runner

The system SHALL provide a pipeline runner composing every stage end-to-end — raw input to compiled document or enumerated diagnostics; the runner MUST NOT report success while any blocking diagnostic exists.

#### Scenario: End-to-end success

- GIVEN valid clinical input covering happy-path facts
- WHEN the runner executes
- THEN a compiled document is produced

#### Scenario: Diagnostics enumerate on failure

- GIVEN input producing any blocking diagnostic
- WHEN the runner executes
- THEN no document is emitted and every diagnostic is enumerated

### Requirement: Zero-Dependency CLI

The system SHALL expose a CLI entry point using only the standard library (argparse is the working assumption, frozen in `design.md`), registered via `[project.scripts]`; the command name and argument surface SHALL be frozen in `design.md` and owner-reviewed at bundle approval.

#### Scenario: Script entry registered, deps still zero

- GIVEN Phase 4 completed
- WHEN `pyproject.toml` is parsed
- THEN `[project.scripts]` registers the CLI and `[project].dependencies` has length `0` (entries only if admitted by an approval record)

#### Scenario: CLI compiles

- GIVEN the installed package and valid input
- WHEN the CLI is invoked
- THEN it compiles the input and exits with the success code

### Requirement: Strict Exit-Code Mapping

The CLI SHALL map outcomes to exit codes by a deterministic, documented mapping (frozen in `design.md`); any blocking diagnostic MUST NOT exit `0`, and identical failing input SHALL always produce the identical exit code.

#### Scenario: Non-zero on diagnostics

- GIVEN input producing `SEMANTIC_AMBIGUITY_BLOCK`
- WHEN the CLI runs
- THEN the exit code is non-zero per the documented mapping

#### Scenario: Deterministic exit codes

- GIVEN the same failing input run twice
- WHEN the exit codes are compared
- THEN they are identical

### Requirement: Documentation

`README.md` and `docs/architecture.md` SHALL be non-empty and SHALL describe the pipeline, contracts, and invariants; `.gitignore` SHALL be appended to cover `.coverage` and `.mimosa/`.

#### Scenario: Docs filled

- GIVEN Phase 4 completed
- WHEN `README.md` and `docs/architecture.md` are inspected
- THEN both are non-empty and cover pipeline, contracts, and invariants

### Requirement: Final Quality Gates

At the final gate the full suite SHALL pass with `tests_failed == 0` and measured branch coverage ≥ 95.0, and `mypy --strict` and `ruff check` SHALL both exit `0`; any non-zero result is BLOCKED.

#### Scenario: Computable quality gate

- GIVEN the final state of the repository
- WHEN `pytest`, `mypy --strict`, and `ruff check` run
- THEN `tests_failed == 0`, branch coverage ≥ 95.0, and both static checks exit `0`
