"""Integration tests for the minimal Phase-1 chain (APPROVAL-PHASE1 Unit 4).

``structured_feed → input_validation → SourceFactIR``: feed bytes parsed
by the driving adapter, its accepted facts re-validated by the first
pipeline stage, asserted end-to-end — positive and negative cases. The
chain is composed INSIDE these tests: Unit 4 builds no pipeline
composition machinery, CLI, renderer, or policy (later units own those).
Placed under ``tests/unit/`` because ``testpaths = ["tests"]`` already
discovers it (smaller change; no pyproject edit) — ``tests/integration/``
stays reserved for the Phase-4 ``pipeline.run`` suite (task 4.2).
"""

import json
from collections.abc import Callable
from dataclasses import dataclass

import pytest

from clinical_compiler.adapters.contract import StructuredFeedFact
from clinical_compiler.adapters.structured_feed import FeedEvaluation, parse_feed
from clinical_compiler.core.diagnostics import DiagnosticCode
from clinical_compiler.core.ir import SourceFactIR
from clinical_compiler.core.types import Certainty, Provenance
from clinical_compiler.passes.input_validation import run_input_validation
from clinical_compiler.pipeline_types import StageResult

pytestmark = pytest.mark.integration

VALID_RECORD: dict[str, object] = {
    "fact_id": "raw-1",
    "field_id": "FC",
    "raw_value": 72,
    "provenance": {"source_kind": "monitor", "source_ref": "m-9"},
}


@dataclass(frozen=True, slots=True)
class ChainOutcome:
    """Outcome of the minimal two-hop chain, composed inside the tests.

    Attributes:
        feed: The adapter's evaluation of the feed bytes.
        accepted: The wrappers the adapter accepted, in encounter order
            — each carrying its CRC-002 ``source_asserted_certainty``.
        stage: The input-validation stage result over the accepted
            wrappers' facts.
    """

    feed: FeedEvaluation
    accepted: tuple[StructuredFeedFact, ...]
    stage: StageResult[SourceFactIR]


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


def _run_chain(data: bytes) -> ChainOutcome:
    """Compose the chain exactly as the design sequence diagram's first hops do.

    Adapter bytes → candidate records; accepted wrappers' facts → the
    input-validation stage. A feed-level fault terminates the chain with
    zero facts — the stage still runs, on the empty survivor set.
    """
    feed = parse_feed(data)
    if feed.diagnostic is not None:
        return ChainOutcome(feed, (), run_input_validation(()))
    accepted = tuple(e.fact for e in feed.records if e.fact is not None)
    stage = run_input_validation(tuple(wrapped.fact for wrapped in accepted))
    return ChainOutcome(feed, accepted, stage)


def _admitted_ids(outcome: ChainOutcome) -> tuple[str, ...]:
    """Return the admitted fact ids in encounter order."""
    return tuple(fact.fact_id for fact in outcome.stage.admitted)


# --- Full positive chain --------------------------------------------------------


def test_valid_feed_chains_to_admitted_source_fact_ir(
    make_provenance: Callable[..., Provenance],
) -> None:
    """Driving Adapter scenario end to end: monitor FC 72 and TA 120/80."""
    outcome = _run_chain(
        _feed(
            _line(_record(fact_id="raw-1", field_id="FC", raw_value=72)),
            _line(
                _record(fact_id="raw-2", field_id="TA", raw_value="120/80")
            ),
        )
    )
    assert outcome.feed.diagnostic is None
    assert outcome.stage.diagnostics == ()
    assert outcome.stage.admitted == (
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


def test_admitted_facts_are_the_adapter_output_unchanged() -> None:
    """The chain never rewrites a surviving fact (D1 verbatim pass-through)."""
    outcome = _run_chain(
        _feed(
            _line(_record(fact_id="raw-1")),
            _line(_record(fact_id="raw-2", field_id="TA", raw_value="120/80")),
        )
    )
    adapter_facts = tuple(wrapped.fact for wrapped in outcome.accepted)
    assert outcome.stage.admitted == adapter_facts
    assert all(
        admitted is fact
        for admitted, fact in zip(
            outcome.stage.admitted, adapter_facts, strict=True
        )
    )


# --- CRC-002: declared certainty preserved alongside the facts ------------------


def test_declared_certainty_is_preserved_alongside_admitted_facts() -> None:
    """CRC-002 (BOTH_SEPARATED): a declared certainty rides the whole chain.

    The stage never touches the wrapper's certainty; the integration pins
    that the admitted fact is the very fact the declared-certainty
    wrapper carries, and the declaration survives verbatim beside it.
    """
    outcome = _run_chain(
        _feed(_line(_record(fact_id="raw-c", source_asserted_certainty="confirmed")))
    )
    wrapper = outcome.accepted[0]
    assert wrapper.source_asserted_certainty is Certainty.CONFIRMED
    assert outcome.stage.admitted == (wrapper.fact,)
    assert outcome.stage.admitted[0].fact_id == "raw-c"


def test_wrapper_certainty_pairing_survives_per_fact() -> None:
    """Declaration pairing is per fact: declared → verbatim, absent → None."""
    outcome = _run_chain(
        _feed(
            _line(
                _record(fact_id="raw-c", source_asserted_certainty="probable")
            ),
            _line(_record(fact_id="raw-plain")),
        )
    )
    assert _admitted_ids(outcome) == ("raw-c", "raw-plain")
    certainty_by_id = {
        wrapper.fact.fact_id: wrapper.source_asserted_certainty
        for wrapper in outcome.accepted
    }
    assert certainty_by_id == {"raw-c": Certainty.PROBABLE, "raw-plain": None}


# --- Mixed feed: per-record quarantine respected end-to-end ---------------------


def test_mixed_feed_quarantine_respected_end_to_end() -> None:
    """Record-level faults quarantine only their own record through the chain."""
    missing_field_id = {k: v for k, v in _record().items() if k != "field_id"}
    outcome = _run_chain(
        _feed(
            _line(_record(fact_id="raw-1")),
            "{not json",
            _line(_record(fact_id="raw-2", field_id="TA", raw_value="120/80")),
            _line(_record(fact_id="raw-x", x_priority="high")),
            _line(missing_field_id),
            _line(_record(fact_id="raw-bad", raw_value=True)),
        )
    )
    record_codes = tuple(
        evaluation.diagnostic.code
        for evaluation in outcome.feed.records
        if evaluation.diagnostic is not None
    )
    assert record_codes == (
        DiagnosticCode.INPUT_CONTRACT_ERROR,  # line 2: not JSON
        DiagnosticCode.INPUT_CONTRACT_ERROR,  # unknown key
        DiagnosticCode.INPUT_CONTRACT_ERROR,  # missing required key
        DiagnosticCode.TYPE_ERROR,  # bool raw_value for numeric FC
    )
    # Every record partitions exactly: accepted XOR diagnosed.
    assert len(outcome.accepted) + len(record_codes) == len(outcome.feed.records)
    # Survivors reach SourceFactIR in encounter order; nothing the
    # adapter quarantined was ever handed to the stage.
    assert _admitted_ids(outcome) == ("raw-1", "raw-2")
    assert outcome.stage.diagnostics == ()


# --- Consistency between the two validation layers ------------------------------


def test_all_faulty_feed_admits_nothing_and_contradicts_nothing() -> None:
    """Adapter diagnostics and stage re-validation agree on a faulty feed."""
    outcome = _run_chain(
        _feed(
            _line(_record(raw_value="72")),  # TYPE_ERROR: str for numeric FC
            _line(_record(provenance={"source_kind": "whatsapp"})),  # vocabulary
            _line(
                _record(source_asserted_certainty="surely")
            ),  # certainty outside taxonomy
        )
    )
    assert outcome.accepted == ()
    assert outcome.stage.admitted == ()
    assert outcome.stage.diagnostics == ()
    assert all(
        evaluation.diagnostic is not None
        for evaluation in outcome.feed.records
    )


def test_no_admitted_fact_violates_the_frozen_contract() -> None:
    """Re-running the stage on its own output admits everything again."""
    outcome = _run_chain(
        _feed(
            _line(_record(fact_id="raw-1")),
            _line(_record(fact_id="raw-2", field_id="TA", raw_value="120/80")),
        )
    )
    recheck = run_input_validation(outcome.stage.admitted)
    assert recheck.admitted == outcome.stage.admitted
    assert recheck.diagnostics == ()


# --- Whole-feed fault (FC-03) terminates the chain cleanly ----------------------


def test_undecodable_bytes_terminate_the_chain_with_zero_facts() -> None:
    """A feed-level fault yields no records and an empty stage result."""
    outcome = _run_chain(b"\xff\xfe\xfa")
    assert outcome.feed.records == ()
    assert outcome.feed.diagnostic is not None
    assert outcome.feed.diagnostic.code is DiagnosticCode.INPUT_CONTRACT_ERROR
    assert outcome.stage.admitted == ()
    assert outcome.stage.diagnostics == ()


def test_feed_level_fault_never_admits_a_decodable_tail() -> None:
    """A valid line after undecodable bytes is never partially admitted."""
    outcome = _run_chain(b"\xff" + _line(_record()).encode("utf-8"))
    assert outcome.feed.records == ()
    assert outcome.stage.admitted == ()


# --- Empty feed -----------------------------------------------------------------


def test_empty_feed_chains_to_empty_admitted_without_diagnostics() -> None:
    """Zero bytes admit nothing and diagnose nothing through the chain."""
    outcome = _run_chain(b"")
    assert outcome.feed.records == ()
    assert outcome.feed.diagnostic is None
    assert outcome.stage.admitted == ()
    assert outcome.stage.diagnostics == ()


# --- Determinism ----------------------------------------------------------------


def test_chain_is_deterministic() -> None:
    """Identical bytes produce the identical chain outcome, faults included."""
    feed = _feed(
        _line(_record(fact_id="raw-1")),
        "{not json",
        _line(_record(fact_id="raw-bad", raw_value=True)),
        _line(_record(fact_id="raw-2", field_id="TA", raw_value="120/80")),
    )
    assert _run_chain(feed) == _run_chain(feed)
