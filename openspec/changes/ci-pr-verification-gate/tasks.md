# Tasks: ci-pr-verification-gate — Clinical Compiler PR Verification CI

## Phase 1: Planning & Baseline (Completed in this Work Unit)

- [x] 1.1 Freeze repository baseline (`main@f8658a3`) and discover qualified environment versions (`uv 0.12.7`, `Python 3.11`).
- [x] 1.2 Establish SDD planning bundle in `openspec/changes/ci-pr-verification-gate/` (`proposal.md`, `design.md`, `tasks.md`).
- [x] 1.3 Verify that planning leaves working tree clean of workflow implementation (`.github/workflows/` untouched).

---

## Phase 2: Workflow Implementation (Completed)

- [x] 2.1 Create `.github/workflows/ci.yml` with top-level triggers (`pull_request`, `push` to `main`), `permissions: contents: read`, and concurrency group `${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}` (`cancel-in-progress: true`).
- [x] 2.2 Implement `governance` job:
  - Checkout with `fetch-depth: 0` and `persist-credentials: false` (`actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1` `# v7.0.1`)
  - Provenance log step echoing `PR_HEAD_SHA`, `BASE_SHA`, and `TESTED_REVISION` (or `COMMIT_SHA` on push)
  - PR-scoped diff checks (`if: github.event_name == 'pull_request'`):
    * `git diff --check "${{ github.event.pull_request.base.sha }}"...HEAD`
    * Archive immutability guard using `git diff --no-renames --diff-filter=MDT "${{ github.event.pull_request.base.sha }}"...HEAD -- openspec/changes/archive/`
- [x] 2.3 Implement `static` job:
  - Checkout with `persist-credentials: false` (`actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1` `# v7.0.1`)
  - Setup `astral-sh/setup-uv@c771a70e6277c0a99b617c7a806ffedaca235ff9` (`# v9.0.0`) with `version: "0.12.7"` and `python-version: "3.11"`
  - Deterministic lockfile sync: `uv sync --locked --python 3.11`
  - Lint check: `uv run --no-sync ruff check src tests`
  - Typecheck: `uv run --no-sync mypy --strict src`
- [x] 2.4 Implement `tests` job:
  - Checkout with `persist-credentials: false` (`actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1` `# v7.0.1`)
  - Setup `astral-sh/setup-uv@c771a70e6277c0a99b617c7a806ffedaca235ff9` (`# v9.0.0`) with `version: "0.12.7"` and `python-version: "3.11"`
  - Deterministic lockfile sync: `uv sync --locked --python 3.11`
  - Full test suite & branch coverage gate: `uv run --no-sync pytest -q`
  - CLI entrypoint smoke check: `uv run --no-sync clinical-compiler --help`
- [x] 2.5 Implement `gate` aggregate job:
  - `needs: [governance, static, tests]`
  - `if: always()`
  - Fail-closed evaluation: `test "$GOVERNANCE_RESULT" = "success" && test "$STATIC_RESULT" = "success" && test "$TESTS_RESULT" = "success"`

---

## Phase 3: Verification & Scenario Testing (Future Implementation Work Unit)

- [ ] 3.1 Validate `.github/workflows/ci.yml` syntax.
- [ ] 3.2 Verify archive guard against all 5 matrix scenarios (unmodified archive, added new archive, modified archive, deleted archive, moved archive).
- [ ] 3.3 Open PR on GitHub and verify live CI execution, parallel job execution, and provenance logging.
- [ ] 3.4 Verify stale run cancellation by pushing a second commit to the PR branch.

---

## Phase 4: Activation & Closure (Future Implementation Work Unit)

- [ ] 4.1 Update `docs/agent/RUNTIME.md` and `AGENTS.md` to document the live CI gate.
- [ ] 4.2 Record final execution receipt in `openspec/changes/ci-pr-verification-gate/` and transition status to `IMPLEMENTED — verified`.
