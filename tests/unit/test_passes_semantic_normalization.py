"""Unit tests for clinical_compiler.passes.semantic_normalization."""

from collections.abc import Callable
from itertools import permutations
from typing import cast

import pytest

from clinical_compiler.adapters.structured_feed import parse_feed
from clinical_compiler.core.diagnostics import DiagnosticCode
from clinical_compiler.core.ir import (
    CanonicalClinicalFact,
    CanonicalClinicalIR,
    SourceFactIR,
)
from clinical_compiler.core.types import Certainty, Missingness, Provenance
from clinical_compiler.passes.input_validation import run_input_validation
from clinical_compiler.passes.semantic_normalization import run_semantic_normalization
from clinical_compiler.pipeline_types import StageResult


def _feed_bytes(*lines: str) -> bytes:
    """Encode the given JSONL ``lines`` as feed bytes."""
    return "\n".join(lines).encode("utf-8")


def _fact(**overrides: object) -> SourceFactIR:
    """Build a validated-intake FC fact with the given field overrides."""
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


def _codes(result: StageResult[CanonicalClinicalFact]) -> tuple[DiagnosticCode, ...]:
    """Return the emitted diagnostic codes in encounter order."""
    return tuple(d.code for d in result.diagnostics)


def _admitted_by_field(
    result: StageResult[CanonicalClinicalFact],
) -> dict[str, CanonicalClinicalFact]:
    """Index the admitted canonical facts by field id."""
    return {fact.field_id: fact for fact in result.admitted}


# --- Stage contract (pipeline_types — G-1 leaf placement) ----------------------


def test_normalization_returns_a_stage_result() -> None:
    """The stage speaks the shared stage contract, not ad-hoc shapes."""
    result = run_semantic_normalization((_fact(),))
    assert isinstance(result, StageResult)
    assert result.diagnostics == ()
    assert len(result.admitted) == 1
    assert isinstance(result.admitted[0], CanonicalClinicalFact)


def test_empty_fact_set_yields_empty_stage_result() -> None:
    """No facts in means nothing admitted and nothing diagnosed."""
    result = run_semantic_normalization(())
    assert result.admitted == ()
    assert result.diagnostics == ()


# --- Interpretation table positives (design D8) ---------------------------------


def test_present_int_value_maps_to_present() -> None:
    """A present numeric reading stays verbatim with PRESENT missingness."""
    result = run_semantic_normalization((_fact(),))
    fact = result.admitted[0]
    assert fact.field_id == "FC"
    assert fact.value.value == 72
    assert fact.value.missingness is Missingness.PRESENT


def test_present_str_value_maps_to_present() -> None:
    """A telegraphic string reading (clinical_note TA) is PRESENT too."""
    fact = _fact(
        fact_id="raw-ta",
        field_id="TA",
        raw_value="120/80",
        provenance=Provenance(source_kind="clinical_note", source_ref="n-1"),
    )
    result = run_semantic_normalization((fact,))
    assert result.admitted[0].value.value == "120/80"
    assert result.admitted[0].value.missingness is Missingness.PRESENT


def test_float_value_is_kept_verbatim() -> None:
    """Non-integer numerics pass through without reformatting."""
    result = run_semantic_normalization((_fact(raw_value=72.5),))
    assert result.admitted[0].value.value == 72.5


@pytest.mark.parametrize("source_kind", ["monitor", "lab", "clinical_note"])
def test_every_source_kind_yields_unresolved_certainty(source_kind: str) -> None:
    """No source_kind → certainty inference (CRC-001: mapping rejected).

    Kills the adjudicated-and-rejected automatic table: a mutation
    mapping ``monitor``/``lab`` → CONFIRMED or ``clinical_note`` →
    PROBABLE fails here.
    """
    fact = _fact(
        provenance=Provenance(source_kind=source_kind, source_ref="s-1")
    )
    result = run_semantic_normalization((fact,))
    assert result.admitted[0].value.certainty is Certainty.UNRESOLVED


# --- Assessed absence (PC-2) ----------------------------------------------------


def test_absence_marker_maps_to_missing_with_provenance() -> None:
    """The null raw value is the assessed-absence marker (PC-2).

    The canonical absence carries the source's provenance and cites the
    asserting fact — absence traces to a source assertion, never to
    input absence.
    """
    fact = _fact(
        fact_id="raw-ta",
        field_id="TA",
        raw_value=None,
        provenance=Provenance(source_kind="lab", source_ref="l-1"),
    )
    result = run_semantic_normalization((fact,))
    canonical = result.admitted[0]
    assert canonical.value.missingness is Missingness.MISSING
    assert canonical.value.value is None
    assert canonical.source_fact_refs == ("raw-ta",)
    assert canonical.value.provenance is fact.provenance


def test_absence_is_assessed_absence_never_unassessed() -> None:
    """MISSING is never conflated with UNKNOWN/NOT_ASSESSED (spec)."""
    result = run_semantic_normalization(
        (_fact(fact_id="raw-ta", field_id="TA", raw_value=None),)
    )
    missingness = result.admitted[0].value.missingness
    assert missingness is Missingness.MISSING
    assert missingness is not Missingness.UNKNOWN
    assert missingness is not Missingness.NOT_ASSESSED


# --- Certainty invariants (CRC-001 / CRC-002) -----------------------------------


@pytest.mark.parametrize(
    ("field_id", "raw_value"),
    [("FC", 72), ("FC", 72.5), ("TA", "120/80"), ("TA", None)],
)
def test_certainty_is_unresolved_for_every_admissible_input(
    field_id: str,
    raw_value: object,
) -> None:
    """Fail-closed certainty assignment: UNRESOLVED everywhere in R1."""
    result = run_semantic_normalization(
        (_fact(field_id=field_id, raw_value=raw_value),)
    )
    assert result.admitted[0].value.certainty is Certainty.UNRESOLVED


def test_reserved_certainty_states_are_not_produced() -> None:
    """NOT_PRODUCED invariant: never PROBABLE, LIKELY, or UNLIKELY."""
    single_facts = (
        _fact(fact_id="raw-1", raw_value=72),
        _fact(fact_id="raw-2", raw_value=72.5),
        _fact(fact_id="raw-3", field_id="TA", raw_value="120/80"),
        _fact(fact_id="raw-4", field_id="TA", raw_value=None),
    )
    for fact in single_facts:
        result = run_semantic_normalization((fact,))
        assert result.diagnostics == ()
        canonical = result.admitted[0]
        assert canonical.value.certainty is not Certainty.PROBABLE
        assert canonical.value.certainty is not Certainty.LIKELY
        assert canonical.value.certainty is not Certainty.UNLIKELY


def test_declared_certainty_never_becomes_compiler_certainty() -> None:
    """CRC-002 (BOTH_SEPARATED) across the real chain.

    A record declaring ``source_asserted_certainty`` rides the adapter
    and validation unchanged, but the declaration NEVER leaks into the
    compiler-assigned certainty the normalizer assigns — never
    conflated, never a silent upgrade.
    """
    feed = parse_feed(
        _feed_bytes(
            '{"fact_id": "raw-c", "field_id": "FC", "raw_value": 72, '
            '"provenance": {"source_kind": "monitor", "source_ref": "m-9"}, '
            '"source_asserted_certainty": "confirmed"}',
            '{"fact_id": "raw-p", "field_id": "TA", "raw_value": "120/80", '
            '"provenance": {"source_kind": "clinical_note", "source_ref": "n-1"}, '
            '"source_asserted_certainty": "probable"}',
        )
    )
    accepted = tuple(e.fact for e in feed.records if e.fact is not None)
    validated = run_input_validation(tuple(w.fact for w in accepted))
    result = run_semantic_normalization(validated.admitted)
    by_id = {f.clinical_fact_id: f for f in result.admitted}
    declared = {
        w.fact.fact_id: w.source_asserted_certainty
        for w in accepted
    }
    assert declared == {
        "raw-c": Certainty.CONFIRMED,
        "raw-p": Certainty.PROBABLE,
    }
    # Distinct fields for distinct facts — no conflation possible, and
    # the compiler axis stays UNRESOLVED despite CONFIRMED/PROBABLE
    # declarations on the source axis.
    assert len(by_id) == 2
    for canonical in result.admitted:
        assert canonical.value.certainty is Certainty.UNRESOLVED


def test_absence_marker_certainty_is_unresolved() -> None:
    """Even an asserted absence gets no invented certainty."""
    result = run_semantic_normalization(
        (_fact(fact_id="raw-ta", field_id="TA", raw_value=None),)
    )
    assert result.admitted[0].value.certainty is Certainty.UNRESOLVED


# --- Ambiguity blocks (FC-06) ---------------------------------------------------


def test_conflicting_equal_authority_facts_block() -> None:
    """FC-06: two conflicting FC readings, equal authority → block."""
    facts = (
        _fact(fact_id="raw-1", raw_value=72),
        _fact(fact_id="raw-2", raw_value=80),
    )
    result = run_semantic_normalization(facts)
    assert _codes(result) == (
        DiagnosticCode.SEMANTIC_AMBIGUITY_BLOCK,
        DiagnosticCode.SEMANTIC_AMBIGUITY_BLOCK,
    )
    assert result.admitted == ()


def test_no_canonical_fact_is_created_for_a_conflicted_field() -> None:
    """The spec scenario verbatim: blocked, never guessed."""
    facts = (
        _fact(fact_id="raw-1", raw_value=72),
        _fact(fact_id="raw-2", raw_value=80),
    )
    result = run_semantic_normalization(facts)
    assert all(f.field_id != "FC" for f in result.admitted)


def test_conflict_quarantines_only_the_conflicting_field() -> None:
    """Per-fact quarantine (D1): an unambiguous TA survives an FC clash."""
    facts = (
        _fact(fact_id="raw-1", raw_value=72),
        _fact(fact_id="raw-2", raw_value=80),
        _fact(fact_id="raw-3", field_id="TA", raw_value="120/80"),
    )
    result = run_semantic_normalization(facts)
    assert _codes(result) == (
        DiagnosticCode.SEMANTIC_AMBIGUITY_BLOCK,
        DiagnosticCode.SEMANTIC_AMBIGUITY_BLOCK,
    )
    assert tuple(f.field_id for f in result.admitted) == ("TA",)


def test_absence_versus_value_conflict_blocks() -> None:
    """An asserted absence and a present reading are >1 interpretation."""
    facts = (
        _fact(fact_id="raw-1", field_id="TA", raw_value=None),
        _fact(fact_id="raw-2", field_id="TA", raw_value="120/80"),
    )
    result = run_semantic_normalization(facts)
    assert _codes(result) == (
        DiagnosticCode.SEMANTIC_AMBIGUITY_BLOCK,
        DiagnosticCode.SEMANTIC_AMBIGUITY_BLOCK,
    )
    assert result.admitted == ()


def test_cross_source_conflict_blocks_without_precedence() -> None:
    """Equal authority: no source_kind wins (source_kind informs
    PROVENANCE only — CRC-002)."""
    facts = (
        _fact(fact_id="raw-1", raw_value=72),
        _fact(
            fact_id="raw-2",
            raw_value=80,
            provenance=Provenance(source_kind="clinical_note", source_ref="n-1"),
        ),
    )
    result = run_semantic_normalization(facts)
    assert _codes(result) == (
        DiagnosticCode.SEMANTIC_AMBIGUITY_BLOCK,
        DiagnosticCode.SEMANTIC_AMBIGUITY_BLOCK,
    )
    assert result.admitted == ()


def test_conflicting_group_partitions_fact_xor_diagnostic() -> None:
    """Every input fact is either cited once XOR diagnosed once."""
    facts = (
        _fact(fact_id="raw-1", raw_value=72),
        _fact(fact_id="raw-2", raw_value=80),
        _fact(fact_id="raw-3", raw_value=72),
        _fact(fact_id="raw-4", field_id="TA", raw_value="120/80"),
    )
    result = run_semantic_normalization(facts)
    cited = [ref for f in result.admitted for ref in f.source_fact_refs]
    diagnosed = len(result.diagnostics)
    assert len(cited) + diagnosed == len(facts)
    # Admitting the corroborated 72 while 80 blocks would mean R1 PICKED
    # the majority reading — so every FC fact of the conflicted field
    # quarantines; only the unambiguous raw-4 survives.
    assert cited == ["raw-4"]
    assert diagnosed == 3


# --- Corroboration merges (one admissible interpretation) -----------------------


def test_corroborating_duplicate_values_merge_into_one_fact() -> None:
    """Equal readings are ONE interpretation — one canonical fact."""
    facts = (
        _fact(fact_id="raw-1", raw_value=72),
        _fact(fact_id="raw-2", raw_value=72),
    )
    result = run_semantic_normalization(facts)
    assert result.diagnostics == ()
    assert len(result.admitted) == 1
    assert result.admitted[0].source_fact_refs == ("raw-1", "raw-2")


def _observable_canonical_fact(fact: CanonicalClinicalFact) -> tuple[str, ...]:
    """Capture the canonical representation without numeric coercion."""
    raw_value = fact.value.value
    return (
        fact.clinical_fact_id,
        fact.field_id,
        type(raw_value).__name__,
        repr(raw_value),
        fact.value.certainty.value,
        fact.value.missingness.value,
        fact.value.provenance.source_kind,
        fact.value.provenance.source_ref,
        repr(fact.source_fact_refs),
    )


def test_two_corroborants_are_invariant_under_reversed_input_order() -> None:
    """ACCEPT-R1-001: the same corroborating facts normalize identically."""
    monitor = _fact(
        fact_id="accept-r1-001-monitor",
        raw_value=72,
        provenance=Provenance("monitor", "monitor-primary"),
    )
    lab = _fact(
        fact_id="accept-r1-001-lab",
        raw_value=72,
        provenance=Provenance("lab", "lab-corroborating"),
    )

    forward = run_semantic_normalization((monitor, lab))
    reversed_order = run_semantic_normalization((lab, monitor))

    assert forward.diagnostics == reversed_order.diagnostics == ()
    assert forward == reversed_order


def test_int_and_float_corroborants_have_stable_observable_representation() -> None:
    """ACCEPT-R1-001: 72 and 72.0 stay stable in either encounter order."""
    integer = _fact(
        fact_id="accept-r1-001-int",
        raw_value=72,
        provenance=Provenance("monitor", "monitor-primary"),
    )
    floating = _fact(
        fact_id="accept-r1-001-float",
        raw_value=72.0,
        provenance=Provenance("lab", "lab-corroborating"),
    )

    forward = run_semantic_normalization((integer, floating))
    reversed_order = run_semantic_normalization((floating, integer))

    assert forward.diagnostics == reversed_order.diagnostics == ()
    assert len(forward.admitted) == len(reversed_order.admitted) == 1
    assert _observable_canonical_fact(forward.admitted[0]) == (
        _observable_canonical_fact(reversed_order.admitted[0])
    )


def test_three_corroborants_are_invariant_over_all_six_permutations() -> None:
    """ACCEPT-R1-001: all 3! orders produce one stable canonical fact."""
    facts = (
        _fact(
            fact_id="accept-r1-001-a",
            raw_value=72,
            provenance=Provenance("monitor", "monitor-primary"),
        ),
        _fact(
            fact_id="accept-r1-001-b",
            raw_value=72,
            provenance=Provenance("lab", "lab-corroborating"),
        ),
        _fact(
            fact_id="accept-r1-001-c",
            raw_value=72,
            provenance=Provenance("clinical_note", "note-corroborating"),
        ),
    )
    baseline = run_semantic_normalization(facts)
    expected = tuple(_observable_canonical_fact(fact) for fact in baseline.admitted)

    orders = tuple(permutations(facts))
    assert len(orders) == 6
    for ordered_facts in orders:
        result = run_semantic_normalization(ordered_facts)
        assert result.diagnostics == ()
        assert tuple(_observable_canonical_fact(fact) for fact in result.admitted) == (
            expected
        )


def test_conflict_diagnostics_are_stable_when_group_order_is_reversed() -> None:
    """Conflicting groups keep identical diagnostic messages and ordering."""
    first = _fact(
        fact_id="accept-r1-001-conflict-a",
        raw_value=72,
        provenance=Provenance("monitor", "monitor-primary"),
    )
    second = _fact(
        fact_id="accept-r1-001-conflict-b",
        raw_value=80,
        provenance=Provenance("lab", "lab-conflicting"),
    )

    forward = run_semantic_normalization((first, second))
    reversed_order = run_semantic_normalization((second, first))

    assert forward.admitted == reversed_order.admitted == ()
    assert forward.diagnostics == reversed_order.diagnostics


def test_multiple_fields_are_invariant_under_global_input_permutations() -> None:
    """All global orders preserve canonical facts across FC and TA fields."""
    facts = (
        _fact(
            fact_id="accept-r1-001-fc-monitor",
            field_id="FC",
            raw_value=72,
            provenance=Provenance("monitor", "monitor-primary"),
        ),
        _fact(
            fact_id="accept-r1-001-fc-lab",
            field_id="FC",
            raw_value=72,
            provenance=Provenance("lab", "lab-corroborating"),
        ),
        _fact(
            fact_id="accept-r1-001-ta-monitor",
            field_id="TA",
            raw_value="120/80",
            provenance=Provenance("monitor", "monitor-ta"),
        ),
        _fact(
            fact_id="accept-r1-001-ta-note",
            field_id="TA",
            raw_value="120/80",
            provenance=Provenance("clinical_note", "note-ta"),
        ),
    )
    baseline = run_semantic_normalization(facts)
    expected = tuple(_observable_canonical_fact(fact) for fact in baseline.admitted)

    for ordered_facts in permutations(facts):
        result = run_semantic_normalization(ordered_facts)
        assert result.diagnostics == ()
        assert tuple(_observable_canonical_fact(fact) for fact in result.admitted) == (
            expected
        )


def test_multiple_conflicted_fields_are_invariant_under_global_permutations() -> None:
    """All 4! global permutations preserve deterministic diagnostics across fields."""
    facts = (
        _fact(
            fact_id="accept-r1-001-fc-a",
            field_id="FC",
            raw_value=72,
            provenance=Provenance("monitor", "monitor-fc-a"),
        ),
        _fact(
            fact_id="accept-r1-001-fc-b",
            field_id="FC",
            raw_value=80,
            provenance=Provenance("lab", "lab-fc-b"),
        ),
        _fact(
            fact_id="accept-r1-001-ta-a",
            field_id="TA",
            raw_value="120/80",
            provenance=Provenance("monitor", "monitor-ta-a"),
        ),
        _fact(
            fact_id="accept-r1-001-ta-b",
            field_id="TA",
            raw_value="90/60",
            provenance=Provenance("clinical_note", "note-ta-b"),
        ),
    )
    baseline = run_semantic_normalization(facts)
    assert baseline.admitted == ()
    assert len(baseline.diagnostics) == 4

    orders = tuple(permutations(facts))
    assert len(orders) == 24
    for ordered_facts in orders:
        result = run_semantic_normalization(ordered_facts)
        assert result.admitted == baseline.admitted
        assert result.diagnostics == baseline.diagnostics
        assert result == baseline


def test_corroborating_absence_merges() -> None:
    """Two sources asserting the same absence corroborate it."""
    facts = (
        _fact(fact_id="raw-1", field_id="TA", raw_value=None),
        _fact(
            fact_id="raw-2",
            field_id="TA",
            raw_value=None,
            provenance=Provenance(source_kind="lab", source_ref="l-1"),
        ),
    )
    result = run_semantic_normalization(facts)
    assert result.diagnostics == ()
    canonical = result.admitted[0]
    assert canonical.value.missingness is Missingness.MISSING
    assert canonical.source_fact_refs == ("raw-1", "raw-2")


def test_numerically_equal_int_and_float_are_one_interpretation() -> None:
    """72 and 72.0 denote the same reading — no false ambiguity."""
    facts = (
        _fact(fact_id="raw-1", raw_value=72),
        _fact(fact_id="raw-2", raw_value=72.0),
    )
    result = run_semantic_normalization(facts)
    assert result.diagnostics == ()
    assert len(result.admitted) == 1


# --- Provenance carried through -------------------------------------------------


def test_provenance_carried_through(
    make_provenance: Callable[..., Provenance],
) -> None:
    """The canonical value carries the source's provenance verbatim."""
    provenance = make_provenance(source_kind="lab", source_ref="l-7")
    result = run_semantic_normalization((_fact(provenance=provenance),))
    assert result.admitted[0].value.provenance == provenance


def test_merged_fact_uses_structural_representative_provenance() -> None:
    """Equal authority uses the lowest fact_id, not encounter order."""
    facts = (
        _fact(fact_id="raw-2", provenance=Provenance("lab", "l-2")),
        _fact(fact_id="raw-1", provenance=Provenance("monitor", "m-9")),
    )
    result = run_semantic_normalization(facts)
    assert result.admitted[0].value.provenance == Provenance("monitor", "m-9")


# --- Determinism (design Determinism Mechanism) ---------------------------------


def test_normalization_is_deterministic() -> None:
    """Identical fact sets — conflicts included — normalize identically."""
    facts = (
        _fact(fact_id="raw-1", raw_value=72),
        _fact(fact_id="raw-2", raw_value=80),
        _fact(fact_id="raw-3", field_id="TA", raw_value="120/80"),
        _fact(fact_id="raw-4", field_id="TA", raw_value=None),
    )
    assert run_semantic_normalization(facts) == run_semantic_normalization(
        facts
    )


def test_clinical_fact_id_is_stable_across_runs() -> None:
    """Ids derive from fact identity — never random/uuid/time."""
    result_a = run_semantic_normalization((_fact(fact_id="raw-1"),))
    result_b = run_semantic_normalization((_fact(fact_id="raw-1"),))
    assert result_a.admitted[0].clinical_fact_id == (
        result_b.admitted[0].clinical_fact_id
    )


def test_clinical_fact_id_distinguishes_distinct_identities() -> None:
    """Different supporting facts yield different canonical ids."""
    result_a = run_semantic_normalization((_fact(fact_id="raw-1"),))
    result_b = run_semantic_normalization((_fact(fact_id="raw-2"),))
    assert (
        result_a.admitted[0].clinical_fact_id
        != result_b.admitted[0].clinical_fact_id
    )


def test_merged_refs_are_canonically_sorted() -> None:
    """Refs carry the codepoint-sorted contributing fact ids."""
    facts = (
        _fact(fact_id="raw-b", raw_value=72),
        _fact(fact_id="raw-a", raw_value=72),
    )
    result = run_semantic_normalization(facts)
    assert result.admitted[0].source_fact_refs == ("raw-a", "raw-b")


# --- Downstream compatibility (U1 aggregate) ------------------------------------


def test_admitted_facts_construct_a_canonical_clinical_ir() -> None:
    """The stage's output is a valid CanonicalClinicalIR payload."""
    facts = (
        _fact(fact_id="raw-1", raw_value=72),
        _fact(fact_id="raw-2", field_id="TA", raw_value="120/80"),
    )
    result = run_semantic_normalization(facts)
    ir = CanonicalClinicalIR(facts=result.admitted)
    assert ir.facts == result.admitted
