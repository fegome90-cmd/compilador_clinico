"""Input-validation stage — value-contract enforcement on adapter output.

First stage of the fixed pipeline order (pipeline-passes spec): a pure
defense-in-depth re-validation of every candidate ``SourceFactIR``
against the SAME frozen Unit-1 contract table
(:mod:`clinical_compiler.adapters.contract`) that gated the adapter —
design D8 assigns this stage the ``field enforcement`` half of the
table. The runtime value boundary (CRC-006 /
``ENFORCE_BOUNDED_VALUES_AT_RUNTIME``) holds HERE too:
``SourceFactIR.raw_value`` is broad/untrusted, so a fact that reached
the IR without passing the adapter — or through a future adapter — is
still rejected unless it satisfies the frozen per-field value contract.

Discipline (design D1 blocking granularity): per-fact quarantine —
each fact is admitted XOR mapped to exactly one diagnostic
(``INPUT_CONTRACT_ERROR`` for value-contract violations, ``TYPE_ERROR``
for wrong raw-value types), survivors pass through UNCHANGED in
encounter order, and no semantic normalization happens here (Phase 2
owns interpretation). Faults surface as diagnostics, never as
exceptions crossing the stage boundary (design M2.1). This stage never
imports ``pipeline`` (D5): its stage contract comes from the
:mod:`clinical_compiler.pipeline_types` leaf.
"""

from clinical_compiler.adapters.contract import ALLOWED_SOURCE_KINDS, CONTRACT
from clinical_compiler.core.diagnostics import Diagnostic, DiagnosticCode
from clinical_compiler.core.ir import SourceFactIR
from clinical_compiler.core.types import Provenance
from clinical_compiler.pipeline_types import StageResult

__all__ = ["run_input_validation"]


def _violation(fact: SourceFactIR) -> Diagnostic | None:
    """Return ``fact``'s first value-contract violation, if any.

    Mirrors the frozen contract's fixed check order (``map_record``):
    identifiers, field vocabulary, provenance, then raw-value type —
    so a fact with several violations reports the same first fault the
    record-level mapping would.
    """
    if not isinstance(fact.fact_id, str) or not fact.fact_id:
        return Diagnostic(
            DiagnosticCode.INPUT_CONTRACT_ERROR,
            "fact_id must be a non-empty string",
        )
    if not isinstance(fact.field_id, str):
        return Diagnostic(
            DiagnosticCode.INPUT_CONTRACT_ERROR,
            "field_id must be a string",
        )
    field_contract = CONTRACT.get(fact.field_id)
    if field_contract is None:
        return Diagnostic(
            DiagnosticCode.INPUT_CONTRACT_ERROR,
            f"field_id {fact.field_id!r} outside the frozen contract",
        )
    provenance = fact.provenance
    if not isinstance(provenance, Provenance):
        return Diagnostic(
            DiagnosticCode.INPUT_CONTRACT_ERROR,
            "provenance is not a Provenance record",
        )
    if not isinstance(provenance.source_kind, str):
        return Diagnostic(
            DiagnosticCode.INPUT_CONTRACT_ERROR,
            "source_kind must be a string",
        )
    if provenance.source_kind not in ALLOWED_SOURCE_KINDS:
        return Diagnostic(
            DiagnosticCode.INPUT_CONTRACT_ERROR,
            f"source_kind {provenance.source_kind!r} outside the frozen vocabulary",
        )
    if not isinstance(provenance.source_ref, str) or not provenance.source_ref:
        return Diagnostic(
            DiagnosticCode.INPUT_CONTRACT_ERROR,
            "source_ref must be a non-empty string",
        )
    raw_value = fact.raw_value
    if raw_value is not None and type(raw_value) not in field_contract.raw_value_types:
        return Diagnostic(
            DiagnosticCode.TYPE_ERROR,
            f"raw_value of type {type(raw_value).__name__!r} is not admissible"
            f" for field {fact.field_id!r}",
        )
    return None


def run_input_validation(
    facts: tuple[SourceFactIR, ...],
) -> StageResult[SourceFactIR]:
    """Validate each fact against the frozen value contract (D1).

    Pure and deterministic: identical fact sets — faults included —
    evaluate identically. Survivors are carried through as the same
    objects, in encounter order; each violating fact is quarantined
    with exactly one mapped diagnostic and never admitted downstream.
    """
    admitted: list[SourceFactIR] = []
    diagnostics: list[Diagnostic] = []
    for fact in facts:
        diagnostic = _violation(fact)
        if diagnostic is None:
            admitted.append(fact)
        else:
            diagnostics.append(diagnostic)
    return StageResult(
        admitted=tuple(admitted),
        diagnostics=tuple(diagnostics),
    )
