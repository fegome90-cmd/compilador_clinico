"""Unit tests for clinical_compiler.adapters.structured_feed."""

import json
from collections.abc import Callable
from dataclasses import FrozenInstanceError

import pytest

from clinical_compiler.adapters.contract import (
    ContractEvaluation,
    StructuredFeedFact,
)
from clinical_compiler.adapters.structured_feed import FeedEvaluation, parse_feed
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


def _line(record: dict[str, object]) -> str:
    """Encode one record as a JSONL line."""
    return json.dumps(record)


def _feed(*lines: str) -> bytes:
    """Encode the given lines as feed bytes."""
    return "\n".join(lines).encode("utf-8")


def _clean(result: FeedEvaluation) -> tuple[ContractEvaluation, ...]:
    """Assert no feed-level fault and return the per-record evaluations."""
    assert result.diagnostic is None
    return result.records


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


# --- Verbatim ingestion (Driving Adapter scenario) ---------------------------


def test_valid_feed_bytes_map_to_candidate_source_facts(
    make_provenance: Callable[..., Provenance],
) -> None:
    """The spec's monitor facts ``FC 72`` and ``TA 120/80`` map verbatim."""
    feed = _feed(
        _line(_record(fact_id="raw-1", field_id="FC", raw_value=72)),
        _line(_record(fact_id="raw-2", field_id="TA", raw_value="120/80")),
    )
    records = _clean(parse_feed(feed))
    assert len(records) == 2
    first = _accepted(records[0]).fact
    assert isinstance(first, SourceFactIR)
    assert first.fact_id == "raw-1"
    assert first.field_id == "FC"
    assert first.raw_value == 72
    assert first.provenance == make_provenance(source_kind="monitor", source_ref="m-9")
    second = _accepted(records[1]).fact
    assert second.field_id == "TA"
    assert second.raw_value == "120/80"


def test_records_preserve_encounter_order() -> None:
    """The record sequence is feed-ordered, never reordered."""
    feed = _feed(
        _line(_record(fact_id="raw-2")),
        _line(_record(fact_id="raw-1")),
    )
    records = _clean(parse_feed(feed))
    assert _accepted(records[0]).fact.fact_id == "raw-2"
    assert _accepted(records[1]).fact.fact_id == "raw-1"


def test_declared_certainty_is_carried_through_the_feed() -> None:
    """A declared certainty reaches the wrapper verbatim (CRC-002)."""
    feed = _feed(_line(_record(source_asserted_certainty="confirmed")))
    wrapped = _accepted(_clean(parse_feed(feed))[0])
    assert wrapped.source_asserted_certainty is Certainty.CONFIRMED


def test_absent_certainty_stays_none_through_the_feed() -> None:
    """No declaration means no invented certainty (CRC-002)."""
    feed = _feed(_line(_record()))
    assert _accepted(_clean(parse_feed(feed))[0]).source_asserted_certainty is None


# --- Empty input ---------------------------------------------------------------


def test_empty_feed_yields_no_records_and_no_diagnostic() -> None:
    """Zero bytes is an empty feed, not a fault at the adapter stage."""
    result = parse_feed(b"")
    assert result.records == ()
    assert result.diagnostic is None


def test_blank_lines_are_not_records() -> None:
    """Whitespace-only lines carry no record and raise no diagnostic."""
    result = parse_feed(b"\n   \n\t\n")
    assert result.records == ()
    assert result.diagnostic is None


def test_trailing_newline_does_not_add_a_record() -> None:
    """A universal trailing newline must not become a phantom record."""
    feed = _feed(_line(_record())) + b"\n"
    assert len(_clean(parse_feed(feed))) == 1


# --- FC-03 bytes-level faults (whole-feed quarantine) --------------------------


def test_undecodable_bytes_is_feed_level_input_contract_error() -> None:
    """Bytes that are not UTF-8 fault the whole feed (FC-03)."""
    result = parse_feed(b"\xff\xfe\xfa")
    assert result.records == ()
    assert result.diagnostic is not None
    assert result.diagnostic.code is DiagnosticCode.INPUT_CONTRACT_ERROR


def test_feed_level_fault_admits_no_records() -> None:
    """A decodable tail never rescues an undecodable feed."""
    result = parse_feed(b"\xff" + _line(_record()).encode("utf-8"))
    assert result.records == ()
    assert result.diagnostic is not None
    assert result.diagnostic.code is DiagnosticCode.INPUT_CONTRACT_ERROR


# --- FC-03 record-level structural faults ---------------------------------------


def test_top_level_json_array_line_is_input_contract_error() -> None:
    """A JSON array of records is structurally malformed (FC-03)."""
    line = json.dumps([_record(), _record(fact_id="raw-2")])
    records = _clean(parse_feed(_feed(line)))
    assert _rejected_code(records[0]) is DiagnosticCode.INPUT_CONTRACT_ERROR


@pytest.mark.parametrize("scalar", ["42", '"un texto"', "true", "null"])
def test_non_object_json_line_is_input_contract_error(scalar: str) -> None:
    """JSON scalars are not records: rejected, never guessed (FC-03)."""
    records = _clean(parse_feed(_feed(scalar)))
    assert _rejected_code(records[0]) is DiagnosticCode.INPUT_CONTRACT_ERROR


def test_malformed_json_line_is_input_contract_error() -> None:
    """A line that is not JSON at all is rejected (FC-03)."""
    records = _clean(parse_feed(_feed("{not json")))
    assert _rejected_code(records[0]) is DiagnosticCode.INPUT_CONTRACT_ERROR


def test_malformed_line_message_pins_the_feed_line_number() -> None:
    """Diagnostic messages are deterministic and locate the faulty line."""
    records = _clean(parse_feed(_feed(_line(_record()), "{not json")))
    diagnostic = records[1].diagnostic
    assert diagnostic is not None
    assert "line 2" in diagnostic.message


# --- FC-04: free text is rejected by the structured branch ----------------------


def test_free_text_line_is_input_contract_error() -> None:
    """Unquoted prose is not admissible structured input (FC-04)."""
    feed = _feed("paciente estable, creo que mejoró algo")
    records = _clean(parse_feed(feed))
    assert _rejected_code(records[0]) is DiagnosticCode.INPUT_CONTRACT_ERROR


def test_quoted_free_text_line_is_input_contract_error() -> None:
    """Even JSON-encoded prose is a non-object record (FC-04)."""
    line = json.dumps("paciente estable, creo que mejoró algo")
    records = _clean(parse_feed(_feed(line)))
    assert _rejected_code(records[0]) is DiagnosticCode.INPUT_CONTRACT_ERROR


def test_multiline_prose_blocks_only_its_own_lines() -> None:
    """Each prose line is its own rejected record; clean lines survive."""
    feed = _feed(
        _line(_record()),
        "paciente estable",
        "creo que mejoró algo",
    )
    records = _clean(parse_feed(feed))
    assert _accepted(records[0]).fact.fact_id == "raw-1"
    assert _rejected_code(records[1]) is DiagnosticCode.INPUT_CONTRACT_ERROR
    assert _rejected_code(records[2]) is DiagnosticCode.INPUT_CONTRACT_ERROR


# --- Per-record quarantine (design D1) ------------------------------------------


def test_one_faulty_record_does_not_kill_the_feed() -> None:
    """Quarantine is per record: survivors keep mapping (D1)."""
    feed = _feed(
        _line(_record(fact_id="raw-1")),
        "{not json",
        _line(_record(fact_id="raw-2")),
    )
    records = _clean(parse_feed(feed))
    assert len(records) == 3
    assert _accepted(records[0]).fact.fact_id == "raw-1"
    assert _rejected_code(records[1]) is DiagnosticCode.INPUT_CONTRACT_ERROR
    assert _accepted(records[2]).fact.fact_id == "raw-2"


def test_record_contract_faults_flow_through_the_frozen_mapping() -> None:
    """Record-level FC-01/FC-02/FC-05 keep their contract-mapped codes."""
    missing_field_id = {k: v for k, v in _record().items() if k != "field_id"}
    feed = _feed(
        _line(missing_field_id),
        _line(_record(x_priority="high")),
        _line(_record(raw_value=True)),
    )
    records = _clean(parse_feed(feed))
    assert _rejected_code(records[0]) is DiagnosticCode.INPUT_CONTRACT_ERROR
    assert _rejected_code(records[1]) is DiagnosticCode.INPUT_CONTRACT_ERROR
    assert _rejected_code(records[2]) is DiagnosticCode.TYPE_ERROR


# --- No semantic normalization (Phase 2 owns that) ------------------------------


@pytest.mark.parametrize(
    ("field_id", "raw_value"),
    [("FC", 9999), ("FC", 72.5), ("TA", "quizas alto")],
)
def test_contract_valid_but_semantically_odd_values_pass_verbatim(
    field_id: str,
    raw_value: object,
) -> None:
    """The adapter never judges clinical plausibility."""
    feed = _feed(_line(_record(field_id=field_id, raw_value=raw_value)))
    assert _accepted(_clean(parse_feed(feed))[0]).fact.raw_value == raw_value


def test_absence_marker_passes_through_untouched() -> None:
    """An explicit null raw value stays the assessed-absence marker (PC-2)."""
    feed = _feed(_line(_record(field_id="TA", raw_value=None)))
    assert _accepted(_clean(parse_feed(feed))[0]).fact.raw_value is None


# --- Determinism -----------------------------------------------------------------


def test_parsing_is_deterministic() -> None:
    """Identical bytes evaluate identically, faults included."""
    feed = _feed(
        _line(_record()),
        "paciente estable",
        _line(_record(raw_value=True)),
    )
    assert parse_feed(feed) == parse_feed(feed)


def test_feed_level_faults_are_deterministic() -> None:
    """Undecodable bytes yield the identical evaluation every run."""
    assert parse_feed(b"\xff\xfe") == parse_feed(b"\xff\xfe")


# --- Immutability ------------------------------------------------------------------


def test_feed_evaluation_is_immutable() -> None:
    """The feed-level result rejects mutation."""
    result = parse_feed(b"")
    with pytest.raises(FrozenInstanceError):
        result.diagnostic = None  # type: ignore[misc]
