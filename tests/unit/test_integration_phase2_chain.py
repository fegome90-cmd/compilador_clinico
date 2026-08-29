"""Integration tests for the minimal Phase-2 chain (APPROVAL-PHASE2 Unit 5).

``structured_feed → input_validation → semantic_normalization →
admissibility → CanonicalClinicalIR`` — the Phase-2 prefix of the fixed
stage order (pipeline-passes spec), composed INSIDE these tests via a
local helper (the Phase-1 ``_run_chain`` pattern, extended). Unit 5
builds no pipeline.py, CLI, renderer, or document selection: the chain
exists only here, positive + negative + policy paths.

Task-2.6 full-chain scenario disposition: the ``DocumentIR`` leg of
``DocumentIR → CanonicalClinicalFact → SourceFactIR`` is Phase-3 work
(task 3.1/3.2 own document selection) and is DEFERRED there; this unit
covers the maximal Phase-2-reachable subset — every canonical fact's
``source_fact_refs`` resolve back through a surviving ``SourceFactIR``
carrying the original source provenance.

Composition-level policy guarding (D7): the helper branches on
``PolicyResolution.is_resolved`` — an unresolved policy runs NO
admissibility and yields NO IR (never a silent empty-set continue).
The production ``pipeline.py`` MUST implement the same branch (Phase
4; flagged for owner review in the Unit-5 apply report).
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pytest

from clinical_compiler.adapters.contract import StructuredFeedFact
from clinical_compiler.adapters.seed import (
    DEFERRED_BY_OWNER_DECISION,
    PolicyResolution,
    PolicySeedFault,
    approved_empty_by_deferral,
    load_policy_seed,
)
from clinical_compiler.adapters.structured_feed import FeedEvaluation, parse_feed
from clinical_compiler.core.diagnostics import DiagnosticCode
from clinical_compiler.core.ir import (
    CanonicalClinicalFact,
    CanonicalClinicalIR,
    SourceFactIR,
)
from clinical_compiler.core.types import Certainty, Missingness, Provenance
from clinical_compiler.passes.admissibility import run_admissibility
from clinical_compiler.passes.input_validation import run_input_validation
from clinical_compiler.passes.semantic_normalization import (
    run_semantic_normalization,
)
from clinical_compiler.pipeline_types import StageResult

pytestmark = pytest.mark.integration

VALID_RECORD: dict[str, object] = {
    "fact_id": "raw-1",
    "field_id": "FC",
    "raw_value": 72,
    "provenance": {"source_kind": "monitor", "source_ref": "m-9"},
}

_SEED_FIXTURE: Final[Path] = (
    Path(__file__).resolve().parents[1] / "fixtures" / "policy-seed-sample.json"
)
"""The owner-authored sample seed fixture (task 2.4 test-local seeds)."""

_RESERVED_CERTAINTIES: Final[frozenset[Certainty]] = frozenset(
    {Certainty.PROBABLE, Certainty.LIKELY, Certainty.UNLIKELY}
)
"""CRC-001 NOT_PRODUCED states — never assignable by the R1 compiler."""


@dataclass(frozen=True, slots=True)
class ChainOutcome:
    """Outcome of the Phase-2 chain, composed inside the tests.

    Attributes:
        feed: The adapter's evaluation of the feed bytes.
        accepted: The wrappers the adapter accepted, in encounter order
            — each carrying its CRC-002 ``source_asserted_certainty``.
        policy: The policy resolution gating admissibility.
        policy_blocked: Whether an unresolved policy blocked the gate
            (no admissibility run, no IR — never empty-set-and-continue).
        validated: The input-validation stage result.
        normalized: The semantic-normalization stage result.
        admissible: The admissibility stage result — ``None`` iff the
            policy gate blocked (admissibility never ran).
        ir: The aggregate constructed from the admissible survivors —
            ``None`` iff the policy gate blocked.
    """

    feed: FeedEvaluation
    accepted: tuple[StructuredFeedFact, ...]
    policy: PolicyResolution
    policy_blocked: bool
    validated: StageResult[SourceFactIR]
    normalized: StageResult[CanonicalClinicalFact]
    admissible: StageResult[CanonicalClinicalFact] | None
    ir: CanonicalClinicalIR | None


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
    """Compose the Phase-2 chain exactly as the fixed stage order runs it.

    Adapter bytes → accepted wrappers → input validation → semantic
    normalization → admissibility → ``CanonicalClinicalIR``. A feed-level
    fault leaves every downstream stage running on the empty survivor
    set (the Phase-1 convention). The policy resolution gates
    admissibility: an UNRESOLVED policy runs NO admissibility and
    constructs NO IR — the D7 fail-closed branch. The veto set reaching
    ``run_admissibility`` is always a RESOLVED policy's terms (possibly
    the deferral-approved empty set — the FC-12 production path), and
    provenance resolves against the SURVIVING validated source facts.
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
        )

    source_fact_ids = frozenset(fact.fact_id for fact in validated.admitted)
    admissible = run_admissibility(
        normalized.admitted, policy.terms, source_fact_ids
    )
    ir = CanonicalClinicalIR(facts=admissible.admitted)
    return ChainOutcome(
        feed=feed,
        accepted=accepted,
        policy=policy,
        policy_blocked=False,
        validated=validated,
        normalized=normalized,
        admissible=admissible,
        ir=ir,
    )


def _certainties(outcome: ChainOutcome) -> tuple[Certainty, ...]:
    """Return every canonical certainty the chain produced, any stage."""
    assert outcome.admissible is not None
    stages = (
        tuple(f.value.certainty for f in outcome.normalized.admitted)
        + tuple(f.value.certainty for f in outcome.admissible.admitted)
    )
    assert outcome.ir is not None
    return stages + tuple(f.value.certainty for f in outcome.ir.facts)


# --- 1. Full positive chain ------------------------------------------------------


def test_full_positive_chain_compiles_to_canonical_ir(
    make_provenance: Callable[..., Provenance],
) -> None:
    """Positive path end to end: bytes → validated → canonical → IR.

    Includes a declared ``confirmed`` + a corroborating declared
    ``probable`` FC reading (one interpretation — they merge) and a TA
    assessed-absence marker (explicit null raw value).
    """
    outcome = _run_chain(
        _feed(
            _line(
                _record(
                    fact_id="raw-fc-a",
                    source_asserted_certainty="confirmed",
                )
            ),
            _line(
                _record(
                    fact_id="raw-fc-b",
                    source_asserted_certainty="probable",
                )
            ),
            _line(
                _record(
                    fact_id="raw-ta-x",
                    field_id="TA",
                    raw_value=None,
                    provenance={
                        "source_kind": "clinical_note",
                        "source_ref": "n-1",
                    },
                )
            ),
        ),
        _deferred_empty_policy(),
    )
    assert outcome.feed.diagnostic is None
    assert outcome.policy_blocked is False
    assert len(outcome.validated.admitted) == 3
    assert outcome.validated.diagnostics == ()
    assert len(outcome.normalized.admitted) == 2
    assert outcome.normalized.diagnostics == ()
    assert outcome.admissible is not None
    assert outcome.admissible.diagnostics == ()
    assert outcome.admissible.admitted == outcome.normalized.admitted
    assert outcome.ir is not None

    # Wrappers keep the declared certainties verbatim (CRC-002 axis 1).
    declared = {
        wrapper.fact.fact_id: wrapper.source_asserted_certainty
        for wrapper in outcome.accepted
    }
    assert declared == {
        "raw-fc-a": Certainty.CONFIRMED,
        "raw-fc-b": Certainty.PROBABLE,
        "raw-ta-x": None,
    }

    # CRC-001/002 across the WHOLE chain: declared "confirmed"/"probable"
    # source assertions never upgrade the compiler-assigned certainty.
    assert set(_certainties(outcome)) == {Certainty.UNRESOLVED}
    assert not (_RESERVED_CERTAINTIES & set(_certainties(outcome)))

    fc_fact, ta_fact = outcome.ir.facts  # canonical (field_id, id) order
    assert fc_fact.field_id == "FC"
    assert ta_fact.field_id == "TA"
    assert fc_fact.value.value == 72
    assert fc_fact.value.missingness is Missingness.PRESENT
    assert fc_fact.source_fact_refs == ("raw-fc-a", "raw-fc-b")
    assert ta_fact.value.value is None
    assert ta_fact.value.missingness is Missingness.MISSING
    assert ta_fact.source_fact_refs == ("raw-ta-x",)

    # Task-2.6 reachable legs: every canonical ref resolves back through
    # a surviving SourceFactIR carrying the original source provenance.
    survivors = {fact.fact_id: fact for fact in outcome.validated.admitted}
    assert set(survivors) == {"raw-fc-a", "raw-fc-b", "raw-ta-x"}
    assert survivors["raw-fc-a"].provenance == make_provenance(
        source_kind="monitor", source_ref="m-9"
    )
    assert survivors["raw-ta-x"].provenance == make_provenance(
        source_kind="clinical_note", source_ref="n-1"
    )
    for canonical in outcome.ir.facts:
        for ref in canonical.source_fact_refs:
            assert ref in survivors


def test_declared_assertions_never_upgrade_compiler_certainty_across_chain(
    make_provenance: Callable[..., Provenance],
) -> None:
    """Three declarations on one corroborated reading, one UNRESOLVED fact.

    The whole chain keeps the two axes separated (CRC-002
    BOTH_SEPARATED): the wrappers preserve ``confirmed``/``probable``
    verbatim while the single merged canonical fact stays UNRESOLVED —
    and no reserved certainty (CRC-001 NOT_PRODUCED) appears anywhere.
    """
    outcome = _run_chain(
        _feed(
            _line(
                _record(
                    fact_id="ta-1",
                    field_id="TA",
                    raw_value="120/80",
                    source_asserted_certainty="confirmed",
                )
            ),
            _line(
                _record(
                    fact_id="ta-2",
                    field_id="TA",
                    raw_value="120/80",
                    source_asserted_certainty="probable",
                )
            ),
            _line(_record(fact_id="ta-3", field_id="TA", raw_value="120/80")),
        ),
        _deferred_empty_policy(),
    )
    declared = {
        wrapper.fact.fact_id: wrapper.source_asserted_certainty
        for wrapper in outcome.accepted
    }
    assert declared == {
        "ta-1": Certainty.CONFIRMED,
        "ta-2": Certainty.PROBABLE,
        "ta-3": None,
    }
    assert len(outcome.normalized.admitted) == 1
    canonical = outcome.normalized.admitted[0]
    assert canonical.value.certainty is Certainty.UNRESOLVED
    assert canonical.source_fact_refs == ("ta-1", "ta-2", "ta-3")
    assert canonical.value.provenance == make_provenance(
        source_kind="monitor", source_ref="m-9"
    )
    assert not (_RESERVED_CERTAINTIES & set(_certainties(outcome)))


# --- 2. Veto path (populated seed) ----------------------------------------------


def test_vetoed_fact_quarantined_and_survivors_construct_ir() -> None:
    """The owner seed fixture vetoes one fact; the rest compile to IR.

    The veto is certainty-independent: the vetoed TA reading declared
    ``confirmed`` by its source is still quarantined — the declaration
    rides the wrapper verbatim while the veto blocks the fact.
    """
    policy = load_policy_seed(_SEED_FIXTURE)
    assert policy.is_resolved
    assert policy.terms == frozenset(
        {"test-veto-term-alpha", "test-veto-term-beta"}
    )
    outcome = _run_chain(
        _feed(
            _line(_record(fact_id="fc-ok", raw_value=72)),
            _line(
                _record(
                    fact_id="ta-vetoed",
                    field_id="TA",
                    raw_value="TA: test-veto-term-alpha de noche",
                    source_asserted_certainty="confirmed",
                )
            ),
        ),
        policy,
    )
    assert outcome.policy_blocked is False
    wrapper = outcome.accepted[1]
    assert wrapper.source_asserted_certainty is Certainty.CONFIRMED
    assert outcome.admissible is not None
    assert outcome.admissible.diagnostics[0].code is DiagnosticCode.POLICY_VIOLATION
    assert len(outcome.admissible.diagnostics) == 1
    assert outcome.ir is not None
    assert tuple(fact.field_id for fact in outcome.ir.facts) == ("FC",)
    assert outcome.ir.facts[0].value.certainty is Certainty.UNRESOLVED
    # The vetoed field is absent from the aggregate entirely.
    assert all(fact.field_id != "TA" for fact in outcome.ir.facts)


# --- 3. UNRESOLVED_POLICY blocks the gate ----------------------------------------


def test_unresolved_policy_blocks_gate_with_no_silent_empty_set() -> None:
    """A missing seed blocks: no admissibility run, no IR, explicit state.

    This pins the composition-level D7 branch: the helper must NOT run
    admissibility with a silently empty set when the policy is
    unresolved (the production pipeline.py owes the same branch —
    Phase 4).
    """
    policy = load_policy_seed(_SEED_FIXTURE.parent / "no-such-seed.json")
    assert policy.state.value == "UNRESOLVED_POLICY"
    assert policy.fault is PolicySeedFault.MISSING_FILE
    assert not policy.is_resolved
    assert policy.terms == frozenset()

    outcome = _run_chain(
        _feed(_line(_record(fact_id="raw-1"))),
        policy,
    )
    assert outcome.policy_blocked is True
    # Upstream of the gate still ran — the block is at admissibility.
    assert len(outcome.validated.admitted) == 1
    assert len(outcome.normalized.admitted) == 1
    # The blocked outcome is explicit: admissibility never ran, no IR.
    assert outcome.admissible is None
    assert outcome.ir is None


# --- 4. Ambiguity path ------------------------------------------------------------


def test_ambiguous_group_blocks_and_survivors_continue() -> None:
    """Conflicting equal-authority FC readings block; TA continues to IR."""
    outcome = _run_chain(
        _feed(
            _line(_record(fact_id="fc-a", raw_value=72)),
            _line(_record(fact_id="fc-b", raw_value=80)),
            _line(
                _record(
                    fact_id="ta-ok",
                    field_id="TA",
                    raw_value="120/80",
                )
            ),
        ),
        _deferred_empty_policy(),
    )
    assert tuple(fact.fact_id for fact in outcome.validated.admitted) == (
        "fc-a",
        "fc-b",
        "ta-ok",
    )
    # The whole conflicted group is quarantined — one diagnostic per
    # fact, no canonical fact for the field (R1 never picks).
    assert len(outcome.normalized.admitted) == 1
    assert outcome.normalized.admitted[0].field_id == "TA"
    assert tuple(d.code for d in outcome.normalized.diagnostics) == (
        DiagnosticCode.SEMANTIC_AMBIGUITY_BLOCK,
        DiagnosticCode.SEMANTIC_AMBIGUITY_BLOCK,
    )
    assert outcome.admissible is not None
    assert outcome.admissible.diagnostics == ()
    assert outcome.ir is not None
    assert tuple(fact.field_id for fact in outcome.ir.facts) == ("TA",)
    assert all(fact.field_id != "FC" for fact in outcome.ir.facts)


# --- 5. Determinism ----------------------------------------------------------------


def test_identical_bytes_and_seed_yield_identical_ir() -> None:
    """Identical inputs construct the identical IR, ids included."""
    data = _feed(
        _line(_record(fact_id="raw-1", source_asserted_certainty="confirmed")),
        _line(_record(fact_id="raw-2", field_id="TA", raw_value="120/80")),
        _line(_record(fact_id="raw-3", field_id="TA", raw_value=None)),
    )
    first = _run_chain(data, load_policy_seed(_SEED_FIXTURE))
    second = _run_chain(data, load_policy_seed(_SEED_FIXTURE))
    assert first.policy_blocked is False and second.policy_blocked is False
    assert first.ir is not None and second.ir is not None
    assert first.ir == second.ir
    assert first.ir.facts == second.ir.facts
    assert tuple(f.clinical_fact_id for f in first.ir.facts) == tuple(
        f.clinical_fact_id for f in second.ir.facts
    )
    assert first.admissible == second.admissible
    assert first.feed == second.feed


# --- 6. Aggregate edge: empty survivors ---------------------------------------------


def test_empty_survivors_construct_empty_canonical_ir() -> None:
    """No survivors is a VALID construction: the empty aggregate."""
    # Every fact quarantined upstream (here: the only field conflicts).
    all_blocked = _run_chain(
        _feed(
            _line(_record(fact_id="fc-a", raw_value=72)),
            _line(_record(fact_id="fc-b", raw_value=80)),
        ),
        _deferred_empty_policy(),
    )
    assert all_blocked.normalized.admitted == ()
    assert all_blocked.admissible is not None
    assert all_blocked.admissible.admitted == ()
    assert all_blocked.ir is not None
    assert all_blocked.ir.facts == ()

    # The degenerate feed reaches the same empty aggregate.
    empty_feed = _run_chain(b"", _deferred_empty_policy())
    assert empty_feed.ir is not None
    assert empty_feed.ir.facts == ()
