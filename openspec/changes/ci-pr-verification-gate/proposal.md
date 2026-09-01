# Proposal: ci-pr-verification-gate — Clinical Compiler PR Verification CI

## Change Metadata

| Field | Value |
|-------|-------|
| Change ID | `ci-pr-verification-gate` |
| Date | 2026-09-01 |
| Repository | `compilador_clinico` |
| Base | `main@f8658a3` (post-PR #3 baseline) |
| Status | IMPLEMENTED — CI verified / activation pending |
| Decision Owner | Felipe Gonzalez (human) |
| Reviewer | Human-designated reviewer; MUST be distinct from executor |
| Lineage | `PR #1 (R1 Core) → PR #2 (ACS v1.1) → PR #3 (Permutation Invariance) → PR Verification CI Gate (this proposal)` |
| Scope | `.github/workflows/ci.yml`, `tests/unit/test_ir.py` (bounded Python-3.11 repair), `openspec/changes/ci-pr-verification-gate/`, documentation |
| Non-Scope | Application code changes, new runtime dependencies, deployment/release pipelines, multi-Python PR matrices, external bot requirements, ACS host vendoring |

## Problem / Why

Recent PR reviews, especially PR #3, required manual reconciliation and presented friction points:

1. **Verification Provenance:** Pre-merge confidence currently relies on human/agent text reports of local test runs (e.g. `629 passed`, `99.80% cov`, `ruff PASS`, `mypy PASS`). GitHub itself exhibits zero native workflow execution runs (`GitHub Actions CI = NOT CONFIGURED`). Reviews must explicitly distinguish local executor claims from independent, durable CI evidence bound to the tested revision.
2. **Serial Discovery of Mechanical Defects:** Without parallelized CI feedback, defects in style, types, or tests are discovered sequentially during local developer preflights.
3. **Historical Archive Immutability:** The repository invariant that historical R1 bundles (`openspec/changes/archive/2026-08-29-clinical-compiler-r1/`) are immutable currently depends on ad-hoc diff checks (`git diff ...`) rather than an automated, fail-closed gate.

## Proposed Change

Design and introduce a minimal, single-file GitHub Actions workflow (`.github/workflows/ci.yml`) providing automated, parallel verification on every pull request and push to `main`:

```text
                    ┌──► governance (archive guard, diff check) ──┐
[PR / Push to main] ┼──► static (ruff check, mypy --strict) ──────┼──► gate (CI / gate)
                    └──► tests (pytest + coverage >=95%, smoke) ──┘
```

### Core Characteristics:
- **Parallel Feedback:** Independent jobs for `governance`, `static`, and `tests` surface all mechanical failures simultaneously.
- **Single Aggregate Gate:** A lightweight `gate` job acts as the sole required branch protection status check (`gate` or `CI / gate`).
- **Reproducible Toolchain:** Pinned `uv` (`0.12.7`) via verified `astral-sh/setup-uv` (`v9.0.0`) with `uv sync --locked` and `uv run --no-sync` matching `RUNTIME.md`.
- **Generalized Archive Guard:** Uses Git diff filters (`git diff --no-renames --diff-filter=MDT`) on both PRs and pushes to `main` to block any modification or deletion of existing archive files while permitting legitimate new archive additions.
- **Zero Runtime Bloat:** Introduces zero runtime dependencies, zero external bot dependencies, and zero SaaS telemetry.
- **Explicit Provenance:** Emits clear logs distinguishing `PR_HEAD_SHA`, `BASE_SHA`, and the actual `TESTED_REVISION` (`refs/pull/:id/merge` on PR, commit on push).

## Scope Boundaries

| Area | Impact | Disposition |
|------|--------|-------------|
| `.github/workflows/ci.yml` | NEW | Minimal 4-job single-file workflow |
| `src/clinical_compiler/` | NO CHANGE | Zero production code modifications permitted |
| `tests/unit/test_ir.py` | MODIFIED (bounded exception) | Bounded Python-3.11 compatibility repair required to execute the existing representation-contract assertion on `PR_GATE_PYTHON`. No production semantics changed. |
| Other `tests/` | NO CHANGE | Existing test suite is canonical and unchanged |
| `pyproject.toml` / `uv.lock` | NO CHANGE | Existing dependencies and configs are sufficient |
| `openspec/specs/` | NO CHANGE | Normative domain specs unchanged |
| `openspec/changes/archive/` | NO CHANGE | Fully protected by the new archive guard |
| `openspec/changes/ci-pr-verification-gate/` | NEW | SDD proposal, design, and tasks |
| `docs/agent/RUNTIME.md`, `AGENTS.md` | MODIFIED | Documentation of live CI gate and verification contract |

## Explicit Non-Goals (Anti-Ferrari Principle)

1. **No matrix explosion in PR gate:** PR gate runs on the minimum supported floor (`PR_GATE_PYTHON = 3.11` on Ubuntu). Compatibility matrices across Python 3.12/3.13/3.14 or multi-OS are deferred to an optional weekly workflow.
2. **No external review bots required:** Verification relies purely on standard GitHub Actions runners; no third-party review bots (CodeRabbit, Greptile, etc.) are mandatory for correctness.
3. **No ACS vendoring in CI:** Agent Context System (ACS) validation remains a local agent-side tool and is not converted into an undeclared CI dependency.
4. **No deployment/release automation:** Packaging, Docker builds, PyPI publishing, and deployment infrastructure are strictly out of scope.

## Success Criteria (Acceptance Criteria)

- **AC1 (Automated Verification):** Every PR revision and push to `main` triggers automated verification.
- **AC2 (Provenance Clarity):** CI logs clearly report `PR_HEAD_SHA`, `BASE_SHA`, and `TESTED_REVISION` without conflation.
- **AC3 (Parallel Feedback):** Ruff, mypy, and pytest execute in parallel jobs and report failures independently.
- **AC4 (Coverage Gate):** Pytest enforces branch coverage `>= 95%` (fail-under gate in `pyproject.toml`).
- **AC5 (Lockfile Integrity):** `uv sync --locked` fails if `pyproject.toml` and `uv.lock` drift.
- **AC6 (Archive Immutability):** Modifications or deletions of existing `openspec/changes/archive/` files fail the `governance` job on both PRs and pushes to `main`.
- **AC7 (Archive Extensibility):** Addition of new archive directories in `openspec/changes/archive/` is permitted and passes.
- **AC8 (Least Privilege):** Workflow uses strict `permissions: contents: read` and `persist-credentials: false`.
- **AC9 (Concurrency Control):** Superseded PR runs are automatically cancelled via `concurrency: cancel-in-progress: true`.
- **AC10 (Single Required Check & Fail-Closed Gate):** A single aggregate job (`gate`) serves as the branch protection contract; it evaluates upstream job results explicitly and fails if any required job is not `success` (including failures, cancellations, or skips under `if: always()`).
- **AC11 (Self-Contained):** No external third-party bot or secrets required.
- **AC12 (ACS Boundary):** ACS tooling is not required by GitHub Actions.
- **AC13 (Zero Runtime Deps):** No application dependencies added.
- **AC14 (Maintainability):** Complete workflow is contained in a single well-documented YAML file under 150 lines.
- **AC15 (Diff Hygiene):** Whitespace corruption or merge-conflict markers fail the `governance` job via `git diff --check` on both PRs and pushes to `main`.

## Risks & Mitigations

- **Risk:** Stale CI runs burning compute on rapid push iterations.
  **Mitigation:** `concurrency` group with `cancel-in-progress: true`.
- **Risk:** GitHub Actions checking out ephemeral merge commits causing confusion with raw PR branch SHAs.
  **Mitigation:** Explicit provenance logging in the `governance` step outputting both `github.event.pull_request.head.sha` and the tested commit.
- **Risk:** Archive guard breaking legitimate future archiving operations (`sdd-archive`).
  **Mitigation:** `--diff-filter=MDT` strictly filters Modified, Deleted, and Type-changed files, ignoring Added (`A`) files.
