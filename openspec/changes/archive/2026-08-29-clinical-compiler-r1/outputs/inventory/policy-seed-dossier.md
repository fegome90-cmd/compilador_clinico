# Phase 0 — Policy-Seed Dossier (Task 0.6)

Change: `clinical-compiler-r1` | Subject: the candidate format for `NEVER_AUTO_TERMS` content.
**Structure only — this dossier contains NO clinical content authored by the executor.** Every
example value below is a syntactic placeholder, explicitly non-clinical.

## Mechanism the format feeds (frozen in design D7 + diagnostics-policy spec)

- `core/policy.py` `NEVER_AUTO_TERMS: frozenset[str] = frozenset()` stays the frozen EMPTY
  default; R1 writes NO seed content into core (verified this phase: the constant is empty and
  core is untouched — `baseline-anomalies.md` claims 6a/7).
- The veto set is injected at runtime: the runner loads it from `--policy-seed PATH`
  (CLI surface), and `admissibility` receives it as an explicit `frozenset[str]` parameter.
- Enforcement is identical under every resolution state: a vetoed term is never auto-confirmed
  even at `CONFIRMED` → `POLICY_VIOLATION` (FC-07; certainty-independent invariant).

## Candidate seed format (structure only)

```json
{"terms": ["<owner-authored-term-1>", "<owner-authored-term-2>"]}
```

Structural rules the Phase 2 loader (`adapters/seed.py`, tasks 2.4) will enforce — structure
ONLY, never content:

| Rule | Rationale (source) |
|---|---|
| File MUST parse as a single JSON object | structural validation only (design D7; diagnostics-policy spec) |
| The object MUST contain exactly the key `terms` | fixed candidate format; unknown keys are contract violations, mirroring FC-02 discipline |
| `terms` MUST be a JSON array of strings | the veto set is `frozenset[str]` |
| Entries MUST be unique (duplicates collapse or are rejected — decided at Phase 2 implementation against the frozen contract, not here) | set semantics of `NEVER_AUTO_TERMS` |
| Entries MUST be non-empty strings | an empty string matches nothing and signals a malformed seed |
| ANY structural failure → the seed is invalid; it NEVER falls back to a silent empty set | Policy Resolution State Machine: there is NO execution path where a missing/unreadable seed silently yields an empty set and continues |

Structurally-invalid examples (shape only, no clinical content): `{"term": ["x"]}` (wrong key),
`{"terms": "x"}` (wrong type), `{"terms": [1]}` (non-string entry), `[]` (not an object),
undecodable bytes.

## Policy Resolution State Machine (frozen — design D7 / diagnostics-policy spec)

```text
UNRESOLVED_POLICY
  ├─ owner APPROVED seed      → populated policy (exactly the approved entries, nothing else)
  └─ owner DEFERRED_BY_OWNER  → approved empty policy (APPROVED-BY-DEFERRAL)
```

With NEITHER durable owner decision present, the state is `UNRESOLVED_POLICY` and the gate is
BLOCKED — never empty-set-and-continue. The empty set is only ever an APPROVED-BY-DEFERRAL state.

## Evidence relevant to the gate choice (facts, no decision)

- Corpus parameterization (design Fault Corpus): FC-07 (vetoed term at test-constructed
  `CONFIRMED` → `POLICY_VIOLATION`) and FC-12 (empty-seed branch + ordinary facts → clean
  compile) are parameterized on the seed: under `DEFERRED_BY_OWNER`, FC-07 runs with a
  test-local injected seed (the injection mechanism itself under test); FC-12 asserts the
  production path.
- Exact seed fidelity (diagnostics-policy spec): with an approved seed, `NEVER_AUTO_TERMS`
  contains exactly the approved entries and nothing else.
- Executor boundary (diagnostics-policy spec, Policy Content Governance): the executor MUST NOT
  author `NEVER_AUTO_TERMS` entries; the set is populated exclusively from a
  decision-owner-approved seed or ships empty under an explicit recorded owner decision. A
  search of all executor-produced artifacts for executor-authored clinical policy content must
  return zero (Phase 2 gate).
- Veto-invariant testing either way (tasks 2.7): the tautological baseline policy test is
  replaced with mutation-sensitive tests — any mutation of veto membership OR enforcement causes
  ≥1 failure — independent of which resolution state is chosen at this gate.

## The two resolution states the owner may record (effects stated symmetrically; no selection)

| State | Meaning | Effects if recorded at this gate |
|---|---|---|
| `APPROVED` (with seed file) | The owner authors the seed file in the format above and approves it by name/record | Phase 2 loads it verbatim (task 2.5); effective veto set = exactly the approved entries; FC-07 runs against the approved set; `POLICY_VIOLATION` becomes reachable in production for those terms |
| `DEFERRED_BY_OWNER` | The owner records the explicit decision to ship R1 with the empty set | Effective veto set = empty (an APPROVED-BY-DEFERRAL state, never silent); FC-07 exercised via test-local injected seed; FC-12 asserts the production clean path; a populated core constant remains a later owner-approved change |

The formal choice between these states is recorded by the decision owner in the owner-authored
approval record (see `decision-gate.md`, Decision 2) — not by this dossier.
