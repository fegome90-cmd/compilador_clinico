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
from clinical_compiler.linter.conformance import (
    LINTER_CANONICAL_BREAKING_CHARACTERS,
    lint_conformance,
)
from clinical_compiler.pipeline_types import StageResult
from clinical_compiler.renderers.deterministic import (
    CANONICAL_BREAKING_CHARACTERS as RENDERER_CANONICAL_BREAKING_CHARACTERS,
)
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
            DocumentEntry(
                clinical_fact_ref=fact.clinical_fact_id, presentation_role=ROLE
            )
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
    """One lint-clean document per glyph family — present int/unicode
    string, present float and assessed absence (missing), the unassessed
    fact families (not_assessed, not_applicable) — all lint clean. The
    hardened mode admits at most ONE line per field (P0-1), so families
    are grouped into documents of distinct fields; the unassessed
    document-level sweep has its own pin
    (:func:`test_all_unassessed_document_lints_clean`)."""
    documents = (
        _rendered(
            (
                _fc_fact("c-fc-1"),
                _canonical_fact(
                    clinical_fact_id="c-ta-1",
                    value=_clinical_value(value="120/80 mmHg — reposo"),
                ),
            )
        ),
        _rendered(
            (
                _canonical_fact(
                    clinical_fact_id="c-fc-2",
                    field_id="FC",
                    value=_clinical_value(
                        value=72.5,
                        provenance=Provenance(source_kind="monitor", source_ref="m-2"),
                    ),
                ),
                _canonical_fact(
                    clinical_fact_id="c-ta-2",
                    value=_clinical_value(
                        value=None,
                        missingness=Missingness.MISSING,
                        provenance=Provenance(source_kind="lab", source_ref="l-3"),
                    ),
                ),
            )
        ),
        _rendered(
            (
                _canonical_fact(
                    clinical_fact_id="c-fc-3",
                    field_id="FC",
                    value=_clinical_value(
                        value=None, missingness=Missingness.NOT_ASSESSED
                    ),
                ),
                _canonical_fact(
                    clinical_fact_id="c-ta-3",
                    value=_clinical_value(
                        value=None, missingness=Missingness.NOT_APPLICABLE
                    ),
                ),
            )
        ),
    )
    for document in documents:
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
    document = b"FC: 72 [present] [monitor m-1]\n\nTA: 120/80 [present] [monitor m-1]\n"
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


# --- FC-11 via the byte-level net: the P0-1 injection seams ---------------------


def test_injected_multiline_value_bytes_yield_lint_failure() -> None:
    """FC-11 byte-level net over the P0-1 seam: the renderer refuses a
    line-break-carrying value outright (RENDER_ERROR — renderer unit),
    so these are the bytes a broken renderer would have produced; the
    linter must still reject every injected fragment — the
    provenance-less ``TA: 72`` line and the field-less ``bpm ...`` line
    are each enumerated, never accepted."""
    document = (
        b"FC: unknown [not_assessed]\nTA: 72\nbpm [present] [clinical_note n-1]\n"
    )
    result = _lint(document)
    assert _codes(result) == (
        DiagnosticCode.LINT_FAILURE,
        DiagnosticCode.LINT_FAILURE,
    )
    assert result.admitted == ()


def test_injected_source_ref_with_embedded_newline_yields_lint_failure() -> None:
    """Same byte-level net over the provenance seam: line-split
    provenance fragments are enumerated as LINT_FAILURE (the renderer
    itself now rejects such refs at render time, P0-1)."""
    document = b"FC: unknown [not_assessed]\nTA: 120/80 [present] [monitor m-\n1]\n"
    result = _lint(document)
    assert DiagnosticCode.LINT_FAILURE in _codes(result)
    assert result.admitted == ()


# --- Hardened cross-line rules (P0-1): one line per field, provenance required --


def test_duplicate_field_lines_yield_lint_failure() -> None:
    """Hardened cross-line rule (P0-1): each field token may appear at
    most once per document — a second FC line is a conformance
    violation even when every line individually matches the grammar
    (the renderer can never produce this: normalization yields at most
    one canonical fact per field)."""
    document = b"FC: 72 [present] [monitor m-1]\nFC: 80 [present] [monitor m-2]\n"
    result = _lint(document)
    assert _codes(result) == (DiagnosticCode.LINT_FAILURE,)
    assert "more than once" in result.diagnostics[0].message
    assert result.admitted == ()


def test_repeated_field_lines_are_flagged_per_repeat_in_line_order() -> None:
    """D1 enumeration of the cross-line rule: three FC lines flag the
    second AND third repeats, deterministically in line order."""
    document = (
        b"FC: 72 [present] [monitor m-1]\n"
        b"FC: 80 [present] [monitor m-2]\n"
        b"FC: 90 [present] [monitor m-3]\n"
    )
    messages = _messages(_lint(document))
    assert len(messages) == 2
    assert "line 2" in messages[0] and "more than once" in messages[0]
    assert "line 3" in messages[1] and "more than once" in messages[1]


def test_present_line_without_provenance_yields_lint_failure() -> None:
    """Hardened rule (P0-1): an assessed line REQUIRES the provenance
    segment — a provenance-less PRESENT line (the injection residue the
    diagnosis exhibited: a borrowed-second-line value splitting into
    ``TA: 72 [present]``) can never pass the linter."""
    result = _lint(b"TA: 72 [present]\n")
    assert _codes(result) == (DiagnosticCode.LINT_FAILURE,)
    assert "provenance" in result.diagnostics[0].message
    assert result.admitted == ()


@pytest.mark.parametrize(
    "line",
    [
        b"TA: missing [missing]\n",
        b"TA: not_applicable [not_applicable]\n",
        b"TA: unknown [unknown]\n",
    ],
)
def test_assessed_lines_without_provenance_fail(line: bytes) -> None:
    """Every non-``not_assessed`` token without a provenance segment is
    a conformance violation (missingness-family pins of the rule)."""
    result = _lint(line)
    assert _codes(result) == (DiagnosticCode.LINT_FAILURE,)
    assert "provenance" in result.diagnostics[0].message
    assert result.admitted == ()


# --- Audit remediation (2026-08-30): empty provenance source_ref ----------------


@pytest.mark.parametrize(
    "line",
    [
        b"TA: 72 [present] [monitor ]\n",
        b"TA: missing [missing] [lab ]\n",
        b"TA: not_applicable [not_applicable] [monitor ]\n",
        b"FC: 72 [present] [monitor   ]\n",
        # NBSP U+00A0 (UTF-8 0xC2 0xA0) as the whole ref: whitespace-only
        # per str.strip(), NOT a member of the canonical-breaking set —
        # so exactly the empty-ref rule fires (canonical-breaking forms
        # of whitespace-only refs are the parity rule's cases, e.g. TAB
        # in a ref).
        b"TA: 120/80 [present] [clinical_note \xc2\xa0]\n",
    ],
)
def test_empty_source_ref_yields_lint_failure(line: bytes) -> None:
    """Audit defect (2026-08-30): a clinical line carrying a
    present/missing/not_applicable marker MUST carry NON-EMPTY
    provenance — ``[monitor ]`` (empty ref) or a whitespace-only ref is
    provenance in name only, and is rejected as ``LINT_FAILURE``.

    Defense-in-depth reachability, stated precisely (audit round 2
    wording correction): the frozen contract rejects only the EMPTY
    string ref (``""`` → INPUT_CONTRACT_ERROR, 7d08951); a
    WHITESPACE-ONLY ref (``" "``) is contract-ADMISSIBLE and flows
    through the real pipeline today — this byte-level rule is the only
    net that rejects it. These bytes are hand-injected past the render
    stage to exercise the net directly."""
    result = _lint(line)
    assert _codes(result) == (DiagnosticCode.LINT_FAILURE,)
    assert "source_ref" in result.diagnostics[0].message
    assert "empty" in result.diagnostics[0].message
    assert result.admitted == ()


def test_empty_source_ref_violations_enumerate_in_line_order_deterministically() -> (
    None
):
    """D1 + determinism: two empty-ref lines enumerate exactly one
    LINT_FAILURE each, in line order, and identical bytes yield
    byte-identical diagnostics."""
    document = (
        b"FC: 72 [present] [monitor ]\n"
        b"TA: 120/80 [present] [clinical_note ]\n"
    )
    first = _lint(document)
    second = _lint(document)
    assert first.diagnostics == second.diagnostics
    messages = _messages(first)
    assert len(messages) == 2
    assert "line 1" in messages[0] and "empty" in messages[0]
    assert "line 2" in messages[1] and "empty" in messages[1]
    assert first.admitted == ()


def test_not_assessed_lines_remain_the_only_provenance_less_form() -> None:
    """The unassessed line ``{field}: unknown [not_assessed]`` carries NO
    provenance segment at all and stays lint-clean — the empty-ref rule
    must not over-block the one legitimate provenance-less form."""
    result = _lint(b"TA: unknown [not_assessed]\n")
    assert result.diagnostics == ()
    assert result.admitted == (b"TA: unknown [not_assessed]\n",)


# --- Audit remediation ROUND 2 (2026-08-30): canonical-character parity ---------

# The linter's own frozen net over the canonical-breaking alphabet
# (BLOCKER 1, independent audit round 2): bytes the renderer refuses to
# produce must never lint clean. The set is deliberately DUPLICATED into
# the linter — importing the renderer's constant would let a renderer bug
# validate itself — so these tests pin the duplication by importing BOTH
# constants (tests may; production may not) and asserting parity.


def test_linter_canonical_breaking_charset_is_explicit_frozen_and_complete() -> None:
    """The linter's canonical-breaking set is an EXPLICIT FROZEN
    codepoint set — C0 controls U+0000–U+001F, DEL U+007F, C1 controls
    U+0080–U+009F (incl. NEL U+0085), LINE SEPARATOR U+2028, PARAGRAPH
    SEPARATOR U+2029 — 67 characters, frozen as a module constant with
    no ``unicodedata`` dependency. Shrinking or growing the set fails
    here (mutation-sensitive completeness pin)."""
    assert isinstance(LINTER_CANONICAL_BREAKING_CHARACTERS, frozenset)
    expected_ords = (
        tuple(range(0x0020))  # C0 U+0000–U+001F
        + (0x007F,)
        + tuple(range(0x0080, 0x00A0))  # C1 U+0080–U+009F
        + (0x2028, 0x2029)
    )
    assert len(LINTER_CANONICAL_BREAKING_CHARACTERS) == len(expected_ords) == 67
    for codepoint in expected_ords:
        assert chr(codepoint) in LINTER_CANONICAL_BREAKING_CHARACTERS


def test_linter_charset_parity_with_the_renderer_frozen_set() -> None:
    """Cross-pin (TEST-side import — production nets stay independent):
    the linter's duplicated set is VALUE-IDENTICAL to the renderer's
    frozen ``CANONICAL_BREAKING_CHARACTERS`` — every character the
    renderer refuses to render, the linter refuses to accept, and vice
    versa. Drift in either constant fails here."""
    assert LINTER_CANONICAL_BREAKING_CHARACTERS == (
        RENDERER_CANONICAL_BREAKING_CHARACTERS
    )


def _injected_value_bytes(character: str) -> bytes:
    """A grammar-valid FC line with ``character`` inside the value glyph.

    The renderer declares such bytes impossible (the same character in a
    verbatim value is RENDER_ERROR), so these are hand-injected past the
    render stage to exercise the byte-level net directly."""
    return f"FC: 72{character}bpm [present] [monitor m-1]\n".encode()


@pytest.mark.parametrize(
    "character",
    sorted(LINTER_CANONICAL_BREAKING_CHARACTERS),
    ids=lambda character: f"U+{ord(character):04X}",
)
def test_every_canonical_breaking_character_in_bytes_yields_lint_failure(
    character: str,
) -> None:
    """Completeness pin over the WHOLE frozen set: rendered bytes
    carrying the character (in the value glyph position) are a
    ``LINT_FAILURE`` and are never accepted — for U+000A the injected
    line splits and the existing grammar/one-line-per-field rules block
    it, for U+000D the global LF-only invariant blocks it, and for every
    other character the dedicated parity rule does. Removing the check
    or shrinking the set fails at least one case."""
    result = _lint(_injected_value_bytes(character))
    assert _codes(result)
    assert set(_codes(result)) == {DiagnosticCode.LINT_FAILURE}
    assert result.admitted == ()


@pytest.mark.parametrize(
    "character",
    sorted(LINTER_CANONICAL_BREAKING_CHARACTERS - {"\n", "\r"}),
    ids=lambda character: f"U+{ord(character):04X}",
)
def test_canonical_breaking_character_is_named_with_codepoint_in_line_order(
    character: str,
) -> None:
    """Every character the parity rule itself polices (U+000A cannot
    appear inside a decoded line — it IS the line separator — and
    U+000D keeps its dedicated global LF-only message, preserving the
    existing enumeration order) yields exactly ONE ``LINT_FAILURE`` on
    line 1 naming the exact ``U+XXXX`` — deterministic message, line
    order."""
    result = _lint(_injected_value_bytes(character))
    messages = _messages(result)
    assert messages == [
        (
            f"line 1: contains canonical-breaking character"
            f" U+{ord(character):04X} — no canonical single-line"
            " rendering exists for a document line (canonical-char"
            " parity, audit remediation 2026-08-30)"
        )
    ]
    assert result.admitted == ()


def test_tab_in_value_glyph_yields_lint_failure() -> None:
    """Auditor example: TAB inside a value glyph — mid-line, so the
    trailing-whitespace rule never sees it — is a ``LINT_FAILURE``."""
    result = _lint(b"FC: 72\tbpm [present] [monitor m-1]\n")
    assert _codes(result) == (DiagnosticCode.LINT_FAILURE,)
    assert "U+0009" in result.diagnostics[0].message
    assert result.admitted == ()


def test_tab_in_source_ref_yields_lint_failure() -> None:
    """Auditor example: TAB inside the provenance ``source_ref`` — the
    grammar's ``.*`` ref group accepts it — is a ``LINT_FAILURE``."""
    result = _lint(b"FC: 72 [present] [monitor m\t1]\n")
    assert _codes(result) == (DiagnosticCode.LINT_FAILURE,)
    assert "U+0009" in result.diagnostics[0].message
    assert result.admitted == ()


def test_c1_control_in_source_ref_yields_lint_failure() -> None:
    """Auditor example: NEL U+0085 (a C1 control, an invisible line
    break in most viewers) inside the ``source_ref`` is a
    ``LINT_FAILURE``. The document carries U+0085 UTF-8-encoded
    (``0xC2 0x85``) — a lone ``0x85`` byte would trip the decodability
    invariant instead."""
    result = _lint("FC: 72 [present] [monitor m\x851]\n".encode())
    assert _codes(result) == (DiagnosticCode.LINT_FAILURE,)
    assert "U+0085" in result.diagnostics[0].message
    assert result.admitted == ()


def test_line_separator_in_value_yields_lint_failure() -> None:
    """Auditor example: LINE SEPARATOR U+2028 inside a value glyph —
    fabricates a second VISUAL line inside one physical line — is a
    ``LINT_FAILURE``."""
    result = _lint("FC: 72\u2028bpm [present] [monitor m-1]\n".encode("utf-8"))
    assert _codes(result) == (DiagnosticCode.LINT_FAILURE,)
    assert "U+2028" in result.diagnostics[0].message
    assert result.admitted == ()


def test_canonical_breaking_violations_are_deterministic() -> None:
    """Identical canonical-breaking bytes lint to byte-identical
    diagnostics (determinism pin for the new rule)."""
    document = b"FC: 72\tbpm [present] [monitor m-1]\nTA: 120\x0b/80 [present] [clinical_note n-1]\n"
    first = _lint(document)
    second = _lint(document)
    assert first.diagnostics == second.diagnostics
    messages = _messages(first)
    assert len(messages) == 2
    assert "line 1" in messages[0] and "U+0009" in messages[0]
    assert "line 2" in messages[1] and "U+000B" in messages[1]
    assert first.admitted == ()


@pytest.mark.parametrize(
    "value",
    ["120/80 mmHg — reposo", "36.6 °C", "café ñ", "72 bpm (stable)", "🩺 ok"],
)
def test_printable_unicode_values_still_lint_clean(value: str) -> None:
    """Boundary (no over-blocking): printable ASCII and typical clinical
    unicode — accents, degree sign, em dash, emoji-class characters —
    lint clean; the parity set is an exact codepoint set, never a
    category approximation."""
    fact = _canonical_fact(value=_clinical_value(value=value))
    document = _rendered((fact,))
    assert _lint(document).diagnostics == ()


@pytest.mark.parametrize("ref", ["n-1", "nota-ñ-1", "lab/2026/08/29", "m-9 (rev 2)"])
def test_printable_source_refs_still_lint_clean(ref: str) -> None:
    """Boundary (no over-blocking): printable ``source_ref`` strings
    carry their provenance segment and lint clean."""
    fact = _canonical_fact(
        value=_clinical_value(
            provenance=Provenance(source_kind="monitor", source_ref=ref)
        ),
    )
    document = _rendered((fact,))
    assert _lint(document).diagnostics == ()


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
    document = b"TA: 120/80 [maybe] [monitor m-1] \r\nFC: 72 [present] [monitor m-2]"
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
