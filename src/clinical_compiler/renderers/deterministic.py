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
- Determinism net (Determinism Mechanism #3/#4): a value whose type
  has no canonical rendering (anything beyond ``str``/``int``/
  ``float`` by exact type — a ``dict``/``set`` ``str()`` would leak
  iteration order into the output) fails closed as ``RENDER_ERROR``
  rather than producing nondeterministic bytes.
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

from clinical_compiler.adapters.contract import CONTRACT
from clinical_compiler.core.diagnostics import Diagnostic, DiagnosticCode
from clinical_compiler.core.ir import CanonicalClinicalIR, DocumentIR
from clinical_compiler.core.types import ClinicalValue, Missingness
from clinical_compiler.pipeline_types import StageResult

__all__ = ["render_document"]

_UNASSESSED_GLYPH: str = "unknown"


def _value_glyph(value: ClinicalValue) -> str | None:
    """Canonical glyph for one clinical value, or ``None`` if the
    value type has no canonical rendering.

    ``PRESENT`` values render verbatim under Determinism Mechanism #3:
    ``str(int)`` and the deterministic shortest ``str(float)``
    (locale-free, never locale ``format()``); strings verbatim. Exact
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
    document IR itself never stores values), verifies the entries ↔
    facts bijection (FC-10 safety net), and emits one deterministic
    line per fact plus one explicit ``unknown [not_assessed]`` line
    per contract field with no fact — all sorted by the resolved
    ``(field_id, clinical_fact_id)`` codepoint key.

    Args:
        document: The assembled document IR (refs + presentation
            roles only).
        facts: The admissible canonical fact set the document refers
            to, as the explicit ``CanonicalClinicalIR`` aggregate.

    Returns:
        A ``StageResult`` admitting a single ``bytes`` document on
        success; on any internal inconsistency the admitted tuple is
        empty (never a partial document) and every fault is enumerated
        as a ``RENDER_ERROR`` diagnostic.
    """
    diagnostics: list[Diagnostic] = []
    by_id = {fact.clinical_fact_id: fact for fact in facts.facts}

    referenced: set[str] = set()
    for entry in document.entries:
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
            diagnostics.append(
                Diagnostic(
                    DiagnosticCode.RENDER_ERROR,
                    f"canonical fact {fact.clinical_fact_id!r}"
                    f" ({fact.field_id!r}) carries a value of type"
                    f" {type(fact.value.value).__name__!r} that has no"
                    " canonical rendering",
                )
            )
            continue
        provenance = fact.value.provenance
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
