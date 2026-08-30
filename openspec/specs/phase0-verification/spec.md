<!-- PROVENANCE
Domain: phase0-verification
Origin: delta spec of change `clinical-compiler-r1` — merged into the main spec on 2026-08-29 by the sdd-archive phase (artifact store: hybrid).
This was the FIRST population of openspec/specs/ (main specs were empty). Content below this comment is byte-faithful to the approved delta; its SHA-256 is recorded in the archived change state.yaml under bundle_hashes_sha256 (change now at openspec/changes/archive/2026-08-29-clinical-compiler-r1/).
-->
# Phase 0 Verification Specification

## Purpose

Phase 0 is the strictly read-only first execution phase: it re-verifies the baseline, produces evidence-based dossiers (input contract, policy seed format, hygiene inventory), and ends at a human decision gate. It selects nothing and mutates nothing. This domain also carries the hash-bound activation gate that governs every phase.

## Requirements

### Requirement: Read-Only Phase 0

Phase 0 MUST NOT mutate any source file; if a verification command would require an environment change (e.g. a dependency sync), the outcome SHALL be recorded `UNKNOWN` (terminal), never achieved by installing — and an `UNKNOWN` outcome is gate-blocking: it counts as an anomaly requiring owner adjudication and can never yield a gate PASS (see Baseline Verification Gate); prohibited actions (virtualenv creation, package install/upgrade/uninstall, writes outside the repository, starting/stopping processes or services, network access) SHALL NOT occur in any phase.

#### Scenario: No mutation outside declared writes

- GIVEN Phase 0 declared writes limited to `openspec/changes/clinical-compiler-r1/outputs/inventory/`
- WHEN before/after evidence (tracked-tree `git status`/`git diff`, `uv.lock` hash, installed-package listing, repository file manifest) is compared
- THEN the snapshots differ only within the declared writes

#### Scenario: Environment change required

- GIVEN a verification command that cannot run without installing something
- WHEN it is evaluated
- THEN its result is recorded `UNKNOWN`, no install occurs, and the `UNKNOWN` counts as a blocking anomaly in the Baseline Verification Gate

### Requirement: Baseline Verification Gate

Phase 0 SHALL re-run tests, type-check, and lint in the existing provisioned environment and compute `BASELINE_ANOMALIES` = number of Current Baseline claims contradicted by observation PLUS number of claims whose verification outcome is `UNKNOWN` (verification not runnable, evidence unobtainable — the claim is neither contradicted nor confirmed); every `UNKNOWN` is a blocking anomaly requiring owner adjudication — `UNKNOWN` is a legitimate terminal observation state but is never a PASS; `0` → PASS, `> 0` → BLOCKED with enumerated anomalies (contradictions and `UNKNOWN`s listed separately).

#### Scenario: Clean baseline

- GIVEN the repository at baseline commit `c6578b6`
- WHEN baseline verification runs
- THEN `BASELINE_ANOMALIES == 0` and the gate PASSES

#### Scenario: Contradicted claim

- GIVEN an observed result that contradicts a proposal baseline claim
- WHEN `BASELINE_ANOMALIES` is computed
- THEN the gate is BLOCKED and every anomaly is enumerated

#### Scenario: Unverifiable claim blocks the gate

- GIVEN a baseline claim whose verification cannot run (e.g. the command would require an install) or whose evidence is unobtainable
- WHEN `BASELINE_ANOMALIES` is computed
- THEN the claim counts as an `UNKNOWN` anomaly, the gate is BLOCKED with it enumerated for owner adjudication, and the gate never PASSES on an unverified claim

### Requirement: Evidence-Based Dossiers

Phase 0 SHALL produce under `outputs/inventory/` an input-contract dossier presenting structured feed vs free-text telegraphic notes with costs and risks as a complete fail-closed decision envelope (reason_for_block, question, options, option_effects, selection_mode, allowed_answer_domain, continuation_after_each_answer) — no executor selection and no ordering or framing that biases the choice — and a policy-seed dossier defining the candidate format for `NEVER_AUTO_TERMS` — structure only, never clinical content authored by the executor.

#### Scenario: Options without selection

- GIVEN the input-contract dossier
- WHEN it is inspected
- THEN both input options appear with costs and risks in the complete decision envelope, and no executor-made selection or biasing framing exists

#### Scenario: Structure-only policy dossier

- GIVEN the policy-seed dossier
- WHEN it is inspected
- THEN it defines the seed format and contains no clinical entries authored by the executor

### Requirement: Hygiene Inventory

Phase 0 SHALL record the hygiene findings: the tautological test in `test_policy.py`, the orphan diagnostic codes (`TYPE_ERROR`, `PROVENANCE_ERROR` with no producing stage), and the `.gitignore` gaps (`.coverage`, `.mimosa/`).

#### Scenario: Findings enumerated

- GIVEN Phase 0 completes
- WHEN the hygiene inventory is inspected
- THEN the tautological test, both orphan codes, and both `.gitignore` gaps are listed

### Requirement: Phase 0 Decision Gate

Phase 0 SHALL end by presenting the decision owner the complete decision envelope for: input-format selection, policy-seed approval or deferral, and Phase 1 authorization. The executor SHALL prepare `decision-gate.md` as a dossier and record SKELETON only (complete fail-closed envelope fields — reason_for_block, question, options, option_effects, selection_mode, allowed_answer_domain, continuation_after_each_answer — with every decision field left blank); the actual `INPUT_CONTRACT_DECISION` and the policy-seed status (`APPROVED` or `DEFERRED_BY_OWNER`) SHALL be stated by the decision owner in the owner-authored phase-approval record, which SHALL name the chosen input format and the seed decision. Executor-authored decisions — with or without attribution — are invalid; absence of either owner-stated decision → BLOCKED.

#### Scenario: Decisions recorded

- GIVEN Phase 0 outputs complete
- WHEN the decision gate is evaluated
- THEN `INPUT_CONTRACT_DECISION` and the policy-seed status are stated by the decision owner in the owner-authored approval record, naming the chosen input format and the seed decision

#### Scenario: Missing decision blocks

- GIVEN either owner-stated decision absent from the approval record
- WHEN the gate is evaluated
- THEN the gate is BLOCKED and Phase 1 does not execute

#### Scenario: Executor-authored decision is invalid

- GIVEN a `decision-gate.md` in which the executor filled the decision fields, even with decision-owner attribution
- WHEN the gate is evaluated
- THEN the gate is BLOCKED; only owner-stated decisions in the approval record count

### Requirement: Hash-Bound Activation Gate

Execution SHALL remain blocked until a durable approval record exists that binds the exact SHA-256 of every file in the bundle — `proposal.md`, `design.md`, `tasks.md`, and the seven domain specs (`specs/clinical-fact-model/spec.md`, `specs/phase0-verification/spec.md`, `specs/input-contract/spec.md`, `specs/pipeline-passes/spec.md`, `specs/diagnostics-policy/spec.md`, `specs/determinism-rendering/spec.md`, `specs/cli-surface/spec.md`) — as they stand at approval time, recorded either as the ten individual per-file SHA-256 digests or as a single bundle-manifest SHA-256 computed over the ordered concatenation of those ten digests; the record SHALL explicitly name the approved phase(s), record Felipe Gonzalez as the approving decision owner, reference a validation receipt — the contract-conformance audit of the bundle plus a post-repair consistency check — performed on the exact bound hashes, and be authored or verified by a reviewer distinct from the executor; a later phase activates only through an updated record naming it, never by implication.

#### Scenario: No record, no execution

- GIVEN no approval record whose hashes match the current bundle
- WHEN the executor attempts to start
- THEN execution is blocked

#### Scenario: Phase-explicit activation

- GIVEN an approval record whose hashes match the bundle and which names exactly `PHASE_0`
- WHEN phases are selected for execution
- THEN only `PHASE_0` is authorized; any later phase remains blocked

#### Scenario: Bundle drift invalidates the record

- GIVEN an approval record whose hashes matched at approval time
- WHEN any bound bundle file (including any domain spec) no longer matches its recorded hash
- THEN execution is blocked until a new record binds the current hashes

#### Scenario: Unevidenced readiness activates nothing

- GIVEN an approval record lacking the validation receipt for the exact bound hashes
- WHEN the executor attempts to start
- THEN execution is blocked; a self-asserted readiness status is not promotion evidence
