# Design: clinical-compiler R1 — Working, Contract-Governed Clinical Record Compiler

## Document Authority

| Field | Value |
|-------|-------|
| Status | DRAFT — not normative. Becomes `normative_for_phase0` only via a durable SHA-256-bound approval record (e.g. `APPROVAL-PHASE0.md` in this change directory) that binds the exact SHA-256 of every bundle file — `proposal.md`, `design.md`, `tasks.md`, and the seven domain specs — at approval time (ten individual per-file digests or a single bundle-manifest SHA-256 over their ordered concatenation), explicitly names the approved phase(s), records Felipe Gonzalez as the approving decision owner, references a validation receipt (contract-conformance audit plus post-repair consistency check) performed on the exact bound hashes, and is authored or verified by a reviewer distinct from the executor. No artifact in this bundle becomes normative-for-execution without that phase-explicit, hash-bound record; later phases activate only through an updated record naming them, never by implication. |
| Role | Normative technical design; derives from `proposal.md`; satisfies all seven domain specs |
| Derived artifacts | `tasks.md` (execution plan — MUST NOT redefine this document) |
| Baseline | Commit `c6578b6`; core (`types.py`, `ir.py`, `diagnostics.py`, `policy.py`) frozen green, NOT re-proposed |

## Governance (execution-contract routing)

This bundle executes under the **AI Work Agent Execution Contract, id `ai-work-agent-execution-contract-0.3`, version 0.3**. Provenance caveat: the copy governing this work is the repository mirror at `openspec/contracts/clinical-compiler-handoff-drive-mirror-20260828/ai-work-agent-execution-contract-0.3.md`; the mirror is non-canonical and the contract's own audit state is `baseline_result: pending-deep-baseline` — it is used as governing context for this change only and cannot support corpus-wide stability claims about the contract itself.

Router decision record (contract §2.1, emitted at bundle authoring time):

```yaml
router_decision:
  router_version: "0.3"
  task_class: governed
  execution_required: true
  persistent_mutation: true
  authority_sensitive: true
  human_decision_possible: true
  multiple_artifacts: true
  runtime_discovery_required: true
  external_interfaces: true          # the CLI surface and input contract are external interfaces being defined
  benchmark_or_comparison: false
  rollback_required: true
  delegation_required: false         # single executor; no consequential sub-delegation
  antidrift_risk: material
  selected_profile: GOVERNED
  modules_to_load: [M0, M1, M2, M3, M4, M5, M6]
  reason: authority boundary + protected state + human approval envelope + candidate freeze + rollback
```

`selected_profile: GOVERNED` per contract §2.3 triggers, each present in this change: (a) authority or ownership boundary — decision owner vs reviewer vs executor separation; (b) protected state — the frozen core and the hash-bound bundle; (c) human approval or decision envelope — the Phase 0 decision gate and the activation record; (d) candidate identity/freeze required — hash-bound activation over all bundle files; (e) lifecycle/staging/promotion/rollback required — phase gates, activation lifecycle, rollback. No §2.3 FULL_ANTIDRIFT trigger is present (no benchmark/comparison, no adversarial audit, no cross-session continuation). Where this bundle adopts a named practice defined in a non-loaded module — M7.1 evidence-integrity marking of golden evidence (Determinism Mechanism) and the M10.3-shaped final receipt (tasks.md) — it is adopted by explicit reference as bundle discipline; if any FULL_ANTIDRIFT trigger materializes, the router MUST be re-evaluated before continuation.

Module → bundle-section manifest (how each loaded module is satisfied):

| Module | Satisfied by |
|--------|--------------|
| M0 Core | proposal Change Metadata (GOAL/DONE WHEN, audience, not_role), Scope Boundaries, Side-Effect Budget; tasks Authority & Conventions |
| M1 Controlled execution | tasks 0.1–0.4 (pre-flight/runtime discovery, no-install discipline); phase ordering per M1.3 |
| M2 Interfaces & artifacts | design §Interfaces and §CLI Surface (M2.1 interface contracts); §Artifact Contracts (M2.2) |
| M3 Failure/recovery/validation/observability | Gate Checklist (pre-declared computable PASS, M3.2); fault corpus + fail-closed (M3.3); run IDs + per-capture timestamps in evidence (M3.4) |
| M4 Authority/ownership/subject identity | proposal §Approval & Activation; hash-bound activation over all bundle files (candidate freeze, M4.2) |
| M5 Human control & governed state | Phase 0 decision envelopes (M5.1); activation lifecycle + single-executor crash/restart policy (M5.2) |
| M6 Promotion/rollback/claims | approval record incl. validation receipt (M6.1); §Migration / Rollback (M6.2); coverage-vs-baseline rationale (M6.3); computed gates + bounded claims (M6.4) |

Routing rules (adopted from the contract): escalation is one-way — `BASIC → CONTROLLED → GOVERNED → FULL_ANTIDRIFT` (§2.4) — and once a material trigger activates a module there is no silent downgrade within the transaction. The router is re-evaluated on any §2.5 trigger: scope expands; new files/artifacts change blast radius; persistent mutation appears; authority becomes ambiguous; a secret becomes necessary; protected state is encountered; a human decision becomes material; the candidate/subject changes; a new actor is introduced; evidence integrity becomes relevant; a benchmark/comparison begins; an unexpected failure changes strategy; rollback becomes necessary; context/duration crosses the profile's safe envelope; existing evidence becomes insufficient. Fail-closed default (§2.6): when two profiles are plausible, the higher one is chosen if the uncertainty can affect authority, persistent state, safety, reproducibility, evidence, human control, or rollback — and tasks are never inflated merely because they are technically interesting.

Execution topology & crash recovery (M5.2). Exactly ONE executor (the SDD apply agent) is active per phase; the activation model authorizes a single executor per approval record, so no inter-process or cross-agent locking is required — the absence of locking is a reasoned decision under the single-executor assumption, not an omission. Concurrent executors are out of scope and MUST NOT be started; if a second actor appears (§2.5 re-evaluation: new actor), the executor stops and re-routes through the owner. Crash/restart policy: every phase gate is computable from repository state alone (never asserted), so recovery is idempotent — a restarted executor re-computes the current phase's gate from the working tree, re-verifies the side-effect budget snapshots, and resumes; partially written phase output is re-derived or overwritten by idempotent re-execution, and documents are written atomically (temp + `os.replace`) so no partial artifact persists; the durable approval record is the restart anchor; no execution state lives outside the repository, so there is nothing else to recover.

## Technical Approach

Functional core, imperative shell, on the existing IR ladder. The four passes, linter, and renderer are **pure functions**: each consumes a tuple of surviving facts and returns a `StageResult` (survivors + diagnostics). All I/O lives at the edges — `adapters/` (driving: bytes → records → `SourceFactIR`), `renderers/` + `linter/` (driven: `DocumentIR` → bytes → verdict), `cli.py` (shell). `pipeline.py` composes stages in fixed taxonomy order and owns the fail-closed emission gate. Hexagonal framing is TARGET state: today the scaffold is zero-byte; this design fills it into that shape. Zero runtime dependencies — stdlib only (`argparse`, `json`, `hashlib`, `pathlib`).

The pipeline runs **every stage on the survivors of the previous stage** (per-fact quarantine, full diagnostic enumeration), then **gates document emission on the accumulated diagnostic set being empty** (fail-closed whole-run). One invalid fact blocks the document — by design (Decision 1).

## Architecture Decisions

| # | Decision | Choice | Alternatives | Rationale |
|---|----------|--------|--------------|-----------|
| 1 | Blocking granularity | Per-fact quarantine + **whole-run fail-closed**: every stage processes survivors, quarantines blocked facts (never consumed downstream), accumulates diagnostics; a document is emitted IFF the accumulator is empty; otherwise all diagnostics are enumerated, no document. All 8 codes are blocking in R1 (no warning severity). | (a) emit document despite blocked facts; (b) per-document success; (c) fail-fast halt at first faulty stage. | (a)/(b) emit a document silently omitting blocked facts — violates "No silent omission" and the corpus gate. (c) hides fixable faults; the spec blocks the FACT, not the stage, and requires ALL diagnostics enumerated. |
| 2 | Fault corpus | Frozen below — 12 fault classes + 2 positive controls, each mapped to its code, branch-safe across both input-contract options. | Implementer-authored corpus. | diagnostics-policy: corpus frozen in `design.md`, never authored by the implementer — otherwise the implementation writes its own exam. |
| 3 | Exit-code mapping | Frozen below: 0 success; 2 usage; 3–10 one per diagnostic category; 70 internal. Precedence = minimum code present in stage order (documented order, not enum order). | Single generic 1; HTTP-style ranges. | cli-surface demands a deterministic documented mapping; per-category codes are greppable; a fixed total order makes identical failing input → identical code. |
| 4 | CLI name/surface | `[project.scripts]` → **`clinical-compiler = "clinical_compiler.cli:main"`**; one subcommand `compile INPUT [--mode MODE] [--policy-seed PATH] [--output PATH]`. | `crc`; `clincomp`; `check`/`lint` verbs. | Explicit clinical name, kebab-case matching PyPI `clinical-record-compiler`. R1 has exactly one verb; extra verbs would fake scope the specs do not grant. |
| 5 | Module map / dependency direction | Frozen below. Rule: `cli → pipeline → {passes, linter, renderers} → {adapters(contract), pipeline_types} → core{ir, diagnostics, policy} → types`; `StageResult` lives in the leaf module `pipeline_types.py` (re-exported by `pipeline.py`) so passes never import `pipeline`; nothing imports `cli`/`pipeline` except `__main__`; `core` stays a stdlib-only leaf. | Flat layout; passes importing adapters; StageResult declared inside `pipeline.py`. | Anchors on the existing `ir → types` direction; keeps the frozen core leaf-pure; the contract table has one consumer point (composition root). Declaring `StageResult` in `pipeline.py` would force passes to violate this very rule — adjudicated G-1, see §Interfaces. |
| 6 | Determinism mechanism | Frozen below: tuple containers, explicit codepoint sort keys, locale-free formatting, UTF-8/`\n`-only output, canonical JSON, golden SHA-256 digest, cross-run test under randomized `PYTHONHASHSEED`. | Rely on dict insertion order; `repr()` output. | CPython string hashing is per-process randomized — hash-order dependence is latent nondeterminism the gate must catch; spec bans unordered iteration, locale, time, randomness. |
| 7 | Policy seed injection (branch mechanism) | `admissibility` takes the veto set as an explicit `frozenset[str]` parameter; the runner loads it from `--policy-seed PATH` (owner-authored JSON `{"terms": [...]}`), with an absent/missing seed resolved per the Policy Resolution State Machine (§ below) — never a silent empty set. `core/policy.NEVER_AUTO_TERMS` stays the frozen empty default — R1 writes NO seed content into core. | Mutating the core constant at import time; shipping a seeded core. | Executor authors no clinical content; a runtime-injected file-backed set keeps every entry owner-attributable and the core diff empty. "Exact seed fidelity" applies to the effective veto set: exactly the approved entries, nothing else. A permanently seeded core constant is a later owner-approved change. |
| 8 | Input contract location | `adapters/contract.py` — one declarative frozen table (required keys, per-`field_id` raw-value type predicates, provenance requirements) consumed by BOTH the adapter (structural parse) and `input_validation` (field enforcement). | Duplicating contract logic in adapter and pass; external config file. | input-contract: "adapters and validation SHALL enforce exactly the frozen contract" — one table makes "exactly" testable and the Phase 0 freeze a single committed artifact. |
| 9 | Core type narrowing vs runtime bounded values (CRC-006) | `DEFER_CORE_TYPE_NARROWING_TO_R2` + `ENFORCE_BOUNDED_VALUES_AT_RUNTIME` (owner adjudication 2026-08-28): `ClinicalValue.value: Any` stays in R1, recorded as `r2_debt` requiring a separately approved core migration. The runtime semantic boundary is enforced NOW: `SourceFactIR.raw_value` may remain broad/untrusted, but adapters/contract + Phases 1–2 MUST reject values outside the frozen field contract, and an arbitrary Python object MUST NOT become an admissible canonical value merely because `ClinicalValue.value` is currently `Any`. | (a) narrow the core annotation in R1; (b) defer both the annotation and the boundary to R2. | (a) is a core migration inside a change whose core is frozen additive-only — it requires separate approval; (b) defers the wrong thing: type annotation narrowing deferred ≠ boundary deferred — the admissibility boundary is a runtime semantic, not a type annotation. |
| 10 | Canonical fact-set representation (CRC-003) | `CanonicalClinicalIR` — an explicit lightweight frozen dataclass holding `facts: tuple[CanonicalClinicalFact, ...]`, added additively to `core/ir.py` (owner adjudication 2026-08-28; see §Module Map for the placement rationale). | Implicit bare tuple between stages; a generic graph/provenance framework. | CRC-003 adjudicated the explicit aggregate; constraint is MINIMAL — no framework, no graph database, no generic provenance engine, no pass manager; `core/ir.py` is the home of the IR types and the additive-only core rule authorizes the addition with recorded justification. |

### Policy Resolution State Machine (D7 — normative, CRC-005)

```text
UNRESOLVED_POLICY
  ├─ owner APPROVED seed  → populated policy
  └─ owner DEFERRED_BY_OWNER → approved empty policy
```

There MUST BE NO execution path where a missing/unreadable seed file silently yields an empty set and continues: with neither durable owner decision present, the policy-resolution state is `UNRESOLVED_POLICY` and the gate is BLOCKED. The empty set is only ever an APPROVED-BY-DEFERRAL state (a recorded owner decision `DEFERRED_BY_OWNER`).

## Fault Corpus (frozen — diagnostics-policy gate material)

Positive controls MUST compile clean; fault classes MUST yield exactly their mapped code; silently-accepted count `0`.

| ID | Class (contract-level, branch-safe) | Structured-branch instance | Free-text instance (if selected) | Code |
|----|-------------------------------------|---------------------------|----------------------------------|------|
| PC-1 | Unassessed field renders explicit `unknown` | no fact for `FC` → renders `FC: unknown [not_assessed]` | note omitting FC | — (output assertion) |
| PC-2 | Assessed absence traces to a source assertion | fact asserting `missing` for `TA` → absence WITH provenance | "TA: sin dato" per grammar | — (chain assertion) |
| FC-01 | Missing required contract key | fact record lacking `field_id` | token stream missing field token | `INPUT_CONTRACT_ERROR` |
| FC-02 | Unknown key outside the contract | extra key `x_priority` | unsupported annotation | `INPUT_CONTRACT_ERROR` |
| FC-03 | Structurally malformed input | top-level JSON array; undecodable bytes | non-grammatical prose | `INPUT_CONTRACT_ERROR` |
| FC-04 | Free-text outside micro-grammar | n/a — structured branch rejects any free text | "paciente estable, creo que mejoró algo" | `INPUT_CONTRACT_ERROR` |
| FC-05 | Conformant record, wrong value type | `raw_value: true` (bool) for numeric field `FC` | well-formed token, non-numeric value | `TYPE_ERROR` |
| FC-06 | >1 admissible interpretation, no disambiguator | conflicting same-`field_id` facts, equal authority | token with two grammar parses | `SEMANTIC_AMBIGUITY_BLOCK` |
| FC-07 | Vetoed term regardless of certainty (tested at `CONFIRMED`) | value matches an approved seed term; canonical fact constructed with certainty `CONFIRMED` (test-constructed — R1's normalizer assigns no `CONFIRMED`; the veto invariant is certainty-independent) | idem | `POLICY_VIOLATION` |
| FC-08 | Provenance absent or unresolvable | `source_fact_refs` pointing at no surviving `SourceFactIR` | idem | `PROVENANCE_ERROR` |
| FC-09 | No admissible entries for the requested mode | all facts blocked upstream; selection requested | idem | `DOCUMENT_SELECTION_ERROR` |
| FC-10 | Rendering fault (internal inconsistency safety net) | `DocumentIR` entry referencing an absent canonical id (injected fixture) | idem | `RENDER_ERROR` |
| FC-11 | Rendered output violates a mode conformance rule | entry with a presentation role outside the mode's allowed set (injected fixture) | idem | `LINT_FAILURE` |
| FC-12 | Empty-seed branch passes through | owner-recorded deferral + ordinary facts → zero `POLICY_VIOLATION` | idem | — (clean compile) |

FC-07/FC-12 are parameterized on the seed: under DEFERRED, FC-07 runs with a test-local injected seed (the injection mechanism itself is under test); FC-12 asserts the production path.

## Exit-Code Table (frozen — cli-surface gate material)

| Code | Class | Trigger (computed from accumulated diagnostics / invocation) |
|------|-------|--------------------------------------------------------------|
| 0 | Success | Document emitted AND diagnostics empty |
| 2 | Usage error | argparse failure; missing/unreadable `INPUT`; unknown `--mode`; invalid `--policy-seed`. No compile attempted. (Matches argparse's own exit 2.) |
| 3 | Input contract violation | ≥1 `INPUT_CONTRACT_ERROR` |
| 4 | Type violation | ≥1 `TYPE_ERROR` |
| 5 | Semantic ambiguity | ≥1 `SEMANTIC_AMBIGUITY_BLOCK` |
| 6 | Policy violation | ≥1 `POLICY_VIOLATION` |
| 7 | Provenance failure | ≥1 `PROVENANCE_ERROR` |
| 8 | Document selection failure | ≥1 `DOCUMENT_SELECTION_ERROR` |
| 9 | Render failure | ≥1 `RENDER_ERROR` |
| 10 | Conformance lint failure | ≥1 `LINT_FAILURE` |
| 70 | Internal error | Unexpected exception — fail-closed catch-all; best-effort diagnostics on stderr; NEVER 0 |

Precedence (deterministic): exit code = **minimum code among 3–10 present**, in the stage order above. This is NOT `DiagnosticCode` declaration order — `PROVENANCE_ERROR` (declared last, emitted at admissibility) ranks at 7 because the earliest-stage fault explains the rest. The mapping is a pure function of the diagnostic SET, order-independent.

## CLI Surface (frozen recommendation — owner-reviewed at bundle approval)

```text
clinical-compiler compile INPUT [--mode MODE] [--policy-seed PATH] [--output PATH]

INPUT          path to input artifact satisfying the frozen contract ('-' / stdin: deferred to R2)
--mode         document mode; default and only R1 mode: NURSING_RECORD_TELEGRAPHIC
--policy-seed  path to owner-authored seed JSON {"terms": [...]}; an absent seed resolves per the
                Policy Resolution State Machine (D7): empty veto set ONLY under a recorded
                DEFERRED_BY_OWNER — otherwise UNRESOLVED_POLICY blocks (never empty-set-and-continue)
--output       document destination; default stdout; a path is written atomically (temp + os.replace)
```

Invariants: diagnostics always to **stderr**, one per line, stable format `CODE: message (path)`; the document stream carries bytes ONLY at exit 0 — a failed run writes nothing to it (no partial document). `--json` diagnostics, `check`-only mode, stdin: deferred.

Interface contract properties (M2.1) — `clinical-compiler compile`:

```text
Timeout/limits: synchronous single-process run; no wall-clock timeout is imposed or needed in
  R1 — every stage is a pure, in-memory, terminating computation; there is no network wait,
  daemon, or retry loop. Input is read whole (bounded by file size and available memory); R1
  sets no artificial input-size cap (a cap would be a contract change requiring a new owner
  decision). Diagnostic enumeration is bounded by the input fact count.
Security properties: no network access; no subprocess/shell invocation, no eval/exec anywhere
  in library code; no secrets read, logged, or echoed. Input bytes are UNTRUSTED_CONTENT —
  parsed strictly against the frozen contract, never executed; the seed file is structurally
  validated only; --output is written atomically (temp + os.replace) so no partial document is
  ever visible; the exit-70 catch-all guarantees untrusted input can never exit 0 or crash
  silently.
Failure behavior: mapped to the frozen exit-code table (0 / 2 / 3–10 / 70); no partial output
  on any non-zero exit; diagnostics one per line on stderr.
```

## Module Map (target layout; dependency rule)

```text
src/clinical_compiler/
├── core/                        FROZEN leaf — imports nothing outside stdlib
│   ├── types.py                 Certainty | Missingness | Provenance | ClinicalValue
│   ├── ir.py                    SourceFactIR → CanonicalClinicalFact → DocumentIR  (ir → types)
│   │                            + CanonicalClinicalIR (D10 — adjudicated ADDITIVE aggregate, CRC-003;
│   │                            explicit lightweight frozen dataclass, facts: tuple[CanonicalClinicalFact, ...])
│   ├── diagnostics.py           DiagnosticCode (8) | Diagnostic
│   └── policy.py                NEVER_AUTO_TERMS (empty default; runtime injection — D7)
├── adapters/                    driving side; only pipeline/cli import it
│   ├── contract.py              declarative frozen input-contract table (single source of truth)
│   ├── structured_feed.py       bytes → candidate records → SourceFactIR (branch A)
│   ├── free_text.py             telegraphic micro-grammar parser (branch B — built ONLY if the
│   │                            Phase 0 gate selects free-text; else not created, recorded)
│   └── seed.py                  --policy-seed loader + structural validation (never content)
├── passes/                      pure transformations
│   ├── input_validation.py      contract + type enforcement → INPUT_CONTRACT_ERROR | TYPE_ERROR
│   ├── semantic_normalization.py deterministic interpretation → SEMANTIC_AMBIGUITY_BLOCK
│   ├── admissibility.py         veto + provenance resolution → POLICY_VIOLATION | PROVENANCE_ERROR
│   └── document_selection.py    DocumentIR assembly → DOCUMENT_SELECTION_ERROR
├── renderers/deterministic.py   DocumentIR → bytes → RENDER_ERROR
├── linter/conformance.py        bytes vs mode rules → LINT_FAILURE
├── pipeline_types.py             NEW — leaf stage-contract module: StageResult[_T] (pure; no I/O).
│                                 Passes import THIS leaf, never pipeline; pipeline.py re-exports
│                                 it — adjudicated G-1 (see §Interfaces)
├── pipeline.py                  NEW — composition root: stage order, accumulator, emission gate,
│                                CompileResult, exit-code derivation; re-exports StageResult
└── cli.py                       NEW — argparse shell: file IO, seed loading, exit code
```

Dependency rule: `cli → pipeline → {passes, renderers, linter} → {adapters(contract), pipeline_types} → core{ir, diagnostics, policy} → types`. `core` imports nothing from the new packages — R1's ONLY core change is the adjudicated additive `CanonicalClinicalIR` in `core/ir.py` (CRC-003, owner adjudication 2026-08-28; recorded design justification per the proposal's additive-only core rule); every other core module is untouched. **Placement rationale (D10):** `core/ir.py` is the declared home of the IR-ladder types, the addition is stdlib-only (D5's frozen-leaf rule holds) and additive with recorded justification, and every consumer (the passes) already imports `core.ir` — no new dependency edge. The admissible canonical fact set crosses the admissibility → document-selection boundary as an explicit `CanonicalClinicalIR` (constructed with the invariants below), never as an implicit bare tuple. Each `__init__.py` gains a one-line docstring so the scaffold gate's zero-byte count is 0. The zero-byte placeholder `adapters/README.md` is REMOVED (recorded decision: replaced by real modules).

## Sequence Diagram — compile pipeline with blocking granularity

```mermaid
sequenceDiagram
    participant U as User/shell
    participant C as cli.main
    participant R as pipeline.run
    participant A as adapters(contract)
    participant IV as input_validation
    participant SN as semantic_normalization
    participant AD as admissibility
    participant DS as document_selection
    participant RE as renderers.deterministic
    participant LI as linter.conformance

    U->>C: compile INPUT [--mode --policy-seed --output]
    C->>C: argparse; open INPUT; load seed (or empty) [usage errors → exit 2]
    C->>R: CompileRequest(bytes, mode, veto_set)
    R->>A: parse bytes against contract table
    alt undecodable / malformed
        A-->>R: INPUT_CONTRACT_ERROR (records quarantined)
    end
    A-->>R: candidate records
    R->>IV: enforce frozen contract + field types (per-fact: admit or quarantine)
    IV-->>R: SourceFactIR set + {INPUT_CONTRACT_ERROR, TYPE_ERROR}
    R->>SN: normalize survivors (deterministic certainty/missingness table)
    Note over SN: conflicting same-field facts, equal authority,<br/>no disambiguator → SEMANTIC_AMBIGUITY_BLOCK<br/>(R1 has NO conflict resolution — never picks)
    SN-->>R: CanonicalClinicalFact set + {SEMANTIC_AMBIGUITY_BLOCK}
    R->>AD: veto check (injected seed) + provenance resolution
    Note over AD: vetoed term NEVER auto-confirmed — even<br/>certainty=confirmed → POLICY_VIOLATION;<br/>unresolvable source_fact_refs → PROVENANCE_ERROR
    AD-->>R: admitted facts + {POLICY_VIOLATION, PROVENANCE_ERROR}
    R->>DS: assemble DocumentIR for mode (fact ids + presentation roles only)
    DS-->>R: DocumentIR + {DOCUMENT_SELECTION_ERROR}
    R->>R: emission gate: accumulated diagnostics empty?
    alt ANY diagnostic present (fail-closed whole run)
        R-->>C: CompileResult(document=None, diagnostics)
        C-->>U: enumerate diagnostics on stderr; nothing to document stream; exit 3–10 (min present)
    else diagnostics empty
        R->>RE: render DocumentIR → bytes (sorted, canonical)
        RE-->>R: bytes + {RENDER_ERROR}
        R->>LI: lint bytes against mode rules
        LI-->>R: verdict + {LINT_FAILURE}
        alt RENDER_ERROR or LINT_FAILURE
            R-->>C: CompileResult(document=None, diagnostics)
            C-->>U: diagnostics on stderr; exit 9/10
        else lint-clean
            R-->>C: CompileResult(document=bytes, ())
            C-->>U: document to stdout/--output (atomic); exit 0
        end
    end
```

Every stage runs on survivors only; quarantine is per-fact; diagnostics accumulate; the gate is whole-run. Rendering/linting are reached ONLY on a fully clean run — `RENDER_ERROR`/`LINT_FAILURE` are defense-in-depth over internal inconsistency, exercised via injected fixtures (FC-10/FC-11).

**Dangling-ref adjudication (CRC-004 — `ACCEPTED_AS_FUNCTIONALLY_ABSORBED`, owner adjudication 2026-08-28).**

```text
P4/document_selection: dangling canonical references impossible by construction
Renderer: injected inconsistent DocumentIR → RENDER_ERROR (defense-in-depth)
```

Rationale: P4 constructs references only from surviving admissible canonical facts; `RENDER_ERROR` does not redefine P4 ownership, and the same defect is NOT also classified as `DOCUMENT_SELECTION_ERROR`. The case is reachable only via internal corruption or injection, exercised via injected fixture (FC-10).

## Determinism Mechanism (frozen)

1. **Immutable, ordered containers.** Stage I/O is frozen dataclasses with `tuple` fields. Ordering uses explicit sort keys: document entries sorted by `(field_id, clinical_fact_id)` in Unicode **codepoint order** — never locale collation, never dict/set iteration order.
2. **No environment leakage.** No `datetime.now`, `time`, `random`, `locale`, env vars, or host names in any output path; the document embeds no timestamps.
3. **Canonical formatting.** UTF-8, `\n` line endings only, no trailing whitespace, numbers via `str(int)` or explicit fixed-decimal (never locale `format()`). Any JSON: `json.dumps(..., sort_keys=True, ensure_ascii=True, separators=(",", ":"))`.
4. **Hash-order independence.** No code path depends on `hash()` ordering or unsorted set/dict iteration reaching output; verified by the cross-run gate.
5. **Golden digests.** `tests/golden/` commits the golden document AND its SHA-256 digest. The determinism test compiles the fixture set twice via `subprocess` in fresh interpreters (`python -I`, `PYTHONHASHSEED=0` vs `random`), asserting digest equality across runs AND against the committed digest.

6. **Evidence integrity of goldens (M7.1 vocabulary).** Golden evidence carries an `EVIDENCE_INTEGRITY = VALID | DEGRADED | INVALID` status. Implementation-generated goldens alone are `DEGRADED` — the implementation would be writing its own exam. Therefore at least one expected sample (expected document bytes + digest for one fixture set) MUST be authored independently of the implementation — by the decision owner or an owner-designated audit path — and committed under `tests/golden/independent/`; the executor requests it at the Phase 3 gate and never authors it. Absence of the independent sample → the golden evidence is `DEGRADED` and the Phase 3 determinism gate BLOCKS pending owner input. The Final Receipt records the golden `EVIDENCE_INTEGRITY` status.

## Deterministic Interpretation Table (semantic_normalization)

| Source condition | Certainty | Missingness |
|------------------|-----------|-------------|
| `source_kind ∈ {monitor, lab}` (device-asserted), value present | `UNRESOLVED` — no deterministic certainty rule is approved in R1; `source_kind` informs `PROVENANCE` only (CRC-002) | `PRESENT` |
| `source_kind = clinical_note` (human-asserted) | `UNRESOLVED` | `PRESENT` |
| Source explicitly asserts absence (contract marker / `"sin dato"` per grammar) | `UNRESOLVED` | `MISSING` (assessed absence — provenance mandatory) |
| Source explicitly marks non-applicability | `UNRESOLVED` | `NOT_APPLICABLE` |
| No fact exists for the field | — (no canonical fact) | `NOT_ASSESSED` at document level → renders explicit `unknown` |
| Conflicting same-`field_id` facts, equal authority, no disambiguator | — | — → `SEMANTIC_AMBIGUITY_BLOCK` (no canonical fact) |

**Certainty assignment (CRC-001 — adjudicated, owner adjudication 2026-08-28).** The automatic mapping table (`monitor/lab → CONFIRMED`, `clinical_note → PROBABLE`) is adjudicated and rejected by owner 2026-08-28 as automatic semantics — it is NOT an executable rule in R1, and `CONFIRMED` MUST NOT be inferred merely from `source_kind`. Enum strategy = `RETAIN_FOR_COMPATIBILITY` (no destructive removal of `PROBABLE`/`LIKELY`/`UNLIKELY`). R1 production semantics: `PROBABLE = NOT_PRODUCED`, `LIKELY = NOT_PRODUCED`, `UNLIKELY = NOT_PRODUCED` — reserved states; retaining an enum member does not authorize the R1 compiler to produce it. Absent an approved deterministic certainty rule → `compiler_assigned_certainty = UNRESOLVED` (this is the ADJUDICATED rule, not a pending guard); no deterministic certainty rule is approved in R1, so the certainty column above is `UNRESOLVED` everywhere. Missingness semantics are unaffected by this adjudication.

**Certainty authority model (normative — CRC-002, `BOTH_SEPARATED`, owner adjudication 2026-08-28).**

- `source_asserted_certainty`: role = `clinical_source_assertion`; authority = `PRESERVED` (verbatim) — what the source declared, captured verbatim when present in input (optional, never invented).
- `compiler_assigned_certainty`: role = `processing_and_admissibility_state`; authority = `NON_CLINICAL` — what the pipeline computes per the adjudicated rule above.

Invariants (normative): `source_asserted_certainty` MUST NOT be overwritten; `compiler_assigned_certainty` MUST NOT silently upgrade the source assertion; `source_kind` alone MUST NOT establish clinical certainty; unresolved authority or interpretation fails closed. Provenance and certainty are different axes: a monitor/lab origin informs `PROVENANCE`, it does not by itself demonstrate clinical truth.

**Taxonomy retention (CRC-001).** `CANDIDATE`/`LIKELY`/`UNLIKELY`/`AMBIGUOUS` stay in the taxonomy for later contract extensions (enum strategy `RETAIN_FOR_COMPATIBILITY` — no destructive removal); R1's contract does not produce them (recorded: no invented certainty). `UNRESOLVED` is the adjudicated fail-closed certainty, produced absent an approved deterministic certainty rule — which in R1 is always.

## Interfaces / Contracts

```python
# pipeline_types.py — leaf stage contract shared by all passes (pure; no I/O).
# Passes import THIS leaf module, never pipeline (D5 dependency rule).
_T = TypeVar("_T")

@dataclass(frozen=True, slots=True)
class StageResult(Generic[_T]):
    admitted: tuple[_T, ...]
    diagnostics: tuple[Diagnostic, ...]
    # each pass: run_<stage>(facts, ...) -> StageResult[OutputT]

# pipeline.py — composition root (imports pipeline_types and RE-EXPORTS StageResult;
# nothing but cli/__main__ imports pipeline)
@dataclass(frozen=True, slots=True)
class CompileResult:
    document: str | None          # None whenever diagnostics exist (fail-closed)
    diagnostics: tuple[Diagnostic, ...]

def derive_exit_code(diagnostics: tuple[Diagnostic, ...]) -> int:
    """Pure function of the diagnostic SET; min stage-order code; 0 iff empty."""

# adapters/contract.py — declarative, single source of truth (illustrative shape)
CONTRACT: Mapping[str, FieldContract]  # field_id -> required keys, type predicate, provenance rule

# core/ir.py — adjudicated ADDITIVE aggregate (CRC-003 / D10, owner adjudication 2026-08-28)
@dataclass(frozen=True, slots=True)
class CanonicalClinicalIR:
    facts: tuple[CanonicalClinicalFact, ...]
    # Construction-time invariants (validated at construction; fail-closed):
    #   unique clinical_fact_id; lineage validation boundary; no document prose;
    #   no document_mode; deterministic representation (ordering of facts).
    # Constraint: MINIMAL — no framework, no graph database, no generic provenance
    #   engine, no pass manager.

# admissibility — veto set injected, never from a mutated core (D7)
def run_admissibility(facts: tuple[CanonicalClinicalFact, ...],
                      veto_terms: frozenset[str]) -> StageResult[CanonicalClinicalFact]: ...
```

**G-1 adjudication (binding, resolved at design level before freeze).** `StageResult` lives in the leaf module `pipeline_types.py`, importable by every pass without violating Decision 5's dependency rule; `pipeline.py` re-exports it for the composition root. The executor executes this placement; it is not an executor decision.

Interface contract properties (M2.1) for the Python contracts above: all stage functions and `derive_exit_code` are pure — no I/O, no globals, no side effects; Timeout/limits: not applicable at this layer (pure in-memory functions with terminating loops; no wall-clock or size limits apply below the CLI boundary, which carries the limits declared in §CLI Surface); Security: untrusted content never reaches `eval`/`exec`/subprocess/shell — unknown shapes surface as mapped diagnostics, never as unhandled exceptions crossing a stage boundary (unexpected exceptions are confined to the CLI's exit-70 catch-all); Failure behavior: every stage returns its diagnostics inside `StageResult` — a stage never raises to signal a clinical fault.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/clinical_compiler/passes/{input_validation,semantic_normalization,admissibility,document_selection}.py` | Implement | Four pure passes per Module Map |
| `src/clinical_compiler/linter/conformance.py`, `renderers/deterministic.py` | Implement | Mode lint + canonical renderer |
| `src/clinical_compiler/adapters/{__init__,contract,structured_feed,seed}.py` | Create | Driving side; `free_text.py` only if the gate selects it |
| `src/clinical_compiler/adapters/README.md` | Delete | Zero-byte placeholder; replaced by real modules (recorded) |
| `src/clinical_compiler/pipeline_types.py` | Create | Leaf stage-contract module: `StageResult[_T]`; re-exported by `pipeline.py` (G-1 adjudication, §Interfaces) |
| `src/clinical_compiler/{pipeline,cli}.py` | Create | Composition root (re-exports `StageResult`) + argparse shell |
| `src/clinical_compiler/{passes,linter,renderers}/__init__.py` | Modify | One-line docstrings (scaffold zero-byte gate) |
| `src/clinical_compiler/core/ir.py` | Modify (additive only) | Adjudicated `CanonicalClinicalIR` aggregate (CRC-003 / D10, owner adjudication 2026-08-28): explicit lightweight frozen dataclass holding `facts: tuple[CanonicalClinicalFact, ...]`, with construction-time invariants — unique `clinical_fact_id`; lineage validation boundary; no document prose; no `document_mode`; deterministic representation (ordering); MINIMAL — no framework, no graph database, no generic provenance engine, no pass manager |
| `src/clinical_compiler/core/{types,diagnostics,policy}.py` | Unchanged | Zero modifications in R1 (the `core/ir.py` aggregate is R1's only core change, additive with recorded justification) |
| `pyproject.toml` | Modify | `[project.scripts]` only; dependencies stay `[]` |
| `tests/conftest.py` | Modify | Extend existing `make_provenance`/`make_clinical_value` factories with fact/IR factories |
| `tests/fixtures/`, `tests/golden/`, `tests/integration/` | Create | Corpus fixtures, golden document + digest, runner/exit-code/determinism tests |
| `tests/unit/test_policy.py` | Modify | Replace tautological test with mutation-sensitive tests |
| `README.md`, `docs/architecture.md` | Fill (0 bytes today) | Pipeline, contracts, invariants, exit-code table |
| `.gitignore` | Modify | Append `.coverage`, `.mimosa/` |

## Artifact Contracts (authority classes — M2.2)

| Artifact | Path / topic | Producer | Consumer | Format | authority_class | creation_condition | validation | rollback_relation |
|---|---|---|---|---|---|---|---|---|
| Phase 0 inventory & evidence | `openspec/changes/clinical-compiler-r1/outputs/inventory/*` | Executor (Phase 0) | Decision owner, reviewer | Markdown + captured command output, run-ID/timestamp stamped | `EVIDENCE` | Phase 0 activation | Side-effect budget before/after snapshot comparison | Deleted or regenerated only by owner instruction; retained across rollback (evidence of the attempt) |
| Golden files & digests | `tests/golden/*` (incl. `tests/golden/independent/`) | Executor (generator) + ≥1 independently authored expected sample (owner or owner-designated audit path) | Determinism gate | Deterministic document + SHA-256 digest | `EVIDENCE` (frozen regression baseline once committed) | Phase 3 gate | Cross-run digest equality + golden comparison tests | Changing a golden invalidates prior determinism evidence (candidate-drift analog): re-freeze + re-verify under an owner-recorded decision |
| Approval record | `APPROVAL-PHASE0.md` (change directory) | Decision owner (reviewer-verified) | Executor activation check | Hash-bound Markdown | `AUTHORITATIVE_STATE` | Owner approval of a phase | Bound hashes match current bundle files; validation receipt referenced | Superseded ONLY by a newer owner-authored record; the executor never edits or deletes it |
| Runtime compiled documents | `--output` destination / stdout | CLI at runtime | Clinician/user | UTF-8 deterministic bytes | `DERIVED_OUTPUT` | Clean compile (exit 0) | Lint-clean + golden digest equality | Pure function of input — regenerate by re-running; no rollback meaning |

`state.yaml` is orchestrator-owned bookkeeping, outside executor writes, and intentionally carries no authority class here.

## Phase → Spec Mapping

| Phase | Delivers (spec domains) | Gate |
|-------|-------------------------|------|
| Phase 0 | phase0-verification (all) | `BASELINE_ANOMALIES == 0` (`UNKNOWN` outcomes count as anomalies); decision gate: the owner-authored approval record states `INPUT_CONTRACT_DECISION` + seed status |
| Phase 1 | input-contract (all); pipeline-passes scaffold + input validation; `.gitignore` | Contract committed before adapter code; `TYPE_ERROR` orphan eliminated |
| Phase 2 | clinical-fact-model certainty/missingness/provenance + `CanonicalClinicalIR` aggregate (CRC-003); diagnostics-policy governance + mutation tests; normalization + admissibility | `PROVENANCE_ERROR` orphan eliminated; tautology replaced |
| Phase 3 | determinism-rendering (all); document selection | Golden digests committed; cross-run SHA-256 equality |
| Phase 4 | cli-surface (all); docs | `[project.scripts]` + deps `[]`; exit codes tested; final quality suite |

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Each pass: admit/quarantine partition, mapped codes, interpretation table | pytest, existing factory fixtures, parametrized over the Fault Corpus |
| Contract | Adapters enforce exactly the frozen contract; exit mapping is a pure total function | Corpus-driven parametrization; mutation checklist (veto membership/enforcement mutation → ≥1 failure) |
| Integration | Runner end-to-end: happy path, each corpus fault, no partial document, stderr diagnostics | `pipeline.run` in-process; `cli.main` via `subprocess` for exit codes |
| Determinism | Byte-identical output, fresh interpreters, randomized `PYTHONHASHSEED`, golden digest | `python -I` double compile; SHA-256 vs committed digest |

## Migration / Rollout

Project lineage (CRC-010 — owner adjudication 2026-08-28):

```text
PROJECT_LINEAGE     = SUCCESSOR_OF_V0_5
REPOSITORY_TOPOLOGY = NEW_IMPLEMENTATION_REPOSITORY
MIGRATION_BASELINE  = UNRESOLVED_UNTIL_EXACT_EVIDENCE
```

Normative consequences: the repository may be physically new, but the product does NOT lose the lineage of the OKF Clinical Record Compiler v0.5. The bundle MUST NOT claim migration, CLI/golden/runtime compatibility, or v0.5 preservation until exact executable evidence exists — `MIGRATION_BASELINE = UNRESOLVED_UNTIL_EXACT_EVIDENCE` blocks any such claim. (The frozen `c6578b6` baseline remains the in-repo implementation baseline — a different axis, unchanged by this adjudication.) R1 claims no migration, no CLI/golden/runtime compatibility, and no v0.5 preservation. Each phase ends at its computable gate; BLOCKED enumerates failures and halts.

### Rollback (M6.2 — trigger, steps, verification)

**Triggers:** (a) any phase gate BLOCKED with failures the executor cannot repair inside that phase's declared writes; (b) a side-effect budget violation (before/after snapshots differ outside declared writes); (c) material regression vs the verified baseline (e.g., core tests fail, coverage collapse); (d) an explicit owner decision to abort.

**Steps:** (1) the executor STOPS at the trigger and reports `blocked` with enumerated failures — it never self-authorizes rollback of approved state; (2) on owner instruction, revert this change's commits (`git revert`, or reset the working branch to the last approved state) — R1's only core change is the adjudicated additive `CanonicalClinicalIR` (CRC-003), reverted together with the change's commits, so baseline `c6578b6` remains valid; (3) `outputs/` evidence artifacts are RETAINED (they document the attempt — `EVIDENCE` class) unless the owner orders deletion; (4) the approval record (`AUTHORITATIVE_STATE`) is never deleted by the executor — if execution is abandoned, the owner supersedes it with a newer record.

**Verification of rollback:** `git diff c6578b6 -- src/clinical_compiler/core` is empty AND the baseline suite re-runs green (pytest 29/29, `mypy --strict` exit 0, `ruff check` exit 0) AND the repository file manifest matches the baseline-plus-retained-evidence expectation.

**Automatic rollback is unsafe (owner adjudication required) when:** commits outside this change landed after the phase commits; an owner decision record exists for work already applied (e.g., a recorded seed decision); or the trigger is a dispute about gate semantics rather than a mechanical failure. Never overwrite independently changed newer state blindly.

## What We Do NOT Build in R1

- **No NLP/ML dependencies**; the free-text branch, IF selected, is a bounded telegraphic micro-grammar (stdlib parser) — else free-text is rejected with `INPUT_CONTRACT_ERROR` and deferred to R2.
- **No persistence / evidence store / receipts** — that was qwen-ctl's domain; the only durable artifacts here are the SDD bundle and approval record.
- **No network, no GUI, no CI** (CI is a separate candidate change).
- **No stdin/`-` input, no `--json` diagnostics, no `check`-only subcommand** — the surface is exactly one verb.
- **No new document modes** beyond `NURSING_RECORD_TELEGRAPHIC`; no cross-source conflict resolution (ambiguity blocks, never picks); no certainty production beyond the adjudicated fail-closed rule (`UNRESOLVED` everywhere in R1; no automatic source_kind→certainty inference — CRC-001); no core modifications beyond the adjudicated additive `CanonicalClinicalIR` (CRC-003).

## Open Questions

- [ ] Input-format branch — owner decides at the Phase 0 gate; mechanisms here are branch-safe (`free_text.py` conditional; corpus instantiates both branches).
- [ ] `NEVER_AUTO_TERMS` seed content — owner approves or records deferral; enforcement identical either way (D7).
- [ ] CLI name/surface — frozen as recommendation above; final owner review at bundle approval.
- [ ] Exact rendered glyph vocabulary (line/bracket formats) — frozen at implementation via the first golden file; the INVARIANTS (sort key, explicit `unknown`, provenance on every line) are frozen here.
