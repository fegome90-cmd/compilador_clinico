"""Unit tests for clinical_compiler.core.policy.

Content-bearing, mutation-sensitive replacement for the baseline
tautological test (task 2.7; diagnostics-policy spec —
"Mutation-Sensitive Policy Tests"): any mutation of ``NEVER_AUTO_TERMS``
MEMBERSHIP — a populated core default, a mutable binding — fails at
least one test here. Veto-ENFORCEMENT mutation is killed by
``tests/unit/test_passes_admissibility.py`` (the D7 injected-parameter
suite, live kill evidenced by Phase-2 Unit 5); these tests complement
it by pinning the core constant itself.
"""

import pytest

from clinical_compiler.core.policy import NEVER_AUTO_TERMS


def test_never_auto_terms_is_an_immutable_string_set() -> None:
    """The veto policy is a frozenset of strings by contract."""
    assert isinstance(NEVER_AUTO_TERMS, frozenset)
    assert all(isinstance(term, str) for term in NEVER_AUTO_TERMS)


def test_never_auto_terms_is_the_frozen_empty_default() -> None:
    """D7: the core default is empty — membership arrives only via seed.

    Kills the populated-default membership mutation: adding ANY term to
    the core constant fails this equality. The approved-empty
    production path (FC-12) comes from a recorded ``DEFERRED_BY_OWNER``
    seed resolution, never from a populated core.
    """
    assert NEVER_AUTO_TERMS == frozenset()


def test_never_auto_terms_membership_cannot_be_mutated_in_place() -> None:
    """The frozen binding exposes no membership-mutation API.

    Kills the mutable-binding mutation: a plain ``set`` would accept
    ``.add``; the ``frozenset`` type makes the in-place mutation
    operator itself unavailable (AttributeError).
    """
    with pytest.raises(AttributeError):
        NEVER_AUTO_TERMS.add("test-veto-term-placeholder")
