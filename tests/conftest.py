"""Shared test fixtures for the clinical_compiler test suite."""

from collections.abc import Callable
from typing import Any

import pytest

from clinical_compiler.core.types import (
    Certainty,
    ClinicalValue,
    Missingness,
    Provenance,
)


@pytest.fixture
def make_provenance() -> Callable[..., Provenance]:
    """Factory fixture building ``Provenance`` records with defaults."""

    def _make(
        source_kind: str = "monitor",
        source_ref: str = "m-1",
    ) -> Provenance:
        """Build a Provenance with the given or default fields."""
        return Provenance(source_kind=source_kind, source_ref=source_ref)

    return _make


@pytest.fixture
def make_clinical_value(
    make_provenance: Callable[..., Provenance],
) -> Callable[..., ClinicalValue]:
    """Factory fixture building ``ClinicalValue`` records with defaults."""

    def _make(
        value: Any = "72 bpm",
        certainty: Certainty = Certainty.PROBABLE,
        missingness: Missingness = Missingness.PRESENT,
        provenance: Provenance | None = None,
    ) -> ClinicalValue:
        """Build a ClinicalValue with the given or default fields."""
        return ClinicalValue(
            value=value,
            certainty=certainty,
            missingness=missingness,
            provenance=provenance or make_provenance(),
        )

    return _make
