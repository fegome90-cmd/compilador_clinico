# Phase 0 — Decision-Gate Record SKELETON (Task 0.9)

Change: `clinical-compiler-r1` | Prepared: 2026-08-29 by the SDD apply executor (Phase 0).

**This is a SKELETON. Every decision field below is intentionally BLANK.** The executor prepares
the envelope only; the decisions themselves are stated EXCLUSIVELY by the decision owner (Felipe
Gonzalez) in the owner-authored phase-approval record (the mechanism of `APPROVAL-PHASE0.md` — an
updated durable record naming the approved phase(s)). Per the phase0-verification spec, an
executor-authored decision — with or without owner attribution — is INVALID and BLOCKS the gate;
filing this skeleton does not activate anything.

## Gate rule (computed at evaluation time, never assumed)

- PASS iff the owner-authored approval record (a) states `INPUT_CONTRACT_DECISION` naming the
  chosen input format, (b) states the policy-seed status (`APPROVED` with seed, or
  `DEFERRED_BY_OWNER`), and (c) explicitly authorizes Phase 1 by name, binding the then-current
  bundle hashes per the activation mechanism.
- BLOCKED if either owner-stated decision is absent, or any decision is found executor-authored.
- Independent of this gate: the baseline gate stands at `BASELINE_ANOMALIES = 3` (strict
  computed) pending the drift-count adjudication in item ADJ-1 below (`baseline-anomalies.md`).

---

## Decision 1 — INPUT_CONTRACT_DECISION

```yaml
decision_field: INPUT_CONTRACT_DECISION
owner_decision: ________   # BLANK — decision owner fills, in the owner-authored approval record
dossier: outputs/inventory/input-contract-dossier.md   # complete evidence + envelope
reason_for_block: >-
  Task 1.1 freezes the input contract as a direct function of this decision; freezing any
  contract without the owner's recorded selection would be an executor-authored decision
  (invalid; fails the gate with or without attribution).
question: Which input format(s) does clinical-compiler R1 accept — structured feed, free-text
  telegraphic notes, or both?
options:
  - STRUCTURED_FEED_ONLY
  - STRUCTURED_FEED_PLUS_FREE_TEXT
option_effects: See the symmetrical costs/risks/branch-safety/downstream-consequence table in
  the dossier (Fault Corpus FC-01..FC-12 dual-column instances for both branches).
selection_mode: OPEN
allowed_answer_domain: [STRUCTURED_FEED_ONLY, STRUCTURED_FEED_PLUS_FREE_TEXT]
continuation_after_each_answer: See dossier (each answer's Phase 1 consequence and the
  no-valid-answer BLOCKED path are enumerated there).
```

## Decision 2 — POLICY_SEED_DECISION

```yaml
decision_field: POLICY_SEED_DECISION
owner_decision: ________   # BLANK — decision owner fills; if APPROVED, the record names the owner-authored seed file
dossier: outputs/inventory/policy-seed-dossier.md   # format + state machine + evidence (structure only, no clinical content)
reason_for_block: >-
  NEVER_AUTO_TERMS content is exclusively decision-owner territory (diagnostics-policy spec);
  with neither durable owner decision present, policy resolution is UNRESOLVED_POLICY and the
  gate is BLOCKED — there is no silent empty-set path.
question: Does R1 ship with an owner-approved NEVER_AUTO_TERMS seed (APPROVED, owner authors the
  {"terms": [...]} file) or under an explicit recorded deferral (DEFERRED_BY_OWNER, approved
  empty set)?
options:
  - APPROVED            # owner-authored seed file in the dossier's frozen format, named in the record
  - DEFERRED_BY_OWNER   # approved empty veto set; FC-07 via test-local injected seed; FC-12 asserts production path
option_effects: Symmetrical effects table in the dossier (exact-seed fidelity vs
  approved-by-deferral; enforcement identical either way).
selection_mode: OPEN
allowed_answer_domain: [APPROVED, DEFERRED_BY_OWNER]
continuation_after_each_answer: See dossier — each state's Phase 2 loading path (tasks 2.4/2.5)
  and the UNRESOLVED_POLICY BLOCKED path are enumerated there.
```

## Decision 3 — CLI_SURFACE_CONFIRMATION

```yaml
decision_field: CLI_SURFACE_CONFIRMATION
owner_decision: ________   # BLANK — decision owner fills
dossier: design.md §CLI Surface (frozen recommendation, owner-reviewed at bundle approval) +
  specs/cli-surface/spec.md
reason_for_block: >-
  The CLI name/surface is one of the three open questions recorded at PHASE_0 start
  (state.yaml); it is frozen in design as a recommendation and awaits the owner's formal close
  at this gate. No CLI code is written before Phase 4 regardless.
question: Is the frozen CLI surface accepted as designed — [project.scripts]
  clinical-compiler = "clinical_compiler.cli:main"; one verb
  "compile INPUT [--mode MODE] [--policy-seed PATH] [--output PATH]" (stdin/--json/check
  deferred to R2)?
options:
  - CONFIRM_AS_DESIGNED
  - REVISE            # owner states the revision; a material revision requires a bundle change + re-approval (hash-bound)
option_effects:
  CONFIRM_AS_DESIGNED: Phase 4 implements tasks 4.1-4.7 exactly as frozen (exit-code table,
    stderr diagnostics, atomic --output).
  REVISE: Phase 4 blocks; the frozen surface changes only through a recorded bundle revision
    and a new hash-bound approval record.
selection_mode: OPEN
allowed_answer_domain: [CONFIRM_AS_DESIGNED, REVISE]
continuation_after_each_answer:
  CONFIRM_AS_DESIGNED: CLI question formally closed; Phase 4 proceeds per design D3/D4 when
    authorized.
  REVISE: No Phase 4 CLI work until a revised, re-approved bundle exists.
```

## Decision 4 — PHASE_1_AUTHORIZATION

```yaml
decision_field: PHASE_1_AUTHORIZATION
owner_decision: ________   # BLANK — decision owner fills; requires an updated durable approval record naming PHASE_1
dossier: APPROVAL-PHASE0.md (activation mechanism) + tasks.md Activation Reminder
reason_for_block: >-
  PHASE_0 authorized PHASE_0 ONLY. A later phase activates exclusively through an updated
  durable approval record naming that phase and binding the then-current bundle hashes — never
  by implication.
question: Is Phase 1 (input contract, adapters, input validation — first mutating phase)
  authorized to execute?
options:
  - AUTHORIZE_PHASE_1    # owner issues the updated approval record naming PHASE_1 + the Decision 1/2 outcomes
  - HOLD                 # phases remain blocked; owner may first adjudicate ADJ-1/ADJ-2 below
option_effects:
  AUTHORIZE_PHASE_1: Phase 1 begins at task 1.1 (contract frozen and committed before adapter
    code) under the side-effect budget.
  HOLD: All phases 1-4 remain blocked; Phase 0 outputs stand as evidence.
selection_mode: OPEN
allowed_answer_domain: [AUTHORIZE_PHASE_1, HOLD]
continuation_after_each_answer:
  AUTHORIZE_PHASE_1: Executor verifies the new record's bound hashes against the current bundle,
    then executes Phase 1 only.
  HOLD: Nothing further executes; this skeleton and the inventory are retained as EVIDENCE.
```

## Adjudications reserved to the owner at this gate (not decisions that activate phases)

```yaml
- adjudication_field: BASELINE_ANOMALIES_DRIFT_COUNTING   # ADJ-1
  owner_adjudication: ________   # BLANK
  input: outputs/inventory/baseline-anomalies.md   # strict computed BASELINE_ANOMALIES = 3 (C-1, C-2, C-3 — the pre-declared known drift G-2/G-3)
  question: >-
    Do the three enumerated drift contradictions count toward BASELINE_ANOMALIES (gate stays
    BLOCKED), or are they adjudicated as reconciled by design.md File Changes ("Modify — extend
    existing conftest") so the count resolves to 0 (gate PASS)?
- adjudication_field: GITIGNORE_SCOPE_WIDENING            # ADJ-2 (optional, default no-change)
  owner_adjudication: ________   # BLANK
  input: outputs/inventory/hygiene-inventory.md sections 3-4 (G-4: .pi/; additionally observed: _ctx/)
  question: >-
    Beyond the spec-named .gitignore additions (.coverage, .mimosa/ — task 1.8), does the owner
    widen the R1 list to cover .pi/ and/or _ctx/, or do they remain out of R1 scope?
```

## Where the decisions are validly stated

Only in the owner-authored phase-approval record (durable, hash-bound, reviewer-verified, per
`APPROVAL-PHASE0.md` and the phase0-verification spec). This file records envelopes and remains
executor-authored evidence; it MUST NOT be edited into a decision record — any executor-entered
value in a `owner_decision`/`owner_adjudication` field above is invalid by construction.
