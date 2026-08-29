"""Unit tests for clinical_compiler.renderers.deterministic (tasks 3.3 + 3.5).

Covers the deterministic renderer's frozen contract: canonical byte
output per the design Determinism Mechanism (task 3.3) and the FC-10
injection fixture — a ``DocumentIR`` entry referencing an absent
canonical id yields ``RENDER_ERROR`` and never a partial document
(task 3.5, renderer half; the FC-11 ``LINT_FAILURE`` half belongs to
the linter unit).

Renderer I/O (design §Module Map + CRC-004): the renderer consumes the
``DocumentIR`` (refs + presentation roles only) TOGETHER with the
``CanonicalClinicalIR`` it resolves against — the IR never stores
values, so the fact aggregate is the single value authority and the
dangling-ref safety net's reference point.
"""

import hashlib
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
from clinical_compiler.pipeline_types import StageResult
from clinical_compiler.renderers.deterministic import render_document

MODE = "NURSING_RECORD_TELEGRAPHIC"
ROLE = "telegraphic_entry"


def _clinical_value(**overrides: object) -> ClinicalValue:
    """Build a present TA clinical value with the given overrides."""
    params: dict[str, object] = {
        "value": "120/80",
        "certainty": Certainty.UNRESOLVED,
        "missingness": Missingness.PRESENT,
        "provenance": Provenance(source_kind="clinical_note", source_ref="n-1"),
    }
    params.update(overrides)
    return ClinicalValue(
        value=params["value"],
        certainty=cast(Certainty, params["certainty"]),
        missingness=cast(Missingness, params["missingness"]),
        provenance=cast(Provenance, params["provenance"]),
    )


def _canonical_fact(**overrides: object) -> CanonicalClinicalFact:
    """Build a canonical TA fact with the given field overrides."""
    params: dict[str, object] = {
        "clinical_fact_id": "c-ta-1",
        "field_id": "TA",
        "value": _clinical_value(),
        "source_fact_refs": ("raw-1",),
    }
    params.update(overrides)
    return CanonicalClinicalFact(
        clinical_fact_id=cast(str, params["clinical_fact_id"]),
        field_id=cast(str, params["field_id"]),
        value=cast(ClinicalValue, params["value"]),
        source_fact_refs=cast("tuple[str, ...]", params["source_fact_refs"]),
    )


def _fc_fact(clinical_fact_id: str = "c-fc-1") -> CanonicalClinicalFact:
    """Build a present FC fact (int value, monitor provenance)."""
    return _canonical_fact(
        clinical_fact_id=clinical_fact_id,
        field_id="FC",
        value=_clinical_value(
            value=72,
            provenance=Provenance(source_kind="monitor", source_ref="m-9"),
        ),
    )


def _entries(facts: tuple[CanonicalClinicalFact, ...]) -> tuple[DocumentEntry, ...]:
    """Build one entry per fact, in the given fact order."""
    return tuple(
        DocumentEntry(clinical_fact_ref=fact.clinical_fact_id, presentation_role=ROLE)
        for fact in facts
    )


def _render(
    facts: tuple[CanonicalClinicalFact, ...],
    entries: tuple[DocumentEntry, ...] | None = None,
) -> StageResult[bytes]:
    """Render a document over the facts, defaulting to one entry each."""
    document = DocumentIR(
        document_mode=MODE,
        entries=_entries(facts) if entries is None else entries,
    )
    return render_document(document, CanonicalClinicalIR(facts=facts))


def _codes(result: StageResult[bytes]) -> tuple[DiagnosticCode, ...]:
    """Return the emitted diagnostic codes in emission order."""
    return tuple(diagnostic.code for diagnostic in result.diagnostics)


# --- Stage contract (renderer speaks StageResult[bytes]) -----------------------


def test_clean_render_admits_document_bytes_without_diagnostics() -> None:
    """The renderer returns one bytes document and no diagnostics."""
    result = _render((_fc_fact(), _canonical_fact()))
    assert isinstance(result, StageResult)
    assert result.diagnostics == ()
    assert len(result.admitted) == 1
    assert isinstance(result.admitted[0], bytes)


# --- Canonical format (task 3.3 — exact bytes) ---------------------------------


def test_renders_canonical_telegraphic_document_bytes() -> None:
    """Sorted fact lines: field, value glyph, missingness, provenance.

    Pinned against literal bytes (not composed from the implementation)
    so any glyph-vocabulary mutation fails here — this is the format
    the Phase-3 golden freeze (task 3.7) will commit.
    """
    result = _render((_canonical_fact(), _fc_fact()))
    assert result.admitted[0] == (
        b"FC: 72 [present] [monitor m-9]\n"
        b"TA: 120/80 [present] [clinical_note n-1]\n"
    )


def test_pc1_unassessed_field_renders_explicit_unknown() -> None:
    """PC-1 / task 3.6 glyph: no fact for FC → the frozen line
    ``FC: unknown [not_assessed]`` — never dropped, never rewritten as
    assessed absence."""
    result = _render((_canonical_fact(),))
    assert result.admitted[0] == (
        b"FC: unknown [not_assessed]\n"
        b"TA: 120/80 [present] [clinical_note n-1]\n"
    )


def test_fact_carrying_not_assessed_renders_unknown_unassessed() -> None:
    """clinical-fact-model scenario: a fact with missingness
    ``not_assessed`` renders explicitly as unknown/unassessed."""
    fact = _canonical_fact(
        value=_clinical_value(
            value=None, missingness=Missingness.NOT_ASSESSED
        ),
    )
    result = _render((fact,))
    assert result.admitted[0] == (
        b"FC: unknown [not_assessed]\n"
        b"TA: unknown [not_assessed] [clinical_note n-1]\n"
    )


def test_missing_fact_renders_assessed_absence_with_provenance() -> None:
    """PC-2: an assessed absence (``missing``) renders WITH provenance
    and a glyph distinct from the unassessed ``unknown`` — the two
    absence families are never conflated."""
    fact = _canonical_fact(
        value=_clinical_value(
            value=None,
            missingness=Missingness.MISSING,
            provenance=Provenance(source_kind="lab", source_ref="l-3"),
        ),
    )
    result = _render((fact,))
    assert result.admitted[0] == (
        b"FC: unknown [not_assessed]\n"
        b"TA: missing [missing] [lab l-3]\n"
    )


def test_not_applicable_fact_renders_distinct_glyph() -> None:
    """``not_applicable`` keeps its own assessed-absence glyph."""
    fact = _canonical_fact(
        value=_clinical_value(
            value=None, missingness=Missingness.NOT_APPLICABLE
        ),
    )
    result = _render((fact,))
    assert result.admitted[0] == (
        b"FC: unknown [not_assessed]\n"
        b"TA: not_applicable [not_applicable] [clinical_note n-1]\n"
    )


def test_unknown_missingness_renders_explicit_unknown() -> None:
    """The unassessed family renders the explicit ``unknown`` word."""
    fact = _canonical_fact(
        value=_clinical_value(value=None, missingness=Missingness.UNKNOWN),
    )
    result = _render((fact,))
    assert result.admitted[0] == (
        b"FC: unknown [not_assessed]\n"
        b"TA: unknown [unknown] [clinical_note n-1]\n"
    )


# --- Value formatting (Determinism Mechanism #3) -------------------------------


def test_numbers_render_locale_free() -> None:
    """``str(int)`` for integers; floats via the deterministic shortest
    representation — never locale ``format()``."""
    fc_int = _canonical_fact(
        clinical_fact_id="c-fc-int",
        field_id="FC",
        value=_clinical_value(
            value=-3,
            provenance=Provenance(source_kind="monitor", source_ref="m-1"),
        ),
    )
    result = _render((fc_int,))
    lines = result.admitted[0].decode("utf-8").splitlines()
    assert lines[0] == "FC: -3 [present] [monitor m-1]"
    assert lines[1] == "TA: unknown [not_assessed]"

    fc_float = _canonical_fact(
        clinical_fact_id="c-fc-float",
        field_id="FC",
        value=_clinical_value(
            value=72.5,
            provenance=Provenance(source_kind="monitor", source_ref="m-1"),
        ),
    )
    result = _render((fc_float,))
    assert result.admitted[0].decode("utf-8").splitlines()[0] == (
        "FC: 72.5 [present] [monitor m-1]"
    )


def test_string_values_render_verbatim_utf8() -> None:
    """String values render verbatim, UTF-8 encoded."""
    fact = _canonical_fact(
        value=_clinical_value(value="120/80 mmHg — reposo"),
    )
    result = _render((fact,))
    document = result.admitted[0]
    assert document.decode("utf-8").splitlines()[1] == (
        "TA: 120/80 mmHg — reposo [present] [clinical_note n-1]"
    )


# --- Byte-level invariants (UTF-8, LF only, no trailing whitespace) ------------


def test_output_is_utf8_lf_only_without_trailing_whitespace() -> None:
    """Determinism Mechanism #3: UTF-8, ``\\n`` only, no trailing
    whitespace on any line, exactly one final newline."""
    result = _render((_fc_fact(), _canonical_fact()))
    document = result.admitted[0]
    assert b"\r" not in document
    assert document.endswith(b"\n")
    assert not document.endswith(b"\n\n")
    text = document.decode("utf-8")
    for line in text.split("\n"):
        assert line == "" or (
            not line.endswith(" ") and not line.endswith("\t")
        )


# --- Determinism (sort key, hash-order independence) ---------------------------


def test_entry_order_of_the_ir_does_not_reach_the_output() -> None:
    """The renderer sorts by the resolved ``(field_id,
    clinical_fact_id)`` codepoint key itself — a permuted DocumentIR
    renders identical bytes (the renderer never trusts IR entry
    order; DocumentEntry carries no field_id to sort by)."""
    facts = (_canonical_fact(), _fc_fact())
    canonical = _render(facts)
    reversed_entries = tuple(reversed(_entries(facts)))
    permuted = _render(facts, entries=reversed_entries)
    assert permuted.admitted[0] == canonical.admitted[0]


def test_fact_insertion_order_before_aggregate_is_immaterial() -> None:
    """Facts inserted in different orders construct identical
    aggregates and render identical bytes."""
    first = _render((_fc_fact(), _canonical_fact()))
    second = _render((_canonical_fact(), _fc_fact()))
    assert second.admitted[0] == first.admitted[0]


def test_sha256_digest_identical_across_permutations_and_repeats() -> None:
    """Byte determinism pinned by SHA-256: repeat renders and order
    permutations that must not matter yield equal digests."""
    canonical = _render((_fc_fact(), _canonical_fact()))
    repeat = _render((_fc_fact(), _canonical_fact()))
    permuted = _render((_canonical_fact(), _fc_fact()))
    digests = {
        hashlib.sha256(result.admitted[0]).hexdigest()
        for result in (canonical, repeat, permuted)
    }
    assert len(digests) == 1


# --- FC-10 injection fixture (task 3.5 — RENDER_ERROR safety net) ---------------


def test_fc10_dangling_ref_yields_render_error_and_no_partial_document() -> None:
    """FC-10: an entry referencing an absent canonical id →
    ``RENDER_ERROR``; the renderer never crashes and never emits a
    partial document (defense-in-depth, CRC-004 renderer side)."""
    ghost = DocumentEntry(clinical_fact_ref="c-ghost", presentation_role=ROLE)
    entries = (_entries((_fc_fact(), _canonical_fact())) + (ghost,))
    result = _render((_fc_fact(), _canonical_fact()), entries=entries)
    assert _codes(result) == (DiagnosticCode.RENDER_ERROR,)
    assert result.admitted == ()
    assert "c-ghost" in result.diagnostics[0].message


def test_omitted_fact_yields_render_error() -> None:
    """Safety net (omission direction): a canonical fact with no
    document entry would be silently dropped from the document —
    blocked as ``RENDER_ERROR`` instead (design D1: no silent
    omission)."""
    facts = (_fc_fact(), _canonical_fact())
    entries = _entries((_fc_fact(),))
    result = _render(facts, entries=entries)
    assert _codes(result) == (DiagnosticCode.RENDER_ERROR,)
    assert result.admitted == ()
    assert "c-ta-1" in result.diagnostics[0].message


def test_duplicate_ref_yields_render_error() -> None:
    """Safety net: one entry per fact — a repeated ref is an internal
    inconsistency, not two document lines."""
    entries = _entries((_fc_fact(),)) + _entries((_fc_fact(),))
    result = _render((_fc_fact(),), entries=entries)
    assert _codes(result) == (DiagnosticCode.RENDER_ERROR,)
    assert result.admitted == ()
    assert "c-fc-1" in result.diagnostics[0].message


def test_unrenderable_value_type_yields_render_error() -> None:
    """Determinism net: a value whose type has no canonical rendering
    (here a dict, whose ``str()`` would leak iteration order —
    Determinism Mechanism #4) fails closed instead of producing
    nondeterministic bytes."""
    fact = _canonical_fact(
        value=_clinical_value(value={"nested": "dict"}),
    )
    result = _render((fact,))
    assert _codes(result) == (DiagnosticCode.RENDER_ERROR,)
    assert result.admitted == ()


def test_multiple_inconsistencies_are_all_enumerated() -> None:
    """D1 full enumeration: a dangling ref AND an omitted fact both
    surface — one ``RENDER_ERROR`` each, no partial document."""
    facts = (_fc_fact(), _canonical_fact())
    ghost = DocumentEntry(clinical_fact_ref="c-ghost", presentation_role=ROLE)
    entries = (_entries((_fc_fact(),)) + (ghost,))
    result = _render(facts, entries=entries)
    assert _codes(result) == (
        DiagnosticCode.RENDER_ERROR,
        DiagnosticCode.RENDER_ERROR,
    )
    assert result.admitted == ()


# --- Empty-entries edge ---------------------------------------------------------


def test_empty_entries_and_empty_aggregate_render_all_unassessed() -> None:
    """The consistent empty document: no entries and no facts render
    every contract field as explicitly unassessed — deterministic,
    never a crash, never an empty byte string."""
    result = _render((), entries=())
    assert result.diagnostics == ()
    assert result.admitted[0] == (
        b"FC: unknown [not_assessed]\nTA: unknown [not_assessed]\n"
    )


# --- Provenance on every fact line (Open Question 4 invariant) ------------------


def test_provenance_on_every_fact_line_and_none_on_unassessed_lines() -> None:
    """Every line carrying a fact carries its provenance; unassessed
    document-level lines carry none (there is no source to cite — the
    frozen PC-1 line has none)."""
    result = _render((_fc_fact(), _canonical_fact()))
    lines = result.admitted[0].decode("utf-8").splitlines()
    assert lines[0].endswith("[monitor m-9]")
    assert lines[1].endswith("[clinical_note n-1]")

    unassessed = _render((_canonical_fact(),))
    fc_line = unassessed.admitted[0].decode("utf-8").splitlines()[0]
    assert fc_line == "FC: unknown [not_assessed]"
