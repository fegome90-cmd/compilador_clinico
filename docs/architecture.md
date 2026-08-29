# Architecture — `clinical-record-compiler` R1

The architecture record for R1: how the compiler is structured, which contracts are frozen, and which invariants the implementation enforces by construction. Normative sources are `openspec/changes/clinical-compiler-r1/design.md` (decisions D1–D10, fault corpus, exit-code table, determinism mechanism) and the seven domain specs under `openspec/changes/clinical-compiler-r1/specs/` — this document describes the implemented state and never re-decides what those files freeze. User-facing usage lives in the [README](../README.md).

---

## Pipeline

Fixed stage order (design D1). `pipeline.run` is the composition root; every stage is a pure function and every stage consumes ONLY the survivors of the previous stage.

```
INPUT bytes (JSONL)
      │
      ▼
parse_feed (adapters/structured_feed)      per-record contract mapping
      │                                      INPUT_CONTRACT_ERROR per bad line;
      ▼                                      non-UTF-8 bytes fault the whole feed
input_validation ──────────────────────────  INPUT_CONTRACT_ERROR | TYPE_ERROR
      │
      ▼
semantic_normalization ────────────────────  SEMANTIC_AMBIGUITY_BLOCK
      │
      ▼
admissibility ──────────────────────────────  POLICY_VIOLATION | PROVENANCE_ERROR
      │
      ▼
CanonicalClinicalIR (explicit aggregate, CRC-003)
      │
      ▼
document_selection ─────────────────────────  DOCUMENT_SELECTION_ERROR
      │
      ▼
emission gate (fail-closed, whole-run) ─────  ANY accumulated diagnostic → no document
      │  reached ONLY while the diagnostic set is empty
      ▼
renderers/deterministic (DocumentIR + CanonicalClinicalIR → bytes) ── RENDER_ERROR
      │
      ▼
linter/conformance (bytes vs mode rules) ───  LINT_FAILURE
      │
      ▼
document bytes (UTF-8, \n) at exit 0 only
```

Blocking granularity (design D1):

- **Per-fact quarantine.** A faulting record is quarantined with its diagnostic while the remaining records keep flowing. Stages never raise to signal a clinical fault — faults surface as `Diagnostic`s inside `StageResult` (design M2.1).
- **Full enumeration, never fail-fast.** A feed-level fault still runs every later stage on the (possibly empty) survivor set, maximizing enumeration over fail-fast hiding.
- **Whole-run emission gate.** The document is emitted IFF the accumulated diagnostic set is empty and render + lint both admit. `CompileResult` makes the failure state unrepresentable: a document never coexists with diagnostics, and a document-less, diagnostic-less outcome exists only under an unresolved policy. One invalid fact blocks the document — never a partial one.
- **D7 policy gate.** A `PolicyResolution` that is not `is_resolved` runs no admissibility, no selection, no render, no lint — an explicit blocked outcome (CLI usage exit 2). There is no execution path where an unresolved policy degrades into a silent empty veto set (CRC-005).

Exit codes are the pure function `derive_exit_code(diagnostic set)`: the minimum stage-order code among 3–10 present, 0 iff empty; exit 2 (usage — no compile attempted) and exit 70 (unexpected-exception catch-all) are CLI-boundary mappings. The frozen table lives in the README and `design.md` §Exit-Code Table.

---

## IR ladder

`SourceFactIR → CanonicalClinicalFact → CanonicalClinicalIR → DocumentIR → bytes` — every hop narrows authority; a fact's value has exactly one home (CRC-004 single authority):

| IR | Module | Carries | Never carries |
|----|--------|---------|---------------|
| `SourceFactIR` | `core/ir.py` | One fact verbatim from one source: `fact_id`, `field_id`, `raw_value: object`, `provenance` | Any interpretation |
| `CanonicalClinicalFact` | `core/ir.py` | Normalized fact: `clinical_fact_id`, `field_id`, `ClinicalValue` (value + certainty + missingness + provenance), `source_fact_refs: tuple[str, ...]` | Document placement |
| `CanonicalClinicalIR` | `core/ir.py` | Explicit aggregate of the admissible set: `facts: tuple[CanonicalClinicalFact, ...]` (R1's only core change, additive, CRC-003/D10) | Document prose, `document_mode` |
| `DocumentIR` | `core/ir.py` | `document_mode` + ordered `DocumentEntry`s referencing canonical facts by `clinical_fact_ref` + `presentation_role` | **Values — ever** |
| bytes | `renderers/deterministic.py` | The final document, lint-clean or not emitted | Any partial rendering |

Construction-time invariants enforced by `CanonicalClinicalIR`: unique `clinical_fact_id`; lineage validation (non-empty, non-empty-string `source_fact_refs`); canonical `(field_id, clinical_fact_id)` codepoint ordering of `facts`; MINIMAL surface — a plain frozen dataclass, no framework, no graph database, no pass manager.

`clinical_fact_id` is derived deterministically: `{field_id}:{sha256(canonical-JSON preimage of [field_id, codepoint-sorted fact_id set])}` — collision-safe, stable across runs and input orderings, stdlib only (no random/uuid/time).

---

## Contracts

### Input contract (frozen, `adapters/contract.py` — single source of truth)

Owner decision `INPUT_CONTRACT_DECISION = STRUCTURED_FEED_ONLY` (APPROVAL-PHASE1.md): the wire format is JSONL — one fact-record object per non-blank line (a top-level JSON array is FC-03; undecodable bytes fault the whole feed). The contract is a declarative `CONTRACT` table plus the pure `map_record`; adapters and validation enforce exactly this table, and contract changes REQUIRE a new recorded owner decision.

| Rule | Content |
|------|---------|
| Record keys | required: `fact_id`, `field_id`, `raw_value`, `provenance`; optional: `source_asserted_certainty`; the allowed set is closed (unknown key → `INPUT_CONTRACT_ERROR`) |
| Fields (R1) | `FC` → `raw_value: int \| float`; `TA` → `raw_value: str` — checked by **exact runtime type**, never `isinstance` (a `bool` never passes a numeric field) |
| `raw_value: null` | Admitted for every field — the structured branch's assessed-absence marker (PC-2); normalizes to `MISSING` with mandatory provenance |
| Provenance | Must declare exactly `source_kind` + `source_ref` (both strings); `source_kind` ∈ `{monitor, lab, clinical_note}` (`ALLOWED_SOURCE_KINDS`) |
| `source_asserted_certainty` | Optional; must name a `Certainty` member; captured verbatim (CRC-002 authority `PRESERVED`) — never invented, never overwritten |
| Runtime value boundary | CRC-006 (`ENFORCE_BOUNDED_VALUES_AT_RUNTIME`): `ClinicalValue.value` stays `Any` in the frozen core, but only the exact types each field declares become admissible canonical values |

### Policy resolution machine (frozen, D7 / CRC-005 — `adapters/seed.py`)

```
UNRESOLVED_POLICY
  ├─ owner APPROVED seed          → POPULATED           (veto terms from the owner file)
  └─ owner DEFERRED_BY_OWNER      → APPROVED_EMPTY_BY_DEFERRAL (empty set, cited)
```

- `core.policy.NEVER_AUTO_TERMS` stays the frozen empty default — never mutated, never imported by the enforcement stage; the effective veto set is runtime-injected (`run_admissibility(..., veto_terms, source_fact_ids)` — required parameters, so composition can never silently resolve against nothing).
- The approved-empty state is reachable ONLY through `approved_empty_by_deferral`, which REQUIRES a citation naming the durable owner decision (`POLICY_SEED_DECISION = DEFERRED_BY_OWNER`, APPROVAL-PHASE1.md — transcribed in `DEFERRED_BY_OWNER_DECISION`). An uncited empty set is unrepresentable, including via direct construction.
- The CLI's absent `--policy-seed` resolves to the approved-empty policy under that citation (the FC-12 production path). A given seed failing structural validation — missing file, unreadable, malformed JSON, wrong shape (`{"terms": [...]}` with string, non-empty terms only), non-string or empty-string term — resolves `UNRESOLVED_POLICY` with a typed `PolicySeedFault`, mapped to CLI usage exit 2. Never empty-set-and-continue.
- Seed validation is STRUCTURAL only — no clinical content is authored or judged by the implementation.
- `UNRESOLVED_POLICY` is a resolution STATE, not a `DiagnosticCode`: the 8-code taxonomy is frozen, and translating the blocked state into exit 2 belongs to the shell.

### Stage contract (`pipeline_types.py` — leaf, G-1 adjudication)

`StageResult[_T]` (`admitted: tuple[...]` + `diagnostics: tuple[Diagnostic, ...]`) lives in the leaf module so passes never import `pipeline`; `pipeline.py` re-exports it. `CompileRequest` (bytes, mode, `PolicyResolution`) and `CompileResult` (document `bytes | None`, diagnostics, policy) carry the fail-closed invariants at construction time.

---

## Invariants

**Determinism mechanism (design, frozen).**
1. Immutable ordered containers — frozen dataclasses, `tuple` fields, explicit sort keys; document entries ordered by `(field_id, clinical_fact_id)` in Unicode codepoint order — never locale collation, never dict/set iteration.
2. No environment leakage — no `datetime.now`, `time`, `random`, `locale`, env vars, or host names in any output path; the document embeds no timestamps.
3. Canonical formatting — UTF-8, `\n` only, no trailing whitespace, exactly one final newline; `str(int)` / deterministic `str(float)`; any JSON via `json.dumps(..., sort_keys=True, ensure_ascii=True, separators=(",", ":"))`.
4. Hash-order independence — no code path lets `hash()` ordering or unsorted set/dict iteration reach output (veto diagnostics report the codepoint-minimal match over the sorted term set; `CanonicalClinicalIR` sorts at construction).
5. Golden digests — `tests/golden/` commits fixture sets + document SHA-256s; the cross-run gate compiles each set twice in fresh interpreters (`python -I`, `PYTHONHASHSEED=0` vs random) and asserts digest equality across runs AND against the committed digest.
6. Evidence integrity — see the dedicated invariant below.

Rendered glyph vocabulary (frozen via the first golden file, design Open Question 4): fact lines are `{field}: {value} [{missingness}] [{source_kind} {source_ref}]`; a field with no fact renders the explicit unassessed line `{field}: unknown [not_assessed]` (no provenance segment — no source exists). The linter validates the BYTES against the same vocabulary as an independent net (rules duplicated on purpose — a renderer bug must not validate itself).

**Certainty authority — BOTH_SEPARATED (CRC-002, normative).**
- `source_asserted_certainty`: role `clinical_source_assertion`, authority `PRESERVED` — what the source declared, captured verbatim when present, never overwritten.
- `compiler_assigned_certainty`: role `processing_and_admissibility_state`, authority `NON_CLINICAL` — what the pipeline computes, never a silent upgrade of the source assertion.
- `source_kind` alone MUST NOT establish clinical certainty; provenance and certainty are different axes (a monitor/lab origin informs `PROVENANCE`, it does not demonstrate clinical truth). Unresolved authority or interpretation fails closed.

**NOT_PRODUCED certainty (CRC-001, adjudicated).** The automatic mapping (`monitor/lab → CONFIRMED`, `clinical_note → PROBABLE`) is adjudicated and rejected — NOT executable semantics. No deterministic certainty rule is approved in R1, so `compiler_assigned_certainty = UNRESOLVED` for every canonical fact — the adjudicated fail-closed rule, not a pending guard. `PROBABLE`, `LIKELY`, `UNLIKELY` are NOT_PRODUCED (taxonomy members retained `RETAIN_FOR_COMPATIBILITY`; retention does not authorize production).

**Missingness non-conflation.** Assessed absence (`MISSING`, `NOT_APPLICABLE`) is a source assertion — it traces to provenance, never to input absence (PC-2: `raw_value: null` is the R1 structured marker; `NOT_APPLICABLE` has no R1 marker and is unreachable rather than invented). Unassessed (`UNKNOWN`, `NOT_ASSESSED`) is document-level — a field with no fact renders explicit `unknown [not_assessed]`, never dropped, never rewritten as assessed absence (PC-1).

**Fail-closed emission.** `CompileResult` construction invariants (document XOR diagnostics; empty outcome only under unresolved policy) plus the CLI's exit-70 catch-all make "silently empty" unrepresentable: untrusted input can never exit 0 by accident, never crash with a bare traceback, never leave a partial document. `--output` writes are atomic (temp file + fsync + `os.replace` + parent-dir fsync; temp artifact removed on any failure).

**EVIDENCE_INTEGRITY of goldens (M7.1 vocabulary).** Golden evidence carries `VALID | DEGRADED | INVALID`; implementation-generated goldens alone are `DEGRADED` (the implementation must not write its own exam). The committed corpus carries `EVIDENCE_INTEGRITY = VALID`: each scenario's digests are self-consistent AND at least one expected sample under `tests/golden/independent/` is authored independently of the implementation (owner or owner-designated audit path — never the executor).

---

## Module map & dependency rule

```
src/clinical_compiler/
├── core/                        FROZEN leaf — stdlib only, imports nothing from new packages
│   ├── types.py                 Certainty | Missingness | Provenance | ClinicalValue
│   ├── ir.py                    SourceFactIR → CanonicalClinicalFact → DocumentIR
│   │                            + CanonicalClinicalIR (R1's ONLY core change — additive, CRC-003/D10)
│   ├── diagnostics.py           DiagnosticCode (8) | Diagnostic
│   └── policy.py                NEVER_AUTO_TERMS (frozen empty default — runtime injection, D7)
├── adapters/                    driving side; imported by pipeline/cli, never the reverse
│   ├── contract.py              frozen input-contract table (single source of truth)
│   ├── structured_feed.py       JSONL bytes → per-record contract evaluations (branch A)
│   ├── seed.py                  policy-seed loader (structural validation only)
│   └── free_text.py             NOT built — STRUCTURED_FEED_ONLY recorded
├── passes/                      pure transformations (input_validation, semantic_normalization,
│                                admissibility, document_selection)
├── renderers/deterministic.py   DocumentIR + CanonicalClinicalIR → bytes
├── linter/conformance.py        bytes vs mode rules (independent net)
├── pipeline_types.py            leaf stage contract: StageResult[_T] (passes import this, never pipeline)
├── pipeline.py                  composition root: stage order, accumulator, emission gate,
│                                CompileRequest/CompileResult, derive_exit_code
└── cli.py                       argparse shell: file I/O, seed loading, exit codes, atomic write
```

Dependency rule (design D5): `cli → pipeline → {passes, renderers, linter} → {adapters(contract), pipeline_types} → core{ir, diagnostics, policy} → types`. Nothing imports `cli`/`pipeline` except the console-script entry point (`[project.scripts]`, `clinical_compiler.cli:main`). Functional core, imperative shell: all I/O lives at the edges (adapters driving; renderers/linter/CLI driven); the pipeline and every stage are pure — no I/O, no globals mutated, no time/locale/random/env in any output path.

---

## Lineage (CRC-010 — owner adjudication 2026-08-28)

```text
PROJECT_LINEAGE     = SUCCESSOR_OF_V0_5
REPOSITORY_TOPOLOGY = NEW_IMPLEMENTATION_REPOSITORY
MIGRATION_BASELINE  = UNRESOLVED_UNTIL_EXACT_EVIDENCE
```

The repository may be physically new, but the product does not lose the lineage of the OKF Clinical Record Compiler v0.5. Because `MIGRATION_BASELINE` is unresolved pending exact executable evidence, R1 makes NO claim of migration, CLI/golden/runtime compatibility, or v0.5 preservation — any such claim is blocked until evidence exists. (The frozen `c6578b6` in-repo baseline is a different axis and is unaffected.)

---

## Governance

R1 executes under `openspec/changes/clinical-compiler-r1/` with the **AI Work Agent Execution Contract 0.3**, profile `GOVERNED`: `proposal.md` (scope, side-effect budget) → `design.md` (normative) → `tasks.md` (plan, phase gates) → `specs/*` (seven domain specs) → `outputs/` (phase evidence). No phase executes without a durable hash-bound approval record (`APPROVAL-PHASE*.md`) naming the bundle SHA-256s, the approved phase(s), and the decision owner (Felipe Gonzalez); the executor never edits approval records or commits. The frozen core is additive-only with recorded justification — R1's only core change is the adjudicated `CanonicalClinicalIR` (`core/ir.py`, CRC-003). Runtime dependencies are zero; the runtime is stdlib-only.
