"""Unit tests for clinical_compiler.passes.document_selection."""

from dataclasses import fields
from typing import cast

from clinical_compiler.core.diagnostics import DiagnosticCode
from clinical_compiler.core.ir import (
    CanonicalClinicalFact,
    CanonicalClinicalIR,
    DocumentEntry,
    DocumentIR,
)
from clinical_compiler.core.types import (
    Certainty,
    ClinicalValue,
    Missingness,
    Provenance,
)
from clinical_compiler.passes.admissibility import run_admissibility
from clinical_compiler.passes.document_selection import run_document_selection
from clinical_compiler.pipeline_types import StageResult

MODE = "NURSING_RECORD_TELEGRAPHIC"


def _canonical_fact(**overrides: object) -> CanonicalClinicalFact:
    """Build a canonical TA fact with the given field overrides."""
    params: dict[str, object] = {
        "clinical_fact_id": "c-ta-1",
        "field_id": "TA",
        "value": ClinicalValue(
            value="120/80",
            certainty=Certainty.UNRESOLVED,
            missingness=Missingness.PRESENT,
            provenance=Provenance(source_kind="clinical_note", source_ref="n-1"),
        ),
        "source_fact_refs": ("raw-1",),
    }
    params.update(overrides)
    return CanonicalClinicalFact(
        clinical_fact_id=cast(str, params["clinical_fact_id"]),
        field_id=cast(str, params["field_id"]),
        value=cast(ClinicalValue, params["value"]),
        source_fact_refs=cast("tuple[str, ...]", params["source_fact_refs"]),
    )


def _mixed_facts() -> tuple[CanonicalClinicalFact, ...]:
    """Three facts whose insertion order differs from canonical order.

    Canonical ``(field_id, clinical_fact_id)`` codepoint order is
    ``FC/c-fc-1``, ``TA/c-ta-1``, ``TA/c-ta-2`` — NOT the insertion
    order below.
    """
    return (
        _canonical_fact(clinical_fact_id="c-ta-2"),
        _canonical_fact(
            clinical_fact_id="c-fc-1",
            field_id="FC",
            value=ClinicalValue(
                value=72,
                certainty=Certainty.UNRESOLVED,
                missingness=Missingness.PRESENT,
                provenance=Provenance(source_kind="monitor", source_ref="m-9"),
            ),
        ),
        _canonical_fact(clinical_fact_id="c-ta-1"),
    )


def _codes(result: StageResult[DocumentIR]) -> tuple[DiagnosticCode, ...]:
    """Return the emitted diagnostic codes in emission order."""
    return tuple(d.code for d in result.diagnostics)


# --- Stage contract (pipeline_types — G-1 leaf placement) ----------------------


def test_returns_a_stage_result_with_a_single_document() -> None:
    """The stage speaks the shared stage contract: one document or none."""
    result = run_document_selection(
        CanonicalClinicalIR(facts=_mixed_facts()), MODE
    )
    assert isinstance(result, StageResult)
    assert result.diagnostics == ()
    assert len(result.admitted) == 1
    assert isinstance(result.admitted[0], DocumentIR)
    assert result.admitted[0].document_mode == MODE


def test_entries_reference_canonical_fact_ids_in_canonical_order() -> None:
    """One entry per fact; refs are the ``clinical_fact_id`` values in
    the canonical ``(field_id, clinical_fact_id)`` codepoint order."""
    result = run_document_selection(
        CanonicalClinicalIR(facts=_mixed_facts()), MODE
    )
    entries = result.admitted[0].entries
    assert len(entries) == 3
    assert tuple(entry.clinical_fact_ref for entry in entries) == (
        "c-fc-1",
        "c-ta-1",
        "c-ta-2",
    )


def test_every_entry_carries_the_presentation_role() -> None:
    """Each entry carries the mode's presentation role.

    Pinned against the literal R1 role (not the module constant) so a
    mutation of the assigned role vocabulary fails here.
    """
    result = run_document_selection(
        CanonicalClinicalIR(facts=_mixed_facts()), MODE
    )
    for entry in result.admitted[0].entries:
        assert entry.presentation_role == "telegraphic_entry"


# --- Single authority / CRC-004 (refs only, never values) ----------------------


def test_document_ir_contains_no_clinical_values() -> None:
    """CRC-004 side one: the IR never stores clinical values.

    Entries carry exactly the two ref/role fields, both plain strings —
    the values ("120/80", 72) live only in the canonical facts.
    """
    result = run_document_selection(
        CanonicalClinicalIR(facts=_mixed_facts()), MODE
    )
    document = result.admitted[0]
    assert {field.name for field in fields(DocumentEntry)} == {
        "clinical_fact_ref",
        "presentation_role",
    }
    for entry in document.entries:
        assert isinstance(entry.clinical_fact_ref, str)
        assert isinstance(entry.presentation_role, str)
        assert not isinstance(entry.clinical_fact_ref, ClinicalValue)
        assert not isinstance(entry.presentation_role, ClinicalValue)
    assert tuple(entry.clinical_fact_ref for entry in document.entries) == tuple(
        fact.clinical_fact_id for fact in CanonicalClinicalIR(
            facts=_mixed_facts()
        ).facts
    )


def test_refs_are_built_only_from_surviving_facts() -> None:
    """CRC-004 side two: every ref resolves to an aggregate fact id.

    Selection builds refs exclusively from the facts it consumed, so a
    dangling ref is impossible by construction (the renderer's
    RENDER_ERROR is defense-in-depth over injection, never produced
    here).
    """
    facts = _mixed_facts()
    result = run_document_selection(CanonicalClinicalIR(facts=facts), MODE)
    fact_ids = {fact.clinical_fact_id for fact in facts}
    for entry in result.admitted[0].entries:
        assert entry.clinical_fact_ref in fact_ids


# --- Determinism (design Determinism Mechanism) --------------------------------


def test_selection_is_deterministic_across_runs_and_insertion_orders() -> None:
    """Identical fact sets — any insertion order — select identically."""
    first = run_document_selection(
        CanonicalClinicalIR(facts=_mixed_facts()), MODE
    )
    reordered = CanonicalClinicalIR(facts=_mixed_facts()[::-1])
    second = run_document_selection(reordered, MODE)
    assert first == second
    assert first.admitted[0].entries == second.admitted[0].entries


# --- Selection failures (FC-09 / pipeline-passes spec) -------------------------


def test_fc09_all_facts_blocked_upstream_then_selection_requested() -> None:
    """FC-09: everything quarantined upstream → DOCUMENT_SELECTION_ERROR."""
    blocked = (
        _canonical_fact(
            clinical_fact_id="c-ta-veto",
            value=ClinicalValue(
                value="paciente estable",
                certainty=Certainty.UNRESOLVED,
                missingness=Missingness.PRESENT,
                provenance=Provenance(source_kind="clinical_note", source_ref="n-1"),
            ),
        ),
        _canonical_fact(
            clinical_fact_id="c-ta-ghost", source_fact_refs=("raw-ghost",)
        ),
    )
    upstream = run_admissibility(
        blocked, frozenset({"estable"}), frozenset({"raw-1"})
    )
    assert upstream.admitted == ()
    result = run_document_selection(
        CanonicalClinicalIR(facts=upstream.admitted), MODE
    )
    assert _codes(result) == (DiagnosticCode.DOCUMENT_SELECTION_ERROR,)
    assert result.admitted == ()


def test_empty_admissible_set_with_valid_mode_yields_error() -> None:
    """Unit-level empty-set arm: no admissible entries → no document."""
    result = run_document_selection(CanonicalClinicalIR(facts=()), MODE)
    assert _codes(result) == (DiagnosticCode.DOCUMENT_SELECTION_ERROR,)
    assert result.admitted == ()


# --- Unknown mode (pass-level fail-closed arm) ---------------------------------


def test_unknown_mode_yields_document_selection_error_no_document() -> None:
    """A mode outside the R1 vocabulary cannot produce a valid document."""
    result = run_document_selection(
        CanonicalClinicalIR(facts=_mixed_facts()), "SOAP_NOTE"
    )
    assert _codes(result) == (DiagnosticCode.DOCUMENT_SELECTION_ERROR,)
    assert result.admitted == ()
    assert "SOAP_NOTE" in result.diagnostics[0].message


def test_mode_matching_is_exact_not_case_folded() -> None:
    """The mode vocabulary is exact codepoint matching — no folding."""
    result = run_document_selection(
        CanonicalClinicalIR(facts=_mixed_facts()), "nursing_record_telegraphic"
    )
    assert _codes(result) == (DiagnosticCode.DOCUMENT_SELECTION_ERROR,)
    assert result.admitted == ()


def test_empty_mode_string_is_unknown() -> None:
    """The empty string is not a mode — truthiness must not short-cut."""
    result = run_document_selection(CanonicalClinicalIR(facts=()), "")
    assert _codes(result) == (
        DiagnosticCode.DOCUMENT_SELECTION_ERROR,
        DiagnosticCode.DOCUMENT_SELECTION_ERROR,
    )
    assert result.admitted == ()


def test_unknown_mode_and_empty_set_emit_both_diagnostics() -> None:
    """D1 full enumeration: both request-level faults are reported.

    The unknown mode is named first (request validity), the empty
    admissible set second (content enumeration) — and no document is
    assembled.
    """
    result = run_document_selection(CanonicalClinicalIR(facts=()), "SOAP_NOTE")
    assert _codes(result) == (
        DiagnosticCode.DOCUMENT_SELECTION_ERROR,
        DiagnosticCode.DOCUMENT_SELECTION_ERROR,
    )
    assert "unknown document mode" in result.diagnostics[0].message
    assert "no admissible canonical facts" in result.diagnostics[1].message
    assert result.admitted == ()
