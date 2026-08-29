# Phase 0 — BEFORE Evidence

Change: `clinical-compiler-r1` | Phase: 0 (read-only verification & inventory)
Declared writes for this phase: `openspec/changes/clinical-compiler-r1/outputs/inventory/` only.
Baseline commit: `c6578b6` (verified below: HEAD == c6578b6).
Tooling note: `uv 0.11.2 (Homebrew 2026-03-26 aarch64-apple-darwin)`. No `uv sync` was executed anywhere in this phase; every `uv run` uses `--no-sync`.

## Run IDs and UTC timestamps (per capture)

| Run ID | Capture | UTC timestamp (ISO-8601) |
|---|---|---|
| `clinical-compiler-r1/0/01` | tracked-tree `git status` (long + porcelain) | 2026-08-29T13:14:29Z |
| `clinical-compiler-r1/0/02` | tracked-tree `git diff` (vs HEAD `c6578b6`; `--stat` + full) | 2026-08-29T13:14:29Z |
| `clinical-compiler-r1/0/03` | `uv.lock` SHA-256 + uv version note | 2026-08-29T13:15:05Z |
| `clinical-compiler-r1/0/04` | installed-package listing (venv site-packages) | 2026-08-29T13:15:05Z |
| `clinical-compiler-r1/0/05` | repository file manifest (SHA-256 per file) | 2026-08-29T13:15:20Z |

## 1. Tracked-tree git status (run 0/01)

```text
On branch main
Your branch is up to date with 'origin/main'.

Changes not staged for commit:
	modified:   pyproject.toml
	modified:   tests/unit/test_ir.py

Untracked files:
	.coverage
	.mimosa/
	.pi/
	_ctx/
	openspec/
	tests/conftest.py

no changes added to commit (use "git add" and/or "git commit -a" -a)
```

Porcelain:

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

Note: the `git status` long-form output above normalizes the "use git add" hint lines; the
porcelain form is byte-exact from the run. HEAD confirmed by `git log --oneline -3` (run 0/02):
`c6578b6 feat: scaffold clinical record compiler with typed core and test suite` (single commit; `main`).

## 2. Tracked-tree git diff vs `c6578b6` (run 0/02)

`git diff --stat`:

```text
 pyproject.toml        |  7 ++++++-
 tests/unit/test_ir.py | 38 ++++++++++++++++----------------------
 2 files changed, 22 insertions(+), 23 deletions(-)
```

Full diff (verbatim):

```diff
diff --git a/pyproject.toml b/pyproject.toml
index f49fc10..acbde79 100644
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -25,7 +25,12 @@ clinical_compiler = ["py.typed"]
 [tool.pytest.ini_options]
 testpaths = ["tests"]
 pythonpath = ["src"]
-addopts = "--cov=clinical_compiler --cov-report=term-missing"
+addopts = "--cov=clinical_compiler --cov-report=term-missing --strict-markers"
+markers = [
+    "unit: fast isolated unit tests",
+    "integration: tests exercising multiple components together",
+    "slow: tests that take significant time",
+]
 
 [tool.coverage.run]
 branch = true
diff --git a/tests/unit/test_ir.py b/tests/unit/test_ir.py
index fc65d94..8051ae6 100644
+++ b/tests/unit/test_ir.py
--- b/tests/unit/test_ir.py
+++ b/tests/unit/test_ir.py
@@ -1,5 +1,6 @@
 # tests/unit/test_ir.py
 
+from collections.abc import Callable
 from dataclasses import FrozenInstanceError
 
 import pytest
@@ -10,12 +11,7 @@ from clinical_compiler.core.ir import (
     DocumentIR,
     SourceFactIR,
 )
-from clinical_compiler.core.types import (
-    Certainty,
-    ClinicalValue,
-    Missingness,
-    Provenance,
-)
+from clinical_compiler.core.types import Certainty, ClinicalValue, Provenance
 
 
 def test_document_ir_references_facts_instead_of_storing_values() -> None:
@@ -33,19 +29,11 @@ def test_document_ir_references_facts_instead_of_storing_values() -> None:
     assert document.entries[0].clinical_fact_ref == "fact-001"
 
 
-def make_clinical_value() -> ClinicalValue:
-    """Build a representative clinical value for IR tests."""
-    return ClinicalValue(
-        value="72 bpm",
-        certainty=Certainty.PROBABLE,
-        missingness=Missingness.PRESENT,
-        provenance=Provenance(source_kind="monitor", source_ref="m-9"),
-    )
-
-
-def test_source_fact_ir_keeps_raw_value_and_provenance() -> None:
+def test_source_fact_ir_keeps_raw_value_and_provenance(
+    make_provenance: Callable[..., Provenance],
+) -> None:
     """SourceFactIR preserves the raw value and its attribution."""
-    provenance = Provenance(source_kind="clinical_note", source_ref="note-3")
+    provenance = make_provenance(source_kind="clinical_note", source_ref="note-3")
     source_fact = SourceFactIR(
         fact_id="raw-1",
         field_id="heart_rate",
@@ -56,19 +44,23 @@ def test_source_fact_ir_keeps_raw_value_and_provenance() -> None:
     assert source_fact.provenance is provenance
 
 
-def test_source_fact_ir_is_immutable() -> None:
+def test_source_fact_ir_is_immutable(
+    make_provenance: Callable[..., Provenance],
+) -> None:
     """SourceFactIR mutation is rejected by the frozen contract."""
     source_fact = SourceFactIR(
         fact_id="raw-1",
         field_id="heart_rate",
         raw_value="FC 72",
-        provenance=Provenance(source_kind="monitor", source_ref="m-9"),
+        provenance=make_provenance(),
     )
     with pytest.raises(FrozenInstanceError):
         source_fact.raw_value = "FC 80"  # type: ignore[misc]
 
 
-def test_canonical_fact_references_its_source_facts() -> None:
+def test_canonical_fact_references_its_source_facts(
+    make_clinical_value: Callable[..., ClinicalValue],
+) -> None:
     """CanonicalClinicalFact lists the source facts supporting it."""
     canonical = CanonicalClinicalFact(
         clinical_fact_id="fact-001",
@@ -80,7 +72,9 @@ def test_canonical_fact_references_its_source_facts() -> None:
     assert canonical.value.certainty is Certainty.PROBABLE
 
 
-def test_canonical_fact_is_immutable() -> None:
+def test_canonical_fact_is_immutable(
+    make_clinical_value: Callable[..., ClinicalValue],
+) -> None:
     """CanonicalClinicalFact mutation is rejected by the frozen contract."""
     canonical = CanonicalClinicalFact(
         clinical_fact_id="fact-001",
```

Drift interpretation (facts only, no adjudication): the two tracked modifications are
test-infrastructure changes (pytest markers registration + refactor of `test_ir.py` onto the
untracked `tests/conftest.py` factories). No runtime dependency, `[project.scripts]`, or core
source change is present in the diff.

## 3. `uv.lock` SHA-256 (run 0/03)

```text
0f53bca908037d7b249b3a3e07b31e766b09be1dc16156c8b8a5804254f6d7a1  uv.lock
```

`uv.lock` size: 132973 bytes. uv version note: `uv 0.11.2`.

## 4. Installed-package listing (run 0/04)

Method: read-only directory listing of the provisioned venv site-packages
(`eza -1 .venv/lib/python*/site-packages`, sorted). Direct venv-query commands (e.g.
`uv pip list`) are outside this phase's command allowlist; the directory listing is the
equivalent evidence obtained with allowlisted tools. Distributions present (name-version from
`dist-info`):

```text
ast_serialize-0.8.0
clinical_record_compiler-0.1.0        (editable local project: __editable__.clinical_record_compiler-0.1.0.pth)
coverage-7.15.4
iniconfig-2.3.0
librt-0.15.0
mypy-2.3.1
mypy_extensions-1.1.0
packaging-26.3
pathspec-1.1.1
pluggy-1.6.0
pygments-2.21.0
pytest-9.1.1
pytest_cov-7.1.0
ruff-0.16.5
typing_extensions-4.16.0
```

Plus runtime plumbing (`_pytest`, `coverage`, `mypy`, `mypyc`, `ruff`, `pluggy`, `py.py`,
`ast_serialize`, `librt`, `pygments`, `pathspec`, `packaging`, `iniconfig`, `typing_extensions`,
`__pycache__`, `_virtualenv.pth`, `a1_coverage.pth`, `08ae81f72d5a2b5fa9e0__mypyc.cpython-314-darwin.so`).
Interpreter: CPython 3.14 (pyc tags `cpython-314`). This matches the dev-only dependency group
(pytest, pytest-cov, ruff, mypy + transitive) with the project installed editable. No
non-dev distributions are present.

## 5. Repository file manifest (run 0/05)

Method: `fd . --type f --exclude .git --exclude .venv -j 1 -x shasum -a 256 {}` from the repo
root, sorted. `fd` is gitignore-aware: gitignored caches (`__pycache__/`, `.pytest_cache/`,
`.mypy_cache/`, `.ruff_cache/`, `*.egg-info/`, `.atl/`, `.venv/`) are excluded from the listing
by the same rules git applies; `.git` and `.venv` excluded explicitly. 49 files listed.

```text
5cde62f4c1b5f7f3ab8a59c9865ec87177c6e26928c0bd29ba327feb4df2933f  ./_ctx/telemetry/events.jsonl
03ff243703cbc0ca171e60c9180f0bda6cef18f93f72cc13d6a2629b19c52533  ./_ctx/telemetry/last_run.json
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  ./docs/architecture.md
adee99ca83fae5e424f4b119ab399ea144454f8b811465e3c6882455a8d64051  ./openspec/changes/clinical-compiler-r1/APPROVAL-PHASE0.md
75335698149cee43243c2db6ef45d6d716c07de6dd60903fc19ac5ed45c7d9ef  ./openspec/changes/clinical-compiler-r1/design.md
04ed8dafa60d85a15b693de984984eed1845c5d96643c0de20b79e99814dd840  ./openspec/changes/clinical-compiler-r1/proposal.md
580b1d2a0d20c4a9582b1451ba5e4f469622364ab70aee7a9a598c1e7a48f1cc  ./openspec/changes/clinical-compiler-r1/specs/cli-surface/spec.md
90ab38d41ad7112a1dfca1186d8e160d35bddec01f11c00820f49b530d392e54  ./openspec/changes/clinical-compiler-r1/specs/clinical-fact-model/spec.md
3a09007bad60e639d9ebdeee60b0379af4927e94d099d98b489dbd8229ad9c78  ./openspec/changes/clinical-compiler-r1/specs/determinism-rendering/spec.md
ee9852b388cef55dfac37fef0ffca931795cb13eb0ca2871be28094397f50f23  ./openspec/changes/clinical-compiler-r1/specs/diagnostics-policy/spec.md
7ffd272d5182ef5b09e13a9fb08bef75bfd310481c002d37c7f7f8a0930fdd7a  ./openspec/changes/clinical-compiler-r1/specs/input-contract/spec.md
f0314a15a3dee6c78f4b56519520a82d3148f5fd519b40d2dbd4ca137b991600  ./openspec/changes/clinical-compiler-r1/specs/phase0-verification/spec.md
0aa5627c3e73e8d034dcb41510f720bb14adb4757fe06689873f72eca0036147  ./openspec/changes/clinical-compiler-r1/specs/pipeline-passes/spec.md
425e122badf87a6e003d939792731c55c003047a92b4eb936abe5d62b394ddce  ./openspec/changes/clinical-compiler-r1/state.yaml
086e7884d4904f15900bb76af18500467ed44a29d724a5d11c109ba231cd9f0f  ./openspec/changes/clinical-compiler-r1/tasks.md
0c5be35575497dd4ecc49894a3a34a4bf900b4df11eac54cb620a64e3b903e4f  ./openspec/config.yaml
fe219fc26a84ae3a9f072e50a9126579d32498f09a81dcf0fee834c1e63ab06b  ./openspec/contracts/clinical-compiler-handoff-drive-mirror-20260828/ai-work-agent-execution-contract-0.3.md
b27a17e3d26b565bbb4d769d3445a77e36bc7654f55a8ba0f59a1ad782771d57  ./openspec/contracts/clinical-compiler-handoff-drive-mirror-20260828/BOOTSTRAP.md
6474d07f095c96eebc01104f061d5f7b548d80d33343bdc43b50db758d07ed62  ./openspec/contracts/clinical-compiler-handoff-drive-mirror-20260828/EXPORT_SHA256SUMS.txt
60effd508fa259011ba7c496c80d2f10c08ec6176a241869af2f547188e2665e  ./openspec/contracts/clinical-compiler-handoff-drive-mirror-20260828/hybrid-agent-method-1.1-rc2.md
0f8afdbf9ccfbb67ae469ce9119240af2d6e9696248028a401800c80145dcf71  ./openspec/contracts/clinical-compiler-handoff-drive-mirror-20260828/INDEX.md
8679d8b566857f1db5dddcf20af520026acf598e7d56ef780a82a94ed679339d  ./openspec/contracts/clinical-compiler-handoff-drive-mirror-20260828/MIRROR_MANIFEST.md
54de7ba643cfb236dcde997866472511091e84f6adcde0398f51bd82f69edd35  ./openspec/contracts/clinical-compiler-handoff-drive-mirror-20260828/README.md
b1dad5e9ebd9efcca2ebc31bc6cd2f80b51ebbc1349673d39ce6a56f24a4bd1f  ./openspec/contracts/clinical-compiler-handoff-drive-mirror-20260828/SCHEMA.md
d75554cd7cc6332712495c19577e8f76c8e739fc59ca91187d0dcbcae3320915  ./pyproject.toml
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  ./README.md
5f734f702f35872714f8266a306c9edaa7fc001a6595307eb51998b537515c69  ./src/clinical_compiler/__init__.py
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  ./src/clinical_compiler/adapters/README.md
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  ./src/clinical_compiler/core/__init__.py
60c81842d5b5c513ffa7b08ae79c2504aba9f6e8e74061c56833ff3a8dc033d6  ./src/clinical_compiler/core/diagnostics.py
978289748b3701156f16bc3d2a75a7f4f1f87b589c729c1ce478e4931e910a25  ./src/clinical_compiler/core/ir.py
fdd620ef2fa98eab05bd6619693d8e9d69822828860531ecf6e868e260486d64  ./src/clinical_compiler/core/policy.py
caa23180361d464010c68c68f5f04aa239dda8aa0959e4980cf543283a241499  ./src/clinical_compiler/core/types.py
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  ./src/clinical_compiler/linter/__init__.py
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  ./src/clinical_compiler/linter/conformance.py
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  ./src/clinical_compiler/passes/__init__.py
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  ./src/clinical_compiler/passes/admissibility.py
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  ./src/clinical_compiler/passes/document_selection.py
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  ./src/clinical_compiler/passes/input_validation.py
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  ./src/clinical_compiler/passes/semantic_normalization.py
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  ./src/clinical_compiler/py.typed
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  ./src/clinical_compiler/renderers/__init__.py
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  ./src/clinical_compiler/renderers/deterministic.py
a4684250040d4bef194a5238c840caf00598cc16febf237d618c96663e8f56e8  ./tests/conftest.py
525b035f0aef945ab3b0bb599a726941b6ac98d6b90b39df36f55761c6f09c59  ./tests/unit/test_diagnostics.py
34fd0fa5055d5091e1705ffcb6225932881680069f99d6bc2677e8846176f6cd  ./tests/unit/test_ir.py
be5d3ba436c0f713958950ede666e688dbcf57d440aa0b7eb6a1a07c3c0dc403  ./tests/unit/test_policy.py
c8dae8799e408b8680d707b72065be96d98e18f9db9b0152d26c3a163a284c12  ./tests/unit/test_types.py
0f53bca908037d7b249b3a3e07b31e766b09be1dc16156c8b8a5804254f6d7a1  ./uv.lock
```

Transcription note: every line whose digest is
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` is the SHA-256 of a
zero-byte file (that digest is the standard empty-file digest).

Notable BEFORE-state facts (fed into `baseline-anomalies.md`):
- `tests/conftest.py` EXISTS (untracked; 51 lines; `make_provenance` + `make_clinical_value` factories).
- `tests/fixtures/` and `tests/golden/` EXIST as empty directories (not listed by `fd --type f` because they contain no files).
- `pyproject.toml` and `tests/unit/test_ir.py` are modified vs `c6578b6` (diff in section 2).
- Untracked non-repo dirs: `.mimosa/`, `.pi/`, `_ctx/` (AI-runtime artifacts; `_ctx/telemetry/` files listed above), plus `.coverage` (53 KB data file from the 2026-08-28 baseline verification run, NOT gitignored).
- `openspec/` (this change directory) is itself untracked.

## Side-effect prevention measures for the verification runs (declared up front)

The three verification commands (runs 0/06-0/08) are executed with cache/write-suppression so
that tool caches do not mutate anything outside the declared writes. None of these changes the
semantic result of a command (they only suppress speed caches / redirect the coverage data file):

- `PYTHONDONTWRITEBYTECODE=1` — no `.pyc` writes anywhere.
- `COVERAGE_FILE=<repo>/openspec/changes/clinical-compiler-r1/outputs/inventory/.coverage-run-0-06` — coverage data written INSIDE the declared writes; the pre-existing root `.coverage` (baseline artifact of 2026-08-28) is neither overwritten nor deleted.
- pytest `-p no:cacheprovider` — no `.pytest_cache` writes.
- mypy `--cache-dir=/dev/null` — no `.mypy_cache` writes.
- ruff `--no-cache` — no `.ruff_cache` writes.
