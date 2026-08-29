"""Policy-seed adapter — the D7 Policy Resolution State Machine (CRC-005).

Loads the owner-authored ``--policy-seed PATH`` file and models policy
resolution as the frozen state machine (design D7 / diagnostics-policy
spec, normative):

    UNRESOLVED_POLICY
      ├─ owner APPROVED seed  → populated policy
      └─ owner DEFERRED_BY_OWNER → approved empty policy

There is NO execution path where a missing or unreadable seed silently
yields an empty set and continues: with neither durable owner decision
present the state is ``UNRESOLVED_POLICY`` and the gate is BLOCKED —
never empty-set-and-continue.

- Structural validation ONLY (Phase-0 dossier, task 0.6): the seed must
  be JSON of exactly the shape ``{"terms": [...]}`` with string entries.
  No clinical judgment lives here and the executor authors NO clinical
  content — ``NEVER_AUTO_TERMS`` stays the frozen empty core default
  (design D7); the effective veto set is runtime-injected from the
  owner-authored file. ``core.policy`` is never imported or mutated.
- The approved-EMPTY policy is reachable ONLY through
  :func:`approved_empty_by_deferral`, which REQUIRES a citation naming
  the durable owner decision — ``POLICY_SEED_DECISION = DEFERRED_BY_OWNER``,
  recorded by the decision owner in the Phase-0 decision-gate resolutions
  of ``APPROVAL-PHASE1.md`` (that record IS the durable state; this
  constant transcribes it, it does not create it). Construction-time
  invariants make an uncited approved-empty policy unrepresentable,
  including via direct ``PolicyResolution`` construction.
- ``UNRESOLVED_POLICY`` is a resolution STATE, not a ``DiagnosticCode``:
  the frozen 8-code taxonomy is untouched, and the design Exit-Code
  Table maps an invalid ``--policy-seed`` to the CLI usage error (exit
  2) at the shell — translation from a blocked resolution to an exit
  code belongs to the composition root/CLI, never to this loader.
- Faults (missing file, unreadable bytes/dir, malformed JSON, wrong
  shape, non-string term, empty-string term) surface as
  ``UNRESOLVED_POLICY`` with a typed :class:`PolicySeedFault` reason and
  a deterministic human-readable detail — never as exceptions crossing
  the adapter boundary, never as a populated-but-empty policy.
- Determinism: the resolved set is a normalized ``frozenset`` —
  duplicates collapse, file-side order is irrelevant, identical inputs
  load identically. Details embed only deterministic data (the path as
  given, fixed messages, first offending entry index in file order).

FLAGGED (owner review — under-specified seams, minimal faithful
readings): (1) an owner-authored ``{"terms": []}`` seed loads as
``POPULATED`` with an empty set — D7's "empty only via deferral" letter
is read as governing the ABSENT/unreadable-seed path, since the seed
file is by definition owner-authored and emptiness then traces to the
owner's own artifact; a stricter reading would reject zero-term seeds
at this boundary. (2) duplicate entries dedupe into the set (exact
seed fidelity is set-level). (3) the empty-string term is rejected as
``EMPTY_TERM`` — structurally a degenerate term whose substring
containment in :mod:`clinical_compiler.passes.admissibility` would
vacuously veto every string-valued fact. (4) the spec prescribes no
split between UNRESOLVED_POLICY faults and usage errors at THIS layer;
all loader faults report UNRESOLVED_POLICY and the exit-2 usage mapping
is deferred to the CLI per the frozen Exit-Code Table.

This module is a stdlib-only leaf (design D5): it imports nothing from
``pipeline``, the passes, or the core — composition consumes it.
"""

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final

__all__ = [
    "DEFERRED_BY_OWNER_DECISION",
    "PolicyResolution",
    "PolicyResolutionState",
    "PolicySeedFault",
    "approved_empty_by_deferral",
    "load_policy_seed",
    "populated_policy",
    "unresolved_policy",
]


class PolicyResolutionState(StrEnum):
    """States of the D7 Policy Resolution State Machine."""

    POPULATED = "POPULATED"
    APPROVED_EMPTY_BY_DEFERRAL = "APPROVED_EMPTY_BY_DEFERRAL"
    UNRESOLVED_POLICY = "UNRESOLVED_POLICY"


class PolicySeedFault(StrEnum):
    """Typed reasons a seed fails to resolve (each blocks the gate)."""

    MISSING_FILE = "MISSING_FILE"
    UNREADABLE_FILE = "UNREADABLE_FILE"
    MALFORMED_JSON = "MALFORMED_JSON"
    WRONG_SHAPE = "WRONG_SHAPE"
    NON_STRING_TERM = "NON_STRING_TERM"
    EMPTY_TERM = "EMPTY_TERM"


DEFERRED_BY_OWNER_DECISION: Final[str] = (
    "APPROVAL-PHASE1.md — POLICY_SEED_DECISION = DEFERRED_BY_OWNER"
)
"""The durable owner decision authorizing the empty veto set.

Transcribes the Phase-0 decision-gate resolution recorded by the
decision owner in ``APPROVAL-PHASE1.md`` (durable state + test-local
seeds; empty set is an approved-by-deferral state). The only citation
this module's own tests and documentation treat as canonical.
"""

_DEFERRAL_MARKER: Final[str] = "DEFERRED_BY_OWNER"
_SEED_TERMS_KEY: Final[str] = "terms"


@dataclass(frozen=True, slots=True)
class PolicyResolution:
    """Outcome of policy resolution — exactly one D7 state, legally shaped.

    Attributes:
        state: The resolution state (populated / approved-empty-by-
            deferral / unresolved).
        terms: The effective veto set — carried ONLY by ``POPULATED``
            (possibly empty for an owner-authored zero-term seed);
            empty for the two non-populated states.
        fault: The typed reason — present ONLY on ``UNRESOLVED_POLICY``.
        detail: Deterministic human-readable fault detail (loader
            output for the composition root's usage/diagnostic text).
        deferral_reference: The cited durable owner decision — present
            ONLY on ``APPROVED_EMPTY_BY_DEFERRAL``.

    Construction-time invariants enforce the legal field combinations
    per state, so an approved-empty policy without a citation naming
    ``DEFERRED_BY_OWNER`` is unrepresentable even via direct
    construction — the fail-closed core of D7/CRC-005.
    """

    state: PolicyResolutionState
    terms: frozenset[str]
    fault: PolicySeedFault | None
    detail: str | None
    deferral_reference: str | None

    @property
    def is_resolved(self) -> bool:
        """Whether a durable owner decision resolved the policy."""
        return self.state is not PolicyResolutionState.UNRESOLVED_POLICY

    def __post_init__(self) -> None:
        if self.state is PolicyResolutionState.POPULATED:
            if self.fault is not None:
                raise ValueError("POPULATED carries no fault")
            if self.deferral_reference is not None:
                raise ValueError("POPULATED carries no deferral reference")
        elif self.state is PolicyResolutionState.APPROVED_EMPTY_BY_DEFERRAL:
            if self.terms:
                raise ValueError("APPROVED_EMPTY_BY_DEFERRAL carries no terms")
            if self.fault is not None:
                raise ValueError("APPROVED_EMPTY_BY_DEFERRAL carries no fault")
            if (
                self.deferral_reference is None
                or _DEFERRAL_MARKER not in self.deferral_reference
            ):
                raise ValueError(
                    "APPROVED_EMPTY_BY_DEFERRAL requires citing the durable"
                    " owner decision DEFERRED_BY_OWNER (APPROVAL-PHASE1.md)"
                )
        else:
            if self.terms:
                raise ValueError("UNRESOLVED_POLICY carries no terms")
            if self.fault is None:
                raise ValueError("UNRESOLVED_POLICY requires a typed fault")
            if self.deferral_reference is not None:
                raise ValueError(
                    "UNRESOLVED_POLICY carries no deferral reference"
                )


def populated_policy(terms: frozenset[str]) -> PolicyResolution:
    """Build the ``POPULATED`` resolution from an owner-approved seed."""
    return PolicyResolution(
        state=PolicyResolutionState.POPULATED,
        terms=terms,
        fault=None,
        detail=None,
        deferral_reference=None,
    )


def unresolved_policy(fault: PolicySeedFault, detail: str) -> PolicyResolution:
    """Build the blocked ``UNRESOLVED_POLICY`` resolution with its reason."""
    return PolicyResolution(
        state=PolicyResolutionState.UNRESOLVED_POLICY,
        terms=frozenset(),
        fault=fault,
        detail=detail,
        deferral_reference=None,
    )


def approved_empty_by_deferral(decision_record: str) -> PolicyResolution:
    """Build the approved-empty policy — ONLY by citing the deferral.

    The empty veto set exists solely as an APPROVED-BY-DEFERRAL state
    (D7): the caller MUST name the durable owner decision, i.e. cite
    ``POLICY_SEED_DECISION = DEFERRED_BY_OWNER`` as recorded in
    ``APPROVAL-PHASE1.md`` (see :data:`DEFERRED_BY_OWNER_DECISION`, the
    canonical citation). Any citation not naming the deferral decision
    is rejected — silent ``frozenset()``-and-continue is unreachable
    through this API.
    """
    if not decision_record or _DEFERRAL_MARKER not in decision_record:
        raise ValueError(
            "approved-empty policy requires citing the durable owner"
            " decision DEFERRED_BY_OWNER (APPROVAL-PHASE1.md) — the empty"
            " set is never obtainable without naming the deferral"
        )
    return PolicyResolution(
        state=PolicyResolutionState.APPROVED_EMPTY_BY_DEFERRAL,
        terms=frozenset(),
        fault=None,
        detail=None,
        deferral_reference=decision_record,
    )


def load_policy_seed(path: str | Path) -> PolicyResolution:
    """Load and structurally validate a ``--policy-seed`` file.

    Reads the owner-authored JSON seed of exactly the shape
    ``{"terms": [...]}`` and resolves it per D7: a structurally valid
    file yields ``POPULATED`` with the normalized term set; any fault —
    missing file, unreadable bytes, malformed JSON, wrong shape,
    non-string or empty-string term — yields ``UNRESOLVED_POLICY`` with
    a typed fault (gate BLOCKED upstream; never an empty-and-continue
    populated policy). Deterministic: duplicates collapse and file-side
    order never changes the resolved set.
    """
    seed_path = Path(path)
    try:
        text = seed_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return unresolved_policy(
            PolicySeedFault.MISSING_FILE,
            f"policy seed {str(seed_path)!r} not found — no seed and no"
            " durable owner decision present",
        )
    except (OSError, UnicodeDecodeError) as exc:
        return unresolved_policy(
            PolicySeedFault.UNREADABLE_FILE,
            f"policy seed {str(seed_path)!r} unreadable:"
            f" {type(exc).__name__} — UTF-8 text expected",
        )

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return unresolved_policy(
            PolicySeedFault.MALFORMED_JSON,
            f"policy seed {str(seed_path)!r} is not valid JSON:"
            f" {exc.msg} at line {exc.lineno} column {exc.colno}",
        )

    if not isinstance(payload, dict) or set(payload.keys()) != {
        _SEED_TERMS_KEY
    }:
        return unresolved_policy(
            PolicySeedFault.WRONG_SHAPE,
            f"policy seed {str(seed_path)!r} must be exactly"
            " {'terms': [...]} — a JSON object with the single key"
            " 'terms'",
        )
    terms_value = payload[_SEED_TERMS_KEY]
    if not isinstance(terms_value, list):
        return unresolved_policy(
            PolicySeedFault.WRONG_SHAPE,
            f"policy seed {str(seed_path)!r} 'terms' must be a list of"
            " strings",
        )

    terms: list[str] = []
    for index, term in enumerate(terms_value):
        if not isinstance(term, str):
            return unresolved_policy(
                PolicySeedFault.NON_STRING_TERM,
                f"policy seed {str(seed_path)!r} term entry {index} is"
                f" {type(term).__name__!r}, not a string",
            )
        if term == "":
            return unresolved_policy(
                PolicySeedFault.EMPTY_TERM,
                f"policy seed {str(seed_path)!r} term entry {index} is the"
                " empty string — a vacuous veto match",
            )
        terms.append(term)

    return populated_policy(frozenset(terms))
