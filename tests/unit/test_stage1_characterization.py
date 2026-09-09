"""Independent Stage 1 characterization over the frozen R1 seams."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import pytest

from clinical_compiler import pipeline
from clinical_compiler.adapters.seed import (
    DEFERRED_BY_OWNER_DECISION,
    PolicyResolution,
    approved_empty_by_deferral,
    load_policy_seed,
)
from clinical_compiler.core.diagnostics import Diagnostic, DiagnosticCode
from clinical_compiler.passes.document_selection import NURSING_RECORD_TELEGRAPHIC
from clinical_compiler.pipeline import CompileRequest, derive_exit_code
from clinical_compiler.pipeline_types import StageResult

pytestmark = pytest.mark.integration
ROOT: Final[Path] = Path(__file__).resolve().parents[2]
SRC: Final[Path] = ROOT / "src"
GOLDEN: Final[Path] = ROOT / "tests" / "golden"
POLICY_SEED: Final[Path] = ROOT / "tests" / "fixtures" / "policy-seed-sample.json"
EXPECTED_BRANCH: Final[str] = "codex/wo-001-clinical-kernel-preparation"
R1_BASELINE_COMMIT: Final[str] = "729134461850a17d240327fb5d8243c9e77f976d"
R1_PROTECTED_PATHS: Final[tuple[str, ...]] = ("src/clinical_compiler",)
STAGE1_ALLOWED_PATHS: Final[frozenset[str]] = frozenset(
    {
        "tests/unit/test_stage1_characterization.py",
        "tests/unit/test_architecture_gates.py",
        "tests/golden/manifest.json",
        "tests/golden/independent/MANIFEST.json",
        "docs/agent/ARCHITECTURE.md",
        "openspec/changes/clinical-kernel-stage1-characterization/tasks.md",
    }
)
CONTEXT: Final[dict[str, str]] = {
    "document_mode": "NURSING_RECORD_TELEGRAPHIC",
    "policy": "DEFERRED_BY_OWNER_DECISION",
}


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, check=False, text=True
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _r1_production_subject_is_unchanged() -> bool:
    diff = subprocess.run(
        ["git", "diff", "--quiet", R1_BASELINE_COMMIT, "--", *R1_PROTECTED_PATHS],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "--", *R1_PROTECTED_PATHS],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    assert diff.returncode in (0, 1), diff.stderr
    assert status.returncode == 0, status.stderr
    return diff.returncode == 0 and status.stdout == ""


def test_stage1_identity_and_scope_guard() -> None:
    """Bind Stage 1 to the R1 production subject, not repository HEAD."""
    assert _git("branch", "--show-current") == EXPECTED_BRANCH
    assert _r1_production_subject_is_unchanged()
    assert tuple(sorted(STAGE1_ALLOWED_PATHS)) == (
        "docs/agent/ARCHITECTURE.md",
        "openspec/changes/clinical-kernel-stage1-characterization/tasks.md",
        "tests/golden/independent/MANIFEST.json",
        "tests/golden/manifest.json",
        "tests/unit/test_architecture_gates.py",
        "tests/unit/test_stage1_characterization.py",
    )


def _manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _context(manifest: dict[str, Any]) -> dict[str, str]:
    assert "compile_context" in manifest, "C1 missing compile_context"
    assert manifest["compile_context"] == CONTEXT, "C1 conflicting compile_context"
    return CONTEXT


def _policy() -> PolicyResolution:
    return approved_empty_by_deferral(DEFERRED_BY_OWNER_DECISION)


def test_compile_context_metadata_is_explicit_and_identical() -> None:
    parent = _manifest(GOLDEN / "manifest.json")
    independent = _manifest(GOLDEN / "independent" / "MANIFEST.json")
    assert _context(parent) == _context(independent)


def test_c1_independent_expected_bytes_match_pipeline_and_digest() -> None:
    parent = _manifest(GOLDEN / "manifest.json")
    independent = _manifest(GOLDEN / "independent" / "MANIFEST.json")
    mode = _context(independent)["document_mode"]
    names = tuple(sorted(str(row["name"]) for row in parent["scenarios"]))
    assert tuple(sorted(str(row["name"]) for row in independent["scenarios"])) == names
    for row in sorted(independent["scenarios"], key=lambda item: item["name"]):
        data = (GOLDEN / str(row["input"])).read_bytes()
        expected = (GOLDEN / str(row["document"])).read_bytes()
        assert hashlib.sha256(data).hexdigest() == row["input_sha256"]
        assert hashlib.sha256(expected).hexdigest() == row["sha256"]
        result = pipeline.run(CompileRequest(data, mode, _policy()))
        assert result.diagnostics == (), row["name"]
        assert result.document is not None
        assert result.document == expected
        assert hashlib.sha256(result.document).hexdigest() == row["sha256"]


def test_c1_missing_compile_context_fails_closed_with_named_scenario(
    tmp_path: Path,
) -> None:
    invalid_manifest = _manifest(GOLDEN / "independent" / "MANIFEST.json")
    del invalid_manifest["compile_context"]
    manifest_path = tmp_path / "MANIFEST.json"
    manifest_path.write_text(json.dumps(invalid_manifest), encoding="utf-8")

    with pytest.raises(AssertionError, match="C1 missing compile_context"):
        _context(_manifest(manifest_path))


def test_c1_conflicting_document_mode_fails_closed_with_named_scenario(
    tmp_path: Path,
) -> None:
    conflicting_manifest = _manifest(GOLDEN / "independent" / "MANIFEST.json")
    conflicting_context = dict(conflicting_manifest["compile_context"])
    conflicting_context["document_mode"] = "SOME_OTHER_MODE"
    conflicting_manifest["compile_context"] = conflicting_context
    manifest_path = tmp_path / "MANIFEST.json"
    manifest_path.write_text(json.dumps(conflicting_manifest), encoding="utf-8")

    with pytest.raises(AssertionError, match="C1 conflicting compile_context"):
        _context(_manifest(manifest_path))


def _line(value: object) -> bytes:
    return (json.dumps(value) + "\n").encode("utf-8")


def _feed(*values: object) -> bytes:
    return b"".join(_line(value) for value in values)


def _record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "fact_id": "raw-1",
        "field_id": "FC",
        "raw_value": 72,
        "provenance": {"source_kind": "monitor", "source_ref": "m-9"},
    }
    record.update(overrides)
    return record


@dataclass(frozen=True, slots=True)
class FaultOracleCase:
    name: str
    data: bytes
    policy: PolicyResolution
    codes: tuple[DiagnosticCode, ...]
    exit_code: int
    injection: str | None = None
    document_is_none: bool = True


P = _policy()
SP = load_policy_seed(POLICY_SEED)
C = DiagnosticCode
CLEAN = _feed(
    _record(fact_id="std-fc-1", raw_value=80.5),
    _record(fact_id="std-ta-1", field_id="TA", raw_value="120/80"),
)


def _fault(
    name: str,
    data: bytes,
    codes: tuple[DiagnosticCode, ...],
    exit_code: int,
    policy: PolicyResolution = P,
    injection: str | None = None,
) -> FaultOracleCase:
    return FaultOracleCase(name, data, policy, codes, exit_code, injection)


_C2: Final[tuple[FaultOracleCase, ...]] = (
    _fault("FC-01", _line({"fact_id": "raw-1", "raw_value": 72}), (C.INPUT_CONTRACT_ERROR, C.DOCUMENT_SELECTION_ERROR), 3),
    _fault("FC-02", _line(_record(x_priority="high")), (C.INPUT_CONTRACT_ERROR, C.DOCUMENT_SELECTION_ERROR), 3),
    _fault("FC-03 array", _line([_record()]), (C.INPUT_CONTRACT_ERROR, C.DOCUMENT_SELECTION_ERROR), 3),
    _fault("FC-03 UTF-8", b"\xff\xfe not utf-8", (C.INPUT_CONTRACT_ERROR, C.DOCUMENT_SELECTION_ERROR), 3),
    _fault("FC-05 bool", _line(_record(raw_value=True)), (C.TYPE_ERROR, C.DOCUMENT_SELECTION_ERROR), 4),
    _fault("FC-06 conflict", _feed(_record(fact_id="fc-a"), _record(fact_id="fc-b", raw_value=80)), (C.SEMANTIC_AMBIGUITY_BLOCK, C.SEMANTIC_AMBIGUITY_BLOCK, C.DOCUMENT_SELECTION_ERROR), 5),
    _fault("FC-07 policy", _line(_record(fact_id="ta-vetoed", field_id="TA", raw_value="TA: test-veto-term-alpha de noche")), (C.POLICY_VIOLATION, C.DOCUMENT_SELECTION_ERROR), 6, SP),
    _fault("FC-09 empty", b"", (C.DOCUMENT_SELECTION_ERROR,), 8),
    _fault("P1-1 fact_id", _line(_record(fact_id="")), (C.INPUT_CONTRACT_ERROR, C.DOCUMENT_SELECTION_ERROR), 3),
    _fault("P1-1 source_ref", _line(_record(provenance={"source_kind": "monitor", "source_ref": ""})), (C.INPUT_CONTRACT_ERROR, C.DOCUMENT_SELECTION_ERROR), 3),
    _fault("multi-diagnostic", _feed(_record(fact_id="bad-type", raw_value=True), _record(fact_id="fc-a"), _record(fact_id="fc-b", raw_value=80)), (C.TYPE_ERROR, C.SEMANTIC_AMBIGUITY_BLOCK, C.SEMANTIC_AMBIGUITY_BLOCK, C.DOCUMENT_SELECTION_ERROR), 4),
    _fault("quarantined survivor", _feed(_record(fact_id="raw-bad", x_priority="high"), _record(fact_id="raw-ok")), (C.INPUT_CONTRACT_ERROR,), 3),
    _fault("FC-10 render", CLEAN, (C.RENDER_ERROR,), 9, injection="render"),
    _fault("FC-11 lint", CLEAN, (C.LINT_FAILURE,), 10, injection="lint"),
)


def _stage_fault(code: DiagnosticCode) -> Any:
    return lambda *_args: StageResult(
        admitted=(), diagnostics=(Diagnostic(code, "injected"),)
    )


@pytest.mark.parametrize("case", _C2, ids=lambda case: case.name)
def test_c2_fault_oracle_matches_exact_order_nullness_and_exit(
    case: FaultOracleCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    if case.injection is not None:
        attr = {"render": "render_document", "lint": "lint_conformance"}[case.injection]
        code = {"render": C.RENDER_ERROR, "lint": C.LINT_FAILURE}[case.injection]
        monkeypatch.setattr(pipeline, attr, _stage_fault(code))
    result = pipeline.run(
        CompileRequest(case.data, NURSING_RECORD_TELEGRAPHIC, case.policy)
    )
    assert tuple(diagnostic.code for diagnostic in result.diagnostics) == case.codes
    assert (result.document is None) == case.document_is_none
    assert derive_exit_code(result.diagnostics) == case.exit_code


_C3: Final[tuple[tuple[str, bytes], ...]] = (
    ("clean", CLEAN),
    ("fault", _feed(_record(fact_id="fc-a"), _record(fact_id="fc-b", raw_value=80))),
)
CHILD = f"""
import hashlib, json, sys
sys.path.insert(0, {json.dumps(str(SRC))})
from clinical_compiler.adapters.seed import DEFERRED_BY_OWNER_DECISION, approved_empty_by_deferral
from clinical_compiler.adapters.structured_feed import parse_feed
from clinical_compiler.passes.admissibility import run_admissibility
from clinical_compiler.passes.input_validation import run_input_validation
from clinical_compiler.passes.semantic_normalization import run_semantic_normalization
from clinical_compiler.pipeline import CompileRequest, run
from clinical_compiler.passes.document_selection import NURSING_RECORD_TELEGRAPHIC
data = sys.stdin.buffer.read(); policy = approved_empty_by_deferral(DEFERRED_BY_OWNER_DECISION)
result = run(CompileRequest(data, NURSING_RECORD_TELEGRAPHIC, policy)); feed = parse_feed(data)
accepted = () if feed.diagnostic is not None else tuple(e.fact for e in feed.records if e.fact is not None)
validated = run_input_validation(tuple(item.fact for item in accepted)); normalized = run_semantic_normalization(validated.admitted)
facts = run_admissibility(normalized.admitted, policy.terms, frozenset(f.fact_id for f in validated.admitted)).admitted
payload = {{"document_sha256": None if result.document is None else hashlib.sha256(result.document).hexdigest(), "document_is_none": result.document is None, "diagnostic_codes": [d.code.value for d in result.diagnostics], "clinical_fact_ids": [f.clinical_fact_id for f in facts], "source_fact_refs": [list(f.source_fact_refs) for f in facts], "provenance": [{{"source_kind": f.value.provenance.source_kind, "source_ref": f.value.provenance.source_ref}} for f in facts]}}
print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
"""
VARIANTS: Final[tuple[tuple[tuple[str, ...], str], ...]] = (
    (("-I",), "random"),
    ((), "0"),
    ((), "random"),
)


def _child(
    data: bytes, flags: tuple[str, ...], seed: str
) -> tuple[str, dict[str, Any]]:
    env = {"PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": seed}
    if "-I" not in flags:
        env["PYTHONPATH"] = str(SRC)
    result = subprocess.run(
        [sys.executable, *flags, "-c", CHILD],
        cwd=ROOT,
        capture_output=True,
        check=False,
        env=env,
        input=data,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8")
    assert result.stderr == b""
    text = result.stdout.decode("utf-8")
    payload = json.loads(text)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    assert text == canonical + "\n"
    assert tuple(payload) == (
        "clinical_fact_ids",
        "diagnostic_codes",
        "document_is_none",
        "document_sha256",
        "provenance",
        "source_fact_refs",
    )
    return canonical, payload


@pytest.mark.parametrize("label,data", _C3, ids=["clean", "fault"])
def test_c3_fresh_processes_agree_on_canonical_observation(
    label: str, data: bytes
) -> None:
    observations = [_child(data, flags, seed) for flags, seed in VARIANTS]
    first, payload = observations[0]
    for observed, observed_payload in observations[1:]:
        assert observed == first
        assert observed_payload == payload
    if label == "clean":
        assert payload["document_is_none"] is False
        assert isinstance(payload["document_sha256"], str)
        assert payload["diagnostic_codes"] == []
        assert payload["clinical_fact_ids"] != []
    else:
        assert payload["document_is_none"] is True
        assert payload["document_sha256"] is None
        assert payload["diagnostic_codes"] == [
            "SEMANTIC_AMBIGUITY_BLOCK",
            "SEMANTIC_AMBIGUITY_BLOCK",
            "DOCUMENT_SELECTION_ERROR",
        ]
