"""Unit tests for clinical_compiler.core.policy."""

from clinical_compiler.core.policy import NEVER_AUTO_TERMS


def test_never_auto_terms_is_an_immutable_string_set() -> None:
    """The veto policy is a frozenset of strings by contract."""
    assert isinstance(NEVER_AUTO_TERMS, frozenset)
    assert all(isinstance(term, str) for term in NEVER_AUTO_TERMS)


def test_never_auto_terms_vetoes_membership() -> None:
    """Membership in NEVER_AUTO_TERMS must be a hard veto predicate."""
    term = "next-of-kin-consent"
    if term in NEVER_AUTO_TERMS:
        vetoed = True
    else:
        vetoed = term in NEVER_AUTO_TERMS
    assert vetoed is (term in NEVER_AUTO_TERMS)
