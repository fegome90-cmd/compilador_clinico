"""Unit tests for clinical_compiler.core.types."""

from dataclasses import FrozenInstanceError

import pytest

from clinical_compiler.core.types import (
    Certainty,
    ClinicalValue,
    Missingness,
    Provenance,
)


@pytest.mark.parametrize(
    "enum_type",
    [Certainty, Missingness],
)
def test_clinical_enums_have_unique_nonempty_values(
    enum_type: type[Certainty] | type[Missingness],
) -> None:
    """Every enum member maps to a distinct, non-empty string value."""
    values = [member.value for member in enum_type]
    assert len(values) == len(set(values))
    assert all(value != "" for value in values)


def test_certainty_membership_is_stable() -> None:
    """Certainty taxonomy is a closed clinical contract."""
    assert set(Certainty) == {
        Certainty.CANDIDATE,
        Certainty.UNRESOLVED,
        Certainty.LIKELY,
        Certainty.UNLIKELY,
        Certainty.CONFIRMED,
        Certainty.PROBABLE,
        Certainty.AMBIGUOUS,
    }


def test_missingness_distinguishes_unassessed_from_absent() -> None:
    """Unassessed states are distinct from assessed absence states."""
    unassessed = {Missingness.UNKNOWN, Missingness.NOT_ASSESSED}
    assessed_absent = {Missingness.MISSING, Missingness.NOT_APPLICABLE}
    assert unassessed.isdisjoint(assessed_absent)
    assert Missingness.PRESENT not in unassessed | assessed_absent


def test_provenance_holds_source_attribution() -> None:
    """Provenance records its kind and reference verbatim."""
    provenance = Provenance(source_kind="lab", source_ref="lab-2026-081")
    assert provenance.source_kind == "lab"
    assert provenance.source_ref == "lab-2026-081"


def test_provenance_is_immutable() -> None:
    """Provenance mutation is rejected by the frozen contract."""
    provenance = Provenance(source_kind="lab", source_ref="lab-2026-081")
    with pytest.raises(FrozenInstanceError):
        provenance.source_ref = "other"  # type: ignore[misc]


def test_clinical_value_pairs_value_with_assessment() -> None:
    """ClinicalValue keeps value, assessment, and provenance together."""
    provenance = Provenance(source_kind="clinical_note", source_ref="note-7")
    clinical_value = ClinicalValue(
        value="TA 120/80",
        certainty=Certainty.CONFIRMED,
        missingness=Missingness.PRESENT,
        provenance=provenance,
    )
    assert clinical_value.value == "TA 120/80"
    assert clinical_value.certainty is Certainty.CONFIRMED
    assert clinical_value.missingness is Missingness.PRESENT
    assert clinical_value.provenance is provenance


def test_clinical_value_is_immutable() -> None:
    """ClinicalValue mutation is rejected by the frozen contract."""
    clinical_value = ClinicalValue(
        value=98,
        certainty=Certainty.LIKELY,
        missingness=Missingness.PRESENT,
        provenance=Provenance(source_kind="monitor", source_ref="m-1"),
    )
    with pytest.raises(FrozenInstanceError):
        clinical_value.value = 99  # type: ignore[misc]
