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
from collections.abc import Mapping
from typing import cast

import pytest

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
from clinical_compiler.passes.document_selection import (
    NURSING_RECORD_TELEGRAPHIC as SELECTION_NURSING_RECORD_TELEGRAPHIC,
)
from clinical_compiler.passes.document_selection import (
    SUPPORTED_MODES as SELECTION_SUPPORTED_MODES,
)
from clinical_compiler.passes.document_selection import (
    TELEGRAPHIC_ENTRY_ROLE as SELECTION_TELEGRAPHIC_ENTRY_ROLE,
)
from clinical_compiler.pipeline import derive_exit_code
from clinical_compiler.pipeline_types import StageResult
from clinical_compiler.renderers.deterministic import (
    CANONICAL_BREAKING_CHARACTERS,
    MODE_ALLOWED_PRESENTATION_ROLES,
    render_document,
)

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
        b"FC: 72 [present] [monitor m-9]\nTA: 120/80 [present] [clinical_note n-1]\n"
    )


def test_pc1_unassessed_field_renders_explicit_unknown() -> None:
    """PC-1 / task 3.6 glyph: no fact for FC → the frozen line
    ``FC: unknown [not_assessed]`` — never dropped, never rewritten as
    assessed absence."""
    result = _render((_canonical_fact(),))
    assert result.admitted[0] == (
        b"FC: unknown [not_assessed]\nTA: 120/80 [present] [clinical_note n-1]\n"
    )


def test_fact_carrying_not_assessed_renders_unknown_unassessed() -> None:
    """clinical-fact-model scenario: a fact with missingness
    ``not_assessed`` renders explicitly as unknown/unassessed."""
    fact = _canonical_fact(
        value=_clinical_value(value=None, missingness=Missingness.NOT_ASSESSED),
    )
    result = _render((fact,))
    assert result.admitted[0] == (
        b"FC: unknown [not_assessed]\nTA: unknown [not_assessed] [clinical_note n-1]\n"
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
        b"FC: unknown [not_assessed]\nTA: missing [missing] [lab l-3]\n"
    )


def test_not_applicable_fact_renders_distinct_glyph() -> None:
    """``not_applicable`` keeps its own assessed-absence glyph."""
    fact = _canonical_fact(
        value=_clinical_value(value=None, missingness=Missingness.NOT_APPLICABLE),
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
        b"FC: unknown [not_assessed]\nTA: unknown [unknown] [clinical_note n-1]\n"
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
        assert line == "" or (not line.endswith(" ") and not line.endswith("\t"))


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
    entries = _entries((_fc_fact(), _canonical_fact())) + (ghost,)
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


@pytest.mark.parametrize("line_break", ["\n", "\r"])
def test_value_with_line_break_is_unrenderable_render_error(
    line_break: str,
) -> None:
    """P0-1 injection closure: a contract-VALID verbatim string value
    carrying a line break has no canonical single-line rendering — the
    renderer fails closed (RENDER_ERROR, never bytes) instead of
    emitting a line that could borrow the document's line grammar and
    provenance. Verbatim values are never rewritten or escaped
    (input-contract spec: the rendered value is the raw value)."""
    fact = _canonical_fact(
        value=_clinical_value(value=f"72 [present]{line_break}FC: 200"),
    )
    result = _render((fact,))
    assert _codes(result) == (DiagnosticCode.RENDER_ERROR,)
    assert result.admitted == ()
    assert "line break" in result.diagnostics[0].message


@pytest.mark.parametrize("line_break", ["\n", "\r"])
def test_source_ref_with_line_break_is_unrenderable_render_error(
    line_break: str,
) -> None:
    """P0-1: the same closure over the provenance segment — a
    ``source_ref`` carrying a line break cannot render canonically
    (the provenance segment is single-line), so the fact fails closed
    with RENDER_ERROR instead of emitting split provenance bytes."""
    fact = _canonical_fact(
        value=_clinical_value(
            provenance=Provenance(source_kind="monitor", source_ref=f"m-{line_break}1")
        ),
    )
    result = _render((fact,))
    assert _codes(result) == (DiagnosticCode.RENDER_ERROR,)
    assert result.admitted == ()
    assert "source_ref" in result.diagnostics[0].message


# --- Audit remediation (2026-08-30): frozen canonical-breaking charset ----------


def test_canonical_breaking_charset_is_explicit_frozen_and_complete() -> None:
    """The refusal set is an EXPLICIT FROZEN codepoint set — C0 controls
    U+0000–U+001F (incl. TAB/LF/CR), DEL U+007F, C1 controls U+0080–
    U+009F (incl. NEL U+0085), LINE SEPARATOR U+2028, PARAGRAPH
    SEPARATOR U+2029 — 67 characters, frozen as a module constant with
    NO ``unicodedata`` runtime dependency (determinism across Python
    versions). Mutating the set membership fails here."""
    assert isinstance(CANONICAL_BREAKING_CHARACTERS, frozenset)
    expected_ords = (
        tuple(range(0x0020))  # C0 U+0000–U+001F
        + (0x007F,)
        + tuple(range(0x0080, 0x00A0))  # C1 U+0080–U+009F
        + (0x2028, 0x2029)
    )
    assert len(CANONICAL_BREAKING_CHARACTERS) == len(expected_ords) == 67
    for codepoint in expected_ords:
        assert chr(codepoint) in CANONICAL_BREAKING_CHARACTERS
    # LF/CR stay in the set (they remain the named "line break" fault).
    assert "\n" in CANONICAL_BREAKING_CHARACTERS
    assert "\r" in CANONICAL_BREAKING_CHARACTERS


@pytest.mark.parametrize(
    ("character", "codepoint_label"),
    [
        ("\x00", "U+0000"),
        ("\t", "U+0009"),
        ("\x7f", "U+007F"),
        ("\x85", "U+0085"),
        ("\x9f", "U+009F"),
        ("\u2028", "U+2028"),
        ("\u2029", "U+2029"),
    ],
)
def test_value_with_canonical_breaking_character_fails_closed(
    character: str,
    codepoint_label: str,
) -> None:
    """Audit defect (2026-08-30): every character class of the frozen
    set in a verbatim string value → ``RENDER_ERROR`` naming the exact
    codepoint, never bytes, never a transformation. U+2028/U+2029 are
    invisible line breaks in most viewers: rendering them verbatim would
    fabricate a second visual line inside one physical line."""
    fact = _canonical_fact(value=_clinical_value(value=f"72{character}"))
    result = _render((fact,))
    assert _codes(result) == (DiagnosticCode.RENDER_ERROR,)
    assert result.admitted == ()
    assert codepoint_label in result.diagnostics[0].message


@pytest.mark.parametrize(
    ("character", "codepoint_label"),
    [
        ("\x00", "U+0000"),
        ("\t", "U+0009"),
        ("\x7f", "U+007F"),
        ("\x85", "U+0085"),
        ("\x9f", "U+009F"),
        ("\u2028", "U+2028"),
        ("\u2029", "U+2029"),
    ],
)
def test_source_ref_with_canonical_breaking_character_fails_closed(
    character: str,
    codepoint_label: str,
) -> None:
    """The same frozen closure over the provenance segment — a
    ``source_ref`` carrying any canonical-breaking character has no
    canonical single-line rendering and fails closed with
    ``RENDER_ERROR`` naming the exact codepoint."""
    fact = _canonical_fact(
        value=_clinical_value(
            provenance=Provenance(
                source_kind="monitor", source_ref=f"m{character}1"
            )
        ),
    )
    result = _render((fact,))
    assert _codes(result) == (DiagnosticCode.RENDER_ERROR,)
    assert result.admitted == ()
    assert "source_ref" in result.diagnostics[0].message
    assert codepoint_label in result.diagnostics[0].message


@pytest.mark.parametrize(
    "value",
    [
        "120/80",
        "ñ",
        "36.6 °C",
        "café — reposo",
        "72 bpm (stable)",
        "áéíóú ü ß",
    ],
)
def test_printable_and_typical_unicode_values_still_render(value: str) -> None:
    """Boundary (no over-blocking): plain printable ASCII and typical
    clinical unicode (accents, degree sign, em dash) render verbatim as
    before — the refusal set is exact, not a category approximation."""
    result = _render((_canonical_fact(value=_clinical_value(value=value)),))
    assert result.diagnostics == ()
    assert value.encode("utf-8") in result.admitted[0]


@pytest.mark.parametrize("ref", ["n-1", "nota-ñ-1", "lab/2026/08/29", "m-9 (rev 2)"])
def test_printable_source_refs_still_render(ref: str) -> None:
    """Boundary (no over-blocking): printable ``source_ref`` strings —
    including accented and punctuation-bearing refs — render with their
    provenance segment intact."""
    fact = _canonical_fact(
        value=_clinical_value(
            provenance=Provenance(source_kind="monitor", source_ref=ref)
        ),
    )
    result = _render((fact,))
    assert result.diagnostics == ()
    assert f"[monitor {ref}]".encode() in result.admitted[0]


def test_multiple_inconsistencies_are_all_enumerated() -> None:
    """D1 full enumeration: a dangling ref AND an omitted fact both
    surface — one ``RENDER_ERROR`` each, no partial document."""
    facts = (_fc_fact(), _canonical_fact())
    ghost = DocumentEntry(clinical_fact_ref="c-ghost", presentation_role=ROLE)
    entries = _entries((_fc_fact(),)) + (ghost,)
    result = _render(facts, entries=entries)
    assert _codes(result) == (
        DiagnosticCode.RENDER_ERROR,
        DiagnosticCode.RENDER_ERROR,
    )
    assert result.admitted == ()


# --- Audit remediation ROUND 2 (2026-08-30): FC-11 presentation_role -----------

# FC-11's renderer boundary (independent audit round 2): the renderer is
# the LAST point where ``presentation_role`` exists — it validates each
# entry's role against the mode's allowed set BEFORE the role is lost
# (the linter only ever sees bytes). A role outside the allowed set is
# FC-11's prescribed ``LINT_FAILURE`` (the exit-code table maps the
# diagnostic CODE, not the emitting stage), fail-closed, one diagnostic
# per invalid entry. The mode→roles vocabulary is deliberately
# DUPLICATED from ``passes/document_selection`` (renderers must not
# import passes — D5); parity is pinned TEST-side here, where importing
# both is legitimate.

# Test-side parity witness: tests may import passes AND renderers; the
# production modules may not import each other (D5).

def test_renderer_role_vocabulary_parity_with_document_selection() -> None:
    """Cross-pin (TEST-side import): the renderer's duplicated
    mode→allowed-roles mapping is VALUE-IDENTICAL to the frozen
    selection vocabulary — every supported mode is covered, and the
    telegraphic mode's only allowed role is the selection stage's
    ``telegraphic_entry``. Drift in either constant fails here."""
    assert isinstance(MODE_ALLOWED_PRESENTATION_ROLES, Mapping)
    assert set(MODE_ALLOWED_PRESENTATION_ROLES) == set(SELECTION_SUPPORTED_MODES)
    assert MODE_ALLOWED_PRESENTATION_ROLES[SELECTION_NURSING_RECORD_TELEGRAPHIC] == (
        frozenset({SELECTION_TELEGRAPHIC_ENTRY_ROLE})
    )


@pytest.mark.parametrize("role", ["INVALID", "", "narrative_entry"])
def test_presentation_role_outside_the_allowed_set_is_lint_failure(
    role: str,
) -> None:
    """FC-11: an entry whose ``presentation_role`` is outside the
    document mode's allowed set → ``LINT_FAILURE`` (NOT RENDER_ERROR —
    the corpus freezes the code), NO partial document, and a
    deterministic message naming the offending role and the mode."""
    facts = (_fc_fact(), _canonical_fact())
    entries = (
        DocumentEntry(clinical_fact_ref="c-fc-1", presentation_role=role),
        DocumentEntry(clinical_fact_ref="c-ta-1", presentation_role=ROLE),
    )
    result = _render(facts, entries=entries)
    assert _codes(result) == (DiagnosticCode.LINT_FAILURE,)
    assert result.admitted == ()
    assert role in result.diagnostics[0].message
    assert MODE in result.diagnostics[0].message


def test_invalid_role_is_enumerated_per_entry_without_blocking_others_names() -> None:
    """D1 + determinism: two invalid roles enumerate exactly one
    ``LINT_FAILURE`` each, in entry order, each naming ITS entry's
    ref; a valid role between them emits nothing."""
    facts = (_fc_fact(), _canonical_fact())
    entries = (
        DocumentEntry(clinical_fact_ref="c-fc-1", presentation_role="bogus_a"),
        DocumentEntry(clinical_fact_ref="c-ta-1", presentation_role=ROLE),
    )
    single = _render(facts, entries=entries)
    assert [_codes(single)] == [(DiagnosticCode.LINT_FAILURE,)]
    assert "c-fc-1" in single.diagnostics[0].message

    both = _render(
        facts,
        entries=(
            DocumentEntry(clinical_fact_ref="c-ta-1", presentation_role="bogus_b"),
            DocumentEntry(clinical_fact_ref="c-fc-1", presentation_role="bogus_a"),
        ),
    )
    assert _codes(both) == (
        DiagnosticCode.LINT_FAILURE,
        DiagnosticCode.LINT_FAILURE,
    )
    assert "c-ta-1" in both.diagnostics[0].message
    assert "c-fc-1" in both.diagnostics[1].message
    assert both.admitted == ()


def test_document_entries_with_valid_role_render_unchanged() -> None:
    """Valid roles are unaffected: the mode's own role renders exactly
    as before the FC-11 hardening (golden bytes pinned)."""
    result = _render((_fc_fact(), _canonical_fact()))
    assert result.diagnostics == ()
    assert result.admitted[0] == (
        b"FC: 72 [present] [monitor m-9]\nTA: 120/80 [present] [clinical_note n-1]\n"
    )


def test_unknown_document_mode_has_no_allowed_roles_and_fails_closed() -> None:
    """An unknown mode carries NO allowed-role vocabulary — every entry
    fails closed as ``LINT_FAILURE`` (defense-in-depth: selection
    already blocks unknown modes; the renderer never trusts that)."""
    facts = (_fc_fact(),)
    entries = _entries(facts)
    document = DocumentIR(document_mode="SOME_OTHER_MODE", entries=entries)
    result = render_document(document, CanonicalClinicalIR(facts=facts))
    assert _codes(result) == (DiagnosticCode.LINT_FAILURE,)
    assert result.admitted == ()
    assert "SOME_OTHER_MODE" in result.diagnostics[0].message


def test_fc11_role_diagnostic_maps_to_exit_ten() -> None:
    """FC-11's prescribed exit: the role diagnostic is a
    ``LINT_FAILURE`` regardless of its emitting stage, and the frozen
    exit-code table maps that code to 10 — the diagnostic SET drives
    the exit code, never the stage that emitted it."""
    facts = (_fc_fact(),)
    entries = (
        DocumentEntry(clinical_fact_ref="c-fc-1", presentation_role="INVALID"),
    )
    result = _render(facts, entries=entries)
    exit_code = derive_exit_code(result.diagnostics)
    assert exit_code == 10


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
