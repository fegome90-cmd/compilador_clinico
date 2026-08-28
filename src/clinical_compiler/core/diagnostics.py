"""Diagnostic codes and records for the compiler pipeline."""

from dataclasses import dataclass
from enum import StrEnum


class DiagnosticCode(StrEnum):
    """Taxonomy of diagnostic codes, one entry per pipeline failure category.

    Each member's value matches its name so diagnostics serialize
    identically across stages and renderers.
    """

    INPUT_CONTRACT_ERROR = "INPUT_CONTRACT_ERROR"
    TYPE_ERROR = "TYPE_ERROR"
    SEMANTIC_AMBIGUITY_BLOCK = "SEMANTIC_AMBIGUITY_BLOCK"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    DOCUMENT_SELECTION_ERROR = "DOCUMENT_SELECTION_ERROR"
    RENDER_ERROR = "RENDER_ERROR"
    LINT_FAILURE = "LINT_FAILURE"
    PROVENANCE_ERROR = "PROVENANCE_ERROR"


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """An immutable diagnostic record produced by any pipeline stage.

    Attributes:
        code: Taxonomic code identifying the diagnostic category.
        message: Human-readable description of the problem.
        path: Optional source path the diagnostic refers to.
    """

    code: DiagnosticCode
    message: str
    path: str | None = None
