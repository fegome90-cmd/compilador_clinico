# Design: ci-pr-verification-gate — Clinical Compiler PR Verification CI

## 1. Architecture Overview

The PR Verification Gate is a single-file, multi-job GitHub Actions workflow (`.github/workflows/ci.yml`) providing parallelized, fail-closed validation of mechanical repository invariants without external dependencies or privileged permissions.

```text
                                  ┌───────────────────────────────────────────────┐
                                  │ governance                                    │
                                  │ - Checkout (fetch-depth: 0)                   │
                                  │ - Provenance log (PR_HEAD / BASE / TESTED)    │
                                  │ - if: pull_request:                           │
                                  │     * git diff --check                        │
                                  │     * archive guard (base.sha...HEAD)         │
                                  └──────────────────────┬────────────────────────┘
                                                         │
                                  ┌──────────────────────▼────────────────────────┐
                                  │ static                                        │
                                  │ - setup-uv (v9.0.0) + python (PR_GATE = 3.11) │
                                  │ - uv sync --locked                            │
┌────────────────────────┐        │ - uv run --no-sync ruff check src tests       │        ┌────────────────────────┐
│ Trigger:               │        │ - uv run --no-sync mypy --strict src          │        │ gate                   │
│ - pull_request (main)  ├───────►└──────────────────────┬────────────────────────┼───────►│ - needs: [all 3 jobs]  │
│ - push (main)          │                               │                                 │ - if: always()         │
└────────────────────────┘        ┌──────────────────────▼────────────────────────┐        │ - fail-closed:         │
                                  │ tests                                         │        │   test "$RESULT" ==    │
                                  │ - setup-uv (v9.0.0) + python (PR_GATE = 3.11) │        │   "success" for each   │
                                  │ - uv sync --locked                            │        └────────────────────────┘
                                  │ - uv run --no-sync pytest -q (cov >= 95%)     │
                                  │ - uv run --no-sync clinical-compiler --help   │
                                  └───────────────────────────────────────────────┘
```

---

## 2. Provenance & SHA Semantics

GitHub Actions exhibits distinct commit semantics depending on the triggering event. The CI provenance step explicitly distinguishes both event contexts:

### On `pull_request` Events:
| Identifier | Source / Variable | Description |
|---|---|---|
| `PR_HEAD_SHA` | `github.event.pull_request.head.sha` | The raw commit SHA authored on the feature branch. |
| `BASE_SHA` | `github.event.pull_request.base.sha` | Target branch tip (`origin/main`) against which the PR was evaluated. |
| `TESTED_REVISION` | `github.sha` (`refs/pull/:id/merge`) | The ephemeral synthetic merge commit tree tested by the runner. |

### On `push` Events (to `main`):
| Identifier | Source / Variable | Description |
|---|---|---|
| `COMMIT_SHA` | `github.sha` | The commit pushed to `main`. |
| `PREVIOUS_SHA` | `github.event.before` | The previous tip of `main`. |
| `TESTED_REVISION` | `github.sha` (`refs/heads/main`) | The exact commit tree on `main` tested by the runner. |

---

## 3. Workflow Configuration & Security Baseline

### Security Principles:
- **Zero Elevated Privileges:** Workflow-level `permissions: contents: read`. No write permissions, no ID token requests.
- **Immutable Action Pinning:** All third-party GitHub Actions are pinned to full verified 40-character commit SHAs with version comments:
  - `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1` (`# v7.0.1`)
  - `astral-sh/setup-uv@c771a70e6277c0a99b617c7a806ffedaca235ff9` (`# v9.0.0`)
- **Separation of Infrastructure and Toolchain:**
  - `setup-uv` version (`v9.0.0` / `c771a70e62...`) represents CI runner infrastructure.
  - `uv` version (`0.12.7`) represents the qualified repository toolchain.
- **No Repository Secrets:** No external tokens, API keys, or SaaS credentials are used or required.
- **No Privileged Execution of Untrusted PR Code:** PR code runs unprivileged (standard `pull_request` event, read-only `GITHUB_TOKEN`, and zero repository secrets). `persist-credentials: false` is enforced on all checkouts to remove Git credentials from the workspace. `pull_request_target` is strictly forbidden.

### Concurrency & Stale Run Cancellation:
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: true
```
This correctly handles both event types:
- `pull_request`: Evaluates to `${{ github.workflow }}-<PR_NUMBER>` (e.g. `ci-4`), cancelling stale runs when new commits are pushed to that PR.
- `push`: Evaluates to `${{ github.workflow }}-refs/heads/main`, cancelling superseded post-merge runs on rapid successive merges to `main`.

---

## 4. Job Specifications

### Job 1: `governance`
- **Runner:** `ubuntu-latest`
- **Purpose:** Fast repository-level structural integrity and historical immutability.
- **Steps:**
  1. `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1` with `fetch-depth: 0` and `persist-credentials: false` (full history for PR diffs).
  2. **Provenance Logging:** Echo `PR_HEAD_SHA`, `BASE_SHA`, and `TESTED_REVISION` (for PRs) or `COMMIT_SHA` (for pushes).
  3. **PR Diff Checks (`if: github.event_name == 'pull_request'`):**
     - **Diff Hygiene:** `git diff --check "${{ github.event.pull_request.base.sha }}"...HEAD`
     - **Archive Immutability Guard:**
       ```bash
       VIOLATIONS=$(git diff --no-renames --diff-filter=MDT --name-only "${{ github.event.pull_request.base.sha }}"...HEAD -- openspec/changes/archive/)
       if [ -n "$VIOLATIONS" ]; then
         echo "::error::Historical archive files were modified, deleted, or replaced:"
         echo "$VIOLATIONS"
         exit 1
       fi
       ```

### Job 2: `static`
- **Runner:** `ubuntu-latest`
- **Purpose:** Static type safety and stylistic conformance.
- **Steps:**
  1. `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1` with `persist-credentials: false` (shallow checkout).
  2. `astral-sh/setup-uv@c771a70e6277c0a99b617c7a806ffedaca235ff9` with `version: "0.12.7"`, `enable-cache: true`.
  3. **Deterministic Sync:** `uv sync --locked --python 3.11` (fails immediately on `pyproject.toml` ↔ `uv.lock` drift).
  4. **Linting:** `uv run --no-sync ruff check src tests`.
  5. **Type Checking:** `uv run --no-sync mypy --strict src`.

### Job 3: `tests`
- **Runner:** `ubuntu-latest`
- **Purpose:** Full test suite execution, branch coverage enforcement, and CLI sanity.
- **Steps:**
  1. `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1` with `persist-credentials: false`.
  2. `astral-sh/setup-uv@c771a70e6277c0a99b617c7a806ffedaca235ff9` with `version: "0.12.7"`, `enable-cache: true`.
  3. **Deterministic Sync:** `uv sync --locked --python 3.11`.
  4. **Unit & Integration Tests:** `uv run --no-sync pytest -q`
     - Note: `pyproject.toml` injects `addopts = "--cov=clinical_compiler --cov-report=term-missing --strict-markers"` and `fail_under = 95`. A single run of `pytest -q` evaluates the entire test suite and enforces `>= 95%` branch coverage fail-closed.
  5. **CLI Smoke Check:** `uv run --no-sync clinical-compiler --help` (verifies entrypoint parsing and clean exit 0).

### Job 4: `gate`
- **Runner:** `ubuntu-latest`
- **Purpose:** Single aggregate branch-protection anchor with fail-closed result validation.
- **Needs:** `[governance, static, tests]`
- **Condition:** `if: always()`
- **Implementation:**
  ```yaml
  gate:
    name: gate
    if: always()
    needs:
      - governance
      - static
      - tests
    runs-on: ubuntu-latest
    steps:
      - name: Require all verification jobs
        env:
          GOVERNANCE_RESULT: ${{ needs.governance.result }}
          STATIC_RESULT: ${{ needs.static.result }}
          TESTS_RESULT: ${{ needs.tests.result }}
        run: |
          echo "Evaluating upstream job results:"
          echo "governance: $GOVERNANCE_RESULT"
          echo "static:     $STATIC_RESULT"
          echo "tests:      $TESTS_RESULT"
          test "$GOVERNANCE_RESULT" = "success"
          test "$STATIC_RESULT" = "success"
          test "$TESTS_RESULT" = "success"
  ```

---

## 5. Historical Archive Guard Specification

The invariant rule is:
> Existing historical archive content (`openspec/changes/archive/`) is immutable, but creating a new legitimate archive (`sdd-archive`) must remain permitted.

### Guard Behavioral Matrix:

| Scenario | Git Diff Status | `--diff-filter=MDT` Match | Outcome |
|---|---|---|---|
| Existing archive file unmodified | Clean | No matches | **PASS** |
| New archive directory & files added | `A` (Added) | Ignored by `MDT` | **PASS** |
| Existing archive file modified | `M` (Modified) | Matched | **FAIL** (Exit 1) |
| Existing archive file deleted | `D` (Deleted) | Matched | **FAIL** (Exit 1) |
| Historical file renamed/moved | `D` (at old path) + `A` (at new path) via `--no-renames` | Matched (`D`) | **FAIL** (Exit 1) |
| Historical file replaced with symlink | `T` (Type change) | Matched | **FAIL** (Exit 1) |

---

## 6. Proposed Branch Protection Policy

Once the CI workflow is verified on a test PR, the following branch protection rule is recommended for `main`:

- **Target branch:** `main`
- **Require a pull request before merging:** Yes (minimum approvals: 1 or 0 for solo maintainer).
- **Require status checks to pass before merging:**
  - Status check name: `gate`
  - Require branches to be up to date before merging: **Strict** (guarantees that CI green always reflects tested evidence against current `main` in a fail-closed clinical compiler; can be relaxed to Loose with evidence if PR concurrency increases).
- **Require conversation resolution:** Yes.
- **Do not allow bypassing:** Yes.
- **Block force pushes and deletions:** Yes.

---

## 7. Toolchain Baseline & ACS Disposition

- **Python Floor (`PR_GATE_PYTHON`):** Python `3.11` (enforcing the minimum supported environment declared in `pyproject.toml` and `mypy` configuration).
- **Agent Context System (ACS):** The ACS verification script (`validate_agent_context.py`) depends on host environment paths (`$HOME/.claude/skills/agent-context-system`). It remains an agent-side preflight verification tool and is **not** introduced as a GitHub Actions runner dependency.
