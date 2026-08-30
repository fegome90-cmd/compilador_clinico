"""Deterministic renderer — canonical document bytes (tasks 3.3 + 3.5).

Fifth stage of the fixed pipeline order: renders the assembled
``DocumentIR`` into the canonical telegraphic document bytes. Pure and
fail-closed — faults surface as diagnostics, never as exceptions
crossing the stage boundary (design M2.1); the function performs no
I/O (atomic file writes are the CLI/pipeline edge's concern, not the
renderer's — the renderer is bytes-out only).

- Renderer I/O (design §Module Map ``DocumentIR → bytes``, CRC-004):
  the ``DocumentIR`` stores refs + presentation roles ONLY, so the
  renderer consumes it TOGETHER with the ``CanonicalClinicalIR`` it
  resolves against — the aggregate is the single value authority and
  the reference point for the dangling-ref safety net. The design's
  shorthand names only the ``DocumentIR``; the aggregate parameter is
  the minimal faithful completion (FLAGGED for owner review).
- Internal-consistency safety net (task 3.3 / CRC-004 renderer side):
  the entries and the admissible facts must form a bijection — no
  dangling ``clinical_fact_ref`` (FC-10: injected entry referencing an
  absent canonical id), no repeated ref, and no fact silently left
  without an entry (design D1: no silent omission). Any violation
  yields ``RENDER_ERROR`` and NO partial document. Only the dangling
  direction is corpus-frozen (FC-10); the duplicate/omission arms are
  the same bijection invariant read fail-closed (FLAGGED).
- FC-11 presentation-role boundary (audit remediation ROUND 2,
  2026-08-30): every entry's ``presentation_role`` is validated
  against the mode's allowed set (:data:`MODE_ALLOWED_PRESENTATION_ROLES`
  — the renderer is the LAST point where the role exists; the linter
  only sees bytes, so validating there is impossible). A role outside
  the set — including any role at all under an unknown mode, whose
  allowed set is empty — is FC-11's prescribed ``LINT_FAILURE`` per
  invalid entry, fail-closed (no partial document); the frozen
  exit-code table maps the diagnostic CODE (not the emitting stage) to
  exit 10. The vocabulary is deliberately DUPLICATED from
  ``passes/document_selection`` (renderers must not import passes —
  D5), parity pinned TEST-side.
- Determinism net (Determinism Mechanism #3/#4): a value whose type
  has no canonical rendering (anything beyond ``str``/``int``/
  ``float`` by exact type — a ``dict``/``set`` ``str()`` would leak
  iteration order into the output) fails closed as ``RENDER_ERROR``
  rather than producing nondeterministic bytes. The same closure
  covers CONTENT that has no canonical single-line rendering (P0-1
  injection closure): a verbatim string value or ``source_ref``
  carrying a line break (LF/CR) would inject a fabricated document
  line or split the provenance segment, so it is refused — verbatim
  values are never rewritten or escaped (input-contract spec), they
  fail closed. Audit remediation (2026-08-30): the closure now covers
  the FULL explicit frozen set of canonical-breaking characters —
  C0 controls U+0000–U+001F, DEL U+007F, C1 controls U+0080–U+009F
  (incl. NEL U+0085), LINE SEPARATOR U+2028, PARAGRAPH SEPARATOR
  U+2029 — applied to BOTH value glyphs and ``source_ref`` strings,
  frozen as literal codepoints (no ``unicodedata`` runtime
  dependency, so the set cannot drift across Python versions).
- Entry order: ``DocumentEntry`` carries no ``field_id``, so the
  renderer resolves each entry's fact and sorts ALL lines by the
  resolved ``(field_id, clinical_fact_id)`` codepoint key itself — it
  never trusts the IR's entry order (pinned by test; the P3-U1
  selection order dependency is not re-implied here).
- Explicit unknown (task 3.3 / PC-1): contract fields with NO fact
  render the frozen unassessed line
  ``{field}: unknown [not_assessed]`` — never dropped, never rewritten
  as assessed absence. The field sweep uses the frozen input-contract
  vocabulary (design D5 explicitly allows renderers →
  adapters.contract); the aggregate cannot supply it (an unassessed
  field has no fact).
- Glyph vocabulary (design Open Question 4 — frozen only via the
  first golden file, task 3.7): fact lines render
  ``{field}: {value} [{missingness}] [{source_kind} {source_ref}]``
  — the missingness marker reuses the corpus-frozen ``[...]`` bracket
  grammar of PC-1, and provenance appears on every fact line (the
  frozen invariant) as the two provenance fields verbatim. Value
  glyphs: ``str(int)`` / deterministic ``str(float)`` / verbatim
  strings for ``PRESENT``; the taxonomy's own words for assessed
  absence (``missing``, ``not_applicable``); the explicit ``unknown``
  word for the unassessed family (UNKNOWN, NOT_ASSESSED) per the
  frozen PC-1 line. Unassessed document-level lines carry no
  provenance segment (no source exists — matching the frozen PC-1
  bytes). FLAGGED for owner review: these minimal faithful choices
  become the vocabulary the Phase-3 golden freeze commits.

Determinism (design Determinism Mechanism): no time/locale/random/
env dependence; UTF-8 with ``\\n`` line endings only, no trailing
whitespace, one final newline; codepoint sort keys; identical inputs
render identical bytes. This stage never imports ``pipeline`` or
``passes`` (D5): its stage contract comes from
:mod:`clinical_compiler.pipeline_types`.
"""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from clinical_compiler.adapters.contract import CONTRACT
from clinical_compiler.core.diagnostics import Diagnostic, DiagnosticCode
from clinical_compiler.core.ir import CanonicalClinicalIR, DocumentIR
from clinical_compiler.core.types import ClinicalValue, Missingness
from clinical_compiler.pipeline_types import StageResult

__all__ = [
    "CANONICAL_BREAKING_CHARACTERS",
    "MODE_ALLOWED_PRESENTATION_ROLES",
    "render_document",
]

_UNASSESSED_GLYPH: str = "unknown"

# FC-11 presentation-role vocabulary (audit remediation ROUND 2,
# 2026-08-30): the mode → allowed-roles mapping, FROZEN as literals.
# Deliberately DUPLICATED from ``passes/document_selection`` (whose
# ``SUPPORTED_MODES``/``TELEGRAPHIC_ENTRY_ROLE`` carry the identical
# values): renderers MUST NOT import passes (design D5) and no frozen
# shared home exists (``pipeline_types.py`` is a frozen Phase-1 unit;
# core is frozen) — the same deliberate-duplication pattern as the
# linter's ``LINTER_CANONICAL_BREAKING_CHARACTERS``. Parity is pinned
# TEST-side (tests may import both modules; production may not).
#
# This is the renderer's FC-11 boundary: the renderer is the LAST point
# where ``presentation_role`` exists — the linter only ever sees BYTES —
# so a role outside the mode's allowed set is validated HERE, before the
# information is lost, as FC-11's prescribed ``LINT_FAILURE`` (the
# frozen exit-code table maps the diagnostic CODE, not the emitting
# stage). A mode absent from this mapping has an EMPTY allowed set:
# nothing can be validated against an unknown vocabulary, so nothing is
# accepted (fail-closed; unknown modes were already blocked at
# selection — defense-in-depth).
MODE_ALLOWED_PRESENTATION_ROLES: Final[Mapping[str, frozenset[str]]] = (
    MappingProxyType(
        {
            "NURSING_RECORD_TELEGRAPHIC": frozenset({"telegraphic_entry"}),
        }
    )
)

# Explicit FROZEN codepoint set of every character capable of breaking the
# canonical single-line representation (audit remediation 2026-08-30): C0
# controls U+0000–U+001F (incl. TAB/LF/CR), DEL U+007F, C1 controls
# U+0080–U+009F (incl. NEL U+0085), LINE SEPARATOR U+2028, PARAGRAPH
# SEPARATOR U+2029. Frozen as literal codepoints — deliberately NOT derived
# from ``unicodedata`` (whose tables vary across Python versions) — so
# identical input renders, or fails closed, identically on every
# interpreter.
_FORBIDDEN_CODEPOINT_ORDS: Final[tuple[int, ...]] = (
    *range(0x0020),  # C0 controls U+0000–U+001F
    0x007F,
    *range(0x0080, 0x00A0),  # C1 controls U+0080–U+009F
    0x2028,
    0x2029,
)
CANONICAL_BREAKING_CHARACTERS: Final[frozenset[str]] = frozenset(
    chr(codepoint) for codepoint in _FORBIDDEN_CODEPOINT_ORDS
)


def _has_line_break(text: str) -> bool:
    """Whether ``text`` carries a line-break character (LF or CR).

    A verbatim string carrying one has no canonical single-line
    rendering: a document line is the atomic unit of the telegraphic
    mode, and rendering such a string verbatim would let it borrow the
    line grammar and fabricate clinical lines (P0-1 injection closure).
    Values are never rewritten or escaped — they fail closed.
    """
    return "\n" in text or "\r" in text


def _canonical_breaking_character(text: str) -> str | None:
    """First character of ``text`` in the frozen canonical-breaking
    set, or ``None``.

    Complements :func:`_has_line_break`: LF/CR keep their dedicated
    "line break" fault message, while every other character of the
    frozen set (TAB, DEL, C1 controls such as NEL U+0085, U+2028/
    U+2029, ...) fails closed under a deterministic U+XXXX message.
    Membership is an exact codepoint test against
    :data:`CANONICAL_BREAKING_CHARACTERS` — no category approximation,
    so printable unicode (accents, ``°``, ``—``) is never over-blocked.
    """
    for character in text:
        if character in CANONICAL_BREAKING_CHARACTERS:
            return character
    return None


def _value_glyph(value: ClinicalValue) -> str | None:
    """Canonical glyph for one clinical value, or ``None`` if the
    value type has no canonical rendering.

    ``PRESENT`` values render verbatim under Determinism Mechanism #3:
    ``str(int)`` and the deterministic shortest ``str(float)``
    (locale-free, never locale ``format()``); strings verbatim — but a
    string carrying a line break (LF or CR) has NO canonical rendering:
    it would inject a second document line borrowing the grammar and
    provenance of another fact, so it fails closed (P0-1). Exact
    runtime types only — anything else (``bool`` included, and any
    container whose ``str()`` would leak iteration order) has no
    canonical rendering. The absence families render the taxonomy's
    own words: ``missing`` / ``not_applicable`` for assessed absence,
    the explicit ``unknown`` for the unassessed family — never
    conflated (clinical-fact-model Missingness Non-Conflation).
    """
    if value.missingness is Missingness.PRESENT:
        raw = value.value
        if type(raw) is str or type(raw) is int or type(raw) is float:
            if type(raw) is str and _has_line_break(raw):
                return None
            if type(raw) is str and _canonical_breaking_character(raw):
                return None
            return str(raw)
        return None
    if value.missingness is Missingness.MISSING:
        return "missing"
    if value.missingness is Missingness.NOT_APPLICABLE:
        return "not_applicable"
    return _UNASSESSED_GLYPH


def render_document(
    document: DocumentIR, facts: CanonicalClinicalIR
) -> StageResult[bytes]:
    """Render the ``DocumentIR`` into canonical document bytes.

    Resolves every entry's ``clinical_fact_ref`` against the
    admissible canonical fact set (the single value authority — the
    document IR itself never stores values), validates every entry's
    ``presentation_role`` against the document mode's allowed set
    (FC-11 — the last point where the role exists), verifies the
    entries ↔ facts bijection (FC-10 safety net), and emits one
    deterministic line per fact plus one explicit
    ``unknown [not_assessed]`` line per contract field with no fact —
    all sorted by the resolved ``(field_id, clinical_fact_id)``
    codepoint key.

    Args:
        document: The assembled document IR (refs + presentation
            roles only).
        facts: The admissible canonical fact set the document refers
            to, as the explicit ``CanonicalClinicalIR`` aggregate.

    Returns:
        A ``StageResult`` admitting a single ``bytes`` document on
        success; on any internal inconsistency the admitted tuple is
        empty (never a partial document), faults are enumerated as
        ``RENDER_ERROR`` diagnostics, and a ``presentation_role``
        outside the mode's allowed set as a ``LINT_FAILURE`` per
        invalid entry (FC-11).
    """
    diagnostics: list[Diagnostic] = []
    by_id = {fact.clinical_fact_id: fact for fact in facts.facts}

    # FC-11 presentation-role validation (audit remediation ROUND 2,
    # 2026-08-30): the renderer is the LAST point where an entry's
    # ``presentation_role`` exists — downstream only the BYTES travel —
    # so each entry's role is validated against the mode's allowed set
    # HERE, before the information is lost. A role outside the set is
    # FC-11's prescribed ``LINT_FAILURE`` per invalid entry (one per
    # entry, in entry order); an unknown mode carries an EMPTY allowed
    # set, so every entry fails closed. Emission stays fail-closed: any
    # diagnostic yields no document.
    allowed_roles = MODE_ALLOWED_PRESENTATION_ROLES.get(
        document.document_mode, frozenset()
    )

    referenced: set[str] = set()
    for entry in document.entries:
        if entry.presentation_role not in allowed_roles:
            diagnostics.append(
                Diagnostic(
                    DiagnosticCode.LINT_FAILURE,
                    f"document entry for canonical fact"
                    f" {entry.clinical_fact_ref!r} carries"
                    f" presentation_role {entry.presentation_role!r}"
                    " outside the allowed set for document mode"
                    f" {document.document_mode!r} (FC-11, audit"
                    " remediation 2026-08-30)",
                )
            )
        ref = entry.clinical_fact_ref
        if ref not in by_id:
            diagnostics.append(
                Diagnostic(
                    DiagnosticCode.RENDER_ERROR,
                    f"document entry references canonical fact {ref!r}"
                    " absent from the admissible fact set",
                )
            )
        elif ref in referenced:
            diagnostics.append(
                Diagnostic(
                    DiagnosticCode.RENDER_ERROR,
                    f"document entry references canonical fact {ref!r}"
                    " more than once — one entry per fact",
                )
            )
        else:
            referenced.add(ref)

    for fact in facts.facts:
        if fact.clinical_fact_id not in referenced:
            diagnostics.append(
                Diagnostic(
                    DiagnosticCode.RENDER_ERROR,
                    f"canonical fact {fact.clinical_fact_id!r}"
                    f" ({fact.field_id!r}) has no document entry —"
                    " a fact must never be silently omitted",
                )
            )

    items: list[tuple[str, str, str]] = []
    for fact in facts.facts:
        if fact.clinical_fact_id not in referenced:
            continue
        glyph = _value_glyph(fact.value)
        if glyph is None:
            value = fact.value.value
            if type(value) is str:
                breaker = (
                    None
                    if _has_line_break(value)
                    else _canonical_breaking_character(value)
                )
                if breaker is None:
                    detail = (
                        "contains a line break — no canonical single-line"
                        " rendering exists for a verbatim value (P0-1)"
                    )
                else:
                    detail = (
                        "contains canonical-breaking character"
                        f" U+{ord(breaker):04X} — no canonical single-line"
                        " rendering exists for a verbatim value"
                    )
            else:
                detail = "has no canonical rendering"
            diagnostics.append(
                Diagnostic(
                    DiagnosticCode.RENDER_ERROR,
                    f"canonical fact {fact.clinical_fact_id!r}"
                    f" ({fact.field_id!r}) carries a value of type"
                    f" {type(value).__name__!r} that {detail}",
                )
            )
            continue
        provenance = fact.value.provenance
        if _has_line_break(provenance.source_ref):
            diagnostics.append(
                Diagnostic(
                    DiagnosticCode.RENDER_ERROR,
                    f"canonical fact {fact.clinical_fact_id!r}"
                    f" ({fact.field_id!r}) carries a source_ref"
                    " containing a line break — the provenance segment"
                    " has no canonical single-line rendering (P0-1)",
                )
            )
            continue
        ref_breaker = _canonical_breaking_character(provenance.source_ref)
        if ref_breaker is not None:
            diagnostics.append(
                Diagnostic(
                    DiagnosticCode.RENDER_ERROR,
                    f"canonical fact {fact.clinical_fact_id!r}"
                    f" ({fact.field_id!r}) carries a source_ref"
                    " containing canonical-breaking character"
                    f" U+{ord(ref_breaker):04X} — the provenance segment"
                    " has no canonical single-line rendering",
                )
            )
            continue
        line = (
            f"{fact.field_id}: {glyph} [{fact.value.missingness.value}]"
            f" [{provenance.source_kind} {provenance.source_ref}]"
        )
        items.append((fact.field_id, fact.clinical_fact_id, line))

    if diagnostics:
        return StageResult(admitted=(), diagnostics=tuple(diagnostics))

    covered_fields = {field_id for field_id, _, _ in items}
    for field_id in sorted(CONTRACT.keys()):
        if field_id in covered_fields:
            continue
        unassessed = (
            f"{field_id}: {_UNASSESSED_GLYPH}"
            f" [{Missingness.NOT_ASSESSED.value}]"
        )
        items.append((field_id, "", unassessed))

    items.sort(key=lambda item: (item[0], item[1]))
    text = "".join(f"{line}\n" for _, _, line in items)
    return StageResult(admitted=(text.encode("utf-8"),), diagnostics=())
