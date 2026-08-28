"""Core domain types for clinical values and their provenance."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class Certainty(StrEnum):
    """Assessment certainty assigned to a clinical value.

    Members are ordered from most uncertain to most certain:
    ``CANDIDATE`` values are raw candidates, ``UNRESOLVED`` lack a
    decision, ``LIKELY``/``PROBABLE`` are supported by evidence,
    ``CONFIRMED`` is verified, ``UNLIKELY``/``AMBIGUOUS`` express
    negative or conflicting evidence.
    """

    CANDIDATE = "candidate"
    UNRESOLVED = "unresolved"
    LIKELY = "likely"
    UNLIKELY = "unlikely"
    CONFIRMED = "confirmed"
    PROBABLE = "probable"
    AMBIGUOUS = "ambiguous"


class Missingness(StrEnum):
    """Data-presence semantics for a clinical value.

    Distinguishes an assessed absence (``MISSING``, ``NOT_APPLICABLE``)
    from an unassessed one (``UNKNOWN``, ``NOT_ASSESSED``) — conflating
    them is a clinical safety error.
    """

    UNKNOWN = "unknown"
    PRESENT = "present"
    MISSING = "missing"
    NOT_ASSESSED = "not_assessed"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class Provenance:
    """Attribution of a clinical value to its source.

    Attributes:
        source_kind: Kind of source (for example ``"lab"`` or
            ``"clinical_note"``).
        source_ref: Reference identifying the exact source artifact.
    """

    source_kind: str
    source_ref: str


@dataclass(frozen=True)
class ClinicalValue:
    """A clinical value paired with its certainty and provenance.

    Attributes:
        value: The raw clinical value as extracted from the source.
        certainty: Confidence assessment of the value.
        missingness: Data-presence semantics of the value.
        provenance: Attribution to the source of the value.
    """

    value: Any
    certainty: Certainty
    missingness: Missingness
    provenance: Provenance
