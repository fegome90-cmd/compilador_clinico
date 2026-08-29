"""Unit tests for clinical_compiler.adapters.contract."""

from collections.abc import Callable
from dataclasses import FrozenInstanceError, fields

import pytest

from clinical_compiler.adapters.contract import (
    ALLOWED_SOURCE_KINDS,
    CONTRACT,
    REQUIRED_RECORD_KEYS,
    ContractEvaluation,
    FieldContract,
    StructuredFeedFact,
    map_record,
)
from clinical_compiler.core.diagnostics import DiagnosticCode
from clinical_compiler.core.ir import SourceFactIR
from clinical_compiler.core.types import Certainty, Provenance

VALID_RECORD: dict[str, object] = {
    "fact_id": "raw-1",
    "field_id": "FC",
    "raw_value": 72,
    "provenance": {"source_kind": "monitor", "source_ref": "m-9"},
}


def _record(**overrides: object) -> dict[str, object]:
    """Build a contract-conformant FC record with the given overrides."""
    record = dict(VALID_RECORD)
    record.update(overrides)
    return record


def _record_without(key: str) -> dict[str, object]:
    """Build a conformant record with one required key removed."""
    record = _record()
    del record[key]
    return record


def _accepted(evaluation: ContractEvaluation) -> StructuredFeedFact:
    """Assert acceptance and return the mapped fact."""
    assert evaluation.diagnostic is None
    assert evaluation.fact is not None
    return evaluation.fact


def _rejected_code(evaluation: ContractEvaluation) -> DiagnosticCode:
    """Assert rejection and return the emitted diagnostic code."""
    assert evaluation.fact is None
    assert evaluation.diagnostic is not None
    return evaluation.diagnostic.code


# --- Frozen contract surface -------------------------------------------------


def test_required_record_keys_are_frozen() -> None:
    """The record contract requires exactly the four fact-shape keys."""
    assert REQUIRED_RECORD_KEYS == frozenset(
        {"fact_id", "field_id", "raw_value", "provenance"}
    )


def test_source_kind_vocabulary_is_frozen() -> None:
    """Only kinds with a frozen interpretation rule are admissible."""
    assert ALLOWED_SOURCE_KINDS == frozenset({"monitor", "lab", "clinical_note"})


def test_contract_table_freezes_the_field_vocabulary() -> None:
    """The per-field table pins field ids and their raw-value types."""
    assert set(CONTRACT) == {"FC", "TA"}
    fc_contract = CONTRACT["FC"]
    assert isinstance(fc_contract, FieldContract)
    assert fc_contract.raw_value_types == (int, float)
    assert CONTRACT["TA"].raw_value_types == (str,)


# --- Verbatim ingestion (Driving Adapter scenario) ---------------------------


def test_valid_record_maps_to_source_fact_ir(
    make_provenance: Callable[..., Provenance],
) -> None:
    """A conformant record becomes a SourceFactIR preserving every field."""
    fact = _accepted(map_record(_record())).fact
    assert isinstance(fact, SourceFactIR)
    assert fact.fact_id == "raw-1"
    assert fact.field_id == "FC"
    assert fact.raw_value == 72
    assert fact.provenance == make_provenance(source_kind="monitor", source_ref="m-9")


def test_float_raw_value_is_admissible_for_numeric_field() -> None:
    """Non-integer numerics satisfy the numeric field contract."""
    assert _accepted(map_record(_record(raw_value=72.5))).fact.raw_value == 72.5


def test_string_raw_value_is_admissible_for_ta() -> None:
    """TA accepts telegraphic string readings such as ``120/80``."""
    evaluation = map_record(_record(field_id="TA", raw_value="120/80"))
    assert _accepted(evaluation).fact.raw_value == "120/80"


def test_absence_marker_is_admissible_and_preserved_verbatim() -> None:
    """An explicit null raw value is the assessed-absence assertion (PC-2)."""
    evaluation = map_record(_record(field_id="TA", raw_value=None))
    assert _accepted(evaluation).fact.raw_value is None


def test_lab_and_clinical_note_provenance_are_admissible() -> None:
    """Every frozen source kind maps without special casing."""
    for kind in ("lab", "clinical_note"):
        provenance: dict[str, object] = {"source_kind": kind, "source_ref": "s-1"}
        fact = _accepted(map_record(_record(provenance=provenance))).fact
        assert fact.provenance.source_kind == kind


# --- FC-01: missing required contract key ------------------------------------


@pytest.mark.parametrize("key", sorted(REQUIRED_RECORD_KEYS))
def test_missing_required_key_is_input_contract_error(key: str) -> None:
    """Each required key is individually enforced (FC-01)."""
    assert _rejected_code(map_record(_record_without(key))) is (
        DiagnosticCode.INPUT_CONTRACT_ERROR
    )


# --- FC-02: unknown key outside the contract ---------------------------------


def test_unknown_key_is_input_contract_error() -> None:
    """Extra keys such as ``x_priority`` are rejected (FC-02)."""
    assert _rejected_code(map_record(_record(x_priority="high"))) is (
        DiagnosticCode.INPUT_CONTRACT_ERROR
    )


def test_non_string_key_is_input_contract_error() -> None:
    """Non-string keys never crash the evaluation; they are rejected."""
    record: dict[str, object] = {**_record(), 7: "x"}
    assert _rejected_code(map_record(record)) is DiagnosticCode.INPUT_CONTRACT_ERROR


# --- FC-03 / FC-04: structurally malformed / free text ------------------------


@pytest.mark.parametrize(
    "record",
    [
        "paciente estable, creo que mejoró algo",
        ["fact_id"],
        42,
        object(),
    ],
)
def test_non_object_record_is_input_contract_error(record: object) -> None:
    """Free text (FC-04) and non-object shapes (FC-03) are rejected."""
    assert _rejected_code(map_record(record)) is DiagnosticCode.INPUT_CONTRACT_ERROR


# --- Wrong key types / unknown fields -----------------------------------------


@pytest.mark.parametrize("key", ["fact_id", "field_id"])
def test_non_string_identifier_is_input_contract_error(key: str) -> None:
    """Identifiers must be strings."""
    assert _rejected_code(map_record(_record(**{key: 7}))) is (
        DiagnosticCode.INPUT_CONTRACT_ERROR
    )


def test_field_outside_frozen_vocabulary_is_input_contract_error() -> None:
    """The contract is closed: unknown field ids are rejected."""
    assert _rejected_code(map_record(_record(field_id="XYZ", raw_value=1))) is (
        DiagnosticCode.INPUT_CONTRACT_ERROR
    )


# --- Provenance rules ---------------------------------------------------------


@pytest.mark.parametrize(
    "provenance",
    [
        ["monitor", "m-9"],
        {"source_kind": "monitor"},
        {"source_kind": "monitor", "source_ref": "m-9", "x": 1},
        {"source_kind": "whatsapp", "source_ref": "m-9"},
        {"source_kind": 5, "source_ref": "m-9"},
        {"source_kind": "monitor", "source_ref": 5},
    ],
)
def test_provenance_outside_contract_is_input_contract_error(
    provenance: object,
) -> None:
    """Provenance must be an object with exactly the frozen keys."""
    assert _rejected_code(map_record(_record(provenance=provenance))) is (
        DiagnosticCode.INPUT_CONTRACT_ERROR
    )


# --- FC-05 / CRC-006: runtime value boundary ----------------------------------


def test_bool_raw_value_for_numeric_field_is_type_error() -> None:
    """``raw_value: true`` for numeric FC is a TYPE_ERROR (FC-05).

    Guards the bool-is-int trap: bool is an int subclass, so a naive
    ``isinstance`` check would silently admit it.
    """
    assert _rejected_code(map_record(_record(raw_value=True))) is (
        DiagnosticCode.TYPE_ERROR
    )


def test_arbitrary_object_raw_value_is_type_error() -> None:
    """An arbitrary Python object never passes the boundary (CRC-006)."""
    assert _rejected_code(map_record(_record(raw_value=object()))) is (
        DiagnosticCode.TYPE_ERROR
    )


@pytest.mark.parametrize(
    ("field_id", "raw_value"),
    [("FC", "72"), ("TA", 120), ("TA", 72.5)],
)
def test_raw_value_outside_field_contract_is_type_error(
    field_id: str,
    raw_value: object,
) -> None:
    """Value types are bounded per field, not per record."""
    evaluation = map_record(_record(field_id=field_id, raw_value=raw_value))
    assert _rejected_code(evaluation) is DiagnosticCode.TYPE_ERROR


# --- Certainty authority model (CRC-002) ---------------------------------------


@pytest.mark.parametrize("declared", ["confirmed", "candidate", "unresolved"])
def test_source_asserted_certainty_is_preserved_verbatim(declared: str) -> None:
    """A declared certainty is captured verbatim, never rewritten."""
    evaluation = map_record(_record(source_asserted_certainty=declared))
    assert _accepted(evaluation).source_asserted_certainty is Certainty(declared)


def test_absent_source_asserted_certainty_is_never_invented() -> None:
    """Without a declaration the capture stays ``None``."""
    assert _accepted(map_record(_record())).source_asserted_certainty is None


@pytest.mark.parametrize("declared", [42, "maybe", None])
def test_invalid_source_asserted_certainty_is_input_contract_error(
    declared: object,
) -> None:
    """A present certainty key must hold a taxonomy member name."""
    assert _rejected_code(map_record(_record(source_asserted_certainty=declared))) is (
        DiagnosticCode.INPUT_CONTRACT_ERROR
    )


def test_certainty_never_lands_on_the_source_fact_ir() -> None:
    """Certainty stays on its own axis: the frozen IR has no slot for it."""
    fact = _accepted(
        map_record(_record(source_asserted_certainty="confirmed"))
    ).fact
    assert [field.name for field in fields(fact)] == [
        "fact_id",
        "field_id",
        "raw_value",
        "provenance",
    ]


# --- Determinism / immutability -------------------------------------------------


def test_mapping_is_deterministic_and_key_order_independent() -> None:
    """Identical inputs evaluate identically, regardless of key order."""
    first = map_record(_record())
    assert first == map_record(_record())
    reordered: dict[str, object] = {
        "provenance": {"source_ref": "m-9", "source_kind": "monitor"},
        "raw_value": 72,
        "field_id": "FC",
        "fact_id": "raw-1",
    }
    assert map_record(reordered) == first
    faulty = _record(raw_value=True)
    assert map_record(faulty) == map_record(faulty)


def test_structured_feed_fact_is_immutable() -> None:
    """The mapped fact wrapper rejects mutation."""
    wrapped = _accepted(map_record(_record()))
    with pytest.raises(FrozenInstanceError):
        wrapped.source_asserted_certainty = Certainty.CONFIRMED  # type: ignore[misc]


def test_contract_evaluation_is_immutable() -> None:
    """The evaluation result rejects mutation."""
    evaluation = map_record(_record())
    with pytest.raises(FrozenInstanceError):
        evaluation.diagnostic = None  # type: ignore[misc]
