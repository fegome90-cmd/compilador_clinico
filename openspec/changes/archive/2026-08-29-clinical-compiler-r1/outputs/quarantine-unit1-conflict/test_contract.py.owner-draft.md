# Quarantine — Unit 1 conflict (resolved 2026-08-29)

Owner's parallel draft, superseded by adjudicated contract reading; preserved for reference.

```python
"""Unit tests for clinical_compiler.adapters.contract."""

import types
import typing

from clinical_compiler.adapters.contract import (
    ALLOWED_FACT_KEYS,
    ALLOWED_PROVENANCE_KEYS,
    OPTIONAL_FACT_KEYS,
    REQUIRED_FACT_KEYS,
    REQUIRED_PROVENANCE_KEYS,
    ProvenanceInput,
    RawScalar,
    StructuredFactInput,
)


def test_required_fact_keys_are_exact() -> None:
    """The required fact key set matches the TypedDict required fields."""
    assert REQUIRED_FACT_KEYS == frozenset(
        {"fact_id", "field_id", "raw_value", "provenance"}
    )


def test_optional_fact_keys_are_exact() -> None:
    """Only source_asserted_certainty is optional at the boundary."""
    assert OPTIONAL_FACT_KEYS == frozenset({"source_asserted_certainty"})


def test_allowed_fact_keys_is_required_union_optional() -> None:
    """ALLOWED_FACT_KEYS is exactly required plus optional keys."""
    assert ALLOWED_FACT_KEYS == REQUIRED_FACT_KEYS | OPTIONAL_FACT_KEYS


def test_provenance_key_contract_is_closed() -> None:
    """Provenance requires exactly source_kind and source_ref."""
    assert REQUIRED_PROVENANCE_KEYS == frozenset({"source_kind", "source_ref"})
    assert ALLOWED_PROVENANCE_KEYS == REQUIRED_PROVENANCE_KEYS


def test_structured_fact_input_typeddict_matches_key_sets() -> None:
    """TypedDict required/optional keys agree with the frozen key sets."""
    assert StructuredFactInput.__required_keys__ == REQUIRED_FACT_KEYS
    assert StructuredFactInput.__optional_keys__ == OPTIONAL_FACT_KEYS


def test_provenance_input_typeddict_has_no_optional_keys() -> None:
    """ProvenanceInput is total: no optional keys allowed."""
    assert ProvenanceInput.__required_keys__ == REQUIRED_PROVENANCE_KEYS
    assert ProvenanceInput.__optional_keys__ == frozenset()


def test_raw_scalar_alias_is_the_four_scalar_origins() -> None:
    """RawScalar is exactly str | int | float | None.

    bool exclusion is an adapter-level validation contract (bool is an
    int subclass); the alias itself only names the four allowed origins.
    """
    assert isinstance(RawScalar, types.UnionType)
    assert set(typing.get_args(RawScalar)) == {str, int, float, type(None)}
```
