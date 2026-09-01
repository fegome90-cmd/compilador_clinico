# tests/unit/test_ir.py

from collections.abc import Callable
from dataclasses import FrozenInstanceError, fields, is_dataclass

import pytest

from clinical_compiler.core.ir import (
    CanonicalClinicalFact,
    CanonicalClinicalIR,
    DocumentEntry,
    DocumentIR,
    SourceFactIR,
)
from clinical_compiler.core.types import Certainty, ClinicalValue, Provenance


def _canonical_fact(
    value: ClinicalValue,
    clinical_fact_id: str = "fact-001",
    field_id: str = "heart_rate",
    source_fact_refs: tuple[str, ...] = ("raw-1",),
) -> CanonicalClinicalFact:
    """Build a CanonicalClinicalFact with sensible test defaults."""
    return CanonicalClinicalFact(
        clinical_fact_id=clinical_fact_id,
        field_id=field_id,
        value=value,
        source_fact_refs=source_fact_refs,
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


def test_source_fact_ir_keeps_raw_value_and_provenance(
    make_provenance: Callable[..., Provenance],
) -> None:
    """SourceFactIR preserves the raw value and its attribution."""
    provenance = make_provenance(source_kind="clinical_note", source_ref="note-3")
    source_fact = SourceFactIR(
        fact_id="raw-1",
        field_id="heart_rate",
        raw_value="FC 72",
        provenance=provenance,
    )
    assert source_fact.raw_value == "FC 72"
    assert source_fact.provenance is provenance


def test_source_fact_ir_is_immutable(
    make_provenance: Callable[..., Provenance],
) -> None:
    """SourceFactIR mutation is rejected by the frozen contract."""
    source_fact = SourceFactIR(
        fact_id="raw-1",
        field_id="heart_rate",
        raw_value="FC 72",
        provenance=make_provenance(),
    )
    with pytest.raises(FrozenInstanceError):
        source_fact.raw_value = "FC 80"  # type: ignore[misc]


def test_canonical_fact_references_its_source_facts(
    make_clinical_value: Callable[..., ClinicalValue],
) -> None:
    """CanonicalClinicalFact lists the source facts supporting it."""
    canonical = CanonicalClinicalFact(
        clinical_fact_id="fact-001",
        field_id="heart_rate",
        value=make_clinical_value(),
        source_fact_refs=("raw-1", "raw-2"),
    )
    assert canonical.source_fact_refs == ("raw-1", "raw-2")
    assert canonical.value.certainty is Certainty.PROBABLE


def test_canonical_fact_is_immutable(
    make_clinical_value: Callable[..., ClinicalValue],
) -> None:
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


def test_canonical_ir_duplicate_fact_ids_fail_construction(
    make_clinical_value: Callable[..., ClinicalValue],
) -> None:
    """Two facts sharing a clinical_fact_id block construction (fail-closed)."""
    first = _canonical_fact(
        make_clinical_value(),
        clinical_fact_id="fact-001",
        field_id="heart_rate",
    )
    second = _canonical_fact(
        make_clinical_value(),
        clinical_fact_id="fact-001",
        field_id="blood_pressure",
    )
    with pytest.raises(ValueError, match="duplicate clinical_fact_id"):
        CanonicalClinicalIR(facts=(first, second))


@pytest.mark.parametrize(
    ("source_fact_refs", "match"),
    [
        pytest.param((), "no source_fact_refs", id="no-refs"),
        pytest.param(("",), "empty source_fact_ref", id="empty-ref"),
    ],
)
def test_canonical_ir_lineage_invalid_fact_fails_construction(
    make_clinical_value: Callable[..., ClinicalValue],
    source_fact_refs: tuple[str, ...],
    match: str,
) -> None:
    """A lineage-invalid fact is carried by no constructed aggregate."""
    lineage_invalid = _canonical_fact(
        make_clinical_value(),
        source_fact_refs=source_fact_refs,
    )
    with pytest.raises(ValueError, match=match):
        CanonicalClinicalIR(facts=(lineage_invalid,))


def test_canonical_ir_carries_clinical_facts_only(
    make_clinical_value: Callable[..., ClinicalValue],
) -> None:
    """The aggregate carries facts only — no prose, no document_mode."""
    fact = _canonical_fact(make_clinical_value())
    ir = CanonicalClinicalIR(facts=(fact,))
    assert [field.name for field in fields(CanonicalClinicalIR)] == ["facts"]
    assert not hasattr(ir, "document_mode")
    assert all(isinstance(item, CanonicalClinicalFact) for item in ir.facts)
    with pytest.raises(TypeError):
        CanonicalClinicalIR(  # type: ignore[call-arg]
            facts=(fact,),
            document_mode="NURSING_RECORD_TELEGRAPHIC",
        )


def test_canonical_ir_representation_is_deterministic(
    make_clinical_value: Callable[..., ClinicalValue],
) -> None:
    """The same fact set constructs to identical orderings every time."""
    heart_rate_b = _canonical_fact(
        make_clinical_value(),
        clinical_fact_id="hr-b",
        field_id="heart_rate",
    )
    heart_rate_a = _canonical_fact(
        make_clinical_value(),
        clinical_fact_id="hr-a",
        field_id="heart_rate",
    )
    blood_pressure = _canonical_fact(
        make_clinical_value(),
        clinical_fact_id="ta-1",
        field_id="blood_pressure",
    )
    forward = CanonicalClinicalIR(
        facts=(heart_rate_b, heart_rate_a, blood_pressure),
    )
    backward = CanonicalClinicalIR(
        facts=(blood_pressure, heart_rate_b, heart_rate_a),
    )
    assert forward.facts == (blood_pressure, heart_rate_a, heart_rate_b)
    assert forward.facts == backward.facts
    assert forward == backward


def test_canonical_ir_is_immutable(
    make_clinical_value: Callable[..., ClinicalValue],
) -> None:
    """CanonicalClinicalIR mutation is rejected by the frozen contract."""
    ir = CanonicalClinicalIR(facts=(_canonical_fact(make_clinical_value()),))
    with pytest.raises(FrozenInstanceError):
        ir.facts = ()  # type: ignore[misc]


def test_canonical_ir_accepts_an_empty_fact_set() -> None:
    """An empty admissible set is representable (no invariants violated)."""
    assert CanonicalClinicalIR(facts=()).facts == ()


def test_canonical_ir_is_a_minimal_plain_frozen_dataclass(
    make_clinical_value: Callable[..., ClinicalValue],
) -> None:
    """Plain frozen dataclass — no framework, no pass manager (MINIMAL)."""
    assert is_dataclass(CanonicalClinicalIR)
    params = CanonicalClinicalIR.__dataclass_params__
    assert params.frozen
    assert hasattr(CanonicalClinicalIR, "__slots__")
    ir = CanonicalClinicalIR(facts=(_canonical_fact(make_clinical_value()),))
    assert type(ir.facts) is tuple
