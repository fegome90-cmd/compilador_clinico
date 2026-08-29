"""Composition root — the fixed stage order, whole-run emission gate,
and exit-code derivation (design D1/D3/D5; tasks 4.1).

Wires the real chain exactly as the design sequence diagram runs it:
``parse_feed → run_input_validation → run_semantic_normalization →
run_admissibility → CanonicalClinicalIR → run_document_selection`` —
every stage consuming ONLY the survivors of the previous stage
(per-fact quarantine, full diagnostic enumeration) — then the
whole-run fail-closed emission gate: ``render_document`` and
``lint_conformance`` are reached ONLY while the accumulated diagnostic
set is empty, and the result carries a document IFF the run finished
clean. One invalid fact blocks the document — by design (D1); stages
are never skipped ahead of their survivors (the Phase-1 convention:
a feed-level fault still runs every later stage on the empty survivor
set, maximizing enumeration over fail-fast hiding).

The D7 policy gate (carried flag from the Phase-2/3 helper chains): a
``PolicyResolution`` that is not ``is_resolved`` runs NO admissibility —
hence no selection, render, or lint — and yields an explicit blocked
outcome. There is no execution path where an unresolved policy degrades
into a silent empty veto set (CRC-005): the veto set reaching
``run_admissibility`` is always a resolved policy's ``terms`` (possibly
the deferral-approved empty set, the FC-12 production path).

Exit codes: :func:`derive_exit_code` is the frozen pure total function
of the diagnostic SET (design Exit-Code Table) — the minimum
stage-order code among 3–10 present, 0 iff empty. Stage order, not
``DiagnosticCode`` declaration order (``PROVENANCE_ERROR`` ranks 7).
Exit 2 (usage: argparse, unreadable input, unknown mode, invalid seed —
"no compile attempted") and exit 70 (unexpected-exception catch-all)
are CLI-boundary mappings: 2 is decided before a compile is attempted,
and per design M2.1 unexpected exceptions are confined to the CLI's
catch-all — this module is pure and never catches or raises for
clinical faults.

FLAGGED (owner review — under-specified seams, minimal faithful
readings of the frozen contract):
1. ``CompileResult.document`` is ``bytes | None``, not the design
   §Interfaces sketch's ``str | None``: the normative sequence diagram
   emits ``CompileResult(document=bytes, ())`` and the frozen
   render/lint stages return ``StageResult[bytes]``; the sketch's
   ``str`` predates the Phase-3 freeze and no stage produces ``str``.
2. ``CompileRequest`` carries the ``PolicyResolution``, not the bare
   ``veto_set`` label in the sequence diagram: the D7 branch is
   indistinguishable on a bare set (resolved-empty vs unresolved), and
   the carried flag REQUIRES the resolution state.
3. ``CompileResult.policy`` is added beyond the sketch's two fields so
   the blocked outcome is observable at the shell: ``UNRESOLVED_POLICY``
   is a resolution state, NOT a ``DiagnosticCode`` (the 8-code taxonomy
   is frozen), and the Exit-Code Table maps it to the CLI's exit 2 —
   the translation needs the state (adapters/seed.py's recorded
   ruling). Without the field, ``document=None, diagnostics=()`` would
   be indistinguishable from success-and-emit-nothing.

Dependency rule (D5): this module imports everything below it —
adapters, passes, renderers, linter, pipeline_types, core — and NOTHING
imports it except the future CLI/``__main__``. Pure: no I/O, no
globals mutated, no time/locale/random/env in any output path.
"""

from dataclasses import dataclass
from typing import Final

from clinical_compiler.adapters.seed import PolicyResolution
from clinical_compiler.adapters.structured_feed import parse_feed
from clinical_compiler.core.diagnostics import Diagnostic, DiagnosticCode
from clinical_compiler.core.ir import CanonicalClinicalIR
from clinical_compiler.linter.conformance import lint_conformance
from clinical_compiler.passes.admissibility import run_admissibility
from clinical_compiler.passes.document_selection import run_document_selection
from clinical_compiler.passes.input_validation import run_input_validation
from clinical_compiler.passes.semantic_normalization import (
    run_semantic_normalization,
)
from clinical_compiler.pipeline_types import StageResult
from clinical_compiler.renderers.deterministic import render_document

__all__ = [
    "CompileRequest",
    "CompileResult",
    "StageResult",
    "derive_exit_code",
    "run",
]

_STAGE_ORDER_EXIT_CODES: Final[tuple[tuple[DiagnosticCode, int], ...]] = (
    (DiagnosticCode.INPUT_CONTRACT_ERROR, 3),
    (DiagnosticCode.TYPE_ERROR, 4),
    (DiagnosticCode.SEMANTIC_AMBIGUITY_BLOCK, 5),
    (DiagnosticCode.POLICY_VIOLATION, 6),
    (DiagnosticCode.PROVENANCE_ERROR, 7),
    (DiagnosticCode.DOCUMENT_SELECTION_ERROR, 8),
    (DiagnosticCode.RENDER_ERROR, 9),
    (DiagnosticCode.LINT_FAILURE, 10),
)
"""The frozen Exit-Code Table rows 3–10, in fixed stage order.

Membership is the only use of the derived set in
:func:`derive_exit_code`; the ordered tuple — never set/dict iteration
order — drives the mapping (design Determinism Mechanism #1/#4).
"""


@dataclass(frozen=True, slots=True)
class CompileRequest:
    """One compile invocation: feed bytes, document mode, policy.

    Attributes:
        data: The raw feed bytes (UNTRUSTED_CONTENT — parsed strictly
            against the frozen contract, never executed).
        document_mode: The requested document mode; R1 supports only
            ``NURSING_RECORD_TELEGRAPHIC`` (an unknown mode surfaces as
            ``DOCUMENT_SELECTION_ERROR`` here; the CLI pre-validates it
            as usage exit 2 — no compile attempted).
        policy: The D7 policy resolution produced by
            ``adapters.seed`` — the resolution STATE gates admissibility;
            only a resolved policy's ``terms`` ever reach
            ``run_admissibility``.
    """

    data: bytes
    document_mode: str
    policy: PolicyResolution


@dataclass(frozen=True, slots=True)
class CompileResult:
    """Outcome of one compile run — the fail-closed emission contract.

    Attributes:
        document: The lint-clean document bytes — present IFF the whole
            run finished with an empty diagnostic set under a resolved
            policy; ``None`` otherwise (never a partial document).
        diagnostics: Every diagnostic enumerated across all stages, in
            deterministic accumulation order (feed-level, then
            per-record, then per-stage in fixed order).
        policy: The policy resolution the run was gated by — the
            blocked state is observable at the shell (an unresolved
            resolution maps to the CLI's usage exit 2; it is a
            resolution state, not a ``DiagnosticCode``).

    Construction-time invariants (fail-closed, mirroring
    ``PolicyResolution.__post_init__``): a document never coexists with
    diagnostics, and a document-less, diagnostic-less outcome exists
    ONLY under an unresolved policy — the silent-empty-success state D7
    forbids is unrepresentable.
    """

    document: bytes | None
    diagnostics: tuple[Diagnostic, ...]
    policy: PolicyResolution

    def __post_init__(self) -> None:
        if self.document is not None and self.diagnostics:
            raise ValueError(
                "CompileResult carries a document AND diagnostics —"
                " emission is fail-closed: any diagnostic blocks the"
                " document"
            )
        if (
            self.document is None
            and not self.diagnostics
            and self.policy.is_resolved
        ):
            raise ValueError(
                "CompileResult carries neither document nor"
                " diagnostics under a RESOLVED policy — a clean run"
                " emits its document; an empty outcome exists only"
                " under UNRESOLVED_POLICY"
            )


def derive_exit_code(diagnostics: tuple[Diagnostic, ...]) -> int:
    """Map the diagnostic SET to its frozen exit code (design D3).

    Pure and order-independent: the minimum stage-order code among
    3–10 present; 0 iff the set is empty. Exit 2 (usage — no compile
    attempted) and exit 70 (unexpected exception) are CLI-boundary
    mappings outside this diagnostic-set domain.
    """
    present = frozenset(diagnostic.code for diagnostic in diagnostics)
    for code, exit_code in _STAGE_ORDER_EXIT_CODES:
        if code in present:
            return exit_code
    return 0


def run(request: CompileRequest) -> CompileResult:
    """Compile feed bytes through the fixed stage order (design D1).

    Every stage runs on the survivors of the previous stage; diagnostics
    accumulate; the document is emitted IFF the accumulated set is empty
    and render + lint both admit. An unresolved policy blocks at the D7
    gate before admissibility. Pure: identical requests compile
    identically; faults surface as diagnostics, never exceptions.
    """
    policy = request.policy
    diagnostics: list[Diagnostic] = []

    feed = parse_feed(request.data)
    if feed.diagnostic is not None:
        diagnostics.append(feed.diagnostic)
    accepted = (
        ()
        if feed.diagnostic is not None
        else tuple(
            evaluation.fact
            for evaluation in feed.records
            if evaluation.fact is not None
        )
    )
    diagnostics.extend(
        evaluation.diagnostic
        for evaluation in feed.records
        if evaluation.diagnostic is not None
    )

    validated = run_input_validation(tuple(fact.fact for fact in accepted))
    diagnostics.extend(validated.diagnostics)
    normalized = run_semantic_normalization(validated.admitted)
    diagnostics.extend(normalized.diagnostics)

    if not policy.is_resolved:
        return CompileResult(
            document=None,
            diagnostics=tuple(diagnostics),
            policy=policy,
        )

    source_fact_ids = frozenset(fact.fact_id for fact in validated.admitted)
    admissible = run_admissibility(
        normalized.admitted, policy.terms, source_fact_ids
    )
    diagnostics.extend(admissible.diagnostics)
    canonical_ir = CanonicalClinicalIR(facts=admissible.admitted)
    selected = run_document_selection(canonical_ir, request.document_mode)
    diagnostics.extend(selected.diagnostics)

    if diagnostics or not selected.admitted:
        return CompileResult(
            document=None,
            diagnostics=tuple(diagnostics),
            policy=policy,
        )

    rendered = render_document(selected.admitted[0], canonical_ir)
    diagnostics.extend(rendered.diagnostics)
    if diagnostics or not rendered.admitted:
        return CompileResult(
            document=None,
            diagnostics=tuple(diagnostics),
            policy=policy,
        )

    linted = lint_conformance(rendered.admitted[0], request.document_mode)
    diagnostics.extend(linted.diagnostics)
    if diagnostics or not linted.admitted:
        return CompileResult(
            document=None,
            diagnostics=tuple(diagnostics),
            policy=policy,
        )

    return CompileResult(
        document=linted.admitted[0],
        diagnostics=(),
        policy=policy,
    )
