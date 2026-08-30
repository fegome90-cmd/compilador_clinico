# Determinism and Rendering Specification

## Purpose

The deterministic renderer and conformance linter: byte-identical output for identical input, golden-file verification, no environment leakage, and `RENDER_ERROR` / `LINT_FAILURE` as the final blocking gates.

## Requirements

### Requirement: Byte-Identical Determinism

Compiling an identical fixture set twice in fresh interpreters SHALL produce outputs with equal SHA-256 digests; the digest SHALL equal the committed golden digest; the renderer MUST NOT depend on unordered iteration, locale, wall-clock time, randomness, or environment state.

Dangling-ref adjudication (CRC-004 — `ACCEPTED_AS_FUNCTIONALLY_ABSORBED`, owner adjudication 2026-08-28):

```text
P4/document_selection: dangling canonical references impossible by construction
Renderer: injected inconsistent DocumentIR → RENDER_ERROR (defense-in-depth)
```

Rationale: P4 constructs references only from surviving admissible canonical facts; `RENDER_ERROR` does not redefine P4 ownership, and the same defect is NOT also classified as `DOCUMENT_SELECTION_ERROR`. The case is reachable only via internal corruption or injection, exercised via injected fixture (FC-10).

#### Scenario: Cross-run digest equality

- GIVEN one fixture set compiled twice in fresh interpreters
- WHEN both outputs are SHA-256 hashed
- THEN the digests are equal

#### Scenario: Golden digest match

- GIVEN the committed golden digest for a fixture set
- WHEN a compile runs
- THEN the output SHA-256 equals the golden digest; any mismatch is BLOCKED

#### Scenario: Render failure

- GIVEN a rendering fault during output production
- WHEN the renderer runs
- THEN `RENDER_ERROR` is emitted and no partial document is emitted

### Requirement: Golden Files

The change SHALL include committed golden files/digests as test fixtures; golden tests SHALL fail on any output-affecting change or nondeterminism.

#### Scenario: Golden regression detection

- GIVEN an output-affecting change to any stage
- WHEN the golden tests run
- THEN at least one golden comparison fails

### Requirement: Conformance Linter

The conformance linter SHALL validate the rendered document against its document-mode conformance rules; rule violations yield `LINT_FAILURE`, and only a lint-clean document SHALL be accepted as final output.

#### Scenario: Lint failure blocks

- GIVEN a rendered document violating a conformance rule of its mode
- WHEN the linter runs
- THEN `LINT_FAILURE` is emitted and the document is not accepted

#### Scenario: Clean document accepted

- GIVEN a conforming rendered document
- WHEN the linter runs
- THEN no `LINT_FAILURE` is emitted and the compile is accepted as final
