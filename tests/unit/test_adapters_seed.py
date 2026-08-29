"""Unit tests for clinical_compiler.adapters.seed (design D7 — CRC-005).

Pins the Policy Resolution State Machine:

    UNRESOLVED_POLICY
      ├─ owner APPROVED seed  → populated policy
      └─ owner DEFERRED_BY_OWNER → approved empty policy

Every fault class resolves to ``UNRESOLVED_POLICY`` with a typed reason —
never to an empty populated policy (no silent empty-set-and-continue), and
the approved-empty state is reachable ONLY by explicitly citing the
durable owner deferral decision (``POLICY_SEED_DECISION = DEFERRED_BY_OWNER``
recorded in APPROVAL-PHASE1.md).

The committed fixture ``tests/fixtures/policy-seed-sample.json`` carries
structurally valid but deliberately NON-CLINICAL test terms — executor-
authored test data, never clinical policy content.
"""

import json
from pathlib import Path
from typing import cast

import pytest

from clinical_compiler.adapters.seed import (
    DEFERRED_BY_OWNER_DECISION,
    PolicyResolution,
    PolicyResolutionState,
    PolicySeedFault,
    approved_empty_by_deferral,
    load_policy_seed,
)
from clinical_compiler.core.diagnostics import DiagnosticCode
from clinical_compiler.core.ir import CanonicalClinicalFact
from clinical_compiler.core.types import (
    Certainty,
    ClinicalValue,
    Missingness,
    Provenance,
)
from clinical_compiler.passes.admissibility import run_admissibility
from clinical_compiler.pipeline_types import StageResult

SAMPLE_SEED_PATH = (
    Path(__file__).resolve().parent.parent / "fixtures" / "policy-seed-sample.json"
)
SAMPLE_SEED_TERMS = frozenset({"test-veto-term-alpha", "test-veto-term-beta"})


def _seed_file(tmp_path: Path, text: str) -> Path:
    """Write raw seed-file text (any validity) under ``tmp_path``."""
    path = tmp_path / "seed.json"
    path.write_text(text, encoding="utf-8")
    return path


def _seed_json(tmp_path: Path, payload: object) -> Path:
    """Write a JSON-serializable seed payload under ``tmp_path``."""
    return _seed_file(tmp_path, json.dumps(payload))


def _canonical_fact(value: object) -> CanonicalClinicalFact:
    """Build one canonical TA fact carrying the given value."""
    return CanonicalClinicalFact(
        clinical_fact_id="c-ta-1",
        field_id="TA",
        value=ClinicalValue(
            value=value,
            certainty=Certainty.UNRESOLVED,
            missingness=Missingness.PRESENT,
            provenance=Provenance(source_kind="clinical_note", source_ref="n-1"),
        ),
        source_fact_refs=("raw-1",),
    )


def _codes(
    result: StageResult[CanonicalClinicalFact],
) -> tuple[DiagnosticCode, ...]:
    """Return the emitted diagnostic codes in encounter order."""
    return tuple(d.code for d in result.diagnostics)


# --- Frozen state-machine surface ---------------------------------------------


def test_state_vocabulary_is_frozen() -> None:
    """The state machine speaks exactly the three D7 states."""
    assert {state.name for state in PolicyResolutionState} == {
        "POPULATED",
        "APPROVED_EMPTY_BY_DEFERRAL",
        "UNRESOLVED_POLICY",
    }


def test_fault_vocabulary_is_frozen() -> None:
    """Every structural seed fault class has a typed reason."""
    assert {fault.name for fault in PolicySeedFault} == {
        "MISSING_FILE",
        "UNREADABLE_FILE",
        "MALFORMED_JSON",
        "WRONG_SHAPE",
        "NON_STRING_TERM",
        "EMPTY_TERM",
    }


def test_deferral_constant_cites_the_durable_owner_record() -> None:
    """The canonical citation names APPROVAL-PHASE1.md's deferral decision."""
    assert "APPROVAL-PHASE1.md" in DEFERRED_BY_OWNER_DECISION
    assert "POLICY_SEED_DECISION" in DEFERRED_BY_OWNER_DECISION
    assert "DEFERRED_BY_OWNER" in DEFERRED_BY_OWNER_DECISION


# --- Owner APPROVED seed → POPULATED ------------------------------------------


def test_owner_seed_file_loads_populated() -> None:
    """A structurally valid seed file yields the populated policy."""
    resolution = load_policy_seed(SAMPLE_SEED_PATH)
    assert resolution.state is PolicyResolutionState.POPULATED
    assert resolution.terms == SAMPLE_SEED_TERMS
    assert resolution.fault is None
    assert resolution.deferral_reference is None
    assert resolution.is_resolved


def test_load_is_deterministic() -> None:
    """Identical loads yield identical resolutions."""
    assert load_policy_seed(SAMPLE_SEED_PATH) == load_policy_seed(SAMPLE_SEED_PATH)


def test_duplicate_terms_normalize_to_a_set(tmp_path: Path) -> None:
    """Duplicate seed entries collapse — the policy is a term SET."""
    resolution = load_policy_seed(
        _seed_json(tmp_path, {"terms": ["t-a", "t-a", "t-b"]})
    )
    assert resolution.state is PolicyResolutionState.POPULATED
    assert resolution.terms == frozenset({"t-a", "t-b"})


def test_term_order_is_irrelevant(tmp_path: Path) -> None:
    """File-side ordering never changes the resolved set."""
    forward = load_policy_seed(
        _seed_json(tmp_path, {"terms": ["t-a", "t-b", "t-c"]})
    )
    shuffled = load_policy_seed(
        _seed_json(tmp_path, {"terms": ["t-c", "t-a", "t-b"]})
    )
    assert forward.terms == shuffled.terms == frozenset({"t-a", "t-b", "t-c"})


def test_empty_terms_seed_is_populated(tmp_path: Path) -> None:
    """An owner-authored zero-term seed is structurally valid emptiness.

    FLAGGED (owner review): D7's letter says the empty set is only ever an
    APPROVED-BY-DEFERRAL state; this reading lets an explicitly provided,
    owner-authored ``{"terms": []}`` seed resolve POPULATED-empty because
    the loader validates STRUCTURE only and the seed file is by definition
    owner-authored (the absent/unreadable path is the one D7 forbids).
    """
    resolution = load_policy_seed(_seed_json(tmp_path, {"terms": []}))
    assert resolution.state is PolicyResolutionState.POPULATED
    assert resolution.terms == frozenset()
    assert resolution.is_resolved


# --- Faults → UNRESOLVED_POLICY (blocked — never empty-set-and-continue) ------


def test_missing_file_is_unresolved(tmp_path: Path) -> None:
    """A seed path that does not exist blocks with MISSING_FILE."""
    resolution = load_policy_seed(tmp_path / "absent.json")
    assert resolution.state is PolicyResolutionState.UNRESOLVED_POLICY
    assert resolution.fault is PolicySeedFault.MISSING_FILE
    assert not resolution.is_resolved


def test_directory_path_is_unresolved_unreadable(tmp_path: Path) -> None:
    """A path that is a directory, not a file, blocks UNREADABLE_FILE."""
    resolution = load_policy_seed(tmp_path)
    assert resolution.state is PolicyResolutionState.UNRESOLVED_POLICY
    assert resolution.fault is PolicySeedFault.UNREADABLE_FILE


def test_undecodable_bytes_are_unresolved_unreadable(tmp_path: Path) -> None:
    """Non-UTF-8 seed bytes block UNREADABLE_FILE (UTF-8-only design)."""
    path = tmp_path / "seed.json"
    path.write_bytes(b"\xff\xfe\x00{\"terms\": []}")
    resolution = load_policy_seed(path)
    assert resolution.state is PolicyResolutionState.UNRESOLVED_POLICY
    assert resolution.fault is PolicySeedFault.UNREADABLE_FILE


def test_malformed_json_is_unresolved(tmp_path: Path) -> None:
    """Non-JSON text blocks with MALFORMED_JSON."""
    resolution = load_policy_seed(_seed_file(tmp_path, "{\"terms\": ["))
    assert resolution.state is PolicyResolutionState.UNRESOLVED_POLICY
    assert resolution.fault is PolicySeedFault.MALFORMED_JSON


@pytest.mark.parametrize(
    "payload",
    [
        ["test-veto-term-alpha"],  # top-level array, not {"terms": [...]}
        {"seeds": ["test-veto-term-alpha"]},  # no "terms" key
        {"terms": [], "extra": 1},  # key outside the frozen seed shape
        {"terms": "test-veto-term-alpha"},  # terms is not a list
        {"terms": 3},  # terms is not a list (non-string scalar)
    ],
)
def test_wrong_shapes_are_unresolved(tmp_path: Path, payload: object) -> None:
    """Any deviation from the ``{"terms": [...]}`` shape blocks WRONG_SHAPE."""
    resolution = load_policy_seed(_seed_json(tmp_path, payload))
    assert resolution.state is PolicyResolutionState.UNRESOLVED_POLICY
    assert resolution.fault is PolicySeedFault.WRONG_SHAPE


@pytest.mark.parametrize("term", [3, None, True, ["nested"]])
def test_non_string_terms_are_unresolved(tmp_path: Path, term: object) -> None:
    """A non-string term entry blocks NON_STRING_TERM."""
    resolution = load_policy_seed(
        _seed_json(tmp_path, {"terms": ["t-ok", term]})
    )
    assert resolution.state is PolicyResolutionState.UNRESOLVED_POLICY
    assert resolution.fault is PolicySeedFault.NON_STRING_TERM


def test_empty_string_term_is_unresolved(tmp_path: Path) -> None:
    """A zero-length term blocks EMPTY_TERM (containment vacuous match)."""
    resolution = load_policy_seed(_seed_json(tmp_path, {"terms": [""]}))
    assert resolution.state is PolicyResolutionState.UNRESOLVED_POLICY
    assert resolution.fault is PolicySeedFault.EMPTY_TERM


@pytest.mark.parametrize(
    "path",
    [
        SAMPLE_SEED_PATH.parent / "absent.json",  # MISSING_FILE
        SAMPLE_SEED_PATH.parent,  # UNREADABLE_FILE (directory)
    ],
)
def test_unresolved_never_carries_terms_or_continues(path: Path) -> None:
    """No fault resolution yields a veto set or a resolved state."""
    resolution = load_policy_seed(path)
    assert resolution.state is PolicyResolutionState.UNRESOLVED_POLICY
    assert resolution.terms == frozenset()
    assert resolution.fault is not None
    assert resolution.deferral_reference is None
    assert not resolution.is_resolved
    assert resolution.detail  # the typed reason carries a deterministic message


# --- owner DEFERRED_BY_OWNER → APPROVED_EMPTY_BY_DEFERRAL ---------------------


def test_deferral_yields_approved_empty_policy() -> None:
    """Citing the durable record yields the approved-empty state."""
    resolution = approved_empty_by_deferral(DEFERRED_BY_OWNER_DECISION)
    assert resolution.state is PolicyResolutionState.APPROVED_EMPTY_BY_DEFERRAL
    assert resolution.terms == frozenset()
    assert resolution.fault is None
    assert resolution.deferral_reference == DEFERRED_BY_OWNER_DECISION
    assert resolution.is_resolved


def test_deferral_without_citation_is_rejected() -> None:
    """An empty citation cannot produce an approved-empty policy."""
    with pytest.raises(ValueError, match="DEFERRED_BY_OWNER"):
        approved_empty_by_deferral("")


def test_deferral_citation_must_name_the_decision() -> None:
    """A citation that does not name the deferral decision is rejected."""
    with pytest.raises(ValueError, match="DEFERRED_BY_OWNER"):
        approved_empty_by_deferral("APPROVAL-PHASE1.md")


def test_direct_construction_cannot_forge_approved_empty() -> None:
    """Even raw construction cannot reach approved-empty without citation."""
    with pytest.raises(ValueError, match="DEFERRED_BY_OWNER"):
        PolicyResolution(
            state=PolicyResolutionState.APPROVED_EMPTY_BY_DEFERRAL,
            terms=frozenset(),
            fault=None,
            detail=None,
            deferral_reference=None,
        )


def test_populated_cannot_carry_fault_or_citation() -> None:
    """The POPULATED state refuses fault/citation payload combinations."""
    with pytest.raises(ValueError, match="POPULATED"):
        PolicyResolution(
            state=PolicyResolutionState.POPULATED,
            terms=frozenset({"t-a"}),
            fault=PolicySeedFault.MISSING_FILE,
            detail=None,
            deferral_reference=None,
        )
    with pytest.raises(ValueError, match="POPULATED"):
        PolicyResolution(
            state=PolicyResolutionState.POPULATED,
            terms=frozenset({"t-a"}),
            fault=None,
            detail=None,
            deferral_reference=DEFERRED_BY_OWNER_DECISION,
        )


def test_approved_empty_cannot_carry_terms_or_fault() -> None:
    """The approved-empty state refuses terms and fault payloads."""
    with pytest.raises(ValueError, match="APPROVED_EMPTY_BY_DEFERRAL"):
        PolicyResolution(
            state=PolicyResolutionState.APPROVED_EMPTY_BY_DEFERRAL,
            terms=frozenset({"t-a"}),
            fault=None,
            detail=None,
            deferral_reference=DEFERRED_BY_OWNER_DECISION,
        )
    with pytest.raises(ValueError, match="APPROVED_EMPTY_BY_DEFERRAL"):
        PolicyResolution(
            state=PolicyResolutionState.APPROVED_EMPTY_BY_DEFERRAL,
            terms=frozenset(),
            fault=PolicySeedFault.MISSING_FILE,
            detail=None,
            deferral_reference=DEFERRED_BY_OWNER_DECISION,
        )


def test_unresolved_cannot_carry_terms_or_citation() -> None:
    """The unresolved state refuses terms and deferral payloads."""
    with pytest.raises(ValueError, match="UNRESOLVED_POLICY"):
        PolicyResolution(
            state=PolicyResolutionState.UNRESOLVED_POLICY,
            terms=frozenset({"t-a"}),
            fault=PolicySeedFault.MISSING_FILE,
            detail="d",
            deferral_reference=None,
        )
    with pytest.raises(ValueError, match="UNRESOLVED_POLICY"):
        PolicyResolution(
            state=PolicyResolutionState.UNRESOLVED_POLICY,
            terms=frozenset(),
            fault=PolicySeedFault.MISSING_FILE,
            detail="d",
            deferral_reference=DEFERRED_BY_OWNER_DECISION,
        )


def test_unresolved_requires_a_typed_fault() -> None:
    """The UNRESOLVED_POLICY state refuses a faultless construction."""
    with pytest.raises(ValueError, match="UNRESOLVED_POLICY"):
        PolicyResolution(
            state=PolicyResolutionState.UNRESOLVED_POLICY,
            terms=frozenset(),
            fault=None,
            detail="no fault",
            deferral_reference=None,
        )


# --- Integration point: loader output feeds run_admissibility -----------------


def test_loaded_seed_feeds_admissibility_veto() -> None:
    """The resolved set wires directly into the stage's veto parameter."""
    resolution = load_policy_seed(SAMPLE_SEED_PATH)
    assert resolution.state is PolicyResolutionState.POPULATED
    fact = _canonical_fact("context test-veto-term-alpha embedded")
    result = run_admissibility(
        (fact,), resolution.terms, frozenset({"raw-1"})
    )
    assert _codes(result) == (DiagnosticCode.POLICY_VIOLATION,)
    assert result.admitted == ()


def test_deferral_empty_set_feeds_admissibility_clean() -> None:
    """FC-12 production-path analog: deferral emptiness compiles clean."""
    resolution = approved_empty_by_deferral(DEFERRED_BY_OWNER_DECISION)
    fact = _canonical_fact("120/80")
    result = run_admissibility(
        (fact,), cast("frozenset[str]", resolution.terms), frozenset({"raw-1"})
    )
    assert result.diagnostics == ()
    assert result.admitted == (fact,)
