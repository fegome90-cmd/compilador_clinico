# Input Contract Specification

## Purpose

How raw per-source clinical facts enter the compiler: the frozen input contract (decided by the owner at the Phase 0 gate — OPEN until then), driving adapter(s), and input validation producing `INPUT_CONTRACT_ERROR` and `TYPE_ERROR`.

## Requirements

### Requirement: Frozen Input Contract

The input contract SHALL be frozen per the recorded `INPUT_CONTRACT_DECISION` before adapter implementation begins; adapters and validation SHALL enforce exactly the frozen contract, and contract changes REQUIRE a new recorded owner decision.

#### Scenario: Freeze before build

- GIVEN `INPUT_CONTRACT_DECISION` stated by the decision owner in the owner-authored approval record
- WHEN Phase 1 begins
- THEN the frozen contract artifact is committed before any adapter code

#### Scenario: Contract violation

- GIVEN input that does not satisfy the frozen contract
- WHEN input validation runs
- THEN `INPUT_CONTRACT_ERROR` is emitted and nothing from the violating input is admitted downstream

### Requirement: Type Validation

Input whose structure satisfies the contract but whose value type is invalid for the target clinical field SHALL be rejected with `TYPE_ERROR`; after Phase 1, `TYPE_ERROR` SHALL have a producing stage and a covering test (no orphan code).

**Runtime value boundary (CRC-006 — owner adjudication 2026-08-28: `DEFER_CORE_TYPE_NARROWING_TO_R2` + `ENFORCE_BOUNDED_VALUES_AT_RUNTIME`).** Core type narrowing of `ClinicalValue.value` (`Any` in R1) is deferred to R2, recorded as `r2_debt` requiring a separately approved core migration. The deferral is annotation-level only — type annotation narrowing deferred ≠ boundary deferred: `SourceFactIR.raw_value` may remain broad/untrusted, but adapters/contract + Phases 1–2 MUST reject values outside the frozen field contract; an arbitrary Python object MUST NOT become an admissible canonical value merely because `ClinicalValue.value` is currently `Any`.

#### Scenario: Wrong value type

- GIVEN a contract-conformant record whose raw value type is invalid for its field
- WHEN input validation runs
- THEN `TYPE_ERROR` is emitted and the record is rejected

#### Scenario: Arbitrary object rejected at the runtime boundary

- GIVEN input carrying a value outside the frozen field contract's admissible types (an arbitrary Python object)
- WHEN the adapter/input-validation boundary processes it
- THEN the value is rejected per the frozen contract (`TYPE_ERROR` / `INPUT_CONTRACT_ERROR`) and never becomes an admissible canonical value

#### Scenario: Orphan eliminated after Phase 1

- GIVEN Phase 1 completed
- WHEN `TYPE_ERROR` is traced
- THEN it has a producing stage and at least one covering test

### Requirement: Driving Adapter

The compiler SHALL provide at least one driving input adapter converting accepted external input into `SourceFactIR` instances that preserve `fact_id`, `field_id`, the verbatim `raw_value`, and provenance. A source-declared certainty (`source_asserted_certainty`), when present in input, SHALL be captured verbatim — an optional field, never invented. Certainty authority model (CRC-002 — `BOTH_SEPARATED`, owner adjudication 2026-08-28): `source_asserted_certainty`: role = `clinical_source_assertion`; authority = `PRESERVED` (verbatim) — it MUST NOT be overwritten; `compiler_assigned_certainty`: role = `processing_and_admissibility_state`; authority = `NON_CLINICAL` — it MUST NOT silently upgrade the source assertion; `source_kind` alone MUST NOT establish clinical certainty; unresolved authority or interpretation fails closed. Provenance and certainty are different axes: a monitor/lab origin informs `PROVENANCE`, it does not by itself demonstrate clinical truth.

#### Scenario: Verbatim ingestion

- GIVEN valid input per the frozen contract (e.g. monitor facts "TA 120/80", "FC 72")
- WHEN it is fed through the driving adapter
- THEN each fact becomes a `SourceFactIR` with raw value and provenance preserved verbatim

#### Scenario: Source-declared certainty captured as provenance

- GIVEN valid input per the frozen contract whose record declares a certainty (`source_asserted_certainty`)
- WHEN it is fed through the driving adapter
- THEN the resulting `SourceFactIR` carries the declared certainty verbatim as `source_asserted_certainty` (role = `clinical_source_assertion`; authority = `PRESERVED`), distinct from `compiler_assigned_certainty` (role = `processing_and_admissibility_state`; authority = `NON_CLINICAL`) — never conflated, never overwritten, never silently upgraded

### Requirement: Conditional Free-Text Input

IF free-text telegraphic input is selected at the Phase 0 gate, THEN the contract SHALL bound it to a telegraphic micro-grammar with no NLP/ML, and any text outside the grammar SHALL yield `INPUT_CONTRACT_ERROR` rather than a guess; IF free-text is not selected, THEN free-text support is out of scope for this change (deferred).

#### Scenario: In-grammar note (conditional)

- GIVEN free-text selected at the gate and a note within the micro-grammar
- WHEN the adapter parses it
- THEN deterministic `SourceFactIR` facts are produced

#### Scenario: Out-of-grammar note (conditional)

- GIVEN free-text selected at the gate and an unparseable note
- WHEN the adapter parses it
- THEN `INPUT_CONTRACT_ERROR` is emitted and no facts are accepted from that note

#### Scenario: Free-text deferred

- GIVEN free-text not selected at the gate
- WHEN free text arrives at the adapter
- THEN it is rejected per the frozen contract with `INPUT_CONTRACT_ERROR`
