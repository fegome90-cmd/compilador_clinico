# R1 Baseline Freeze

## Scope and authority

This document is the Etapa 0 evidence ledger for the documentation-only change
`clinical-kernel-preparation`. It freezes the live checkout and records bounded
evidence; it does not authorize a kernel move, a refactor, or a runtime change.
The code and current specifications remain the ground truth for R1 behavior.
`docs/agent/ARCHITECTURE.md` remains the architecture authority and
`openspec/specs/` remains the normative behavior authority.

Evidence labels are typed as follows:

- **Observed** — directly read from the live checkout or produced by a command
  run against this checkout.
- **Computed** — deterministically derived from observed bytes, hashes, or
  bounded static analysis.
- **Pending** — not run, unavailable, or not sufficient to establish the
  claim; historical logs never substitute for a live gate.

No golden, fixture, source, test, cache, or environment file was regenerated.

## Frozen live identity

The identity check ran before any documentation write at
`2026-09-07T10:50:13Z` UTC:

| Field | Required value | Result | Provenance |
|---|---|---|---|
| Branch | `codex/wo-001-clinical-kernel-preparation` | **Computed — matched** | `git branch --show-current`, exit 0 |
| Commit | `729134461850a17d240327fb5d8243c9e77f976d` | **Computed — matched** | `git rev-parse HEAD`, exit 0 |
| Tree | `1dbc33ee1ffc2dc08498a53a1044a13211c7a078` | **Computed — matched** | `git rev-parse HEAD^{tree}`, exit 0 |

The exact pre-write command also reported `git status --short
--untracked-files=all`, exit 0, with only the four active OpenSpec artifacts
under `openspec/changes/clinical-kernel-preparation/`; `git diff --name-status`,
exit 0, was empty. Those workspace artifacts are an overlay and are not part
of the frozen committed tree.

The archived reference `c6578b685c9dd66bba8958f75749e0d02c061ed1` with tree
`94b213e0ecb99f4c3083984b35f5fe75d67b814b` is historical provenance only. It is
not a substitute for the live baseline.

## Seven non-negotiable R1 invariants

These are compatibility invariants, grouped so the UAPI and its purity, and
the R1 contract and mode scope, remain explicit:

1. **Composition/UAPI:** `CompileRequest` and `CompileResult` remain the
   pipeline boundary, and pure `pipeline.run()` remains the composition root.
2. **Core leaf:** `src/clinical_compiler/core/` remains immutable-domain,
   stdlib-only, and free of imports from outer compiler layers.
3. **R1 input/mode boundary:** `adapters.contract.CONTRACT` admits exactly
   `FC` and `TA`, and `NURSING_RECORD_TELEGRAPHIC` is the only mode.
4. **Fail-closed diagnostics:** all R1 diagnostic categories are blocking;
   any accumulated diagnostic suppresses document emission.
5. **Atomic output:** file output uses a same-directory temporary file,
   flush/fsync, `os.replace`, and parent-directory fsync; failed writes do not
   expose a partial destination.
6. **Byte determinism:** output is UTF-8 and LF-only, has no trailing
   whitespace and one final newline, and uses explicit codepoint ordering.
7. **Runtime closure:** the compiler has no network, database, daemon,
   subprocess, or third-party runtime dependency.

## Golden manifest and scenario anchors

The committed manifest bytes were hashed read-only at
`2026-09-07T10:52:45Z` UTC:

| Manifest | SHA-256 | Integrity status |
|---|---|---|
| `tests/golden/manifest.json` | `669e6f72fa48e50ab42d8b37993bdf77f81a0e940b868f7b8b0b07a7490d6ae9` | Parent implementation corpus: `DEGRADED` by manifest rule |
| `tests/golden/independent/MANIFEST.json` | `1d0b40bad026970a456d810a336da04d0f2307b72b791b9b75697893df151ffa` | Independent corpus: `VALID` by manifest record |

The scenario digests below are the manifest-owned anchors. The parent
implementation documents are explicitly `DEGRADED` because they are
implementation-generated; the independent expected documents are `VALID` by
the independent manifest. `sha256sum` recomputed the listed bytes and exited
0; no golden regeneration occurred.

| Scenario | Input SHA-256 | Implementation document SHA-256 | Independent expected SHA-256 | Evidence integrity |
|---|---|---|---|---|
| `pc1_unassessed_fc` | `d3e4206b6b15bdd9ab32131dca26542104e29ed6941e04a25df1bd07e1864b05` | `31d58796158fc876dc49434008586788938b0d9b5b46a9368ab37aac7ccddb99` | `31d58796158fc876dc49434008586788938b0d9b5b46a9368ab37aac7ccddb99` | parent `DEGRADED`; independent `VALID` |
| `pc2_assessed_absence_ta` | `4af7f05b14487d1e9184c1d7e5fb9f54cfe4abe0ad82b91d42ed162a3c61071d` | `6387f1afe79e6c20ec6f828e323ff45ea9c46207cea7f0e7327b4ca604dad909` | `6387f1afe79e6c20ec6f828e323ff45ea9c46207cea7f0e7327b4ca604dad909` | parent `DEGRADED`; independent `VALID` |
| `standard_mixed` | `f66cbe51ebdb435bb4ca5a3ba9e63e1c8595593b65f591781052470d67eb1b9c` | `e7b5b03fa6d9f150c081684846fb481b7dfda02ebdd24992a7fba164c88b8abc` | `e7b5b03fa6d9f150c081684846fb481b7dfda02ebdd24992a7fba164c88b8abc` | parent `DEGRADED`; independent `VALID` |

The three anchors preserve the R1 distinctions: unassessed FC, assessed
absence TA, and a mixed fact-backed document. Digest equality is not a claim
that the independent corpus was regenerated or re-derived in this batch.

## Typed evidence matrix

| ID | Invariant or gate | Status | Subject | Source / command | Result and provenance |
|---|---|---|---|---|---|
| E-01 | Baseline identity | **Computed** | Live branch, commit, tree | Git identity command at `2026-09-07T10:50:13Z` | All three required values matched; no substituted historical identity. |
| E-02 | `CompileRequest` / `CompileResult` UAPI | **Observed** | `src/clinical_compiler/pipeline.py:112-184` | Source readback and introspection at `2026-09-07T10:52:57Z` | Frozen dataclasses expose the request/result boundary; result construction forbids document-plus-diagnostics. |
| E-03 | Pure `pipeline.run` | **Observed** | `src/clinical_compiler/pipeline.py:222-306` | Source readback | Fixed stage order, diagnostic accumulation, and no I/O imports are present; runtime behavior is covered by the live test run below. |
| E-04 | Stdlib-only core leaf | **Computed** | `src/clinical_compiler/core/*.py` | AST/source scan at `2026-09-07T10:52:45Z` | 22 source files parsed; core imports are stdlib plus the permitted intra-core `.types`; no forbidden runtime imports found. |
| E-05 | FC/TA-only `CONTRACT` | **Observed** | `src/clinical_compiler/adapters/contract.py:65-70` | Readback and introspection at `2026-09-07T10:52:57Z` | `contract_fields=['FC', 'TA']`. |
| E-06 | One document mode | **Observed** | `src/clinical_compiler/passes/document_selection.py:81-83` | Readback and introspection at `2026-09-07T10:52:57Z` | `supported_modes=('NURSING_RECORD_TELEGRAPHIC',)`. |
| E-07 | Blocking diagnostics and fail-closed emission | **Observed** | `pipeline.py:171-184,273-306`; `core/diagnostics.py` | Source readback; live tests | Any diagnostic returns `document=None`; diagnostic taxonomy has eight codes. |
| E-08 | Atomic output | **Observed** | `src/clinical_compiler/cli.py:184-212` | Source readback | Same-directory temp, flush/fsync, `os.replace`, directory fsync, and cleanup on failure are implemented. |
| E-09 | Byte determinism | **Observed** | Renderer/linter and golden anchors | Source readback plus live full test run | Current code and the live tests cover UTF-8/LF, canonical ordering, glyph rules, and linter independence; no goldens were rewritten. |
| E-10 | No network/DB/daemon/runtime dependencies | **Computed** | Source tree and `pyproject.toml` | AST/source scan at `2026-09-07T10:52:45Z` | `forbidden_runtime_imports=NONE`; `project_dependencies=[]`. This is bounded source/config evidence, not a deployment audit. |
| E-11 | Fast test gate | **Observed** | Current checkout | `uv run --no-sync pytest -p no:cacheprovider -q` at `10:51:21Z–10:51:22Z`, exit 0 | 629 passed; the project `addopts` also reported 99.80% branch coverage. |
| E-12 | Explicit coverage gate | **Observed** | Current checkout | `uv run --no-sync pytest -p no:cacheprovider --cov=clinical_compiler --cov-report=term-missing --strict-markers` at `10:51:32Z–10:51:33Z`, exit 0 | 629 passed; 99.80% total branch coverage; required 95.0% reached. Coverage emitted one non-failing `module-not-measured` warning. |
| E-13 | Strict typing | **Observed** | `src/` | `uv run --no-sync mypy --cache-dir=/dev/null --strict src` at `10:51:41Z`, exit 0 | `Success: no issues found in 22 source files`. |
| E-14 | Lint | **Observed** | `src/`, `tests/` | Valid command `uv run --no-sync ruff check --no-cache src tests` at `10:51:58Z`, exit 0 | `All checks passed!` |
| E-15 | Structural readback and exact scope guard | **Observed** | Active OpenSpec change plus documentation outputs | `PYTHONDONTWRITEBYTECODE=1 python3` readback at `10:58:33Z`, exit 0; `git diff --check`, exit 0 | Exactly eight authorized paths were present; canonical docs matched original bytes plus the two approved cross-reference suffixes; forbidden paths were unchanged. |
| E-16 | CI/remote gate and branch-protection readback | **Pending** | External GitHub state | Not run in this bounded local batch | Historical archive logs are not promoted to a live PASS. |

The first literal Ruff ordering attempt,
`uv run --no-sync ruff --no-cache check src tests`, exited 2 at
`2026-09-07T10:51:47Z` because this installed Ruff exposes `--no-cache` under
the `check` subcommand. The valid cache-suppressed command above was then run
once and exited 0; this is recorded as a CLI-shape correction, not a code
failure.

## Cache, environment, and mutation boundary

The checks used `PYTHONDONTWRITEBYTECODE=1`, `UV_NO_CACHE=1`,
`pytest -p no:cacheprovider`, a `COVERAGE_FILE` under a temporary `/tmp`
directory that was removed after each run, `mypy --cache-dir=/dev/null`, and
`ruff check --no-cache`. No install or sync was requested.

The repository `.coverage` file was present before and after the checks with
size `77824` and SHA-256
`553c380651788100ae435933902c52735bcbc2f258b5b6d430be50aaa35f5ec3`; the
repository `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, and 37 `__pycache__`
directories were present both before and after. The known repository state
therefore preserved the pre-existing coverage and cache artifacts. External
tool-manager state was not independently audited and is **Pending**.

## TDD applicability and boundaries

Strict TDD is configured true for the project, but this batch contains only
documentation artifacts and cross-reference lines. No production or test
behavior was designed or authorized, so no RED/GREEN/REFACTOR source cycle was
run. Any later runtime change must re-enter through its own approved change
and TDD evidence.

Rollback is limited to removing this document and
`ARCHITECTURE_DEBT_MAP.md`, reverting the two cross-reference additions, and
leaving source, tests, fixtures, runtime, configuration, dependencies,
normative specs, archive records, and roadmap inputs untouched.
