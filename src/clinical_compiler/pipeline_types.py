"""Leaf stage contract shared by all passes (design D5 / G-1 adjudication).

``StageResult`` lives in THIS leaf module — never in ``pipeline.py`` —
so every pass can import its stage contract without violating the
frozen dependency rule ``passes → pipeline_types → core`` (G-1,
adjudicated at design level; ``pipeline.py`` re-exports it in a later
unit). Pure data only: no I/O, no globals, no side effects.
"""

from dataclasses import dataclass
from typing import Generic, TypeVar

from clinical_compiler.core.diagnostics import Diagnostic

__all__ = ["StageResult"]

_T = TypeVar("_T")


@dataclass(frozen=True, slots=True)
class StageResult(Generic[_T]):
    """Outcome of one pipeline stage over the survivors it received.

    Attributes:
        admitted: Facts that survived the stage, in encounter order —
            passed through unchanged for later stages to consume.
        diagnostics: Diagnostics emitted for the facts this stage
            quarantined, in encounter order — a stage never raises to
            signal a clinical fault (design M2.1).
    """

    admitted: tuple[_T, ...]
    diagnostics: tuple[Diagnostic, ...]
