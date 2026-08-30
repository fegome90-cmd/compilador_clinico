# Diagnostics Policy Specification

## Purpose

Fail-closed diagnostics discipline and human ownership of clinical policy: every fault class maps to a `DiagnosticCode`, no unsafe fact is silently accepted, the 8-code taxonomy is fully covered, and `NEVER_AUTO_TERMS` content belongs exclusively to the decision owner.

## Requirements

### Requirement: Fail-Closed Fault Corpus

For every case in the fault corpus (ambiguous terms, vetoed terms, missing provenance, contract violations; corpus frozen in `design.md`, never authored by the implementer), the compiler SHALL yield its mapped `DiagnosticCode`; the count of silently-accepted unsafe facts MUST be `0`.

#### Scenario: Zero silent acceptance

- GIVEN the frozen fault corpus
- WHEN every case is compiled
- THEN each case yields its mapped `DiagnosticCode` and the silently-accepted count is `0`

### Requirement: Taxonomy Coverage

After the change, every `DiagnosticCode` member SHALL have a producing stage and a covering test; the count of codes with neither MUST be `0`.

#### Scenario: No orphan codes

- GIVEN the final gate
- WHEN the 8 `DiagnosticCode` members are audited for producing stage and covering test
- THEN the orphan count is `0` (baseline orphans `TYPE_ERROR` and `PROVENANCE_ERROR` eliminated)

### Requirement: Policy Content Governance

The executor MUST NOT author `NEVER_AUTO_TERMS` entries; the set SHALL be populated exclusively from a decision-owner-approved seed, or ship empty under an explicit recorded owner decision.

#### Scenario: Executor proposes no clinical content

- GIVEN all executor-produced artifacts of this change
- WHEN executor-authored clinical policy content is searched for
- THEN none exists anywhere

#### Scenario: Exact seed fidelity

- GIVEN an approved seed when Phase 2 implements enforcement
- WHEN `NEVER_AUTO_TERMS` is inspected
- THEN it contains exactly the approved entries and nothing else

### Requirement: Policy Resolution State Machine

Policy resolution SHALL follow the frozen state machine:

```text
UNRESOLVED_POLICY
  ├─ owner APPROVED seed  → populated policy
  └─ owner DEFERRED_BY_OWNER → approved empty policy
```

There MUST BE NO execution path where a missing/unreadable seed file silently yields an empty set and continues: with neither durable owner decision present, the policy-resolution state is `UNRESOLVED_POLICY` and the gate is BLOCKED. The empty set is only ever an APPROVED-BY-DEFERRAL state (a recorded owner decision `DEFERRED_BY_OWNER`).

#### Scenario: UNRESOLVED_POLICY blocks — never empty-set-and-continue

- GIVEN a missing or unreadable policy seed and no durable owner decision (neither `APPROVED` seed nor `DEFERRED_BY_OWNER`)
- WHEN policy resolution is evaluated
- THEN the state is `UNRESOLVED_POLICY`, the gate is BLOCKED, and execution never silently continues with an empty veto set

### Requirement: Mutation-Sensitive Policy Tests

The baseline tautological policy test SHALL be replaced with content-bearing, mutation-sensitive tests: any mutation of `NEVER_AUTO_TERMS` membership or veto enforcement MUST cause at least one test failure.

#### Scenario: Mutation detected

- GIVEN the final test suite
- WHEN the veto enforcement logic or policy membership is mutated
- THEN at least one test fails
