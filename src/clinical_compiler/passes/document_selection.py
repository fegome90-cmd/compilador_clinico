"""Document selection stage — DocumentIR assembly from admissible facts.

Fourth stage of the fixed pipeline order (pipeline-passes spec):
assembles the ``DocumentIR`` for the requested document mode from the
admissible canonical fact set. Pure and fail-closed — faults surface as
diagnostics, never as exceptions crossing the stage boundary (design
M2.1).

- Input representation (CRC-003 / design D10): the admissible set MUST
  arrive as the explicit ``CanonicalClinicalIR`` aggregate — the design
  forbids an implicit bare tuple crossing the admissibility →
  document-selection boundary. The aggregate's construction-time
  invariants (unique ids, validated lineage, canonical
  ``(field_id, clinical_fact_id)`` ordering) therefore already hold
  for everything this stage consumes.
- Single authority / CRC-004 (selection side): entries reference
  canonical facts by ``clinical_fact_id`` and carry a presentation
  role — NEVER a clinical value. Because every ``clinical_fact_ref``
  is built from a fact present in the consumed aggregate, a dangling
  reference is IMPOSSIBLE BY CONSTRUCTION at this stage; the
  renderer's ``RENDER_ERROR`` over dangling refs (FC-10) is
  defense-in-depth over internal corruption or injection, never an
  outcome of this stage (owner adjudication 2026-08-28 — the defect is
  NOT also classified as ``DOCUMENT_SELECTION_ERROR`` because this
  stage cannot produce it).
- Entry ordering (design Determinism Mechanism #1): one entry per
  fact, emitted in the aggregate's canonical ``(field_id,
  clinical_fact_id)`` codepoint order — the same fact set always
  selects to the same entry sequence, regardless of the insertion
  order the facts arrived in.
- Mode vocabulary (R1): ``NURSING_RECORD_TELEGRAPHIC`` is the only
  supported mode. The CLI's exit-2 usage gate for an unknown
  ``--mode`` is a Phase-4 composition concern; at stage level an
  unknown mode is a selection request that cannot produce a valid
  document, so it fails closed with this stage's only mapped code,
  ``DOCUMENT_SELECTION_ERROR`` (pipeline-passes spec, Selection
  failure scenario).
- FC-09: an empty admissible set (all facts blocked upstream) with a
  selection requested yields ``DOCUMENT_SELECTION_ERROR`` and no
  document. D1 full enumeration: an unknown mode AND an empty set
  emit BOTH diagnostics (mode first) — request validity precedes
  content enumeration.

Determinism (design Determinism Mechanism): no time/locale/random/
env dependence; the supported-mode lookup is a linear tuple scan;
identical inputs yield identical ``StageResult``s. This stage never
imports ``pipeline`` (D5): its stage contract comes from the
:mod:`clinical_compiler.pipeline_types` leaf.

FLAGGED (owner review): the presentation-role vocabulary is
under-specified in the frozen bundle — the design/specs require that
entries carry presentation roles and that a role outside the mode's
allowed set lints as ``LINT_FAILURE`` (FC-11), but no field-to-role
table is frozen anywhere. The minimal faithful reading implemented
here assigns ONE uniform role, ``telegraphic_entry``, to every entry
of ``NURSING_RECORD_TELEGRAPHIC``: it names the mode's presentation
style and asserts NO per-field clinical presentation semantics
(inventing a field-to-role table — e.g. TA/FC to vital_sign — would
be executor-authored clinical presentation content). FLAGGED (owner
review): the mode/role constants live here for lack of an
alternative frozen home — ``pipeline_types.py`` (the shared leaf) is
a frozen Phase-1 unit, core is frozen, and renderers/linter may not
import passes; units 2-3 face the same placement question.
"""

from clinical_compiler.core.diagnostics import Diagnostic, DiagnosticCode
from clinical_compiler.core.ir import (
    CanonicalClinicalIR,
    DocumentEntry,
    DocumentIR,
)
from clinical_compiler.pipeline_types import StageResult

__all__ = [
    "NURSING_RECORD_TELEGRAPHIC",
    "SUPPORTED_MODES",
    "TELEGRAPHIC_ENTRY_ROLE",
    "run_document_selection",
]

NURSING_RECORD_TELEGRAPHIC: str = "NURSING_RECORD_TELEGRAPHIC"
SUPPORTED_MODES: tuple[str, ...] = (NURSING_RECORD_TELEGRAPHIC,)
TELEGRAPHIC_ENTRY_ROLE: str = "telegraphic_entry"


def run_document_selection(
    facts: CanonicalClinicalIR, document_mode: str
) -> StageResult[DocumentIR]:
    """Assemble the ``DocumentIR`` for the requested document mode.

    Builds one ``DocumentEntry`` per admissible canonical fact —
    referencing the fact's ``clinical_fact_id`` and carrying the mode's
    presentation role, never a clinical value — in the aggregate's
    canonical ``(field_id, clinical_fact_id)`` order. An unknown mode
    or an empty admissible set (FC-09: everything blocked upstream)
    yields ``DOCUMENT_SELECTION_ERROR`` and no document.

    Args:
        facts: The admissible canonical fact set, as the explicit
            ``CanonicalClinicalIR`` aggregate (design D10 — never an
            implicit bare tuple across this boundary).
        document_mode: The requested document mode; R1 supports only
            ``NURSING_RECORD_TELEGRAPHIC``.

    Returns:
        A ``StageResult`` admitting a single ``DocumentIR`` on
        success; on any selection failure the admitted tuple is empty
        and every request-level fault is enumerated as a
        ``DOCUMENT_SELECTION_ERROR`` diagnostic.
    """
    diagnostics: list[Diagnostic] = []

    if document_mode not in SUPPORTED_MODES:
        diagnostics.append(
            Diagnostic(
                DiagnosticCode.DOCUMENT_SELECTION_ERROR,
                f"unknown document mode {document_mode!r} — supported"
                f" modes: {list(SUPPORTED_MODES)}",
            )
        )

    if not facts.facts:
        diagnostics.append(
            Diagnostic(
                DiagnosticCode.DOCUMENT_SELECTION_ERROR,
                "no admissible canonical facts for document mode"
                f" {document_mode!r} — cannot assemble a document",
            )
        )

    if diagnostics:
        return StageResult(admitted=(), diagnostics=tuple(diagnostics))

    entries = tuple(
        DocumentEntry(
            clinical_fact_ref=fact.clinical_fact_id,
            presentation_role=TELEGRAPHIC_ENTRY_ROLE,
        )
        for fact in facts.facts
    )
    document = DocumentIR(document_mode=document_mode, entries=entries)
    return StageResult(admitted=(document,), diagnostics=())
