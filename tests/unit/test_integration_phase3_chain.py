"""Integration tests for the minimal Phase-3 chain (APPROVAL-PHASE3
Unit 6).

The full fixed stage order end to end — JSONL bytes → ``parse_feed`` →
``input_validation`` → ``semantic_normalization`` → ``admissibility``
(deferral-approved empty veto set, the FC-12 production path) →
``CanonicalClinicalIR`` → ``document_selection`` → ``render_document``
→ ``lint_conformance`` — composed INSIDE these tests via a local helper
(the Phase-1/2 ``_run_chain`` pattern, extended through render + lint).
Unit 6 builds no pipeline.py, CLI, or golden machinery: it pins the
CHAIN semantics the Phase-4 composition root must reproduce.

Byte expectations follow the implementation golden corpus committed at
task 3.7 (the glyph-vocabulary freeze): a later re-freeze under an
owner-recorded decision is EXPECTED to break these assertions and
require re-verification — never silently accepted.

Composition-level policy guarding (D7): the helper branches on
``PolicyResolution.is_resolved`` exactly like the Phase-2 helper — an
unresolved policy runs NO admissibility and yields NO IR and NO
document (never a silent empty-set continue). The production
``pipeline.py`` MUST implement the same branch (Phase 4; carried flag).
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pytest

from clinical_compiler.adapters.seed import (
    DEFERRED_BY_OWNER_DECISION,
    PolicyResolution,
    approved_empty_by_deferral,
    load_policy_seed,
)
from clinical_compiler.adapters.structured_feed import (
    FeedEvaluation,
    parse_feed,
)
from clinical_compiler.core.diagnostics import DiagnosticCode
from clinical_compiler.core.ir import (
    CanonicalClinicalFact,
    CanonicalClinicalIR,
    DocumentEntry,
    DocumentIR,
    SourceFactIR,
)
from clinical_compiler.linter.conformance import lint_conformance
from clinical_compiler.passes.admissibility import run_admissibility
from clinical_compiler.passes.document_selection import (
    NURSING_RECORD_TELEGRAPHIC,
    run_document_selection,
)
from clinical_compiler.passes.input_validation import run_input_validation
from clinical_compiler.passes.semantic_normalization import (
    run_semantic_normalization,
)
from clinical_compiler.pipeline import derive_exit_code
from clinical_compiler.pipeline_types import StageResult
from clinical_compiler.renderers.deterministic import render_document

pytestmark = pytest.mark.integration

VALID_RECORD: dict[str, object] = {
    "fact_id": "raw-1",
    "field_id": "FC",
    "raw_value": 72,
    "provenance": {"source_kind": "monitor", "source_ref": "m-9"},
}

_GOLDEN_ROOT: Final[Path] = (
    Path(__file__).resolve().parents[1] / "golden"
)

_NO_SEED: Final[Path] = _GOLDEN_ROOT / "no-such-seed.json"


@dataclass(frozen=True, slots=True)
class ChainOutcome:
    """Outcome of the full Phase-3 chain, composed inside the tests.

    Attributes:
        feed: The adapter's evaluation of the feed bytes.
        accepted: The wrappers the adapter accepted, in encounter order.
        policy: The policy resolution gating admissibility.
        policy_blocked: Whether an unresolved policy blocked the gate
            (no admissibility run, no IR, no document — never
            empty-set-and-continue).
        validated: The input-validation stage result.
        normalized: The semantic-normalization stage result.
        admissible: The admissibility stage result — ``None`` iff the
            policy gate blocked (admissibility never ran).
        ir: The aggregate constructed from the admissible survivors —
            ``None`` iff the policy gate blocked.
        selected: The document-selection stage result — ``None`` iff
            the policy gate blocked.
        rendered: The render stage result — ``None`` iff selection
            admitted no document or the policy gate blocked.
        linted: The lint stage result — ``None`` iff render admitted no
            bytes or an earlier stage blocked.
        document: The final lint-clean document bytes — ``None`` iff
            any stage admitted nothing (no partial document ever).
    """

    feed: FeedEvaluation
    accepted: tuple[object, ...]
    policy: PolicyResolution
    policy_blocked: bool
    validated: StageResult[SourceFactIR]
    normalized: StageResult[CanonicalClinicalFact]
    admissible: StageResult[CanonicalClinicalFact] | None
    ir: CanonicalClinicalIR | None
    selected: StageResult[DocumentIR] | None
    rendered: StageResult[bytes] | None
    linted: StageResult[bytes] | None
    document: bytes | None


def _record(**overrides: object) -> dict[str, object]:
    """Build a contract-conformant FC record with the given overrides."""
    record = dict(VALID_RECORD)
    record.update(overrides)
    return record


def _line(record: dict[str, object]) -> str:
    """Encode one record as a JSONL line."""
    return json.dumps(record)


def _feed(*lines: str) -> bytes:
    """Encode the given lines as feed bytes."""
    return "\n".join(lines).encode("utf-8")


def _deferred_empty_policy() -> PolicyResolution:
    """Build the approved-empty veto set citing the durable deferral."""
    return approved_empty_by_deferral(DEFERRED_BY_OWNER_DECISION)


def _run_chain(data: bytes, policy: PolicyResolution) -> ChainOutcome:
    """Compose the full Phase-3 chain as the fixed stage order runs it.

    Every stage consumes only the survivors of the previous stage; the
    document emerges ONLY when parse, validation, normalization,
    admissibility, selection, render, and lint ALL admit — any blocking
    diagnostic anywhere leaves ``document`` ``None`` (never partial).
    An unresolved policy runs NO admissibility (D7 fail-closed branch).
    """

    feed = parse_feed(data)
    accepted = (
        ()
        if feed.diagnostic is not None
        else tuple(e.fact for e in feed.records if e.fact is not None)
    )
    validated = run_input_validation(tuple(wrapped.fact for wrapped in accepted))
    normalized = run_semantic_normalization(validated.admitted)

    if not policy.is_resolved:
        return ChainOutcome(
            feed=feed,
            accepted=accepted,
            policy=policy,
            policy_blocked=True,
            validated=validated,
            normalized=normalized,
            admissible=None,
            ir=None,
            selected=None,
            rendered=None,
            linted=None,
            document=None,
        )

    source_fact_ids = frozenset(fact.fact_id for fact in validated.admitted)
    admissible = run_admissibility(
        normalized.admitted, policy.terms, source_fact_ids
    )
    ir = CanonicalClinicalIR(facts=admissible.admitted)
    selected = run_document_selection(ir, NURSING_RECORD_TELEGRAPHIC)
    if selected.diagnostics or not selected.admitted:
        return ChainOutcome(
            feed=feed,
            accepted=accepted,
            policy=policy,
            policy_blocked=False,
            validated=validated,
            normalized=normalized,
            admissible=admissible,
            ir=ir,
            selected=selected,
            rendered=None,
            linted=None,
            document=None,
        )

    rendered = render_document(selected.admitted[0], ir)
    if rendered.diagnostics or not rendered.admitted:
        return ChainOutcome(
            feed=feed,
            accepted=accepted,
            policy=policy,
            policy_blocked=False,
            validated=validated,
            normalized=normalized,
            admissible=admissible,
            ir=ir,
            selected=selected,
            rendered=rendered,
            linted=None,
            document=None,
        )

    linted = lint_conformance(rendered.admitted[0], NURSING_RECORD_TELEGRAPHIC)
    document = linted.admitted[0] if linted.admitted else None
    return ChainOutcome(
        feed=feed,
        accepted=accepted,
        policy=policy,
        policy_blocked=False,
        validated=validated,
        normalized=normalized,
        admissible=admissible,
        ir=ir,
        selected=selected,
        rendered=rendered,
        linted=linted,
        document=document,
    )


def _golden_document(name: str) -> bytes:
    """The committed implementation golden for a scenario, by name."""
    manifest = json.loads(
        (_GOLDEN_ROOT / "manifest.json").read_text(encoding="utf-8")
    )
    entry = next(
        scenario
        for scenario in manifest["scenarios"]
        if scenario["name"] == name
    )
    return (_GOLDEN_ROOT / str(entry["document"])).read_bytes()


def _lines(document: bytes) -> list[str]:
    """Decode document bytes to lines (final newline dropped)."""
    return document.decode("utf-8").split("\n")[:-1]


# --- 1. Happy path: full chain renders a lint-clean document -------------


def test_happy_path_document_is_lint_clean_and_matches_golden() -> None:
    """FC + TA present facts compile to the frozen golden document.

    The full chain admits exactly one lint-clean document whose bytes
    equal the committed ``standard_mixed`` implementation golden (the
    task-3.7 glyph-vocabulary freeze) — the Phase-4 composition root
    must reproduce these exact bytes.
    """
    data = _feed(
        _line(
            _record(
                fact_id="std-fc-1",
                raw_value=80.5,
                provenance={"source_kind": "monitor", "source_ref": "m-3"},
            )
        ),
        _line(
            _record(
                fact_id="std-ta-1",
                field_id="TA",
                raw_value="120/80",
            )
        ),
    )
    outcome = _run_chain(data, _deferred_empty_policy())

    assert outcome.policy_blocked is False
    assert outcome.feed.diagnostic is None
    assert outcome.validated.diagnostics == ()
    assert outcome.normalized.diagnostics == ()
    assert outcome.admissible is not None
    assert outcome.admissible.diagnostics == ()
    assert outcome.selected is not None
    assert outcome.selected.diagnostics == ()
    assert outcome.rendered is not None
    assert outcome.rendered.diagnostics == ()
    assert outcome.linted is not None
    assert outcome.linted.diagnostics == ()
    assert outcome.document is not None

    assert _lines(outcome.document) == [
        "FC: 80.5 [present] [monitor m-3]",
        "TA: 120/80 [present] [monitor m-9]",
    ]
    assert outcome.document == _golden_document("standard_mixed")


def test_two_full_runs_are_byte_identical() -> None:
    """Determinism across the whole chain: identical bytes in, identical
    document bytes out — every stage result equal, ids included."""
    data = _feed(
        _line(_record(fact_id="raw-fc", raw_value=72)),
        _line(
            _record(
                fact_id="raw-ta",
                field_id="TA",
                raw_value="120/80",
            )
        ),
    )
    first = _run_chain(data, _deferred_empty_policy())
    second = _run_chain(data, _deferred_empty_policy())
    assert first.document is not None and second.document is not None
    assert first.document == second.document
    assert first.ir == second.ir
    assert first.selected == second.selected
    assert first.rendered == second.rendered
    assert first.linted == second.linted


# --- 2. PC-1 / PC-2 end to end -------------------------------------------


def test_pc1_unassessed_fc_renders_explicit_unknown() -> None:
    """PC-1: no fact for ``FC`` → explicit ``FC: unknown [not_assessed]``
    — never dropped, never rewritten as assessed absence."""
    data = _feed(
        _line(
            _record(
                fact_id="pc1-ta-1",
                field_id="TA",
                raw_value="120/80",
            )
        )
    )
    outcome = _run_chain(data, _deferred_empty_policy())
    assert outcome.document is not None
    assert _lines(outcome.document) == [
        "FC: unknown [not_assessed]",
        "TA: 120/80 [present] [monitor m-9]",
    ]
    # Never dropped: the FC line exists. Never conflated: it carries the
    # unassessed token, no provenance (no source exists to trace).
    fc_line = _lines(outcome.document)[0]
    assert fc_line == "FC: unknown [not_assessed]"
    assert "missing" not in fc_line
    assert outcome.document == _golden_document("pc1_unassessed_fc")


def test_pc2_assessed_absence_traces_to_source_assertion() -> None:
    """PC-2: ``TA`` explicit null → assessed absence (``missing``) WITH
    provenance — traced to a source assertion, never to input absence."""
    data = _feed(
        _line(_record(fact_id="pc2-fc-1", raw_value=72)),
        _line(
            _record(
                fact_id="pc2-ta-1",
                field_id="TA",
                raw_value=None,
                provenance={
                    "source_kind": "clinical_note",
                    "source_ref": "n-1",
                },
            )
        ),
    )
    outcome = _run_chain(data, _deferred_empty_policy())
    assert outcome.document is not None
    assert _lines(outcome.document) == [
        "FC: 72 [present] [monitor m-9]",
        "TA: missing [missing] [clinical_note n-1]",
    ]
    # The assessed-absence line is distinguishable from PC-1's unassessed
    # line: different glyph, different missingness token, WITH a source.
    ta_line = _lines(outcome.document)[1]
    assert ta_line.startswith("TA: missing [missing] [clinical_note n-1]")
    assert "unknown" not in ta_line
    assert "not_assessed" not in ta_line
    assert outcome.document == _golden_document("pc2_assessed_absence_ta")


# --- 3. Policy-blocked path: no document ---------------------------------


def test_unresolved_policy_blocks_the_whole_chain() -> None:
    """A missing seed blocks: no admissibility run, no IR, no document.

    The D7 fail-closed branch at composition level — the unresolved
    policy never degrades into a silent empty veto set.
    """
    policy = load_policy_seed(_NO_SEED)
    assert not policy.is_resolved

    outcome = _run_chain(
        _feed(_line(_record(fact_id="raw-1"))),
        policy,
    )
    assert outcome.policy_blocked is True
    # Upstream of the gate still ran — the block is at admissibility.
    assert len(outcome.validated.admitted) == 1
    assert len(outcome.normalized.admitted) == 1
    assert outcome.admissible is None
    assert outcome.ir is None
    assert outcome.selected is None
    assert outcome.rendered is None
    assert outcome.linted is None
    assert outcome.document is None


# --- 4. Diagnostics-enumeration path: bad fact → no document --------------


def test_bad_fact_surfaces_diagnostics_and_yields_no_document() -> None:
    """FC-02 end to end: the feed's only record carries an unknown key
    (``x_priority``) → the record is quarantined with
    ``INPUT_CONTRACT_ERROR``, nothing is admissible downstream, document
    selection fails closed (FC-09 leg), and NO document is emitted —
    the diagnostic reaches the surface instead.
    """
    data = _feed(
        _line(_record(fact_id="raw-1", x_priority="high"))
    )
    outcome = _run_chain(data, _deferred_empty_policy())

    # The diagnostic surfaces at the adapter boundary.
    assert outcome.feed.diagnostic is None  # feed bytes themselves parse
    assert tuple(
        record.diagnostic.code
        for record in outcome.feed.records
        if record.diagnostic is not None
    ) == (DiagnosticCode.INPUT_CONTRACT_ERROR,)

    # Per-fact quarantine: no survivor anywhere downstream.
    assert outcome.accepted == ()
    assert outcome.validated.admitted == ()
    assert outcome.normalized.admitted == ()
    assert outcome.admissible is not None
    assert outcome.admissible.admitted == ()
    assert outcome.ir is not None
    assert outcome.ir.facts == ()

    # FC-09 leg: selection over an empty admissible set fails closed.
    assert outcome.selected is not None
    assert outcome.selected.admitted == ()
    assert tuple(
        diagnostic.code for diagnostic in outcome.selected.diagnostics
    ) == (DiagnosticCode.DOCUMENT_SELECTION_ERROR,)

    # No document — never a partial one.
    assert outcome.rendered is None
    assert outcome.linted is None
    assert outcome.document is None


# --- 8. FC-11 at the renderer boundary (audit remediation ROUND 2) ----------


def test_injected_document_ir_with_invalid_role_is_lint_failure() -> None:
    """FC-11 end to end: an injected (test-constructed) ``DocumentIR``
    whose entry carries a ``presentation_role`` outside the mode's
    allowed set is rejected AT THE RENDERER BOUNDARY — the last point
    where the role exists — with ``LINT_FAILURE``, and no document
    bytes survive. The exit-code table maps that diagnostic set to 10:
    the CODE drives the exit, never the emitting stage."""
    data = _feed(
        _line(_record(fact_id="raw-fc", raw_value=72)),
        _line(
            _record(
                fact_id="raw-ta",
                field_id="TA",
                raw_value="120/80",
            )
        ),
    )
    outcome = _run_chain(data, _deferred_empty_policy())
    assert outcome.ir is not None

    # The real selection stage always emits the mode's own role; the
    # injection REPLACES it — role corruption can only be test-built,
    # exactly the shape the corpus freezes for FC-11.
    tampered = DocumentIR(
        document_mode=NURSING_RECORD_TELEGRAPHIC,
        entries=(
            DocumentEntry(
                clinical_fact_ref=outcome.ir.facts[0].clinical_fact_id,
                presentation_role="INVALID",
            ),
            DocumentEntry(
                clinical_fact_ref=outcome.ir.facts[1].clinical_fact_id,
                presentation_role="telegraphic_entry",
            ),
        ),
    )
    rendered = render_document(tampered, outcome.ir)
    assert rendered.admitted == ()
    assert tuple(d.code for d in rendered.diagnostics) == (
        DiagnosticCode.LINT_FAILURE,
    )
    assert "INVALID" in rendered.diagnostics[0].message

    # FC-11's prescribed exit code — the diagnostic set maps to 10.
    assert derive_exit_code(rendered.diagnostics) == 10


def test_injected_document_ir_with_wrong_mode_fails_role_validation() -> None:
    """A ``DocumentIR`` stamped with an unknown mode has NO allowed-role
    vocabulary — every entry fails closed as ``LINT_FAILURE`` and no
    document is emitted (defense-in-depth over a corrupted IR)."""
    data = _feed(_line(_record(fact_id="raw-fc", raw_value=72)))
    outcome = _run_chain(data, _deferred_empty_policy())
    assert outcome.ir is not None

    tampered = DocumentIR(
        document_mode="SOME_OTHER_MODE",
        entries=(
            DocumentEntry(
                clinical_fact_ref=outcome.ir.facts[0].clinical_fact_id,
                presentation_role="telegraphic_entry",
            ),
        ),
    )
    rendered = render_document(tampered, outcome.ir)
    assert rendered.admitted == ()
    assert tuple(d.code for d in rendered.diagnostics) == (
        DiagnosticCode.LINT_FAILURE,
    )
    assert "SOME_OTHER_MODE" in rendered.diagnostics[0].message
