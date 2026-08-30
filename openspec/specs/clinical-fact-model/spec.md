<!-- PROVENANCE
Domain: clinical-fact-model
Origin: delta spec of change `clinical-compiler-r1` — merged into the main spec on 2026-08-29 by the sdd-archive phase (artifact store: hybrid).
This was the FIRST population of openspec/specs/ (main specs were empty). Content below this comment is byte-faithful to the approved delta; its SHA-256 is recorded in the archived change state.yaml under bundle_hashes_sha256 (change now at openspec/changes/archive/2026-08-29-clinical-compiler-r1/).
-->
# Clinical Fact Model Specification

## Purpose

Invariants of the committed core (`core/types.py`, `core/ir.py`, `core/diagnostics.py`, `core/policy.py`) that every new compiler stage MUST uphold: certainty, missingness semantics, provenance traceability, and the IR ladder `SourceFactIR → CanonicalClinicalFact → DocumentIR`. The core is a frozen baseline — additive changes only.

## Requirements

### Requirement: Core Baseline Immutability

The change MUST NOT alter the public signatures or semantics of the committed core modules; core modifications SHALL be additive only, each with a recorded design justification.

#### Scenario: Additive-only diff

- GIVEN the committed core at baseline commit `c6578b6`
- WHEN the change is fully applied
- THEN a comparison of the core public API shows only additions, each justified in `design.md`

#### Scenario: Non-additive change escalated

- GIVEN a proposed modification that alters or removes existing core API
- WHEN no recorded design decision approves it
- THEN the change SHALL be escalated to the decision owner, not silently merged

### Requirement: Missingness Non-Conflation

The pipeline MUST preserve the core distinction between unassessed data (`unknown`, `not_assessed`) and assessed absence (`missing`, `not_applicable`); unassessed data SHALL render explicitly as `unknown` and MUST NOT be dropped or rewritten as assessed absence.

#### Scenario: Unassessed survives compilation

- GIVEN a source fact with missingness `not_assessed`
- WHEN the document compiles successfully
- THEN the rendered entry explicitly presents the value as unknown/unassessed

#### Scenario: Assessed absence requires a source assertion

- GIVEN a compiled document entry presenting assessed absence
- WHEN its provenance chain is inspected
- THEN the absence traces to a source fact that asserted it, never to mere absence of input

### Requirement: Certainty Preservation

Every canonical clinical fact SHALL carry a certainty from the core `Certainty` taxonomy; certainty SHALL be derived deterministically by explicit normalization rules, never silently invented or dropped.

**Certainty authority model (CRC-002 — `BOTH_SEPARATED`, owner adjudication 2026-08-28).** `source_asserted_certainty`: role = `clinical_source_assertion`; authority = `PRESERVED` (verbatim) — what the source declared, captured verbatim when present in input (optional, never invented). `compiler_assigned_certainty`: role = `processing_and_admissibility_state`; authority = `NON_CLINICAL` — what the pipeline computes. Invariants (normative): `source_asserted_certainty` MUST NOT be overwritten; `compiler_assigned_certainty` MUST NOT silently upgrade the source assertion; `source_kind` alone MUST NOT establish clinical certainty; unresolved authority or interpretation fails closed. Provenance and certainty are different axes: a monitor/lab origin informs `PROVENANCE`, it does not by itself demonstrate clinical truth.

**Certainty taxonomy (CRC-001 — owner adjudication 2026-08-28).** Enum strategy = `RETAIN_FOR_COMPATIBILITY` (no destructive removal of `PROBABLE`/`LIKELY`/`UNLIKELY`). R1 production semantics: `PROBABLE = NOT_PRODUCED`, `LIKELY = NOT_PRODUCED`, `UNLIKELY = NOT_PRODUCED` — reserved states; retaining an enum member does not authorize the R1 compiler to produce it. The automatic mapping table (`monitor/lab → CONFIRMED`, `clinical_note → PROBABLE`) is adjudicated and rejected by owner 2026-08-28 — it is not an executable rule, and `CONFIRMED` MUST NOT be inferred merely from `source_kind`. Absent an approved deterministic certainty rule → `compiler_assigned_certainty = UNRESOLVED` (adjudicated fail-closed rule; no deterministic certainty rule is approved in R1).

#### Scenario: Fail-closed certainty assignment

- GIVEN a validated source fact with unambiguous telegraphic content (e.g. "TA 120/80")
- WHEN semantic normalization produces the canonical fact
- THEN its `compiler_assigned_certainty` is `UNRESOLVED` per the adjudicated fail-closed rule — deterministic, never invented (no deterministic certainty rule is approved in R1)

#### Scenario: Source-asserted certainty is stored as provenance, distinct from the compiler-assigned field

- GIVEN a source fact whose input declares a certainty (`source_asserted_certainty`)
- WHEN the fact is ingested and normalized
- THEN the declared certainty is stored verbatim as `source_asserted_certainty` (role = `clinical_source_assertion`; authority = `PRESERVED`), distinct from `compiler_assigned_certainty` (role = `processing_and_admissibility_state`; authority = `NON_CLINICAL`) — never conflated, never overwritten, never silently upgraded

#### Scenario: Adjudicated clinical_note semantics stay fail-closed

- GIVEN a `clinical_note` source fact (and likewise a `monitor`/`lab` source fact)
- WHEN semantic normalization produces the canonical fact
- THEN its `compiler_assigned_certainty` is `UNRESOLVED` — the adjudicated-and-rejected mapping produces no `PROBABLE` (and no `CONFIRMED` from `source_kind`)

#### Scenario: Reserved certainty states are NOT_PRODUCED in R1

- GIVEN any admissible input in R1
- WHEN semantic normalization produces canonical facts
- THEN `compiler_assigned_certainty` is never `PROBABLE`, `LIKELY`, or `UNLIKELY` (reserved states — `RETAIN_FOR_COMPATIBILITY` authorizes retention, not production)

### Requirement: Provenance Traceability

Every rendered value SHALL resolve through `DocumentIR → CanonicalClinicalFact → SourceFactIR` back to its original provenance; facts with missing or unresolvable provenance MUST be blocked with `PROVENANCE_ERROR`, never admitted.

#### Scenario: Full chain resolution

- GIVEN a successfully compiled document
- WHEN any rendered value is followed through the IR ladder
- THEN the chain resolves to a `SourceFactIR` carrying the original source provenance

#### Scenario: Missing provenance blocks

- GIVEN a fact whose provenance is absent or unresolvable
- WHEN the pipeline processes it
- THEN `PROVENANCE_ERROR` is emitted and the fact is not admitted to the document

### Requirement: CanonicalClinicalIR Explicit Aggregate

The admissible canonical fact set SHALL be represented as `CanonicalClinicalIR` — an explicit lightweight frozen dataclass holding `facts: tuple[CanonicalClinicalFact, ...]` (CRC-003, owner adjudication 2026-08-28; added additively to `core/ir.py` with recorded design justification per the additive-only core rule). Construction-time invariants (validated at construction; fail-closed): unique `clinical_fact_id`; lineage validation boundary; no document prose; no `document_mode`; deterministic representation (ordering). Constraint (normative): MINIMAL — no framework, no graph database, no generic provenance engine, no pass manager.

#### Scenario: Duplicate fact ids fail construction

- GIVEN canonical facts including two with the same `clinical_fact_id`
- WHEN a `CanonicalClinicalIR` is constructed from them
- THEN construction fails closed — no aggregate exists with duplicated `clinical_fact_id`

#### Scenario: Lineage validation boundary

- GIVEN a canonical fact whose lineage does not validate
- WHEN `CanonicalClinicalIR` construction is attempted
- THEN construction fails closed — the lineage-invalid fact is not carried by any constructed aggregate

#### Scenario: No document prose and no document mode

- GIVEN a constructed `CanonicalClinicalIR`
- WHEN its payload and type surface are inspected
- THEN it carries clinical facts only — no document prose and no `document_mode` (mode selection is a downstream concern)

#### Scenario: Deterministic representation

- GIVEN the same set of canonical facts constructed into `CanonicalClinicalIR` more than once
- WHEN the `facts` orderings are compared
- THEN they are identical — the aggregate's representation is deterministic (explicit ordering, stable across constructions)

### Requirement: Single Authority Per Fact

`DocumentIR` entries SHALL reference canonical fact identifiers only — never embedded values — so each clinical fact has exactly one authority.

#### Scenario: Document references identifiers

- GIVEN an assembled `DocumentIR`
- WHEN its entries are inspected
- THEN every entry references a canonical fact id and carries a presentation role, with no duplicated value authority
