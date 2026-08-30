"""Unit tests for clinical_compiler.passes.admissibility."""

from typing import cast

import pytest

from clinical_compiler.core import policy as core_policy
from clinical_compiler.core.diagnostics import DiagnosticCode
from clinical_compiler.core.ir import CanonicalClinicalFact, CanonicalClinicalIR
from clinical_compiler.core.types import (
    Certainty,
    ClinicalValue,
    Missingness,
    Provenance,
)
from clinical_compiler.passes.admissibility import run_admissibility
from clinical_compiler.pipeline_types import StageResult


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


def _numeric_fact(**overrides: object) -> CanonicalClinicalFact:
    """Build a canonical FC numeric fact with the given field overrides."""
    params: dict[str, object] = {
        "clinical_fact_id": "c-fc-1",
        "field_id": "FC",
        "value": ClinicalValue(
            value=72,
            certainty=Certainty.UNRESOLVED,
            missingness=Missingness.PRESENT,
            provenance=Provenance(source_kind="monitor", source_ref="m-9"),
        ),
        "source_fact_refs": ("raw-1",),
    }
    params.update(overrides)
    return _canonical_fact(**params)


def _with_certainty(
    fact: CanonicalClinicalFact, certainty: Certainty
) -> CanonicalClinicalFact:
    """Rebuild the fact's value carrying the given certainty."""
    old = fact.value
    return CanonicalClinicalFact(
        clinical_fact_id=fact.clinical_fact_id,
        field_id=fact.field_id,
        value=ClinicalValue(
            value=old.value,
            certainty=certainty,
            missingness=old.missingness,
            provenance=old.provenance,
        ),
        source_fact_refs=fact.source_fact_refs,
    )


def _codes(
    result: StageResult[CanonicalClinicalFact],
) -> tuple[DiagnosticCode, ...]:
    """Return the emitted diagnostic codes in encounter order."""
    return tuple(d.code for d in result.diagnostics)


RESOLVABLE_IDS: frozenset[str] = frozenset({"raw-1", "raw-2", "raw-9"})


# --- Stage contract (pipeline_types — G-1 leaf placement) ----------------------


def test_returns_a_stage_result() -> None:
    """The stage speaks the shared stage contract, not ad-hoc shapes."""
    result = run_admissibility(
        (_canonical_fact(),), frozenset(), RESOLVABLE_IDS
    )
    assert isinstance(result, StageResult)
    assert result.diagnostics == ()
    assert result.admitted == (_canonical_fact(),)


def test_empty_fact_set_yields_empty_stage_result() -> None:
    """No facts in means nothing admitted and nothing diagnosed."""
    result = run_admissibility((), frozenset({"estable"}), frozenset())
    assert result.admitted == ()
    assert result.diagnostics == ()


# --- Veto hits (FC-07 — design D7 / pipeline-passes spec) ----------------------


def test_vetoed_term_is_quarantined_with_policy_violation() -> None:
    """A fact whose value contains a veto term blocks with POLICY_VIOLATION."""
    fact = _canonical_fact(
        clinical_fact_id="c-ta-veto",
        value=ClinicalValue(
            value="paciente estable",
            certainty=Certainty.UNRESOLVED,
            missingness=Missingness.PRESENT,
            provenance=Provenance(source_kind="clinical_note", source_ref="n-1"),
        ),
    )
    result = run_admissibility((fact,), frozenset({"estable"}), RESOLVABLE_IDS)
    assert _codes(result) == (DiagnosticCode.POLICY_VIOLATION,)
    assert result.admitted == ()


@pytest.mark.parametrize("certainty", list(Certainty))
def test_veto_is_certainty_independent(certainty: Certainty) -> None:
    """FC-07 at test-constructed certainty — even CONFIRMED blocks.

    R1's normalizer assigns no ``CONFIRMED``; the veto invariant is
    certainty-independent, so the corpus case is constructed here at
    every taxonomy member. A mutation gating the veto on certainty
    (for example sparing ``CONFIRMED``) fails on this test.
    """
    base = _canonical_fact(
        clinical_fact_id="c-ta-veto",
        value=ClinicalValue(
            value="paciente estable",
            certainty=certainty,
            missingness=Missingness.PRESENT,
            provenance=Provenance(source_kind="clinical_note", source_ref="n-1"),
        ),
    )
    result = run_admissibility(
        (base,), frozenset({"estable"}), RESOLVABLE_IDS
    )
    assert _codes(result) == (DiagnosticCode.POLICY_VIOLATION,)
    assert result.admitted == ()


def test_veto_term_matches_as_substring_of_the_value() -> None:
    """The spec wording: a fact *containing* a vetoed term.

    A hedge embedded in a longer value still vetoes — equality-only
    matching would be trivially bypassed by embedding (fail-open).
    """
    fact = _canonical_fact(
        clinical_fact_id="c-ta-hedge",
        value=ClinicalValue(
            value="paciente estable, creo que mejoró algo",
            certainty=Certainty.CONFIRMED,
            missingness=Missingness.PRESENT,
            provenance=Provenance(source_kind="clinical_note", source_ref="n-1"),
        ),
    )
    result = run_admissibility((fact,), frozenset({"creo que"}), RESOLVABLE_IDS)
    assert _codes(result) == (DiagnosticCode.POLICY_VIOLATION,)


def test_veto_term_equal_to_whole_value_matches() -> None:
    """Exact value == term is the containment edge case — still a hit."""
    fact = _canonical_fact(
        clinical_fact_id="c-ta-exact",
        value=ClinicalValue(
            value="estable",
            certainty=Certainty.UNRESOLVED,
            missingness=Missingness.PRESENT,
            provenance=Provenance(source_kind="clinical_note", source_ref="n-1"),
        ),
    )
    result = run_admissibility((fact,), frozenset({"estable"}), RESOLVABLE_IDS)
    assert _codes(result) == (DiagnosticCode.POLICY_VIOLATION,)


def test_non_string_values_never_match_a_veto_term() -> None:
    """Numeric values are never string-matched — no str coercion.

    A veto term of ``"72"`` must not hit the numeric value ``72``;
    the veto applies to the value's textual content only.
    """
    fact = _with_certainty(_numeric_fact(), Certainty.CONFIRMED)
    result = run_admissibility((fact,), frozenset({"72", "estable"}), RESOLVABLE_IDS)
    assert result.diagnostics == ()
    assert result.admitted == (fact,)


def test_assessed_absence_value_never_matches() -> None:
    """A MISSING fact (value None) has no textual content to veto."""
    fact = _canonical_fact(
        clinical_fact_id="c-ta-absent",
        value=ClinicalValue(
            value=None,
            certainty=Certainty.UNRESOLVED,
            missingness=Missingness.MISSING,
            provenance=Provenance(source_kind="lab", source_ref="l-1"),
        ),
    )
    result = run_admissibility((fact,), frozenset({"estable"}), RESOLVABLE_IDS)
    assert result.diagnostics == ()


# --- Veto misses and the D7 boundary (CRC-005) ---------------------------------


def test_veto_miss_passes_through_unchanged() -> None:
    """A value containing no veto term is admitted despite a live veto set."""
    fact = _canonical_fact()
    result = run_admissibility((fact,), frozenset({"estable"}), RESOLVABLE_IDS)
    assert result.diagnostics == ()
    assert result.admitted == (fact,)


def test_empty_veto_set_is_a_pure_no_op() -> None:
    """CRC-005 boundary pin: empty parameter means NO vetoes — period.

    The stage is a pure function of its inputs: a caller passing
    ``frozenset()`` gets no veto enforcement, even on values that
    would match real terms. The UNRESOLVED_POLICY guarding lives in
    the seed loader / composition root (design D7), NEVER here —
    this stage substitutes no default policy of its own.
    """
    vetoed = _canonical_fact(
        clinical_fact_id="c-ta-would-match",
        value=ClinicalValue(
            value="paciente estable",
            certainty=Certainty.CONFIRMED,
            missingness=Missingness.PRESENT,
            provenance=Provenance(source_kind="clinical_note", source_ref="n-1"),
        ),
    )
    ordinary = _numeric_fact()
    result = run_admissibility((vetoed, ordinary), frozenset(), RESOLVABLE_IDS)
    assert result.diagnostics == ()
    assert result.admitted == (vetoed, ordinary)


def test_stage_never_reads_the_core_policy_constant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D7: the injected parameter is the ONLY veto source.

    Mutating ``core.policy.NEVER_AUTO_TERMS`` (the frozen empty
    default) must change nothing — the stage holds no code path to
    it. Kills the core-constant-consultation mutation.
    """
    monkeypatch.setattr(
        core_policy, "NEVER_AUTO_TERMS", frozenset({"estable"})
    )
    fact = _canonical_fact(
        clinical_fact_id="c-ta-isolated",
        value=ClinicalValue(
            value="paciente estable",
            certainty=Certainty.UNRESOLVED,
            missingness=Missingness.PRESENT,
            provenance=Provenance(source_kind="clinical_note", source_ref="n-1"),
        ),
    )
    result = run_admissibility((fact,), frozenset(), RESOLVABLE_IDS)
    assert result.diagnostics == ()
    assert result.admitted == (fact,)


# --- Provenance resolution (FC-08) ----------------------------------------------


def test_unresolvable_refs_yield_provenance_error() -> None:
    """FC-08: refs pointing at no surviving SourceFactIR block the fact."""
    fact = _canonical_fact(
        clinical_fact_id="c-ta-ghost", source_fact_refs=("raw-ghost",)
    )
    result = run_admissibility((fact,), frozenset(), RESOLVABLE_IDS)
    assert _codes(result) == (DiagnosticCode.PROVENANCE_ERROR,)
    assert result.admitted == ()


def test_partially_unresolvable_refs_still_block() -> None:
    """ALL refs must resolve — one dangling ref poisons the lineage."""
    fact = _canonical_fact(
        clinical_fact_id="c-ta-partial",
        source_fact_refs=("raw-1", "raw-ghost"),
    )
    result = run_admissibility((fact,), frozenset(), RESOLVABLE_IDS)
    assert _codes(result) == (DiagnosticCode.PROVENANCE_ERROR,)
    assert result.admitted == ()


def test_absent_refs_yield_provenance_error() -> None:
    """FC-08 'absent' arm: empty source_fact_refs is no lineage.

    The U1 aggregate rejects this structurally at construction, but
    this stage consumes the bare fact tuple (design interface), so
    the absent arm is reachable — and fail-closed — HERE.
    """
    fact = _canonical_fact(
        clinical_fact_id="c-ta-nolineage", source_fact_refs=()
    )
    result = run_admissibility((fact,), frozenset(), RESOLVABLE_IDS)
    assert _codes(result) == (DiagnosticCode.PROVENANCE_ERROR,)
    assert result.admitted == ()


def test_resolvable_refs_admit() -> None:
    """Every ref present in the surviving set → clean admission."""
    fact = _canonical_fact(
        clinical_fact_id="c-ta-resolved",
        source_fact_refs=("raw-2", "raw-1"),
    )
    result = run_admissibility((fact,), frozenset(), RESOLVABLE_IDS)
    assert result.diagnostics == ()
    assert result.admitted == (fact,)


# --- Per-fact quarantine and partition (D1) -------------------------------------


def test_per_fact_quarantine_partition() -> None:
    """Veto quarantines its fact; clean facts of other fields survive."""
    clean_fc = _numeric_fact()
    vetoed = _canonical_fact(
        clinical_fact_id="c-ta-veto",
        value=ClinicalValue(
            value="paciente estable",
            certainty=Certainty.UNRESOLVED,
            missingness=Missingness.PRESENT,
            provenance=Provenance(source_kind="clinical_note", source_ref="n-1"),
        ),
    )
    ghost = _canonical_fact(
        clinical_fact_id="c-ta-ghost", source_fact_refs=("raw-ghost",)
    )
    clean_ta = _canonical_fact(
        clinical_fact_id="c-ta-clean", source_fact_refs=("raw-2",)
    )
    result = run_admissibility(
        (clean_fc, vetoed, ghost, clean_ta),
        frozenset({"estable"}),
        RESOLVABLE_IDS,
    )
    assert result.admitted == (clean_fc, clean_ta)
    assert _codes(result) == (
        DiagnosticCode.POLICY_VIOLATION,
        DiagnosticCode.PROVENANCE_ERROR,
    )


def test_fact_with_both_faults_emits_both_codes_and_quarantines_once() -> None:
    """D1 full diagnostic enumeration: both fault classes are reported."""
    fact = _canonical_fact(
        clinical_fact_id="c-ta-both",
        value=ClinicalValue(
            value="paciente estable",
            certainty=Certainty.CONFIRMED,
            missingness=Missingness.PRESENT,
            provenance=Provenance(source_kind="clinical_note", source_ref="n-1"),
        ),
        source_fact_refs=("raw-ghost",),
    )
    result = run_admissibility((fact,), frozenset({"estable"}), RESOLVABLE_IDS)
    assert _codes(result) == (
        DiagnosticCode.POLICY_VIOLATION,
        DiagnosticCode.PROVENANCE_ERROR,
    )
    assert result.admitted == ()


def test_each_fault_class_is_reported_specifically() -> None:
    """A vetoed-but-resolvable fact yields ONLY POLICY_VIOLATION; an
    unvetoed-but-dangling fact yields ONLY PROVENANCE_ERROR."""
    vetoed_clean = _canonical_fact(
        clinical_fact_id="c-ta-veto",
        value=ClinicalValue(
            value="paciente estable",
            certainty=Certainty.UNRESOLVED,
            missingness=Missingness.PRESENT,
            provenance=Provenance(source_kind="clinical_note", source_ref="n-1"),
        ),
        source_fact_refs=("raw-1",),
    )
    plain_ghost = _canonical_fact(
        clinical_fact_id="c-ta-ghost",
        value=ClinicalValue(
            value="120/80",
            certainty=Certainty.UNRESOLVED,
            missingness=Missingness.PRESENT,
            provenance=Provenance(source_kind="clinical_note", source_ref="n-1"),
        ),
        source_fact_refs=("raw-ghost",),
    )
    result = run_admissibility(
        (vetoed_clean, plain_ghost), frozenset({"estable"}), RESOLVABLE_IDS
    )
    assert _codes(result) == (
        DiagnosticCode.POLICY_VIOLATION,
        DiagnosticCode.PROVENANCE_ERROR,
    )


# --- Survivor identity (pure passthrough) ---------------------------------------


def test_survivors_pass_through_unchanged_by_identity() -> None:
    """Admitted facts are the SAME objects — never rebuilt or reordered."""
    first = _numeric_fact()
    second = _canonical_fact()
    result = run_admissibility(
        (first, second), frozenset({"estable"}), RESOLVABLE_IDS
    )
    assert result.admitted[0] is first
    assert result.admitted[1] is second


# --- Determinism (design Determinism Mechanism) ---------------------------------


def test_admissibility_is_deterministic() -> None:
    """Identical inputs — faults included — yield identical results."""
    facts = (
        _numeric_fact(),
        _canonical_fact(
            clinical_fact_id="c-ta-veto",
            value=ClinicalValue(
                value="paciente estable",
                certainty=Certainty.CONFIRMED,
                missingness=Missingness.PRESENT,
                provenance=Provenance(source_kind="clinical_note", source_ref="n-1"),
            ),
        ),
        _canonical_fact(
            clinical_fact_id="c-ta-ghost", source_fact_refs=("raw-ghost",)
        ),
    )
    first = run_admissibility(facts, frozenset({"estable"}), RESOLVABLE_IDS)
    second = run_admissibility(facts, frozenset({"estable"}), RESOLVABLE_IDS)
    assert first == second


def test_multiple_matching_terms_report_the_codepoint_minimal_one() -> None:
    """Frozenset iteration order never reaches output: the reported
    term is the codepoint-minimal match, stable across hash seeds."""
    fact = _canonical_fact(
        clinical_fact_id="c-ta-multi",
        value=ClinicalValue(
            value="alpha beta",
            certainty=Certainty.UNRESOLVED,
            missingness=Missingness.PRESENT,
            provenance=Provenance(source_kind="clinical_note", source_ref="n-1"),
        ),
    )
    result = run_admissibility(
        (fact,), frozenset({"beta", "alpha"}), RESOLVABLE_IDS
    )
    assert _codes(result) == (DiagnosticCode.POLICY_VIOLATION,)
    assert "alpha" in result.diagnostics[0].message
    assert "beta" not in result.diagnostics[0].message


# --- Downstream compatibility (U1 aggregate) ------------------------------------


def test_admitted_facts_construct_a_canonical_clinical_ir() -> None:
    """The stage's output is a valid CanonicalClinicalIR payload — the
    admissible set crosses into document selection as the aggregate."""
    facts = (
        _numeric_fact(),
        _canonical_fact(
            clinical_fact_id="c-ta-clean", source_fact_refs=("raw-2",)
        ),
    )
    result = run_admissibility(facts, frozenset(), RESOLVABLE_IDS)
    ir = CanonicalClinicalIR(facts=result.admitted)
    assert tuple(ir.facts) == result.admitted
