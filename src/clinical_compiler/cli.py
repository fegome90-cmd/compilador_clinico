"""Argparse shell — the zero-dependency CLI entry point (design D4;
tasks 4.3/4.4/4.5). Frozen surface, exactly one verb:

    clinical-compiler compile INPUT [--mode MODE] [--policy-seed PATH]
                                      [--output PATH]

Responsibilities (design §CLI Surface + §Exit-Code Table, frozen):

- Read INPUT bytes and load the D7 policy, then hand a
  :class:`~clinical_compiler.pipeline.CompileRequest` to the composition
  root. Usage faults — argparse failure, missing/unreadable INPUT,
  unknown ``--mode``, invalid ``--policy-seed`` (an UNRESOLVED_POLICY
  resolution) — map to exit 2 with NO compile attempted.
- Seed wiring: the flag GIVEN loads the owner-authored file via
  :func:`clinical_compiler.adapters.seed.load_policy_seed`; any fault
  resolves UNRESOLVED_POLICY → exit 2 (never empty-set-and-continue).
  The flag ABSENT resolves to the approved-empty policy citing the
  durable owner decision :data:`~clinical_compiler.adapters.seed.\
DEFERRED_BY_OWNER_DECISION` (APPROVAL-PHASE1.md,
  ``POLICY_SEED_DECISION = DEFERRED_BY_OWNER``) — the FC-12 production
  path; there is no code path that synthesizes an empty veto set without
  that citation.
- Diagnostics always to **stderr**, one per line, stable
  ``CODE: message (path)`` format; a failed run writes nothing to the
  document stream (no partial document). Exit code = the pure
  :func:`~clinical_compiler.pipeline.derive_exit_code` over the
  diagnostic set (minimum stage-order code among 3–10; 0 iff empty).
- The document reaches stdout (buffered binary, nothing else is ever
  written there) or ``--output`` ONLY at exit 0. ``--output`` is written
  atomically: temp file in the destination directory, write + flush +
  fsync, ``os.replace``, then a parent-directory fsync (durability
  protocol) — no partial document is ever visible, and a failed write
  leaves no temp artifact behind.
- Exit 70 is the fail-closed catch-all for unexpected exceptions: a
  best-effort line on stderr, never 0, never a bare traceback. Destination
  write faults (OSError on ``--output``) are not one of the frozen exit-2
  triggers, so they reach the catch-all — flagged in apply-progress.

``main`` returns the exit code as ``int`` (testable; no SystemExit leaks
for usage faults — argparse's ``error`` is overridden). Setuptools
console scripts invoke ``sys.exit(main())``, so the returned int IS the
process exit status; ``[project.scripts]`` registers
``clinical-compiler = "clinical_compiler.cli:main"`` (task 4.4).

Dependency rule (D5): imports everything below it — ``pipeline``,
``adapters.seed``, ``passes.document_selection`` (mode vocabulary) — and
nothing imports this module except a console-script entry point. No
network, no subprocess/shell, no eval/exec, no time/locale/random in any
output path (design Determinism Mechanism #2; M2.1 security/limits
properties hold here: input bytes are UNTRUSTED_CONTENT parsed
downstream, never executed).
"""

import argparse
import os
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Final, NoReturn, cast

from clinical_compiler.adapters.seed import (
    DEFERRED_BY_OWNER_DECISION,
    PolicyResolution,
    approved_empty_by_deferral,
    load_policy_seed,
)
from clinical_compiler.core.diagnostics import Diagnostic
from clinical_compiler.passes.document_selection import (
    NURSING_RECORD_TELEGRAPHIC as _DEFAULT_MODE,
)
from clinical_compiler.passes.document_selection import SUPPORTED_MODES
from clinical_compiler.pipeline import (
    CompileRequest,
    CompileResult,
    derive_exit_code,
    run,
)

__all__ = ["main"]

_SUCCESS_EXIT: Final[int] = 0
_USAGE_EXIT: Final[int] = 2
_INTERNAL_EXIT: Final[int] = 70

_USAGE_PREFIX: Final[str] = "clinical-compiler: error:"
_INTERNAL_PREFIX: Final[str] = "clinical-compiler: internal error:"


class _UsageError(Exception):
    """A usage fault mapped to exit 2 — no compile attempted."""


class _Parser(argparse.ArgumentParser):
    """ArgumentParser that raises instead of calling ``sys.exit(2)``.

    Keeping usage faults as exceptions lets ``main`` return the exit
    code as a plain ``int`` (task 4.3: testable, no SystemExit leakage);
    the mapping back to exit 2 stays at the shell boundary where it
    belongs per the frozen table.
    """

    def error(self, message: str) -> NoReturn:
        """Replace argparse's print-and-exit with a typed usage fault."""
        raise _UsageError(message) from None


def _build_parser() -> argparse.ArgumentParser:
    """Build the frozen single-verb argument surface."""
    parser = _Parser(
        prog="clinical-compiler",
        description="Deterministic clinical-record compiler (R1).",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    compile_command = commands.add_parser(
        "compile",
        help="Compile INPUT into the R1 document mode.",
    )
    compile_command.add_argument(
        "input",
        metavar="INPUT",
        help="Path to the input artifact satisfying the frozen contract.",
    )
    compile_command.add_argument(
        "--mode",
        default=_DEFAULT_MODE,
        choices=SUPPORTED_MODES,
        help="Document mode (default and only R1 mode).",
    )
    compile_command.add_argument(
        "--policy-seed",
        dest="policy_seed",
        default=None,
        metavar="PATH",
        help=(
            "Owner-authored seed JSON {'terms': [...]}; absent flag"
            " resolves per the D7 Policy Resolution State Machine."
        ),
    )
    compile_command.add_argument(
        "--output",
        default=None,
        metavar="PATH",
        help="Document destination (default stdout; written atomically).",
    )
    return parser


def _format_diagnostic(diagnostic: Diagnostic) -> str:
    """Render one diagnostic in the stable stderr format.

    ``CODE: message (path)`` — the `` (path)`` suffix appears only when
    the diagnostic carries a path.
    """
    if diagnostic.path is None:
        return f"{diagnostic.code}: {diagnostic.message}"
    return f"{diagnostic.code}: {diagnostic.message} ({diagnostic.path})"


def _read_input(input_path: Path) -> bytes:
    """Read the INPUT artifact whole; any read fault is a usage fault."""
    try:
        return input_path.read_bytes()
    except OSError as error:
        raise _UsageError(
            f"cannot read input {str(input_path)!r}:"
            f" {type(error).__name__}"
        ) from error


def _resolve_policy(seed_path: str | None) -> PolicyResolution:
    """Resolve the D7 policy for this invocation.

    A given ``--policy-seed`` loads through the structurally validating
    adapter; the flag absent resolves to the approved-empty policy under
    the durable ``DEFERRED_BY_OWNER`` owner decision. Never an uncited
    empty set (CRC-005).
    """
    if seed_path is None:
        return approved_empty_by_deferral(DEFERRED_BY_OWNER_DECISION)
    return load_policy_seed(seed_path)


def _atomic_write(document: bytes, destination: Path) -> None:
    """Write the document atomically (durability protocol).

    Temp file in the destination directory (same filesystem) → write +
    flush + ``fsync`` → ``os.replace`` → parent-directory ``fsync``. A
    failure at any point removes the temp artifact and propagates — no
    partial document is ever visible under the destination name.
    """
    directory = destination.parent
    file_descriptor, temp_name = tempfile.mkstemp(
        dir=directory,
        prefix=f".{destination.name}.",
        suffix=".tmp",
    )
    temporary = Path(temp_name)
    try:
        with os.fdopen(file_descriptor, "wb") as handle:
            handle.write(document)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _emit(result: CompileResult, output: str | None) -> int:
    """Deliver the run outcome: stderr diagnostics + document stream.

    A failed run writes nothing to the document stream and returns the
    frozen family exit code; an outcome carrying neither document nor
    diagnostics under a resolved policy is unrepresentable per
    ``CompileResult`` — should one ever surface, the shell still fails
    closed at 70 rather than silently succeeding.
    """
    for diagnostic in result.diagnostics:
        print(_format_diagnostic(diagnostic), file=sys.stderr)

    document = result.document
    if document is None:
        if not result.diagnostics:
            print(
                f"{_INTERNAL_PREFIX}: the run reported neither a document"
                " nor diagnostics — failing closed",
                file=sys.stderr,
            )
            return _INTERNAL_EXIT
        return derive_exit_code(result.diagnostics)

    if output is None:
        sys.stdout.buffer.write(document)
        sys.stdout.buffer.flush()
    else:
        _atomic_write(document, Path(output))
    return _SUCCESS_EXIT


def _execute(namespace: argparse.Namespace) -> int:
    """Run one compile invocation from parsed arguments."""
    input_path = Path(cast(str, namespace.input))
    data = _read_input(input_path)

    policy = _resolve_policy(cast("str | None", namespace.policy_seed))
    if not policy.is_resolved:
        detail = policy.detail if policy.detail is not None else "unresolved"
        print(f"UNRESOLVED_POLICY: {detail}", file=sys.stderr)
        return _USAGE_EXIT

    result = run(
        CompileRequest(
            data=data,
            document_mode=cast(str, namespace.mode),
            policy=policy,
        )
    )
    return _emit(result, cast("str | None", namespace.output))


def main(argv: Sequence[str] | None = None) -> int:
    """Compile per the frozen surface; return the process exit code.

    Usage faults (argparse, unreadable INPUT, unknown ``--mode``,
    invalid ``--policy-seed``) exit 2 with no compile attempted; any
    unexpected exception is confined to the fail-closed exit-70
    catch-all (best-effort stderr line, never 0).
    """
    try:
        namespace = _build_parser().parse_args(argv)
        return _execute(namespace)
    except _UsageError as error:
        print(f"{_USAGE_PREFIX} {error}", file=sys.stderr)
        return _USAGE_EXIT
    except Exception as error:  # noqa: BLE001 — the design-mandated
        # fail-closed catch-all (Exit-Code Table row 70; M2.1: unexpected
        # exceptions are confined here, never 0, never a bare traceback).
        print(
            f"{_INTERNAL_PREFIX} {type(error).__name__}: {error}",
            file=sys.stderr,
        )
        return _INTERNAL_EXIT
