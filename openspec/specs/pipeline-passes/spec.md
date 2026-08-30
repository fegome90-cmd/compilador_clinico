<!-- PROVENANCE
Domain: pipeline-passes
Origin: delta spec of change `clinical-compiler-r1` — merged into the main spec on 2026-08-29 by the sdd-archive phase (artifact store: hybrid).
This was the FIRST population of openspec/specs/ (main specs were empty). Content below this comment is byte-faithful to the approved delta; its SHA-256 is recorded in the archived change state.yaml under bundle_hashes_sha256 (change now at openspec/changes/archive/2026-08-29-clinical-compiler-r1/).
-->
# Pipeline Passes Specification

## Purpose

The four transformation stages — input validation, semantic normalization, admissibility, document selection — composed in the fixed order implied by the diagnostics taxonomy, each blocking fail-closed on its mapped diagnostic codes.

## Requirements

### Requirement: Scaffold Completion

The change SHALL implement every empty module under `src/clinical_compiler/{passes,linter,renderers,adapters}`; at the final gate the count of zero-byte files in those trees MUST be `0` — each implemented, or removed by a recorded design decision.

#### Scenario: Computable scaffold gate

- GIVEN the final phase completed
- WHEN zero-byte files under `src/clinical_compiler/{passes,linter,renderers,adapters}` are counted
- THEN the count is `0`, or every exception has a recorded design decision

### Requirement: Fixed Stage Order

The pipeline SHALL execute stages in taxonomy order — input validation → semantic normalization → admissibility → document selection → rendering → conformance lint — with provenance enforcement cross-cutting; a fact blocked by a stage MUST NOT be consumed by later stages, and the pipeline MUST NOT emit a successful document that silently omits a blocked fact.

#### Scenario: Blocked fact stops downstream

- GIVEN a fact set containing one contract-violating fact
- WHEN the pipeline runs
- THEN later stages never consume that fact and `INPUT_CONTRACT_ERROR` is reported

#### Scenario: No silent omission

- GIVEN any blocking diagnostic produced during compilation
- WHEN the run finishes
- THEN the diagnostics are enumerated and no successful document is emitted

### Requirement: Semantic Normalization

Semantic normalization SHALL map validated facts to `CanonicalClinicalFact` with a deterministic certainty/missingness interpretation; facts whose interpretation is ambiguous SHALL block with `SEMANTIC_AMBIGUITY_BLOCK` instead of being guessed.

#### Scenario: Unambiguous normalization

- GIVEN a validated fact with a single admissible interpretation
- WHEN it is normalized
- THEN a canonical fact is created with certainty, missingness, and `source_fact_refs` retained

#### Scenario: Ambiguity blocks

- GIVEN a fact with more than one admissible interpretation and no disambiguator
- WHEN it is normalized
- THEN `SEMANTIC_AMBIGUITY_BLOCK` is emitted and no canonical fact is created for it

### Requirement: Admissibility Veto

Admissibility SHALL enforce `NEVER_AUTO_TERMS`: a fact containing a vetoed term MUST NOT be auto-confirmed regardless of computed certainty — even `confirmed` — and SHALL yield `POLICY_VIOLATION`.

#### Scenario: Veto overrides certainty

- GIVEN a fact containing a `NEVER_AUTO_TERMS` term with computed certainty `confirmed`
- WHEN admissibility runs
- THEN the fact is not auto-confirmed and `POLICY_VIOLATION` is emitted

#### Scenario: Empty approved set

- GIVEN an owner-recorded decision to ship R1 with the empty set
- WHEN admissibility runs on ordinary facts
- THEN no `POLICY_VIOLATION` is emitted and compilation proceeds

### Requirement: Document Selection

Document selection SHALL assemble a `DocumentIR` for the target document mode (e.g. `NURSING_RECORD_TELEGRAPHIC`) referencing only canonical fact identifiers with presentation roles; selection failures SHALL yield `DOCUMENT_SELECTION_ERROR` and no document.

#### Scenario: Assembly from admitted facts

- GIVEN admitted canonical facts
- WHEN document selection completes
- THEN entries reference `clinical_fact_ref` ids and carry presentation roles

#### Scenario: Selection failure

- GIVEN a selection request that cannot produce a valid document (e.g. no admissible entries for the mode)
- WHEN selection runs
- THEN `DOCUMENT_SELECTION_ERROR` is emitted and no document is produced
