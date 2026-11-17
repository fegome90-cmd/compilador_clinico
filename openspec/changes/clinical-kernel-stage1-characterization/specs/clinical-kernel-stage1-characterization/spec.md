# Clinical Kernel Stage 1 Characterization and Architecture Gates Specification

## Purpose

Prepare R1 for kernelization with executable behavior and dependency gates. It depends on Etapa 0 and changes no production behavior.

## Requirements

### Requirement: C1 golden context and independent byte oracle

Golden manifests MUST bind mode and policy. The gate MUST compare production bytes with independent bytes and digest; self-consistency SHALL NOT pass alone.

#### Scenario: Context-bound agreement
- GIVEN explicit context and independent expected bytes; WHEN production runs; THEN bytes MUST equal independent bytes and digest.

#### Scenario: Context or byte mismatch
- GIVEN missing context or disagreement; WHEN the gate runs; THEN it MUST fail closed and name the scenario.

### Requirement: C2 exact fault-outcome oracle

An independent row MUST define every fault's ordered diagnostic vector, document nullness, and exit mapping. Compare equality, never membership or sets.

#### Scenario: Exact fault row
- GIVEN a current corpus fault; WHEN the production seam runs; THEN codes, `document is None`, and exit MUST equal the row, including order and multiplicity.

### Requirement: C3 fresh-process structural determinism

Fresh interpreters MUST agree on bytes, diagnostics, IDs, source-fact references, and provenance for identical input and context.

#### Scenario: Fresh clean and fault runs
- GIVEN clean and fault inputs; WHEN fresh processes compile them; THEN observation envelopes, including nullness, MUST match.

### Requirement: C4 missingness is preserved without duplication

Existing C4 tests MUST remain authoritative; Stage 1 MUST add no duplicate unless focused verification disproves coverage.

#### Scenario: Existing evidence
- GIVEN PC-1/PC-2 and normalizer tests cover both branches; WHEN Stage 1 is applied; THEN no new C4 test is added.

### Requirement: C5 certainty separation is preserved without duplication

Existing C5 tests MUST remain authoritative; Stage 1 MUST add no duplicate unless a new public seam is demonstrably uncovered.

#### Scenario: Existing evidence
- GIVEN normalizer and pipeline tests preserve both certainty axes; WHEN Stage 1 is applied; THEN no new C5 test is added.

### Requirement: A1 core remains a leaf

A production-only AST/import gate MUST fail if `clinical_compiler.core` imports adapters, passes, renderers, linter, pipeline, or CLI.

#### Scenario: Forbidden core edge
- GIVEN a core file imports an outer layer; WHEN production ASTs are scanned; THEN the gate MUST fail before runtime execution.

### Requirement: A2 passes remain pure

The AST gate MUST reject pass imports of CLI, filesystem, network, random, time, or locale modules.

#### Scenario: Forbidden pass edge
- GIVEN a pass imports a forbidden module; WHEN the AST gate runs; THEN it MUST fail with file and import.

### Requirement: A3 renderer/linter independence

Renderer and linter MUST NOT import one another or validate through the implementation being checked.

#### Scenario: Cross-import
- GIVEN a renderer/linter cross-import; WHEN the AST gate runs; THEN it MUST fail closed.

### Requirement: A4 zero runtime dependencies remains covered

`tests/unit/test_cli.py::test_pyproject_registers_the_console_script_with_zero_deps` MUST remain the A4 locator, and documentation SHALL point to it.

#### Scenario: Unapproved dependency
- GIVEN non-empty `[project].dependencies` without approval; WHEN the A4 test runs; THEN the gate MUST fail.

### Requirement: A5 has no reverse host dependency

Non-host production modules MUST NOT import CLI, API, MCP, or other host-only modules.

#### Scenario: Reverse host edge
- GIVEN a domain/kernel module imports a host integration; WHEN the AST gate runs; THEN it MUST fail with the offending edge.

### Requirement: A6 stays documentation-only

Stage 1 MUST document that installed/configured presence is not qualification, but MUST NOT add an executable A6 gate before Runtime Bundle exists.

#### Scenario: No Runtime Bundle
- GIVEN Runtime Bundle does not exist; WHEN Stage 1 is applied; THEN only the boundary note is recorded.

### Requirement: No functional mutation

The change MUST NOT modify production source, runtime, APIs, config, main specs, archives, roadmap, or Etapa 0 artifacts.

#### Scenario: Scope audit
- GIVEN the candidate is complete; WHEN its diff is audited; THEN only tests, test metadata, and minimal documentation traceability may appear.
