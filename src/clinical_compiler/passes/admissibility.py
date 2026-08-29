"""Admissibility stage — veto enforcement + provenance resolution.

Third stage of the fixed pipeline order (pipeline-passes spec): each
canonical fact from normalization is admitted only if it clears BOTH
checks; a fact failing either is quarantined per-fact (design D1) and
never consumed downstream. Pure and fail-closed — faults surface as
diagnostics, never as exceptions crossing the stage boundary (design
M2.1).

- Veto (FC-07, design D7 / diagnostics-policy spec): ``veto_terms``
  arrives EXPLICITLY as a parameter — the ONLY veto source this stage
  consults. ``core.policy.NEVER_AUTO_TERMS`` is never read here: the
  frozen empty core default stays untouched (no core mutation), and
  the seed loader / Policy Resolution State Machine (UNRESOLVED_POLICY,
  ``DEFERRED_BY_OWNER``) lives in ``adapters/seed.py`` and the
  composition root, NOT in this stage. The stage is a pure function of
  its inputs: a caller passing ``frozenset()`` gets no veto enforcement
  (the approved-empty FC-12 production path) — guarding that callers
  against silent empty sets is composition's job, never this stage's.
- Veto semantics (certainty-INDEPENDENT): a fact whose value contains
  a vetoed term is blocked with ``POLICY_VIOLATION`` regardless of its
  certainty — even ``CONFIRMED`` never auto-confirms a vetoed term.
  Matching follows the spec wording "a fact containing a vetoed term"
  (corpus: "value matches an approved seed term"): a term matches when
  the fact's ``ClinicalValue.value`` is a ``str`` CONTAINING the term —
  equality is the containment edge case, and embedding a vetoed hedge
  inside a longer value cannot bypass the veto. Non-string values
  (numeric readings, the assessed-absence ``None``) carry no textual
  content and never match a string term.
- Provenance resolution (FC-08): every ``source_fact_ref`` of a
  canonical fact must resolve against the SURVIVING ``SourceFactIR``
  set — resolution against real source facts lives HERE (the U1
  ``CanonicalClinicalIR`` aggregate validates lineage structurally
  only). A fact with refs pointing at no surviving source fact, or
  with no refs at all (the "absent" arm — reachable because this stage
  consumes the bare fact tuple per the frozen design interface, not
  the aggregate), quarantines with ``PROVENANCE_ERROR``.
- Full enumeration (design D1): a fact failing BOTH checks emits BOTH
  diagnostics (veto first, matching the module map's "veto +
  provenance resolution" order) and is quarantined once — no fault is
  hidden behind the other.

Determinism (design Determinism Mechanism): diagnostics follow fact
encounter order; the reported veto term is the codepoint-minimal match
over the sorted veto set, so frozenset iteration order NEVER reaches
output; identical inputs yield identical ``StageResult``s. Survivors
pass through UNCHANGED — same objects, encounter order. This stage
never imports ``pipeline`` (D5): its stage contract comes from the
:mod:`clinical_compiler.pipeline_types` leaf.

FLAGGED (owner review): the frozen design §Interfaces signature is
``run_admissibility(facts, veto_terms)`` — it does not prescribe how
the surviving source facts reach this stage for FC-08 resolution. The
minimal faithful reading implemented here adds an explicit REQUIRED
``source_fact_ids: frozenset[str]`` parameter (ids only — the stage
needs membership, nothing more, from the sources): required and
default-less so the composition root can never silently resolve
against nothing. FLAGGED (owner review): veto "matching" is
implemented as substring containment per the spec's "containing"
wording (the fail-closed reading; equality-only would be bypassable
by embedding).
"""

from clinical_compiler.core.diagnostics import Diagnostic, DiagnosticCode
from clinical_compiler.core.ir import CanonicalClinicalFact
from clinical_compiler.pipeline_types import StageResult

__all__ = ["run_admissibility"]


def _vetoed_term(
    fact: CanonicalClinicalFact, veto_terms: frozenset[str]
) -> str | None:
    """Return the codepoint-minimal veto term the fact's value contains.

    ``None`` when the fact's value is not a string or contains no veto
    term. Sorted candidate iteration keeps the reported term — and the
    diagnostic message — stable regardless of frozenset hash order.
    """
    value = fact.value.value
    if not isinstance(value, str):
        return None
    matches = sorted(term for term in veto_terms if term in value)
    return matches[0] if matches else None


def _unresolvable_refs(
    fact: CanonicalClinicalFact, source_fact_ids: frozenset[str]
) -> tuple[str, ...]:
    """Return the fact's refs with no surviving ``SourceFactIR``, sorted.

    Codepoint-sorted so the diagnostic message is a pure function of
    the ref SET, independent of the tuple's arrival order.
    """
    return tuple(
        sorted(
            ref for ref in fact.source_fact_refs if ref not in source_fact_ids
        )
    )


def run_admissibility(
    facts: tuple[CanonicalClinicalFact, ...],
    veto_terms: frozenset[str],
    source_fact_ids: frozenset[str],
) -> StageResult[CanonicalClinicalFact]:
    """Admit canonical facts that clear veto AND provenance resolution.

    Pure and deterministic: identical inputs — veto hits, dangling
    lineages, both — evaluate identically. Veto hits quarantine with
    ``POLICY_VIOLATION`` (certainty-independent — even ``CONFIRMED``
    blocks); refs resolving to no surviving ``SourceFactIR`` (or no
    refs at all) quarantine with ``PROVENANCE_ERROR``; survivors pass
    through unchanged in encounter order.
    """
    admitted: list[CanonicalClinicalFact] = []
    diagnostics: list[Diagnostic] = []
    for fact in facts:
        blocked = False

        term = _vetoed_term(fact, veto_terms)
        if term is not None:
            diagnostics.append(
                Diagnostic(
                    DiagnosticCode.POLICY_VIOLATION,
                    f"canonical fact {fact.clinical_fact_id!r} carries"
                    f" vetoed term {term!r} — never auto-confirmed"
                    " regardless of certainty",
                )
            )
            blocked = True

        if not fact.source_fact_refs:
            diagnostics.append(
                Diagnostic(
                    DiagnosticCode.PROVENANCE_ERROR,
                    f"canonical fact {fact.clinical_fact_id!r} carries no"
                    " source_fact_refs — provenance absent",
                )
            )
            blocked = True
        else:
            unresolvable = _unresolvable_refs(fact, source_fact_ids)
            if unresolvable:
                diagnostics.append(
                    Diagnostic(
                        DiagnosticCode.PROVENANCE_ERROR,
                        f"canonical fact {fact.clinical_fact_id!r} cites"
                        f" unresolvable source_fact_refs"
                        f" {list(unresolvable)!r} — no surviving"
                        " SourceFactIR",
                    )
                )
                blocked = True

        if not blocked:
            admitted.append(fact)

    return StageResult(
        admitted=tuple(admitted),
        diagnostics=tuple(diagnostics),
    )
