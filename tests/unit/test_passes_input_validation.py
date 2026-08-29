"""Unit tests for clinical_compiler.passes.input_validation."""

from collections.abc import Callable
from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from clinical_compiler.adapters.structured_feed import parse_feed
from clinical_compiler.core.diagnostics import DiagnosticCode
from clinical_compiler.core.ir import SourceFactIR
from clinical_compiler.core.types import Provenance
from clinical_compiler.passes.input_validation import run_input_validation
from clinical_compiler.pipeline_types import StageResult

VALID_FACT = SourceFactIR(
    fact_id="raw-1",
    field_id="FC",
    raw_value=72,
    provenance=Provenance(source_kind="monitor", source_ref="m-9"),
)


def _fact(**overrides: object) -> SourceFactIR:
    """Build a contract-valid FC fact with the given field overrides."""
    params: dict[str, object] = {
        "fact_id": "raw-1",
        "field_id": "FC",
        "raw_value": 72,
        "provenance": Provenance(source_kind="monitor", source_ref="m-9"),
    }
    params.update(overrides)
    return SourceFactIR(
        fact_id=cast(str, params["fact_id"]),
        field_id=cast(str, params["field_id"]),
        raw_value=params["raw_value"],
        provenance=cast(Provenance, params["provenance"]),
    )


def _adapter_facts(*lines: str) -> tuple[SourceFactIR, ...]:
    """Map JSONL ``lines`` through the real adapter into facts."""
    result = parse_feed("\n".join(lines).encode("utf-8"))
    assert result.diagnostic is None
    return tuple(e.fact.fact for e in result.records if e.fact is not None)


def _codes(result: StageResult[SourceFactIR]) -> tuple[DiagnosticCode, ...]:
    """Return the emitted diagnostic codes in encounter order."""
    return tuple(d.code for d in result.diagnostics)


def _admitted_ids(result: StageResult[SourceFactIR]) -> tuple[str, ...]:
    """Return the fact ids of the admitted survivors, in order."""
    return tuple(f.fact_id for f in result.admitted)


# --- Stage contract (pipeline_types — G-1 leaf placement) ----------------------


def test_stage_result_is_immutable() -> None:
    """The shared stage contract rejects mutation."""
    result = StageResult(admitted=(), diagnostics=())
    with pytest.raises(FrozenInstanceError):
        result.admitted = (VALID_FACT,)  # type: ignore[misc]


def test_validation_returns_a_stage_result() -> None:
    """The stage speaks the shared stage contract, not ad-hoc shapes."""
    result = run_input_validation((VALID_FACT,))
    assert isinstance(result, StageResult)
    assert result.admitted == (VALID_FACT,)
    assert result.diagnostics == ()


# --- Verbatim pass-through (no semantic transformation) ------------------------


def test_adapter_produced_facts_pass_through_unchanged(
    make_provenance: Callable[..., Provenance],
) -> None:
    """Facts the adapter accepted are admitted byte-identically."""
    facts = _adapter_facts(
        '{"fact_id": "raw-1", "field_id": "FC", "raw_value": 72,'
        ' "provenance": {"source_kind": "monitor", "source_ref": "m-9"}}',
        '{"fact_id": "raw-2", "field_id": "TA", "raw_value": "120/80",'
        ' "provenance": {"source_kind": "monitor", "source_ref": "m-9"}}',
    )
    result = run_input_validation(facts)
    assert result.diagnostics == ()
    assert result.admitted == (
        SourceFactIR(
            fact_id="raw-1",
            field_id="FC",
            raw_value=72,
            provenance=make_provenance(source_kind="monitor", source_ref="m-9"),
        ),
        SourceFactIR(
            fact_id="raw-2",
            field_id="TA",
            raw_value="120/80",
            provenance=make_provenance(source_kind="monitor", source_ref="m-9"),
        ),
    )


def test_admitted_facts_are_the_same_objects() -> None:
    """The stage never copies or rewrites a surviving fact."""
    facts = (_fact(), _fact(fact_id="raw-2", field_id="TA", raw_value="120/80"))
    result = run_input_validation(facts)
    assert result.admitted[0] is facts[0]
    assert result.admitted[1] is facts[1]


def test_empty_fact_set_yields_empty_stage_result() -> None:
    """No facts in means nothing admitted and nothing diagnosed."""
    result = run_input_validation(())
    assert result.admitted == ()
    assert result.diagnostics == ()


def test_absence_marker_passes_through_untouched() -> None:
    """An explicit null raw value stays the assessed-absence marker (PC-2)."""
    fact = _fact(fact_id="raw-ta", field_id="TA", raw_value=None)
    result = run_input_validation((fact,))
    assert result.diagnostics == ()
    assert result.admitted[0].raw_value is None


def test_float_raw_value_is_admissible_for_numeric_field() -> None:
    """Non-integer numerics satisfy the numeric field contract."""
    result = run_input_validation((_fact(raw_value=72.5),))
    assert result.diagnostics == ()
    assert result.admitted[0].raw_value == 72.5


def test_lab_and_clinical_note_sources_are_admissible() -> None:
    """Every frozen source kind validates without special casing."""
    for kind in ("lab", "clinical_note"):
        provenance = Provenance(source_kind=kind, source_ref="s-1")
        result = run_input_validation((_fact(provenance=provenance),))
        assert result.diagnostics == ()


# --- Value-contract violations → INPUT_CONTRACT_ERROR ---------------------------


def test_unknown_field_id_is_input_contract_error() -> None:
    """The field vocabulary is closed at the stage boundary too."""
    result = run_input_validation((_fact(field_id="XYZ", raw_value=1),))
    assert _codes(result) == (DiagnosticCode.INPUT_CONTRACT_ERROR,)
    assert result.admitted == ()


def test_non_string_field_id_is_input_contract_error() -> None:
    """A non-string field id never reaches later stages."""
    fact = _fact(field_id=cast(str, 7), raw_value=1)
    result = run_input_validation((fact,))
    assert _codes(result) == (DiagnosticCode.INPUT_CONTRACT_ERROR,)


def test_non_string_fact_id_is_input_contract_error() -> None:
    """Identifiers must be strings per the frozen contract."""
    fact = _fact(fact_id=cast(str, 7))
    result = run_input_validation((fact,))
    assert _codes(result) == (DiagnosticCode.INPUT_CONTRACT_ERROR,)


def test_source_kind_outside_vocabulary_is_input_contract_error() -> None:
    """Provenance is part of the frozen value contract (design D8)."""
    provenance = Provenance(source_kind="whatsapp", source_ref="m-9")
    result = run_input_validation((_fact(provenance=provenance),))
    assert _codes(result) == (DiagnosticCode.INPUT_CONTRACT_ERROR,)


@pytest.mark.parametrize(
    "provenance",
    [
        cast(Provenance, "monitor"),
        cast(Provenance, object()),
        Provenance(source_kind=cast(str, 5), source_ref="m-9"),
        Provenance(source_kind="monitor", source_ref=cast(str, 5)),
    ],
)
def test_malformed_provenance_is_diagnosed_never_raised(
    provenance: Provenance,
) -> None:
    """Unknown shapes surface as diagnostics, never as exceptions (M2.1)."""
    result = run_input_validation((_fact(provenance=provenance),))
    assert _codes(result) == (DiagnosticCode.INPUT_CONTRACT_ERROR,)
    assert result.admitted == ()


# --- Type violations → TYPE_ERROR (FC-05 / CRC-006) ----------------------------


def test_bool_raw_value_for_numeric_field_is_type_error() -> None:
    """``raw_value=True`` for numeric FC is rejected (FC-05).

    Guards the bool-is-int trap: a naive ``isinstance`` check would
    silently admit ``True`` as the numeric reading 1.
    """
    result = run_input_validation((_fact(raw_value=True),))
    assert _codes(result) == (DiagnosticCode.TYPE_ERROR,)
    assert result.admitted == ()


def test_arbitrary_object_raw_value_is_type_error() -> None:
    """An arbitrary Python object never crosses the boundary (CRC-006)."""
    result = run_input_validation((_fact(raw_value=object()),))
    assert _codes(result) == (DiagnosticCode.TYPE_ERROR,)
    assert result.admitted == ()


@pytest.mark.parametrize(
    ("field_id", "raw_value"),
    [("FC", "72"), ("FC", [72]), ("TA", 120), ("TA", 72.5)],
)
def test_raw_value_outside_field_contract_is_type_error(
    field_id: str,
    raw_value: object,
) -> None:
    """Value types are bounded per field at the stage boundary."""
    fact = _fact(field_id=field_id, raw_value=raw_value)
    result = run_input_validation((fact,))
    assert _codes(result) == (DiagnosticCode.TYPE_ERROR,)


def test_type_error_orphan_is_eliminated_by_this_stage() -> None:
    """Task 1.9 evidence: TYPE_ERROR has a producing stage + covering test."""
    result = run_input_validation((_fact(raw_value=True),))
    assert result.diagnostics[0].code is DiagnosticCode.TYPE_ERROR


def test_structural_fault_outranks_type_fault_in_check_order() -> None:
    """A fact with both violations reports the frozen contract's first fault."""
    fact = _fact(field_id="XYZ", raw_value=True)
    result = run_input_validation((fact,))
    assert _codes(result) == (DiagnosticCode.INPUT_CONTRACT_ERROR,)


# --- Per-fact quarantine (design D1 blocking granularity) -----------------------


def test_one_violating_fact_does_not_kill_the_rest() -> None:
    """Quarantine is per fact: survivors continue (D1)."""
    facts = (
        _fact(fact_id="raw-1"),
        _fact(fact_id="raw-bad", raw_value=True),
        _fact(fact_id="raw-2", field_id="TA", raw_value="120/80"),
    )
    result = run_input_validation(facts)
    assert _admitted_ids(result) == ("raw-1", "raw-2")
    assert _codes(result) == (DiagnosticCode.TYPE_ERROR,)


def test_quarantined_fact_is_never_admitted_downstream() -> None:
    """A blocked fact is not consumed by the survivor flow (spec scenario)."""
    blocked = _fact(fact_id="raw-bad", raw_value=True)
    result = run_input_validation((_fact(fact_id="raw-1"), blocked))
    assert blocked not in result.admitted
    assert all(f.fact_id != "raw-bad" for f in result.admitted)


def test_each_fact_yields_fact_xor_diagnostic() -> None:
    """Every input fact partitions exactly: admitted XOR diagnosed."""
    facts = (
        _fact(fact_id="raw-1"),
        _fact(fact_id="raw-bad-contract", field_id="XYZ", raw_value=1),
        _fact(fact_id="raw-bad-type", raw_value=True),
        _fact(fact_id="raw-2"),
    )
    result = run_input_validation(facts)
    assert len(result.admitted) + len(result.diagnostics) == len(facts)
    assert _admitted_ids(result) == ("raw-1", "raw-2")


def test_diagnostics_preserve_encounter_order() -> None:
    """Diagnostic order is the input order, deterministic."""
    facts = (
        _fact(fact_id="raw-bad-type", raw_value=True),
        _fact(fact_id="raw-bad-contract", field_id="XYZ", raw_value=1),
    )
    result = run_input_validation(facts)
    assert _codes(result) == (
        DiagnosticCode.TYPE_ERROR,
        DiagnosticCode.INPUT_CONTRACT_ERROR,
    )


# --- Determinism ----------------------------------------------------------------


def test_validation_is_deterministic() -> None:
    """Identical fact sets — faults included — evaluate identically."""
    facts = (
        _fact(fact_id="raw-1"),
        _fact(fact_id="raw-bad-type", raw_value=True),
        _fact(fact_id="raw-bad-contract", field_id="XYZ", raw_value=1),
    )
    assert run_input_validation(facts) == run_input_validation(facts)
