# tests/unit/test_ir.py

from dataclasses import FrozenInstanceError

import pytest

from clinical_compiler.core.ir import (
    CanonicalClinicalFact,
    DocumentEntry,
    DocumentIR,
    SourceFactIR,
)
from clinical_compiler.core.types import (
    Certainty,
    ClinicalValue,
    Missingness,
    Provenance,
)


def test_document_ir_references_facts_instead_of_storing_values() -> None:
    """DocumentIR entries reference facts by id, never store values."""
    entry = DocumentEntry(
        clinical_fact_ref="fact-001",
        presentation_role="hemodynamics",
    )

    document = DocumentIR(
        document_mode="NURSING_RECORD_TELEGRAPHIC",
        entries=(entry,),
    )

    assert document.entries[0].clinical_fact_ref == "fact-001"


def make_clinical_value() -> ClinicalValue:
    """Build a representative clinical value for IR tests."""
    return ClinicalValue(
        value="72 bpm",
        certainty=Certainty.PROBABLE,
        missingness=Missingness.PRESENT,
        provenance=Provenance(source_kind="monitor", source_ref="m-9"),
    )


def test_source_fact_ir_keeps_raw_value_and_provenance() -> None:
    """SourceFactIR preserves the raw value and its attribution."""
    provenance = Provenance(source_kind="clinical_note", source_ref="note-3")
    source_fact = SourceFactIR(
        fact_id="raw-1",
        field_id="heart_rate",
        raw_value="FC 72",
        provenance=provenance,
    )
    assert source_fact.raw_value == "FC 72"
    assert source_fact.provenance is provenance


def test_source_fact_ir_is_immutable() -> None:
    """SourceFactIR mutation is rejected by the frozen contract."""
    source_fact = SourceFactIR(
        fact_id="raw-1",
        field_id="heart_rate",
        raw_value="FC 72",
        provenance=Provenance(source_kind="monitor", source_ref="m-9"),
    )
    with pytest.raises(FrozenInstanceError):
        source_fact.raw_value = "FC 80"  # type: ignore[misc]


def test_canonical_fact_references_its_source_facts() -> None:
    """CanonicalClinicalFact lists the source facts supporting it."""
    canonical = CanonicalClinicalFact(
        clinical_fact_id="fact-001",
        field_id="heart_rate",
        value=make_clinical_value(),
        source_fact_refs=("raw-1", "raw-2"),
    )
    assert canonical.source_fact_refs == ("raw-1", "raw-2")
    assert canonical.value.certainty is Certainty.PROBABLE


def test_canonical_fact_is_immutable() -> None:
    """CanonicalClinicalFact mutation is rejected by the frozen contract."""
    canonical = CanonicalClinicalFact(
        clinical_fact_id="fact-001",
        field_id="heart_rate",
        value=make_clinical_value(),
        source_fact_refs=("raw-1",),
    )
    with pytest.raises(FrozenInstanceError):
        canonical.source_fact_refs = ()  # type: ignore[misc]


def test_document_entry_is_immutable() -> None:
    """DocumentEntry mutation is rejected by the frozen contract."""
    entry = DocumentEntry(
        clinical_fact_ref="fact-001",
        presentation_role="hemodynamics",
    )
    with pytest.raises(FrozenInstanceError):
        entry.presentation_role = "vitals"  # type: ignore[misc]


def test_document_ir_holds_ordered_entries() -> None:
    """DocumentIR preserves entry order and is frozen."""
    first = DocumentEntry(clinical_fact_ref="fact-1", presentation_role="a")
    second = DocumentEntry(clinical_fact_ref="fact-2", presentation_role="b")
    document = DocumentIR(
        document_mode="NURSING_RECORD_TELEGRAPHIC",
        entries=(first, second),
    )
    assert [entry.clinical_fact_ref for entry in document.entries] == [
        "fact-1",
        "fact-2",
    ]
    with pytest.raises(FrozenInstanceError):
        document.entries = ()  # type: ignore[misc]
