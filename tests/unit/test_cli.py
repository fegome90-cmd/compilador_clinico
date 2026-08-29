"""Tests for the Phase-4 CLI shell (tasks 4.3–4.5 — APPROVAL-PHASE4
Unit 2): ``clinical_compiler.cli.main`` over the frozen Exit-Code Table
(design §Exit-Code Table + §CLI Surface; spec cli-surface).

Pinned surface: ``clinical-compiler compile INPUT [--mode MODE]
[--policy-seed PATH] [--output PATH]`` — diagnostics to stderr, one per
line, stable ``CODE: message (path)`` format; document bytes reach
stdout or ``--output`` ONLY at exit 0 (never a partial document);
``--output`` is written atomically (temp + os.replace, parent-dir
fsync); usage faults (argparse, missing/unreadable INPUT, unknown
``--mode``, invalid ``--policy-seed``, UNRESOLVED_POLICY) exit 2 with
NO compile attempted; exit 70 is the fail-closed catch-all for
unexpected exceptions — never 0.

D7 seed wiring: the flag ABSENT resolves to the approved-empty policy
citing the durable ``DEFERRED_BY_OWNER`` decision (APPROVAL-PHASE1.md —
the FC-12 production path, asserted via spy); a GIVEN but faulty seed
yields ``UNRESOLVED_POLICY`` → exit 2, never empty-set-and-continue.

End-to-end fault coverage follows the corpus reachability adjudication
(CRC-004): raw bytes reach exits 3/4/5/6/8; ``PROVENANCE_ERROR`` (7) is
unreachable through ``pipeline.run`` by construction and
``RENDER_ERROR``/``LINT_FAILURE`` (9/10) are defense-in-depth — both
exercised here at the CLI seam via injected stage faults, as FC-10/FC-11
prescribe.

Subprocess tests run ``main`` in fresh interpreters (task 4.5) with an
explicit ``PYTHONPATH`` and varied ``PYTHONHASHSEED`` — identical input
yields identical bytes and exit code across hash seeds (Mechanism #4).
"""

import json
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Final

import pytest

from clinical_compiler import cli, pipeline
from clinical_compiler.adapters.seed import DEFERRED_BY_OWNER_DECISION
from clinical_compiler.core.diagnostics import Diagnostic, DiagnosticCode
from clinical_compiler.pipeline_types import StageResult

pytestmark = pytest.mark.integration

_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
_SRC_ROOT: Final[Path] = _REPO_ROOT / "src"
_PYPROJECT: Final[Path] = _REPO_ROOT / "pyproject.toml"
_SEED_FIXTURE: Final[Path] = (
    _REPO_ROOT / "tests" / "fixtures" / "policy-seed-sample.json"
)

_DRIVER: Final[str] = (
    "import sys;"
    " from clinical_compiler.cli import main;"
    " sys.exit(main(sys.argv[1:]))"
)

_HAPPY_DOCUMENT: Final[bytes] = (
    b"FC: 80.5 [present] [monitor m-9]\n"
    b"TA: 120/80 [present] [monitor m-9]\n"
)


def _record(**overrides: object) -> dict[str, object]:
    """Build a contract-conformant FC record with the given overrides."""
    record: dict[str, object] = {
        "fact_id": "raw-1",
        "field_id": "FC",
        "raw_value": 72,
        "provenance": {"source_kind": "monitor", "source_ref": "m-9"},
    }
    record.update(overrides)
    return record


def _line(record: object) -> str:
    """Encode one record as a JSONL line."""
    return json.dumps(record)


def _feed(*lines: str) -> bytes:
    """Encode the given lines as feed bytes."""
    return "\n".join(lines).encode("utf-8")


def _happy_feed() -> bytes:
    """A clean FC+TA feed whose document matches ``_HAPPY_DOCUMENT``."""
    return _feed(
        _line(_record(fact_id="std-fc-1", raw_value=80.5)),
        _line(
            _record(
                fact_id="std-ta-1",
                field_id="TA",
                raw_value="120/80",
            )
        ),
    )


def _write_feed(tmp_path: Path, data: bytes) -> Path:
    """Materialize feed bytes as the CLI's INPUT artifact."""
    path = tmp_path / "input.jsonl"
    path.write_bytes(data)
    return path


def _run_cli(*argv: str, hash_seed: str = "0") -> subprocess.CompletedProcess[bytes]:
    """Invoke ``cli.main`` in a fresh interpreter (task 4.5 mode)."""
    return subprocess.run(
        [sys.executable, "-c", _DRIVER, *argv],
        capture_output=True,
        check=False,
        env={"PYTHONPATH": str(_SRC_ROOT), "PYTHONHASHSEED": hash_seed},
        timeout=60,
    )


# --- 1. Happy paths: document bytes only at exit 0 -------------------------


def test_happy_path_streams_document_bytes_to_stdout_with_exit_zero(
    tmp_path: Path,
) -> None:
    """Clean feed: exit 0, exact document bytes on stdout, clean stderr."""
    feed = _write_feed(tmp_path, _happy_feed())

    completed = _run_cli("compile", str(feed))

    assert completed.returncode == 0
    assert completed.stdout == _HAPPY_DOCUMENT
    assert completed.stderr == b""


def test_output_flag_writes_document_atomically_with_empty_stdout(
    tmp_path: Path,
) -> None:
    """``--output``: bytes land in the file, nothing on stdout, and no
    temp artifact survives (the atomic protocol leaves only the target)."""
    feed = _write_feed(tmp_path, _happy_feed())
    output = tmp_path / "document.txt"

    completed = _run_cli("compile", str(feed), "--output", str(output))

    assert completed.returncode == 0
    assert output.read_bytes() == _HAPPY_DOCUMENT
    assert completed.stdout == b""
    assert completed.stderr == b""
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "document.txt",
        "input.jsonl",
    ]


def test_output_flag_atomic_protocol_in_process(
    tmp_path: Path,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    """In-process view of the durability protocol: temp file → fsync →
    ``os.replace`` → parent-directory fsync all run; the destination
    carries exactly the document bytes; stdout stays empty."""
    feed = _write_feed(tmp_path, _happy_feed())
    output = tmp_path / "document.txt"

    exit_code = cli.main(["compile", str(feed), "--output", str(output)])

    captured = capsysbinary.readouterr()
    assert exit_code == 0
    assert output.read_bytes() == _HAPPY_DOCUMENT
    assert captured.out == b""
    assert captured.err == b""
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "document.txt",
        "input.jsonl",
    ]


def test_absent_seed_runs_the_deferral_approved_empty_policy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D7 wiring, FC-12 production path: no ``--policy-seed`` resolves to
    the approved-empty policy citing the durable ``DEFERRED_BY_OWNER``
    decision — removing the citation breaks this test (mutation)."""
    citations: list[str] = []
    real = cli.approved_empty_by_deferral

    def _spy(decision_record: str) -> object:
        citations.append(decision_record)
        return real(decision_record)

    monkeypatch.setattr(cli, "approved_empty_by_deferral", _spy)
    feed = _write_feed(tmp_path, _happy_feed())

    exit_code = cli.main(["compile", str(feed)])

    assert exit_code == 0
    assert citations == [DEFERRED_BY_OWNER_DECISION]


def test_valid_seed_file_compiles_clean(tmp_path: Path) -> None:
    """A structurally valid owner seed loads and the compile succeeds."""
    feed = _write_feed(tmp_path, _happy_feed())

    completed = _run_cli(
        "compile", str(feed), "--policy-seed", str(_SEED_FIXTURE)
    )

    assert completed.returncode == 0
    assert completed.stdout == _HAPPY_DOCUMENT
    assert completed.stderr == b""


# --- 2. Fault corpus end to end: stderr lines + family exit codes ----------


@pytest.mark.parametrize(
    ("label", "data", "seed", "code", "expected_exit"),
    [
        (
            "FC-01 missing required key",
            _feed(_line({"fact_id": "raw-1", "raw_value": 72})),
            None,
            b"INPUT_CONTRACT_ERROR:",
            3,
        ),
        (
            "FC-05 bool raw_value for numeric FC",
            _feed(_line(_record(raw_value=True))),
            None,
            b"TYPE_ERROR:",
            4,
        ),
        (
            "FC-06 conflicting equal-authority FC readings",
            _feed(
                _line(_record(fact_id="fc-a", raw_value=72)),
                _line(_record(fact_id="fc-b", raw_value=80)),
            ),
            None,
            b"SEMANTIC_AMBIGUITY_BLOCK:",
            5,
        ),
        (
            "FC-07 vetoed term under the owner seed",
            _feed(
                _line(
                    _record(
                        fact_id="ta-vetoed",
                        field_id="TA",
                        raw_value="TA: test-veto-term-alpha de noche",
                    )
                )
            ),
            _SEED_FIXTURE,
            b"POLICY_VIOLATION:",
            6,
        ),
        (
            "FC-09 empty feed — selection fails closed",
            b"",
            None,
            b"DOCUMENT_SELECTION_ERROR:",
            8,
        ),
    ],
)
def test_fault_corpus_exits_its_family_code_and_never_emits_a_document(
    tmp_path: Path,
    label: str,
    data: bytes,
    seed: Path | None,
    code: bytes,
    expected_exit: int,
) -> None:
    """Any blocking diagnostic: stderr line(s) with the mapped code, the
    frozen family exit code, and NOTHING on stdout or ``--output``."""
    feed = _write_feed(tmp_path, data)
    output = tmp_path / "document.txt"
    argv = ["compile", str(feed), "--output", str(output)]
    if seed is not None:
        argv += ["--policy-seed", str(seed)]

    completed = _run_cli(*argv)

    assert completed.returncode == expected_exit, label
    assert completed.stdout == b"", label
    assert not output.exists(), label
    stderr_lines = completed.stderr.decode("utf-8").splitlines()
    assert stderr_lines, label
    assert any(
        line.startswith(code.decode("utf-8")) for line in stderr_lines
    ), (label, stderr_lines)


def test_seed_fault_yields_the_unresolved_policy_usage_line(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    """A GIVEN but missing seed: ``UNRESOLVED_POLICY`` on stderr, exit 2,
    and NO compile attempted (the pipeline is never invoked — spy)."""
    calls: list[object] = []

    def _spy(*args: object) -> object:
        calls.append(args)
        raise AssertionError("run must not execute on an unresolved policy")

    monkeypatch.setattr(cli, "run", _spy)
    feed = _write_feed(tmp_path, _happy_feed())
    missing_seed = tmp_path / "no-such-seed.json"

    exit_code = cli.main(
        ["compile", str(feed), "--policy-seed", str(missing_seed)]
    )

    captured = capsysbinary.readouterr()
    assert exit_code == 2
    assert calls == []
    assert captured.out == b""
    assert captured.err.startswith(b"UNRESOLVED_POLICY:")


def test_missing_seed_reports_unresolved_policy_on_stderr(
    tmp_path: Path,
) -> None:
    """Subprocess view of the D7 gate: exit 2 and the stable
    ``UNRESOLVED_POLICY:`` stderr line carrying the typed fault."""
    feed = _write_feed(tmp_path, _happy_feed())

    completed = _run_cli(
        "compile", str(feed), "--policy-seed", str(tmp_path / "absent.json")
    )

    assert completed.returncode == 2
    assert completed.stdout == b""
    stderr_lines = completed.stderr.decode("utf-8").splitlines()
    assert len(stderr_lines) == 1
    assert stderr_lines[0].startswith("UNRESOLVED_POLICY:")


def test_malformed_seed_is_a_usage_exit(tmp_path: Path) -> None:
    """A seed that is not valid JSON: exit 2, no document anywhere."""
    feed = _write_feed(tmp_path, _happy_feed())
    broken = tmp_path / "broken-seed.json"
    broken.write_bytes(b"{not json")

    completed = _run_cli(
        "compile", str(feed), "--policy-seed", str(broken)
    )

    assert completed.returncode == 2
    assert completed.stdout == b""
    assert completed.stderr.startswith(b"UNRESOLVED_POLICY:")


# --- 3. Usage errors: exit 2, no compile attempted -------------------------


@pytest.mark.parametrize(
    ("label", "argv_builder"),
    [
        ("no arguments at all", lambda _feed_path: ()),
        (
            "missing INPUT file",
            lambda _feed_path: ("compile", str(_feed_path.parent / "absent.jsonl")),
        ),
        (
            "unreadable INPUT (a directory)",
            lambda _feed_path: ("compile", str(_feed_path.parent)),
        ),
        (
            "unknown --mode",
            lambda feed_path: ("compile", str(feed_path), "--mode", "BOGUS_MODE"),
        ),
        (
            "unknown flag",
            lambda feed_path: ("compile", str(feed_path), "--json"),
        ),
        (
            "missing positional INPUT",
            lambda _feed_path: ("compile", "--output", "out.txt"),
        ),
    ],
)
def test_usage_faults_exit_two_without_emitting_anything(
    tmp_path: Path,
    label: str,
    argv_builder: object,
) -> None:
    """Every usage fault maps to exit 2 with an empty document stream
    (frozen table row 2 — no compile attempted)."""
    feed = _write_feed(tmp_path, _happy_feed())
    argv = argv_builder(feed)  # type: ignore[operator]

    completed = _run_cli(*argv)  # type: ignore[arg-type]

    assert completed.returncode == 2, label
    assert completed.stdout == b"", label
    assert completed.stderr != b"", label


def test_argparse_usage_fault_returns_two_in_process(
    tmp_path: Path,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    """In-process view: an argparse fault surfaces as the returned exit
    code 2 — no SystemExit escapes ``main`` (task 4.3 testability)."""
    feed = _write_feed(tmp_path, _happy_feed())

    assert cli.main(["compile", str(feed), "--mode", "BOGUS_MODE"]) == 2
    assert cli.main([]) == 2
    captured = capsysbinary.readouterr()
    assert captured.out == b""
    assert captured.err.startswith(b"clinical-compiler: error:")


def test_unreadable_input_returns_two_in_process(
    tmp_path: Path,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    """In-process view: a missing INPUT maps to exit 2 with the stable
    usage prefix on stderr (frozen table: no compile attempted)."""
    feed = _write_feed(tmp_path, _happy_feed())

    exit_code = cli.main(
        ["compile", str(feed.parent / "absent.jsonl")]
    )

    captured = capsysbinary.readouterr()
    assert exit_code == 2
    assert captured.out == b""
    assert captured.err.startswith(b"clinical-compiler: error:")
    assert b"cannot read input" in captured.err


# --- 4. Defense-in-depth legs at the CLI seam (FC-10/FC-11 + 70 net) -------


def test_injected_render_fault_exits_nine_with_no_document(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    """FC-10 at the CLI seam: a faulty render stage yields exit 9, the
    RENDER_ERROR stderr line, and zero document bytes on stdout."""
    monkeypatch.setattr(
        pipeline,
        "render_document",
        lambda *args: StageResult(
            admitted=(),
            diagnostics=(Diagnostic(DiagnosticCode.RENDER_ERROR, "injected"),),
        ),
    )
    feed = _write_feed(tmp_path, _happy_feed())

    exit_code = cli.main(["compile", str(feed)])

    captured = capsysbinary.readouterr()
    assert exit_code == 9
    assert captured.out == b""
    assert captured.err.startswith(b"RENDER_ERROR:")


def test_injected_lint_failure_exits_ten_with_no_document(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    """FC-11 at the CLI seam: a failing lint stage yields exit 10 and
    zero document bytes on stdout."""
    monkeypatch.setattr(
        pipeline,
        "lint_conformance",
        lambda *args: StageResult(
            admitted=(),
            diagnostics=(Diagnostic(DiagnosticCode.LINT_FAILURE, "injected"),),
        ),
    )
    feed = _write_feed(tmp_path, _happy_feed())

    exit_code = cli.main(["compile", str(feed)])

    captured = capsysbinary.readouterr()
    assert exit_code == 10
    assert captured.out == b""
    assert captured.err.startswith(b"LINT_FAILURE:")


def test_unexpected_exception_is_fail_closed_exit_seventy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    """The catch-all: an unexpected exception inside the composition
    becomes exit 70 with a best-effort stderr line — never 0, never a
    bare traceback, never document bytes."""
    def _explode(*args: object) -> object:
        raise RuntimeError("injected composition fault")

    monkeypatch.setattr(cli, "run", _explode)
    feed = _write_feed(tmp_path, _happy_feed())

    exit_code = cli.main(["compile", str(feed)])

    captured = capsysbinary.readouterr()
    assert exit_code == 70
    assert captured.out == b""
    assert b"internal error" in captured.err
    assert b"RuntimeError" in captured.err


def test_unrepresentable_empty_outcome_never_exits_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    """Defense-in-depth belt at the shell: a run reporting neither
    document nor diagnostics (unrepresentable per CompileResult) still
    cannot exit 0 — the CLI fails closed at 70."""
    class _Stub:
        document = None
        diagnostics: tuple[Diagnostic, ...] = ()

    monkeypatch.setattr(cli, "run", lambda *args: _Stub())
    feed = _write_feed(tmp_path, _happy_feed())

    exit_code = cli.main(["compile", str(feed)])

    captured = capsysbinary.readouterr()
    assert exit_code == 70
    assert captured.out == b""
    assert captured.err != b""


def test_atomic_write_cleans_the_temp_file_on_write_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    """A failed ``os.replace`` leaves NO temp artifact behind, emits no
    document bytes anywhere, and surfaces as exit 70 (not a usage row —
    the destination fault is not one of the frozen exit-2 triggers)."""
    def _broken_replace(src: object, dst: object) -> None:
        raise OSError("injected replace failure")

    monkeypatch.setattr(cli.os, "replace", _broken_replace)
    feed = _write_feed(tmp_path, _happy_feed())
    output = tmp_path / "document.txt"

    exit_code = cli.main(["compile", str(feed), "--output", str(output)])

    captured = capsysbinary.readouterr()
    assert exit_code == 70
    assert captured.out == b""
    assert not output.exists()
    assert [p.name for p in tmp_path.iterdir()] == ["input.jsonl"]


def test_output_into_a_missing_directory_fails_closed_at_seventy(
    tmp_path: Path,
) -> None:
    """An unwritable destination is not a frozen exit-2 trigger: the
    OSError reaches the catch-all — exit 70, nothing emitted."""
    feed = _write_feed(tmp_path, _happy_feed())
    output = tmp_path / "no-such-dir" / "document.txt"

    exit_code = cli.main(["compile", str(feed), "--output", str(output)])

    assert exit_code == 70


# --- 5. Deterministic stderr bytes and exit codes across hash seeds --------


def test_identical_failing_input_yields_identical_bytes_and_exit(
    tmp_path: Path,
) -> None:
    """Mechanism #4: the same failing feed under different hash seeds
    produces identical return code, stdout, and stderr bytes."""
    feed = _write_feed(
        tmp_path,
        _feed(
            _line(_record(fact_id="fc-a", raw_value=72)),
            _line(_record(fact_id="fc-b", raw_value=80)),
        ),
    )

    first = _run_cli("compile", str(feed), hash_seed="0")
    second = _run_cli("compile", str(feed), hash_seed="random")

    assert first.returncode == second.returncode == 5
    assert first.stdout == second.stdout == b""
    assert first.stderr == second.stderr
    assert first.stderr != b""


def test_identical_clean_input_yields_identical_document_bytes(
    tmp_path: Path,
) -> None:
    """The document stream is byte-identical across fresh interpreters
    with randomized hash seeds (cross-run determinism via the CLI)."""
    feed = _write_feed(tmp_path, _happy_feed())

    first = _run_cli("compile", str(feed), hash_seed="0")
    second = _run_cli("compile", str(feed), hash_seed="random")

    assert first.returncode == second.returncode == 0
    assert first.stdout == second.stdout == _HAPPY_DOCUMENT


# --- 6. Console-script registration + formatter contract -------------------


def test_pyproject_registers_the_console_script_with_zero_deps() -> None:
    """cli-surface packaging scenario: ``[project.scripts]`` registers
    ``clinical-compiler`` → ``clinical_compiler.cli:main`` and
    ``[project].dependencies`` has length 0 (the key is absent — no
    runtime dependencies are declared at all)."""
    parsed = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))

    assert parsed["project"]["scripts"] == {
        "clinical-compiler": "clinical_compiler.cli:main"
    }
    assert parsed["project"].get("dependencies", []) == []


def test_main_is_callable_and_entry_target_exists() -> None:
    """The registered target resolves to a callable ``main`` — console
    scripts invoke ``sys.exit(main())``, so the int return IS the exit
    status (setuptools semantics)."""
    assert callable(cli.main)


@pytest.mark.parametrize(
    ("diagnostic", "expected"),
    [
        (
            Diagnostic(DiagnosticCode.TYPE_ERROR, "bad value"),
            "TYPE_ERROR: bad value",
        ),
        (
            Diagnostic(
                DiagnosticCode.INPUT_CONTRACT_ERROR, "missing key", "in.jsonl"
            ),
            "INPUT_CONTRACT_ERROR: missing key (in.jsonl)",
        ),
    ],
)
def test_diagnostic_stderr_line_format_is_stable(
    diagnostic: Diagnostic, expected: str
) -> None:
    """Frozen stderr format ``CODE: message (path)`` — the `` (path)``
    suffix appears only when a path is carried."""
    assert cli._format_diagnostic(diagnostic) == expected
