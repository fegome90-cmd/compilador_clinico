# Proposal: clinical-compiler R1 — Working, Contract-Governed Clinical Record Compiler

## Change Metadata

| Field | Value |
|-------|-------|
| Change ID | `clinical-compiler-r1` |
| Date | 2026-08-28 |
| Repository | `compilador_clinico` (baseline: single commit `c6578b6`) |
| Status | DRAFT — awaiting bundle approval |
| Decision Owner | Felipe Gonzalez (human) |
| Reviewer | Human-designated reviewer; MUST be distinct from the executor |
| Executor | SDD apply agent — blocked until the activation gate (see Approval & Activation) |
| Role | Scope + requested decision envelope |
| GOAL | Turn the committed, verified clinical core into a working contract-governed compiler: per-source clinical facts in → deterministic, fail-closed, fully traceable clinical document out |
| DONE WHEN | All eight Success Criteria gates are computed PASS at the final gate (Phase 4) with evidence recorded in the Final Receipt (tasks.md) — never asserted |
| Audience / execution target | `tasks.md` instructions target the SDD apply agent (executor) alone; approval sections target the decision owner and the reviewer; nothing in this bundle instructs clinicians or end users |
| not_role | The executor is never the approver, reviewer, clinical-policy author, or decision authority; the decision owner never executes |

Derivation chain — one authority per concern:

- `proposal.md` — scope and requested decision (this file)
- `design.md` — normative technical design (derives from this proposal)
- `tasks.md` — derived execution plan (derives from `design.md`)

`design.md` MUST NOT self-authorize execution. `tasks.md` MUST NOT redefine `design.md`. This proposal MUST NOT serve as its own approval record.

## Problem / Why

Clinicians capture patient state as telegraphic Spanish notes and machine readings scattered across sources: "TA 120/80" in a monitor note, "FC 72" from a monitor, lab results, clinical notes. Compiling those into one safe nursing record (e.g. mode `NURSING_RECORD_TELEGRAPHIC`) is done by hand or by lossy scripts that drop the three things that make a clinical document trustworthy: how certain each value is, whether a missing value was assessed-absent or never assessed, and where each value came from.

This repository has a committed, fully verified core that models exactly those three things — `ClinicalValue` (certainty + missingness + provenance), the IR ladder `SourceFactIR → CanonicalClinicalFact → DocumentIR`, an 8-code diagnostics taxonomy, and the policy veto hook `NEVER_AUTO_TERMS` — and nothing runnable around it. Every pass, the linter, the renderer, and all adapters are empty files. There is no way to feed clinical input in or get a compiled document out.

This change turns the core into a working compiler: a clinician provides raw per-source clinical facts and receives a deterministic compiled clinical document in which unassessed data stays explicitly `unknown` (never conflated with assessed absence), ambiguous input blocks with a diagnostic instead of guessing, vetoed terms are never auto-confirmed regardless of computed certainty, and every rendered value traces back to its sources.

## Current Baseline (verified 2026-08-28)

Verified by execution and inspection (exploration record: `sdd/clinical-compiler-r1/explore`):

- **Core is green:** 29/29 tests pass; 100% branch coverage of implemented core; `mypy --strict` clean; `ruff` clean. `core/types.py`, `core/ir.py`, `core/diagnostics.py`, `core/policy.py` complete, documented, annotated.
- **Scaffold is empty:** 11 zero-byte source files — the 4 passes (`input_validation`, `semantic_normalization`, `admissibility`, `document_selection`), `linter/conformance.py`, `renderers/deterministic.py`, plus `adapters/` (no Python at all, not a package).
- **No runtime glue:** no pipeline runner, no CLI, no `[project.scripts]`.
- **No test infrastructure:** no `conftest.py`, no `tests/fixtures/`, no golden files, no integration tests (inline literals only).
- **Docs empty:** `README.md` and `docs/architecture.md` are 0 bytes.
- **Known gaps:** `NEVER_AUTO_TERMS` is an empty frozenset; `TYPE_ERROR` and `PROVENANCE_ERROR` have no producing stage; `test_policy.py` contains a tautological test; `.gitignore` misses `.coverage` and `.mimosa/`; no CI.
- **Zero runtime dependencies** (dev-only: pytest, pytest-cov, ruff, mypy).

The core is existing baseline, not re-proposed: this change must not alter core signatures or semantics except additively, with recorded design justification.

## Goals

- Fill the scaffold: implement the 4 passes, `linter/conformance.py`, `renderers/deterministic.py`, and adapters, realizing the pipeline already implied by the diagnostics taxonomy (`INPUT_CONTRACT_ERROR`/`TYPE_ERROR` → `SEMANTIC_AMBIGUITY_BLOCK` → `POLICY_VIOLATION` → `DOCUMENT_SELECTION_ERROR` → `RENDER_ERROR` → `LINT_FAILURE`, with `PROVENANCE_ERROR` cross-cutting).
- Runtime glue: a pipeline runner composing the stages, plus a zero-dependency CLI entry point.
- Docs: `README.md` and `docs/architecture.md` describing the pipeline, contracts, and invariants.
- Preserve invariants: zero runtime dependencies; `mypy --strict`; branch coverage ≥ 95; deterministic byte-identical output; fail-closed diagnostics.
- Human-owned clinical policy: `NEVER_AUTO_TERMS` populated only from a decision-owner-approved seed.

## Non-Goals

- No rework or redesign of the committed core.
- No NLP/ML, no FHIR/HL7 integration, no network, no persistence/database, no GUI.
- No natural-language understanding beyond the bounded input contract selected at the Phase 0 gate.
- No CI pipeline (candidate for a separate change).

## Proposed Change

Execution is phased; each phase ends at a measured gate.

**Phase 0 — Read-only verification & inventory (first execution phase).** Strictly read-only under the side-effect budget below. Produces, under `openspec/changes/clinical-compiler-r1/outputs/inventory/`: (a) baseline verification — re-run tests/type/lint in the existing provisioned environment; compute `BASELINE_ANOMALIES` (`UNKNOWN` outcomes count as blocking anomalies — see Success Criteria); (b) input-contract dossier — evidence-based options (structured feed of source facts vs free-text telegraphic notes) with costs and risks, no silent selection; (c) policy-seed dossier — the format for `NEVER_AUTO_TERMS` candidates; the executor proposes structure only, never clinical content; (d) hygiene inventory — tautological test, orphan diagnostic codes, `.gitignore` gaps. Phase 0 ends by presenting the decision owner the complete decision envelope for: input-format selection, policy-seed approval or deferral, and Phase 1 authorization; the decisions themselves are stated by the owner in the owner-authored phase-approval record, never authored by the executor.

**Phase 1 — Input contract, adapters, input validation.** Freeze the input contract per the Phase 0 decision; implement the driving adapter(s) and `input_validation` (produces `INPUT_CONTRACT_ERROR`, `TYPE_ERROR`); add `conftest.py`, `tests/fixtures/`, and the first pipeline-path tests.

**Phase 2 — Semantic normalization + admissibility.** Certainty/missingness normalization (`SEMANTIC_AMBIGUITY_BLOCK`), policy enforcement (`POLICY_VIOLATION`) over the approved `NEVER_AUTO_TERMS` seed; produce `PROVENANCE_ERROR`; replace the tautological policy test with content-bearing, mutation-sensitive tests.

**Phase 3 — Document selection, deterministic renderer, conformance linter.** `DOCUMENT_SELECTION_ERROR`, `RENDER_ERROR`, `LINT_FAILURE`; golden files and the determinism hash gate.

**Phase 4 — Runner, CLI, docs.** Pipeline composition; strict exit-code mapping; `[project.scripts]` entry added to `pyproject.toml`; `README.md` + `docs/architecture.md`; final gates.

Exact module boundaries, adapter contracts, and the CLI surface are frozen in `design.md`, not here.

## Scope Boundaries

| Area | Impact |
|------|--------|
| `src/clinical_compiler/passes/`, `linter/`, `renderers/` | Implement empty modules |
| `src/clinical_compiler/adapters/` | New Python package (driving input adapter; output sink only if design requires) |
| Runner/CLI module (location frozen in `design.md`) | New |
| `tests/` (conftest, fixtures, golden files, integration) | New |
| `pyproject.toml` | `[project.scripts]` only — no dependency additions without admission |
| `README.md`, `docs/architecture.md`, `.gitignore` | Fill / append |
| `src/clinical_compiler/core/` | Frozen baseline; additive changes only, with recorded justification |

## Dependencies (Candidates)

**None proposed.** Preserving zero runtime dependencies is a stated goal; the CLI uses stdlib `argparse` as the working assumption (frozen in `design.md`). Any dependency later found necessary MUST be declared a candidate with an admission condition and approved by the decision owner before install — no implicit install authority exists in this change. Dev tooling (pytest, pytest-cov, ruff, mypy) is already pinned and unchanged.

## Side-Effect Budget (all phases)

**Prevention (allowlist).** Admissible: writing declared files inside the repository; running the existing provisioned toolchain (pytest, ruff, mypy) against it; read-only git and inspection commands. Prohibited in every phase: creating virtual environments; installing, upgrading, or uninstalling packages; writing outside the repository; starting or stopping any process, service, or daemon; network access. Phase 0 additionally prohibits any source-file mutation — observation only; if a verification command would require an environment change (e.g. a dependency sync), the outcome is recorded `UNKNOWN` (terminal), never achieved by installing — and an `UNKNOWN` outcome is gate-blocking (see Success Criteria: `UNKNOWN` can never yield a PASS).

**Detection (evidence).** Every phase captures before/after evidence: tracked-tree `git status`/`git diff`, `uv.lock` hash, installed-package listing, and a repository file manifest. Each evidence capture is stamped with a run ID (`clinical-compiler-r1/<phase>/<sequence>`) and a per-capture UTC timestamp (ISO-8601) — granularity is per capture, not per date — so repeated captures within one phase are orderable and attributable. A phase whose snapshots differ outside its declared writes fails the budget gate. Detection complements the allowlist; neither substitutes for the other.

## Risks / Unknowns

| Risk / Unknown | Severity | Mitigation / Decision path |
|----------------|----------|---------------------------|
| Input format undecided — free-text Spanish telegraphic notes vs structured feed (largest open question) | High | Decided by the decision owner at the Phase 0 gate from the input-contract dossier, presented as a complete fail-closed decision envelope (reason_for_block, question, options, option_effects, selection_mode, allowed_answer_domain, continuation_after_each_answer); never assumed by the executor. |
| Clinical policy content requires human judgment (`NEVER_AUTO_TERMS`) | High | Executor never authors policy entries. Phase 2 proceeds only with an owner-approved seed or an explicit recorded owner decision to ship R1 with the empty set. |
| Free-text parsing pulls toward NLP dependencies, breaking zero-dep + determinism | Med | Bounded telegraphic micro-grammar contract, or explicit deferral of free-text to R2 (frozen in `design.md`). |
| Determinism regressions (iteration order, locale/time leakage in renderer) | Med | Golden files plus the cross-run SHA-256 determinism gate (Success Criteria). |
| Vacuous coverage precedent (baseline tautology) | Med | Diagnostics-coverage gate and mutation-sensitive test criteria frozen in `tasks.md`. |

Open questions requiring human input, each with a stated decision path: (1) input format selection — Phase 0 dossier, owner decides at gate; (2) `NEVER_AUTO_TERMS` seed content, or explicit approval to ship empty in R1 — owner decides at gate; (3) CLI command name and surface — frozen in `design.md`, owner-reviewed at bundle approval. None is silently assumed.

## Success Criteria

Computed, never asserted; any BLOCKED gate enumerates its failures.

- [ ] **Phase 0 baseline gate:** compute `BASELINE_ANOMALIES` = number of Current Baseline claims contradicted by observation PLUS number of claims whose verification outcome is `UNKNOWN` (verification not runnable, evidence unobtainable — the claim is neither contradicted nor confirmed). `UNKNOWN` is a legitimate terminal observation state but is gate-BLOCKING: every `UNKNOWN` counts as an anomaly requiring owner adjudication and can never yield a PASS. `0` → PASS; `> 0` → BLOCKED with enumerated anomalies (contradictions and `UNKNOWN`s listed separately).
- [ ] **Phase 0 decision gate:** `INPUT_CONTRACT_DECISION` and the policy-seed status (`APPROVED` or `DEFERRED_BY_OWNER`) MUST be stated by the decision owner in the owner-authored phase-approval record, which MUST name the chosen input format and the seed decision; the executor prepares the decision dossier/record skeleton only — executor-authored decisions (with or without attribution) are invalid. Either owner-stated decision absent → BLOCKED.
- [ ] **Scaffold completion:** count zero-byte files under `src/clinical_compiler/{passes,linter,renderers,adapters}` after the final phase; `0` → PASS (each implemented, or removed by a recorded design decision).
- [ ] **Zero runtime dependencies:** parse `[project].dependencies` in `pyproject.toml` at the final gate; length `0` → PASS; `> 0` → PASS only if every entry appears in an admitted approval record.
- [ ] **Quality suite:** run `pytest`; `tests_failed == 0` AND measured branch coverage ≥ 95.0 → PASS. Run `mypy --strict` and `ruff check`; both exit `0` → PASS. Any non-zero → BLOCKED. (Recorded rationale for 95.0 vs the baseline core's 100%: R1 adds CLI, integration, subprocess, and defensive surfaces — e.g., the exit-70 catch-all and injected-IR fault paths — whose branches are not always reachable through public entry points; the frozen core keeps its own 100% standard, and raising the R1 target is an owner decision, never a silent one.)
- [ ] **Determinism:** compile an identical fixture set twice in fresh interpreters; SHA-256 of both outputs equal AND equal to the committed golden digest → PASS; mismatch → BLOCKED.
- [ ] **Fail-closed safety:** run the fault corpus (ambiguous terms, vetoed terms, missing provenance, contract violations — corpus frozen in `design.md`, not authored by the implementer); count of silently-accepted unsafe facts `== 0` AND every case yields its mapped `DiagnosticCode` → PASS; any silent acceptance → BLOCKED.
- [ ] **Diagnostics coverage:** count `DiagnosticCode` members with no producing stage and no covering test; `0` → PASS.

## Approval & Activation

```text
PHASE_0_STATUS = READY_FOR_HUMAN_APPROVAL
```

This proposal is not an approval record and cannot activate execution. There is exactly one activation gate: a durable approval record (e.g. `APPROVAL-PHASE0.md` in this change directory) that

1. binds the exact SHA-256 of every file in this bundle — `proposal.md`, `design.md`, `tasks.md`, and the seven domain specs (`specs/clinical-fact-model/spec.md`, `specs/phase0-verification/spec.md`, `specs/input-contract/spec.md`, `specs/pipeline-passes/spec.md`, `specs/diagnostics-policy/spec.md`, `specs/determinism-rendering/spec.md`, `specs/cli-surface/spec.md`) — as they stand at approval time, recorded either as the ten individual per-file SHA-256 digests or as a single bundle-manifest SHA-256 computed over the ordered concatenation of those ten digests (hash values are computed and recorded at approval time; nothing in this bundle pre-states them),
2. explicitly approves `PHASE_0` (and any later phase it authorizes, by name),
3. records Felipe Gonzalez as the approving decision owner,
4. is authored or verified by a reviewer role distinct from the executor, and
5. references a validation receipt — the contract-conformance audit of this bundle plus a post-repair bundle consistency check — performed on the exact hashes bound under (1); an unevidenced, self-asserted readiness status activates nothing (no unevidenced promotion).

The executor (SDD apply agent) remains blocked until that record exists and its bound hashes match the current bundle files. Acceptance of this proposal alone makes nothing executable: no artifact in this bundle becomes normative-for-execution without the phase-explicit, hash-bound record. A later phase activates only through the same mechanism — an updated durable record naming that phase — never by implication.
