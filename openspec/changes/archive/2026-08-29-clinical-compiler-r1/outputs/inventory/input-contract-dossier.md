# Phase 0 — Input-Contract Dossier (Task 0.5)

Change: `clinical-compiler-r1` | Evidence sources: repository files only (core IR types, existing
tests, `design.md` frozen Fault Corpus FC-01..FC-12 dual-column instances, domain specs, the
`sdd/clinical-compiler-r1/explore` record) | No executor selection is made or implied anywhere
below. Options are listed in alphabetical order of their answer values; the ordering carries no
preference.

## Evidence base (what the repository shows today)

1. **No input path exists.** `src/clinical_compiler/adapters/` contains only a zero-byte
   `README.md` — no Python, no contract, no parser (`scaffold-inventory.md`). The explore record
   (2026-08-28) states: "INPUT FORMAT UNKNOWN: no parser/adapter code exists, so the source
   format (notes? FHIR? HL7? plain text?) is UNDETERMINED."
2. **The core IR is fact-shaped.** `core/ir.py` `SourceFactIR(fact_id, field_id, raw_value,
   provenance)` — the entry rung of the IR ladder is per-source, per-field facts with verbatim
   raw values and provenance. Whatever enters must become this.
3. **Existing tests feed structured literals.** `tests/unit/test_ir.py` builds facts like
   `raw_value="FC 72"`, `Provenance(source_kind="monitor", source_ref="m-9")`,
   `source_kind="clinical_note"`; `tests/conftest.py` factories default to `"72 bpm"` monitor
   values. No test parses prose.
4. **The frozen fault corpus is dual-column.** `design.md` Fault Corpus FC-01..FC-12 defines a
   structured-branch instance AND a free-text instance (where applicable) for every fault class,
   and PC-1/PC-2 positive controls — the corpus is branch-safe: either gate answer is fully
   exercisable without new corpus authoring.
5. **The specs freeze the mechanics of either answer.** input-contract spec: contract frozen per
   `INPUT_CONTRACT_DECISION` BEFORE adapter code; driving adapter(s) preserve `fact_id`,
   `field_id`, verbatim `raw_value`, provenance (+ optional verbatim
   `source_asserted_certainty`, CRC-002 `BOTH_SEPARATED`); free-text, IF selected, is bounded to
   a telegraphic micro-grammar with no NLP/ML and out-of-grammar text → `INPUT_CONTRACT_ERROR`,
   never a guess; free-text, IF not selected, is rejected with `INPUT_CONTRACT_ERROR` (deferred).
6. **The runtime value boundary applies to both branches** (CRC-006): values outside the frozen
   field contract are rejected at the boundary regardless of input format; an arbitrary Python
   object never becomes an admissible canonical value.

## Decision envelope (fail-closed; executor fills nothing)

```yaml
reason_for_block: >-
  Phase 1 cannot begin: task 1.1 freezes the input contract as a direct function of
  INPUT_CONTRACT_DECISION, and freezing any contract without the decision owner's recorded
  selection would be an executor-authored decision (invalid per the phase0-verification and
  input-contract specs; executor-authored decisions fail the gate with or without attribution).
  The R1 input surface therefore blocks until the owner states the decision in the
  owner-authored phase-approval record.

question: >-
  Which input format(s) does clinical-compiler R1 accept at its driving adapter — a structured
  feed of source facts, free-text telegraphic notes, or both?

options:
  - answer_value: STRUCTURED_FEED_ONLY
    description: >-
      R1 accepts only a structured per-fact feed (bytes -> candidate records -> SourceFactIR per
      the frozen contract table in adapters/contract.py, design D8). Free text is rejected with
      INPUT_CONTRACT_ERROR and free-text support is recorded as deferred to R2 (tasks 1.3).
    option_effects:
      costs:
        - Input must arrive as conformant per-fact records; any conversion from prose happens
          upstream of the compiler, outside R1 scope (not built in this change).
        - The contract table becomes new frozen surface: committed before any adapter code
          (task 1.1 freeze-before-build) and changeable later only via a new recorded owner
          decision.
      risks:
        - If clinicians' real workflow produces only telegraphic notes, a structured-only R1
          needs a separate feed-producing step before the compiler is usable end-to-end; that
          step is out of scope for this change (proposal Non-Goals: no NLP, no new input work
          beyond the selected contract).
      branch_safety_evidence:
        - Design Fault Corpus column "Structured-branch instance" fully instantiates FC-01
          (missing required key), FC-02 (unknown key x_priority), FC-03 (top-level JSON array /
          undecodable bytes), FC-05 (raw_value: true for numeric FC -> TYPE_ERROR), FC-06
          (conflicting same-field_id facts), FC-07..FC-12 and PC-1/PC-2 — every case maps to its
          code deterministically with no parse-ambiguity surface.
        - FC-04's structured-branch instance is itself defined: the structured branch rejects
          any free text ("paciente estable, creo que mejoró algo") with INPUT_CONTRACT_ERROR.
      downstream_consequence:
        - Phase 1 builds contract.py + structured_feed.py + input_validation; free_text.py is
          NOT created and the deferral is recorded; corpus fixtures instantiate the structured
          column only (task 1.6).
  - answer_value: STRUCTURED_FEED_PLUS_FREE_TEXT
    description: >-
      R1 accepts the structured feed AND free-text telegraphic notes: in addition to
      structured_feed.py, adapters/free_text.py implements a bounded telegraphic
      micro-grammar, stdlib parser only (no NLP/ML), with out-of-grammar text yielding
      INPUT_CONTRACT_ERROR rather than a guess (input-contract spec; design What We Do NOT
      Build).
    option_effects:
      costs:
        - The micro-grammar must be specified and frozen, implemented with stdlib only, and
          covered by corpus fixtures and tests for both branches (task 1.6 gains free-text
          branch instances) — a larger frozen surface and larger test corpus than the
          structured-only branch.
        - Every grammar production adds contract surface: grammar changes later require a new
          recorded owner decision, same as the contract table.
      risks:
        - The proposal's declared medium risk: free-text parsing pulls toward NLP/ML
          dependencies, which would break the zero-runtime-dependency goal and determinism; the
          frozen mitigation is exactly the bounded micro-grammar + INPUT_CONTRACT_ERROR
          fall-through (never a guess) — the risk is bounded by contract, not eliminated by it.
        - Out-of-grammar notes are rejected, so the accepted subset of Spanish telegraphic
          notes is smaller than what clinicians may write; the boundary must be communicated
          (FC-04 documents the fall-through).
      branch_safety_evidence:
        - Design Fault Corpus column "Free-text instance" fully instantiates FC-01 (token
          stream missing field token), FC-02 (unsupported annotation), FC-03 (non-grammatical
          prose), FC-04 ("paciente estable, creo que mejoró algo"), FC-05 (well-formed token,
          non-numeric value), FC-06 (token with two grammar parses), PC-2 ("TA: sin dato" per
          grammar) — the corpus is pre-authored for this branch.
      downstream_consequence:
        - Phase 1 additionally creates free_text.py (task 1.3 conditional branch); fixtures and
          tests add the free-text instances; determinism and fail-closed gates apply
          identically to both adapters.

selection_mode: OPEN

allowed_answer_domain:
  - STRUCTURED_FEED_ONLY
  - STRUCTURED_FEED_PLUS_FREE_TEXT

constraint_note_on_the_domain: >-
  The frozen design (Module Map; tasks 1.2/1.3) creates adapters/structured_feed.py
  unconditionally (branch A) and makes free_text.py conditional (branch B). The two executable
  answer values above therefore cover the bundle's mechanical space, including the "both"
  phrasing of the open question (state.yaml). An answer of free-text WITHOUT the structured
  contract is not executable under the frozen bundle and would require a recorded bundle
  revision, not a gate fill. This is a mechanical constraint statement, not a recommendation;
  both executable values are presented with full effects above.

continuation_after_each_answer:
  STRUCTURED_FEED_ONLY: >-
    Owner states INPUT_CONTRACT_DECISION = STRUCTURED_FEED_ONLY in the owner-authored approval
    record -> Phase 1 freezes the contract table (task 1.1), builds structured_feed.py and
    input_validation, records the free-text deferral (task 1.3 ELSE branch: free text rejected
    with INPUT_CONTRACT_ERROR), and proceeds to the Phase 1 gate.
  STRUCTURED_FEED_PLUS_FREE_TEXT: >-
    Owner states INPUT_CONTRACT_DECISION = STRUCTURED_FEED_PLUS_FREE_TEXT in the owner-authored
    approval record -> Phase 1 freezes the contract table (task 1.1), builds structured_feed.py,
    free_text.py (bounded telegraphic micro-grammar, stdlib only) and input_validation, and
    proceeds to the Phase 1 gate.
  no_valid_owner_answer: >-
    Without an owner-stated decision in the approval record the Phase 0 decision gate remains
    BLOCKED and Phase 1 does not execute (executor-authored decisions are invalid).
```

## Owner-stated recommendations already on record (for completeness, not a selection)

`state.yaml` records the owner's 2026-08-28 recommendation: "structured feed for R1; free-text
deferred to R2", pending formal close at this gate. It is cited here because it exists in the
record; the formal decision is the owner's act in the approval record, and this dossier neither
relies on nor restates it as decided.
