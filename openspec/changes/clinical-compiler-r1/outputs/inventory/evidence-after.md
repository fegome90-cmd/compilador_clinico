# Phase 0 — AFTER Evidence & Side-Effect Budget Gate (Task 0.8)

Change: `clinical-compiler-r1` | Same four artifacts as task 0.1, captured after all Phase 0 work.
Head for run IDs: `clinical-compiler-r1/0/<sequence>`.

## Run IDs and UTC timestamps (per capture)

| Run ID | Capture | UTC timestamp (ISO-8601) |
|---|---|---|
| `clinical-compiler-r1/0/09` | tracked-tree `git status` + `git diff` | 2026-08-29T13:22:36Z |
| `clinical-compiler-r1/0/10` | `uv.lock` SHA-256 | 2026-08-29T13:22:37Z |
| `clinical-compiler-r1/0/11` | installed-package listing (site-packages) | 2026-08-29T13:22:37Z |
| `clinical-compiler-r1/0/12` | repository file manifest (SHA-256 per file) | 2026-08-29T13:22:49Z |
| `clinical-compiler-r1/0/13` | hidden-path verification (`.coverage` mtime/hash, outputs listing, dot-dirs mtimes, `.gitignore`) | 2026-08-29T13:23:19Z |
| `clinical-compiler-r1/0/14` | site-packages BEFORE/AFTER line-diff | 2026-08-29T13:23:40Z |

## 1. Tracked-tree git status / git diff AFTER (run 0/09)

Identical to BEFORE (run 0/01) — same two tracked modifications, same untracked set:

```text
 M pyproject.toml
 M tests/unit/test_ir.py
?? .coverage
?? .mimosa/
?? .pi/
?? _ctx/
?? openspec/
?? tests/conftest.py
```

`git diff --stat` identical to run 0/02 (2 files, +22/−23 — the pre-existing drift, nothing new);
`git diff` output 105 lines, matching the BEFORE diff byte-for-byte in structure and content.
No tracked file changed during Phase 0. (`openspec/` was already untracked as a whole, so the
new `outputs/` files add no porcelain line.)

## 2. `uv.lock` SHA-256 AFTER (run 0/10)

```text
0f53bca908037d7b249b3a3e07b31e766b09be1dc16156c8b8a5804254f6d7a1  uv.lock
```

**Identical to BEFORE** — the environment was not synced/re-resolved by any command
(`--no-sync` everywhere; no `uv sync`, no `uv add`, no installs).

## 3. Installed-package listing AFTER (runs 0/11 + 0/14)

Sorted site-packages listing (38 entries) hashed `eb1dd6f2c97edcadd29e6dcd0669069977253d4306a8999bd84fbea09ab8ab56`;
explicit line-diff against the BEFORE listing (verbatim in `evidence-before.md` section 4):
**diff EMPTY, 38 = 38 lines — IDENTICAL**. No package was installed, upgraded, or removed.

## 4. Repository file manifest AFTER (run 0/12)

Method identical to BEFORE (`fd . --type f --exclude .git --exclude .venv -j 1 -x shasum -a 256`,
sorted; fd is gitignore-aware and — as documented for BEFORE — skips hidden/dot paths, whose
coverage is provided by items 1 and 5 below). Full listing captured at run 0/12; count 57 files
(BEFORE: 49).

**Comparison (hash-for-hash over the union of both manifests):**

- Every file present in the BEFORE manifest is present AFTER with the **identical SHA-256**
  (checked entry-by-entry, including `_ctx/telemetry/*`, `pyproject.toml`, `tests/*`,
  `src/**`, `openspec/**` bundle files — the ten bound bundle files still carry exactly the
  APPROVAL-PHASE0 hashes).
- Files added (8 visible + 1 hidden), ALL inside the declared writes
  `openspec/changes/clinical-compiler-r1/outputs/inventory/`:

| Added file | SHA-256 (from run 0/12) |
|---|---|
| `outputs/inventory/baseline-anomalies.md` | `d77d1206fa84922c96458b19fd9194d2b1d66ba5bf4fc37d8a68f5b07179e1c2` |
| `outputs/inventory/baseline-verification.md` | `ef1317b3d01b5ed702cd19b4df4b1d17dd626293524d9f8cdd924f9ef2fc8a01` |
| `outputs/inventory/decision-gate.md` | `8ecd6535be15507df497a2b7d1b500afbcf2344c93c7fbdb770f13eb80478058` |
| `outputs/inventory/evidence-before.md` | `17d9a9e95497d2cd200b5c674cd69fd367ee201f5f2e83231f7474902b78fac9` (pre-0/12 state) |
| `outputs/inventory/hygiene-inventory.md` | `dad159726687964e8c7671ecd7d17fefc2b5e521aecd44640bd1a506448e81fb` |
| `outputs/inventory/input-contract-dossier.md` | `45f68b0d98682edacab50588bca8edc3d098d278829ec2761a93045ea57905b9` |
| `outputs/inventory/policy-seed-dossier.md` | `ed290d7cd6a09365749e17bc967dd1b37f6f7ecd7c8404a4b487a87a2911d629` |
| `outputs/inventory/scaffold-inventory.md` | `ab199de92a4c8ec0c6086bb9430d7d0394f6107479c1f196ac798f76d6ff0be6` |
| `outputs/inventory/.coverage-run-0-06` (hidden; dot-file, excluded from fd manifest) | coverage data of run 0/06, redirected here by design (see below) |

- `evidence-before.md`'s own hash changed between run 0/12 and this file's authorship only in
  the sense that it was finalized before run 0/06 executed (it is itself a declared write);
  no non-declared path changed.

- Files REMOVED or MODIFIED outside the declared writes: **NONE**.

## 5. Hidden-path verification (run 0/13)

`fd`'s manifest skips dot-paths; these were verified explicitly:

| Path | BEFORE state | AFTER state | Verdict |
|---|---|---|---|
| `.coverage` (root) | 53k, mtime 2026-08-28 07:57 | 53k, mtime 2026-08-28 07:57 (sha `f5c7be7b…`) | **UNTOUCHED** — the pre-existing baseline artifact was preserved by the `COVERAGE_FILE` redirect; run 0/06's data went to `outputs/inventory/.coverage-run-0-06` (inside declared writes) |
| `.mimosa/` | mtime 2026-08-28 07:29 | mtime 2026-08-28 07:29 | unchanged |
| `.pi/` | mtime 2026-08-28 07:29 | mtime 2026-08-28 07:29 | unchanged |
| `.atl/` | mtime 2026-08-28 06:24 | mtime 2026-08-28 06:24 | unchanged |
| `.gitignore` (tracked) | tracked at `c6578b6` | `git diff` empty (0 lines); sha `0ab5af7c…` | unchanged |
| `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `__pycache__/` | pre-existing (2026-08-28) | not written this phase (`-p no:cacheprovider`, `--cache-dir=/dev/null`, `--no-cache`, `PYTHONDONTWRITEBYTECODE=1`) | unchanged |
| `.venv/` | provisioned env | site-packages identical (item 3); `uv.lock` identical (item 2) | **environment unmutated** |

## Side-effect budget gate (computed)

```text
tracked-tree diff (git status/diff)  : IDENTICAL before/after           -> clean
uv.lock hash                         : IDENTICAL (0f53bca9…)            -> clean
installed packages                   : IDENTICAL (38 = 38, empty diff)  -> clean
repository file manifest             : +9 files, ALL inside outputs/inventory/; 0 removals, 0 external modifications -> clean
processes started/stopped            : none (pytest/mypy/ruff ran to completion as allowlisted verification commands)
network access                       : none
installs/syncs/venv creation         : none (uv run --no-sync exclusively; uv 0.11.2)
commits/branches                     : none
source/test/tooling mutations        : none (read-only phase respected)

BUDGET GATE: PASS — snapshots differ ONLY within the declared writes
              openspec/changes/clinical-compiler-r1/outputs/inventory/
```

## Command log (every command executed this phase, allowlisted set)

Read-only inspection / evidence: `eza` listings (repo, src/tests/docs trees, site-packages,
outputs, dot-dirs); `fd` file enumerations (manifests, structure checks); `shasum -a 256`
(bundle precondition: 10 files + ordered concatenation manifest; uv.lock; per-file manifests;
.coverage; .gitignore; site-packages listing); `wc` (byte/line counts); `rg` (TYPE_ERROR /
PROVENANCE_ERROR producer search, manifest line location); `git status`, `git diff`,
`git log`, `git show` (HEAD confirmation); `date -u` (per-capture UTC timestamps — required by
the tasks.md evidence spec; read-only clock read, disclosed here); `uv --version` (version note,
launcher-sanctioned). File contents were additionally read via the Read tool (reads only).

Verification commands (tasks 0.2, all `uv run --no-sync`, with the declared cache-suppression
env/flags): `pytest -p no:cacheprovider` (+`COVERAGE_FILE` redirect into declared writes),
`mypy --cache-dir=/dev/null src`, `ruff check --no-cache src tests` — exits 0/0/0.

Writes performed (all inside `openspec/changes/clinical-compiler-r1/outputs/inventory/`):
the nine files listed in item 4. Nothing else was written, moved, or deleted. `state.yaml`,
`tasks.md`, and every bound bundle file are bit-identical to their APPROVAL-PHASE0 hashes.
