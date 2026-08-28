"""Unit tests for clinical_compiler.core.diagnostics."""

from dataclasses import FrozenInstanceError

import pytest

from clinical_compiler.core.diagnostics import Diagnostic, DiagnosticCode


def test_diagnostic_codes_have_unique_nonempty_values() -> None:
    """Every diagnostic code maps to a distinct, non-empty string value."""
    values = [code.value for code in DiagnosticCode]
    assert len(values) == len(set(values))
    assert all(value != "" for value in values)


@pytest.mark.parametrize("code", list(DiagnosticCode))
def test_diagnostic_accepts_every_code(code: DiagnosticCode) -> None:
    """Diagnostic construction succeeds for each defined code."""
    diagnostic = Diagnostic(code=code, message="problem")
    assert diagnostic.code is code
    assert diagnostic.message == "problem"


def test_diagnostic_path_defaults_to_none() -> None:
    """Path is optional and defaults to None."""
    diagnostic = Diagnostic(code=DiagnosticCode.RENDER_ERROR, message="boom")
    assert diagnostic.path is None


def test_diagnostic_is_immutable() -> None:
    """Field mutation is rejected by the frozen contract."""
    diagnostic = Diagnostic(code=DiagnosticCode.TYPE_ERROR, message="x")
    with pytest.raises(FrozenInstanceError):
        diagnostic.message = "y"  # type: ignore[misc]


def test_diagnostic_declares_closed_attribute_set() -> None:
    """Slots prevent undeclared attributes at runtime.

    The rejection exception class varies by CPython version:
    3.11-3.13 raise AttributeError; 3.14 raises TypeError through
    the slots ``__setattr__`` path.
    """
    diagnostic = Diagnostic(code=DiagnosticCode.LINT_FAILURE, message="m")
    with pytest.raises((AttributeError, TypeError)):
        diagnostic.unexpected = 1  # type: ignore[attr-defined]
