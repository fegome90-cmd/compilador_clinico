"""Semantic-normalization stage — deterministic interpretation (design D8).

Second stage of the fixed pipeline order (pipeline-passes spec): maps
each validated ``SourceFactIR`` survivor onto a
``CanonicalClinicalFact`` per the frozen Deterministic Interpretation
Table. Pure and fail-closed — this stage assigns NO clinical semantics
of its own:

- Certainty (CRC-001): no deterministic certainty rule is approved in
  R1, so ``compiler_assigned_certainty`` is ``UNRESOLVED`` for EVERY
  fact — the adjudicated fail-closed rule, not a guard. The
  adjudicated-and-rejected automatic mapping (``monitor``/``lab`` →
  ``CONFIRMED``, ``clinical_note`` → ``PROBABLE``) is NOT executable
  here, and ``PROBABLE``/``LIKELY``/``UNLIKELY`` are NOT_PRODUCED.
- Certainty authority (CRC-002 — BOTH_SEPARATED): this stage works on
  validated ``SourceFactIR`` only; a source-declared certainty travels
  on the fact itself, in the dedicated ``source_asserted_certainty``
  slot (P0-2 repair — role ``clinical_source_assertion``, authority
  ``PRESERVED``), and never enters this stage's
  ``ClinicalValue.certainty``, so the compiler-assigned certainty axis
  can neither conflate with nor silently upgrade it. ``source_kind``
  informs PROVENANCE only — it is never consulted for certainty and
  never breaks an equal-authority tie.
- Missingness (design D8): a present raw value → ``PRESENT`` verbatim;
  the explicit null raw value is the structured branch's assessed-
  absence contract marker (PC-2) → ``MISSING`` with mandatory
  provenance, carried through from the asserting fact — absence always
  traces to a source assertion, never to input absence. The table's
  explicit ``NOT_APPLICABLE`` row has NO marker in the frozen R1
  structured contract and is therefore unreachable here (flagged in
  the apply report; inventing a marker string would be executor-
  authored clinical semantics). ``NOT_ASSESSED`` is a document-level
  concern (no fact exists), produced downstream — never by this stage.
- Ambiguity (FC-06, design D1): survivors are grouped by ``field_id``;
  a group whose facts carry more than one distinct interpretation
  (``missingness``/value pair) is an equal-authority conflict with no
  disambiguator — R1 NEVER picks, so every fact of the conflicted
  group is quarantined with exactly one ``SEMANTIC_AMBIGUITY_BLOCK``
  diagnostic and no canonical fact is created for the field (admitting
  the corroborated reading while its rival blocks would be picking a
  winner). A group with one shared interpretation — corroborating
  duplicates included — merges into ONE canonical fact citing all
  contributing fact ids: ``72`` and ``72.0`` denote the same reading
  and never false-conflict.

Determinism (design Determinism Mechanism): ``clinical_fact_id`` is
derived from fact identity — ``field_id`` plus the SHA-256 digest over
the canonical-JSON preimage of the codepoint-sorted contributing
``fact_id`` set (stdlib ``hashlib``/``json`` only; never random, uuid,
or time). ``source_fact_refs`` are stored codepoint-sorted so the same
contributor set always constructs the identical canonical fact; the
merged fact's ``ClinicalValue.provenance`` is the first-encountered
contributor's provenance (equal authority ⇒ no precedence rule
exists — flagged in the apply report). Faults surface as diagnostics,
never as exceptions crossing the stage boundary (design M2.1). This
stage never imports ``pipeline`` (D5): its stage contract comes from
the :mod:`clinical_compiler.pipeline_types` leaf.
"""

import hashlib
import json

from clinical_compiler.core.diagnostics import Diagnostic, DiagnosticCode
from clinical_compiler.core.ir import CanonicalClinicalFact, SourceFactIR
from clinical_compiler.core.types import Certainty, ClinicalValue, Missingness
from clinical_compiler.pipeline_types import StageResult

__all__ = ["run_semantic_normalization"]


def _interpret(fact: SourceFactIR) -> tuple[Missingness, object]:
    """Interpret one fact per the D8 table: (missingness, raw value).

    A present raw value is kept verbatim with ``PRESENT``; the explicit
    null marker is the assessed-absence reading (``MISSING``). The
    pair is the fact's admissible interpretation — equality on pairs
    decides corroboration versus conflict downstream.
    """
    if fact.raw_value is None:
        return (Missingness.MISSING, None)
    return (Missingness.PRESENT, fact.raw_value)


def _clinical_fact_id(field_id: str, refs: tuple[str, ...]) -> str:
    """Derive the canonical fact id from fact identity (deterministic).

    SHA-256 over the canonical-JSON preimage ``[field_id, sorted refs]``
    — collision-safe for arbitrary fact-id strings, stable across runs
    and input orderings, stdlib only.
    """
    preimage = json.dumps(
        [field_id, list(refs)], ensure_ascii=True, separators=(",", ":")
    )
    digest = hashlib.sha256(preimage.encode("utf-8")).hexdigest()
    return f"{field_id}:{digest}"


def run_semantic_normalization(
    facts: tuple[SourceFactIR, ...],
) -> StageResult[CanonicalClinicalFact]:
    """Normalize validated survivors into canonical clinical facts (D8).

    Pure and deterministic: identical fact sets — conflicts included —
    normalize identically. Groups survivors by ``field_id`` (in
    first-encounter field order); an unambiguous group yields exactly
    one canonical fact citing all its contributors, a conflicted group
    yields one ``SEMANTIC_AMBIGUITY_BLOCK`` diagnostic per quarantined
    fact and no canonical fact.
    """
    groups: dict[str, list[SourceFactIR]] = {}
    for fact in facts:
        groups.setdefault(fact.field_id, []).append(fact)

    admitted: list[CanonicalClinicalFact] = []
    diagnostics: list[Diagnostic] = []
    for field_id, group in groups.items():
        distinct: list[tuple[Missingness, object]] = []
        for fact in group:
            interpretation = _interpret(fact)
            if interpretation not in distinct:
                distinct.append(interpretation)

        if len(distinct) > 1:
            contributors = ", ".join(fact.fact_id for fact in group)
            for _ in group:
                diagnostics.append(
                    Diagnostic(
                        DiagnosticCode.SEMANTIC_AMBIGUITY_BLOCK,
                        f"field_id {field_id!r} carries {len(distinct)}"
                        f" conflicting equal-authority interpretations"
                        f" ({contributors}) with no disambiguator —"
                        " R1 never picks",
                    )
                )
            continue

        first = group[0]
        missingness = distinct[0][0]
        refs = tuple(sorted(fact.fact_id for fact in group))
        admitted.append(
            CanonicalClinicalFact(
                clinical_fact_id=_clinical_fact_id(field_id, refs),
                field_id=field_id,
                value=ClinicalValue(
                    value=first.raw_value,
                    certainty=Certainty.UNRESOLVED,
                    missingness=missingness,
                    provenance=first.provenance,
                ),
                source_fact_refs=refs,
            )
        )

    return StageResult(
        admitted=tuple(admitted),
        diagnostics=tuple(diagnostics),
    )
