"""Unit tests for clinical_compiler.linter.conformance (tasks 3.4 + 3.5).

Covers the conformance linter's frozen contract: rendered bytes are
validated against the ``NURSING_RECORD_TELEGRAPHIC`` mode rules — the
line grammar ``{field}: {glyph} [{missingness}] [{source_kind}
{source_ref}]``, the allowed glyph/missingness vocabulary, and the byte
invariants (UTF-8 decodable, LF-only, no trailing whitespace, exactly
one final newline). Any violation yields ``LINT_FAILURE`` and the
document is NOT accepted as final (determinism-rendering spec, Conformance
Linter scenarios); the linter never raises (design M2.1) and enumerates
every violation (design D1).

FC-11 (task 3.5, linter half): the corpus freezes the class as "rendered
output violates a mode conformance rule", exercised via injected bytes —
each rule family has a dedicated violating fixture, so removing or
weakening any rule fails at least one test (mutation-sensitive net).

Positive pin (task 3.4): every test of genuine renderer output renders
via the REAL P3-U2 renderer on constructed facts and asserts a
lint-clean verdict — the linter must accept exactly the bytes the
frozen renderer produces, neither inventing rules nor weakening them.
"""

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
from clinical_compiler.linter.conformance import lint_conformance
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


def _rendered(
    facts: tuple[CanonicalClinicalFact, ...],
) -> bytes:
    """Render genuine renderer output over the given facts."""
    document = DocumentIR(
        document_mode=MODE,
        entries=tuple(
            DocumentEntry(clinical_fact_ref=fact.clinical_fact_id, presentation_role=ROLE)
            for fact in facts
        ),
    )
    result = render_document(document, CanonicalClinicalIR(facts=facts))
    assert result.diagnostics == ()
    return result.admitted[0]


def _lint(document: bytes, mode: str = MODE) -> StageResult[bytes]:
    """Lint a document, asserting the stage contract shape."""
    result = lint_conformance(document, mode)
    assert isinstance(result, StageResult)
    return result


def _codes(result: StageResult[bytes]) -> tuple[DiagnosticCode, ...]:
    """Return the emitted diagnostic codes in emission order."""
    return tuple(diagnostic.code for diagnostic in result.diagnostics)


def _messages(result: StageResult[bytes]) -> list[str]:
    """Return the emitted diagnostic messages in emission order."""
    return [diagnostic.message for diagnostic in result.diagnostics]


# --- Stage contract + clean pass (renderer-produced truth) ----------------------


def test_clean_rendered_document_lints_clean_and_is_accepted() -> None:
    """Real renderer output over ordinary facts → zero diagnostics, the
    bytes admitted as final (spec: only a lint-clean document is
    accepted as final)."""
    document = _rendered((_fc_fact(), _canonical_fact()))
    result = _lint(document)
    assert result.diagnostics == ()
    assert result.admitted == (document,)


def test_every_glyph_family_renders_and_lints_clean() -> None:
    """One document exercising every frozen glyph family — present
    int/float/unicode string, assessed absence (missing,
    not_applicable), the unassessed family (unknown, not_assessed
    fact), and the unassessed document-level sweep — all lint clean."""
    facts: tuple[CanonicalClinicalFact, ...] = (
        _canonical_fact(
            clinical_fact_id="c-ta-1",
            value=_clinical_value(value="120/80 mmHg — reposo"),
        ),
        _canonical_fact(
            clinical_fact_id="c-ta-2",
            value=_clinical_value(
                value=None,
                missingness=Missingness.MISSING,
                provenance=Provenance(source_kind="lab", source_ref="l-3"),
            ),
        ),
        _fc_fact("c-fc-1"),
        _canonical_fact(
            clinical_fact_id="c-fc-2",
            field_id="FC",
            value=_clinical_value(
                value=72.5,
                provenance=Provenance(source_kind="monitor", source_ref="m-2"),
            ),
        ),
        _canonical_fact(
            clinical_fact_id="c-fc-3",
            field_id="FC",
            value=_clinical_value(
                value=None, missingness=Missingness.NOT_ASSESSED
            ),
        ),
    )
    document = _rendered(facts)
    result = _lint(document)
    assert result.diagnostics == ()
    assert result.admitted == (document,)


def test_all_unassessed_document_lints_clean() -> None:
    """The consistent empty document (no facts) renders every contract
    field as ``{field}: unknown [not_assessed]`` with NO provenance
    segment — grammar-clean (the unassessed line carries no source)."""
    result = _lint(_rendered(()))
    assert result.diagnostics == ()
    assert result.admitted[0] == (
        b"FC: unknown [not_assessed]\nTA: unknown [not_assessed]\n"
    )


# --- Grammar tolerance pins (producible renderer output stays clean) ------------


def test_value_glyph_containing_brackets_and_colons_lints_clean() -> None:
    """Verbatim string values may contain ``[...]`` segments and
    ``: `` — the grammar parses from the line's right end, so the LAST
    two bracket groups are the missingness/provenance segments and the
    value glyphs before them stay verbatim (right-anchored parse)."""
    fact = _canonical_fact(
        value=_clinical_value(value="x [present] note: 72"),
    )
    document = _rendered((fact,))
    assert document.endswith(
        b"TA: x [present] note: 72 [present] [clinical_note n-1]\n"
    )
    assert _lint(document).diagnostics == ()


def test_empty_string_present_value_lints_clean() -> None:
    """A contract-admissible empty string value renders an empty glyph
    (``TA:  [present] ...``) — producible renderer output, so the
    grammar must accept it (no invented non-empty rule for PRESENT)."""
    fact = _canonical_fact(value=_clinical_value(value=""))
    document = _rendered((fact,))
    assert document.endswith(b"TA:  [present] [clinical_note n-1]\n")
    assert _lint(document).diagnostics == ()


def test_present_glyph_spelling_an_absence_word_lints_clean() -> None:
    """PRESENT glyphs are unrestricted verbatim values — a string value
    that spells ``missing`` must lint clean (glyph/missingness
    consistency constrains only the assessed/unassessed families)."""
    fact = _canonical_fact(value=_clinical_value(value="missing"))
    document = _rendered((fact,))
    assert document.endswith(b"TA: missing [present] [clinical_note n-1]\n")
    assert _lint(document).diagnostics == ()


# --- Byte invariants (injected violating bytes → LINT_FAILURE) ------------------


def test_crlf_line_endings_yield_lint_failure() -> None:
    """CRLF bytes violate the LF-only invariant → LINT_FAILURE, never
    accepted."""
    document = b"FC: 72 [present] [monitor m-1]\r\n"
    result = _lint(document)
    assert DiagnosticCode.LINT_FAILURE in _codes(result)
    assert result.admitted == ()


def test_lone_carriage_return_inside_document_yields_lint_failure() -> None:
    """A CR anywhere in the document (not only as CRLF) violates
    LF-only."""
    document = b"FC: 72 [present] [monitor m-1]\nTA: 120/80\r [present] [monitor m-1]\n"
    result = _lint(document)
    assert DiagnosticCode.LINT_FAILURE in _codes(result)
    assert result.admitted == ()


def test_trailing_space_yields_lint_failure() -> None:
    """A trailing space on any line violates the no-trailing-whitespace
    invariant."""
    result = _lint(b"FC: 72 [present] [monitor m-1] \n")
    assert DiagnosticCode.LINT_FAILURE in _codes(result)
    assert result.admitted == ()


def test_trailing_tab_yields_lint_failure() -> None:
    """A trailing tab on any line violates the no-trailing-whitespace
    invariant."""
    result = _lint(b"FC: 72 [present] [monitor m-1]\t\n")
    assert DiagnosticCode.LINT_FAILURE in _codes(result)
    assert result.admitted == ()


def test_doubled_final_newline_yields_lint_failure() -> None:
    """A blank final line (``\\n\\n`` at the end) violates the
    exactly-one-final-newline invariant."""
    result = _lint(b"FC: 72 [present] [monitor m-1]\n\n")
    assert DiagnosticCode.LINT_FAILURE in _codes(result)
    assert result.admitted == ()


def test_blank_line_inside_document_yields_lint_failure() -> None:
    """A blank line in the middle of the document fails the line
    grammar (a line must carry ``{field}: ...``)."""
    document = (
        b"FC: 72 [present] [monitor m-1]\n"
        b"\n"
        b"TA: 120/80 [present] [monitor m-1]\n"
    )
    result = _lint(document)
    assert DiagnosticCode.LINT_FAILURE in _codes(result)
    assert result.admitted == ()


def test_missing_final_newline_yields_lint_failure() -> None:
    """A document not ending in ``\\n`` violates the byte invariants —
    and its last unterminated line is still linted (not skipped)."""
    document = b"FC: 72 [present] [monitor m-1]\nTA: 120/80 [present] [monitor m-1]"
    result = _lint(document)
    assert DiagnosticCode.LINT_FAILURE in _codes(result)
    assert result.admitted == ()


def test_missing_final_newline_last_line_is_still_linted() -> None:
    """The unterminated last line is analyzed too: a grammar fault on
    it is enumerated alongside the missing-newline violation (D1)."""
    document = b"FC: 72 [present] [monitor m-1]\nnot a telegraphic line"
    result = _lint(document)
    messages = _messages(result)
    assert len(messages) == 2
    assert "final newline" in messages[0]
    assert "grammar" in messages[1]


def test_undecodable_bytes_yield_lint_failure_and_never_raise() -> None:
    """Invalid UTF-8 bytes violate the decodability invariant →
    LINT_FAILURE (M2.1: the linter never raises, whatever the bytes)."""
    result = _lint(b"FC: 72 [present] [monitor \xffm-1]\n")
    assert _codes(result) == (DiagnosticCode.LINT_FAILURE,)
    assert "UTF-8" in result.diagnostics[0].message
    assert result.admitted == ()


def test_arbitrary_garbage_bytes_never_raise() -> None:
    """M2.1 pin: no byte sequence makes the linter raise — worst case
    it enumerates violations."""
    result = _lint(b"\xff\xfe\x00garbage without structure")
    assert DiagnosticCode.LINT_FAILURE in _codes(result)
    assert result.admitted == ()


# --- Line grammar + vocabulary (injected violating bytes) -----------------------


def test_line_without_field_prefix_yields_lint_failure() -> None:
    """A line missing the ``{field}: `` prefix fails the grammar."""
    result = _lint(b"120/80 [present] [monitor m-1]\n")
    assert _codes(result) == (DiagnosticCode.LINT_FAILURE,)
    assert result.admitted == ()


def test_line_missing_colon_separator_yields_lint_failure() -> None:
    """A line with a field token but no ``: `` separator fails the
    grammar."""
    result = _lint(b"TA 120/80 [present] [monitor m-1]\n")
    assert _codes(result) == (DiagnosticCode.LINT_FAILURE,)
    assert result.admitted == ()


def test_field_outside_contract_yields_lint_failure() -> None:
    """A well-formed line over a field outside the frozen contract
    vocabulary fails the grammar's field token rule."""
    result = _lint(b"XX: 1 [present] [monitor m-1]\n")
    assert _codes(result) == (DiagnosticCode.LINT_FAILURE,)
    assert "XX" in result.diagnostics[0].message
    assert result.admitted == ()


def test_missingness_token_outside_vocabulary_yields_lint_failure() -> None:
    """A bracketed missingness token outside the frozen taxonomy fails
    the vocabulary rule."""
    result = _lint(b"TA: 120/80 [maybe] [monitor m-1]\n")
    assert _codes(result) == (DiagnosticCode.LINT_FAILURE,)
    assert "maybe" in result.diagnostics[0].message
    assert result.admitted == ()


def test_missing_missingness_segment_yields_lint_failure() -> None:
    """A line with only a provenance segment (no missingness bracket)
    fails the grammar."""
    result = _lint(b"TA: 120/80 [monitor m-1]\n")
    assert _codes(result) == (DiagnosticCode.LINT_FAILURE,)
    assert result.admitted == ()


def test_source_kind_outside_vocabulary_yields_lint_failure() -> None:
    """A provenance segment whose source_kind is outside the frozen
    feed vocabulary fails the vocabulary rule."""
    result = _lint(b"TA: 120/80 [present] [gossip m-1]\n")
    assert _codes(result) == (DiagnosticCode.LINT_FAILURE,)
    assert "gossip" in result.diagnostics[0].message
    assert result.admitted == ()


# --- Glyph/missingness consistency (allowed glyphs) -----------------------------


def test_assessed_missing_requires_the_missing_glyph() -> None:
    """``[missing]`` renders the taxonomy's own ``missing`` glyph — any
    other glyph is a conformance violation."""
    result = _lint(b"TA: 120/80 [missing] [monitor m-1]\n")
    assert _codes(result) == (DiagnosticCode.LINT_FAILURE,)
    assert result.admitted == ()


def test_not_applicable_requires_the_not_applicable_glyph() -> None:
    """``[not_applicable]`` renders its own distinct glyph."""
    result = _lint(b"TA: 120/80 [not_applicable] [monitor m-1]\n")
    assert _codes(result) == (DiagnosticCode.LINT_FAILURE,)
    assert result.admitted == ()


def test_not_assessed_requires_the_unknown_glyph() -> None:
    """``[not_assessed]`` renders the explicit ``unknown`` word — never
    a value glyph (Missingness Non-Conflation, lint side)."""
    result = _lint(b"TA: 120/80 [not_assessed] [monitor m-1]\n")
    assert _codes(result) == (DiagnosticCode.LINT_FAILURE,)
    assert result.admitted == ()


def test_unknown_requires_the_unknown_glyph() -> None:
    """``[unknown]`` renders the explicit ``unknown`` word."""
    result = _lint(b"TA: 120/80 [unknown] [monitor m-1]\n")
    assert _codes(result) == (DiagnosticCode.LINT_FAILURE,)
    assert result.admitted == ()


# --- FC-11 via the real renderer: values the renderer does not police -----------


def test_rendered_value_with_embedded_newline_yields_lint_failure() -> None:
    """The renderer renders verbatim string values without policing
    their content (P3-U2 flag) — a value containing a newline breaks
    the line grammar in the BYTES, and the linter (defense-in-depth,
    FC-11) must catch it: every broken line is enumerated."""
    fact = _canonical_fact(value=_clinical_value(value="72\nbpm"))
    document = _rendered((fact,))
    assert document == (
        b"FC: unknown [not_assessed]\n"
        b"TA: 72\n"
        b"bpm [present] [clinical_note n-1]\n"
    )
    result = _lint(document)
    assert _codes(result) == (
        DiagnosticCode.LINT_FAILURE,
        DiagnosticCode.LINT_FAILURE,
    )
    assert result.admitted == ()


def test_rendered_source_ref_with_embedded_newline_yields_lint_failure() -> None:
    """Same net over the provenance segment: an embedded newline in a
    source_ref breaks the bytes — caught as LINT_FAILURE, never
    raised."""
    fact = _canonical_fact(
        value=_clinical_value(
            provenance=Provenance(source_kind="monitor", source_ref="m-\n1"),
        ),
    )
    document = _rendered((fact,))
    assert document == (
        b"FC: unknown [not_assessed]\n"
        b"TA: 120/80 [present] [monitor m-\n"
        b"1]\n"
    )
    result = _lint(document)
    assert DiagnosticCode.LINT_FAILURE in _codes(result)
    assert result.admitted == ()


# --- Unknown mode (fail-closed) --------------------------------------------------


def test_unknown_document_mode_fails_closed_with_lint_failure() -> None:
    """The linter validates against its mode's rules — an unknown mode
    has no rules to apply, so the document cannot be validated and the
    stage fails closed with its only mapped code (defense-in-depth:
    unknown modes were already blocked at selection)."""
    document = _rendered((_fc_fact(),))
    result = _lint(document, "SOME_OTHER_MODE")
    assert _codes(result) == (DiagnosticCode.LINT_FAILURE,)
    assert "SOME_OTHER_MODE" in result.diagnostics[0].message
    assert result.admitted == ()


# --- D1 full enumeration + determinism -------------------------------------------


def test_multiple_violations_are_all_enumerated_in_deterministic_order() -> None:
    """D1: a document violating several independent rules enumerates
    one LINT_FAILURE per violated rule — byte invariants first (final
    newline, CR), then per-line checks in line order (trailing
    whitespace, grammar)."""
    document = (
        b"TA: 120/80 [maybe] [monitor m-1] \r\n"
        b"FC: 72 [present] [monitor m-2]"
    )
    result = _lint(document)
    messages = _messages(result)
    assert _codes(result) == (
        DiagnosticCode.LINT_FAILURE,
        DiagnosticCode.LINT_FAILURE,
        DiagnosticCode.LINT_FAILURE,
        DiagnosticCode.LINT_FAILURE,
    )
    assert "final newline" in messages[0]
    assert "carriage return" in messages[1]
    assert "trailing whitespace" in messages[2]
    assert "grammar" in messages[3]
    assert result.admitted == ()


def test_identical_input_yields_identical_diagnostics() -> None:
    """Determinism: linting the same violating bytes twice yields
    byte-identical diagnostics (codes, messages, order)."""
    document = b"TA: 120/80 [maybe] [monitor m-1] \r\n"
    first = _lint(document)
    second = _lint(document)
    assert first.diagnostics == second.diagnostics
    assert first.admitted == second.admitted


def test_only_lint_clean_output_is_accepted_as_final() -> None:
    """Spec scenario (Lint failure blocks): a violating document is
    never admitted — ``admitted`` is empty for every violating fixture
    and the document bytes are never passed through."""
    violating = (
        b"FC: 72 [present] [monitor m-1]\r\n",
        b"FC: 72 [present] [monitor m-1] \n",
        b"XX: 1 [present] [monitor m-1]\n",
        b"TA: 120/80 [maybe] [monitor m-1]\n",
        b"TA: 120/80 [missing] [monitor m-1]\n",
    )
    for document in violating:
        result = _lint(document)
        codes = _codes(result)
        assert codes
        assert set(codes) == {DiagnosticCode.LINT_FAILURE}
        assert result.admitted == ()
