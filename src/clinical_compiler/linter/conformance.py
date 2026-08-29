"""Conformance linter — rendered bytes vs mode rules (tasks 3.4 + 3.5).

Sixth stage of the fixed pipeline order: validates the rendered
document BYTES against the ``NURSING_RECORD_TELEGRAPHIC`` mode's
conformance rules — the final gate before a document is accepted as
output. Pure and fail-closed — violations surface as diagnostics,
never as exceptions crossing the stage boundary (design M2.1); the
linter performs no I/O and never re-renders anything.

- Linter I/O (design §Module Map ``bytes vs mode rules`` and the
  sequence diagram ``lint bytes against mode rules``): consumes the
  rendered ``bytes`` plus the ``document_mode`` whose rules apply, and
  returns a ``StageResult`` admitting the SAME bytes only when they
  are lint-clean (determinism-rendering spec: only a lint-clean
  document is accepted as final); otherwise ``admitted`` is empty and
  every violated rule is enumerated as a ``LINT_FAILURE`` diagnostic
  (design D1).
- Defense-in-depth positioning (CRC-004 / unit P3-U2 flag): the
  linter validates BYTES, not IR structures — it is the net AFTER
  render. The renderer renders verbatim string values without policing
  their content (an embedded newline or carriage return in a value or
  ``source_ref`` produces rule-violating bytes); catching those bytes
  is THIS stage's ownership. The rule set is exactly the frozen mode
  rules — no rule the renderer cannot produce, no weakening of the
  frozen invariants.
- Frozen rule set (task 3.4 + design Determinism Mechanism #3 +
  P3-U2's frozen glyph vocabulary, to be committed by the first golden
  file at task 3.7):
  1. Byte invariants — UTF-8 decodable; LF-only (no ``CR`` byte);
     no trailing whitespace on any line; exactly one final newline.
  2. Line grammar — every line matches
     ``{field}: {glyph} [{missingness}] [{source_kind} {source_ref}]``
     with the provenance segment optional (the unassessed
     document-level line ``{field}: unknown [not_assessed]`` carries
     no source). Lines parse right-anchored, so verbatim value glyphs
     may themselves contain ``[...]`` segments and ``: ``.
  3. Vocabulary tokens — ``field`` within the frozen input contract
     (design D5 explicitly allows linter → adapters.contract);
     ``missingness`` within the ``Missingness`` taxonomy;
     ``source_kind`` within the frozen feed vocabulary.
  4. Glyph/missingness consistency — ``missing`` / ``not_applicable``
     render the taxonomy's own words, the unassessed family renders
     the explicit ``unknown``; ``PRESENT`` glyphs are unrestricted
     verbatim values (an empty string or a value spelling ``missing``
     is contract-admissible and therefore lint-clean).
- FC-11 (task 3.5, linter half): the corpus class is "rendered output
  violates a mode conformance rule", exercised via injected violating
  bytes — one dedicated fixture per rule family (mutation-sensitive
  net: removing or weakening any rule fails at least one test).
- Unknown document mode: fail-closed with this stage's only mapped
  code, ``LINT_FAILURE`` — without known rules nothing can be
  validated, so nothing is accepted (unknown modes were already
  blocked at selection; this is defense-in-depth, FLAGGED).
- Mode vocabulary placement (P3-U1 flag, carried): the mode constants
  cannot be imported from ``passes/document_selection.py`` (design D5
  — linter never imports passes) and no frozen shared home exists
  (``pipeline_types.py`` is a frozen Phase-1 unit; core is frozen), so
  the constant is declared here, value-identical. FLAGGED for owner
  review.
- The glyph/missingness table is deliberately DUPLICATED from the
  renderer's frozen vocabulary rather than imported: the linter must
  stay an independent net — importing renderer internals would let a
  renderer bug validate itself. FLAGGED (duplication is the price of
  independence).

Determinism (design Determinism Mechanism): no time/locale/random/
env dependence; checks run in a fixed order (mode, byte invariants,
then lines ascending — within a line: trailing whitespace, grammar,
vocabulary) so identical bytes yield byte-identical diagnostics.
This stage never imports ``pipeline`` or ``passes`` (D5); its stage
contract comes from :mod:`clinical_compiler.pipeline_types`.
"""

import re
from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from clinical_compiler.adapters.contract import ALLOWED_SOURCE_KINDS, CONTRACT
from clinical_compiler.core.diagnostics import Diagnostic, DiagnosticCode
from clinical_compiler.core.types import Missingness
from clinical_compiler.pipeline_types import StageResult

__all__ = ["lint_conformance"]

_NURSING_RECORD_TELEGRAPHIC: Final[str] = "NURSING_RECORD_TELEGRAPHIC"
_SUPPORTED_MODES: Final[tuple[str, ...]] = (_NURSING_RECORD_TELEGRAPHIC,)

_UNASSESSED_GLYPH: Final[str] = "unknown"

# Glyph/missingness consistency table (the renderer's frozen vocabulary,
# duplicated on purpose — see module docstring). PRESENT is absent: its
# glyphs are unrestricted verbatim values.
_FIXED_GLYPHS: Final[Mapping[Missingness, str]] = MappingProxyType(
    {
        Missingness.MISSING: "missing",
        Missingness.NOT_APPLICABLE: "not_applicable",
        Missingness.UNKNOWN: _UNASSESSED_GLYPH,
        Missingness.NOT_ASSESSED: _UNASSESSED_GLYPH,
    }
)
_MISSINGNESS_TOKENS: Final[frozenset[str]] = frozenset(
    token.value for token in Missingness
)
_CONTRACT_FIELDS: Final[frozenset[str]] = frozenset(CONTRACT.keys())

# Telegraphic line grammar, matched right-anchored: the LAST bracket
# groups are the missingness and provenance segments, so glyphs may
# contain brackets/colons verbatim.
_LINE_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<field>[^:\s]+): (?P<glyph>.*)"
    r" \[(?P<missingness>[a-z_]+)\]"
    r"(?: \[(?P<source_kind>[^\s\]]+) (?P<source_ref>.*)\])?$"
)


def _check_line(line: str, number: int) -> list[Diagnostic]:
    """Lint one decoded line, enumerating every rule it violates.

    Checks run in a fixed order — trailing whitespace, then the line
    grammar and its vocabulary/consistency rules — so identical lines
    yield identical diagnostics in identical order.
    """
    diagnostics: list[Diagnostic] = []

    if line != line.rstrip():
        diagnostics.append(
            Diagnostic(
                DiagnosticCode.LINT_FAILURE,
                f"line {number}: trailing whitespace is forbidden",
            )
        )

    match = _LINE_RE.match(line)
    if match is None:
        diagnostics.append(
            Diagnostic(
                DiagnosticCode.LINT_FAILURE,
                f"line {number}: does not match the telegraphic"
                " line grammar",
            )
        )
        return diagnostics

    field: str = match.group("field")
    if field not in _CONTRACT_FIELDS:
        diagnostics.append(
            Diagnostic(
                DiagnosticCode.LINT_FAILURE,
                f"line {number}: field {field!r} is outside the frozen"
                " contract vocabulary",
            )
        )

    token: str = match.group("missingness")
    if token not in _MISSINGNESS_TOKENS:
        diagnostics.append(
            Diagnostic(
                DiagnosticCode.LINT_FAILURE,
                f"line {number}: missingness token {token!r} is outside"
                " the frozen taxonomy",
            )
        )
    else:
        glyph: str = match.group("glyph")
        expected = _FIXED_GLYPHS.get(Missingness(token))
        if expected is not None and glyph != expected:
            diagnostics.append(
                Diagnostic(
                    DiagnosticCode.LINT_FAILURE,
                    f"line {number}: glyph {glyph!r} does not match the"
                    f" required glyph {expected!r} for missingness"
                    f" {token!r}",
                )
            )

    source_kind: str | None = match.group("source_kind")
    if source_kind is not None and source_kind not in ALLOWED_SOURCE_KINDS:
        diagnostics.append(
            Diagnostic(
                DiagnosticCode.LINT_FAILURE,
                f"line {number}: source_kind {source_kind!r} is outside"
                " the frozen source vocabulary",
            )
        )

    return diagnostics


def lint_conformance(
    document: bytes, document_mode: str
) -> StageResult[bytes]:
    """Validate rendered document bytes against the mode's rules.

    Runs the frozen rule set over the bytes — byte invariants first
    (exactly one final newline, LF-only, UTF-8 decodable), then every
    line in order (trailing whitespace, line grammar, vocabulary
    tokens, glyph/missingness consistency) — enumerating one
    ``LINT_FAILURE`` per violated rule (design D1).

    Args:
        document: The rendered document bytes to validate.
        document_mode: The document mode whose conformance rules
            apply; R1 supports only ``NURSING_RECORD_TELEGRAPHIC``.

    Returns:
        A ``StageResult`` admitting the same bytes when lint-clean
        (only lint-clean output is accepted as final); otherwise the
        admitted tuple is empty and every violation is enumerated as a
        ``LINT_FAILURE`` diagnostic. Never raises (design M2.1).
    """
    if document_mode not in _SUPPORTED_MODES:
        return StageResult(
            admitted=(),
            diagnostics=(
                Diagnostic(
                    DiagnosticCode.LINT_FAILURE,
                    f"unknown document mode {document_mode!r} — no"
                    " conformance rules are available to validate"
                    " against",
                ),
            ),
        )

    diagnostics: list[Diagnostic] = []

    if not document.endswith(b"\n") or document.endswith(b"\n\n"):
        diagnostics.append(
            Diagnostic(
                DiagnosticCode.LINT_FAILURE,
                "document does not end with exactly one final newline",
            )
        )
    if b"\r" in document:
        diagnostics.append(
            Diagnostic(
                DiagnosticCode.LINT_FAILURE,
                "document contains a carriage return — mode output is"
                " LF-only",
            )
        )

    try:
        text = document.decode("utf-8")
    except UnicodeDecodeError:
        diagnostics.append(
            Diagnostic(
                DiagnosticCode.LINT_FAILURE,
                "document bytes are not valid UTF-8",
            )
        )
        return StageResult(admitted=(), diagnostics=tuple(diagnostics))

    lines = text.split("\n")
    if document.endswith(b"\n"):
        lines = lines[:-1]
    for number, line in enumerate(lines, start=1):
        diagnostics.extend(_check_line(line, number))

    if diagnostics:
        return StageResult(admitted=(), diagnostics=tuple(diagnostics))
    return StageResult(admitted=(document,), diagnostics=())
