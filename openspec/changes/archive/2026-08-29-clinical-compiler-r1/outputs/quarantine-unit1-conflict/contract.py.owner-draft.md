# Quarantine — Unit 1 conflict (resolved 2026-08-29)

Owner's parallel draft, superseded by adjudicated contract reading; preserved for reference.

```python
# src/clinical_compiler/adapters/contract.py

"""Structured input contract for clinical-compiler R1.

This module defines the data boundary accepted by structured adapters.

It does not:
- parse bytes or JSON;
- normalize clinical values;
- infer certainty;
- validate field-specific value semantics;
- create canonical clinical facts;
- apply policy.
"""

from typing import NotRequired, TypeAlias, TypedDict

# bool is intentionally excluded.
#
# In Python, bool is a subclass of int, but the R1 contract must not allow
# values such as `true` to pass accidentally as numeric clinical values.
RawScalar: TypeAlias = str | int | float | None


class ProvenanceInput(TypedDict):
    """Source attribution supplied by the upstream producer."""

    source_kind: str
    source_ref: str


class StructuredFactInput(TypedDict):
    """One structured source fact at the compiler boundary.

    Required values are preserved verbatim by the adapter.
    Semantic interpretation belongs to later compiler passes.
    """

    fact_id: str
    field_id: str
    raw_value: RawScalar
    provenance: ProvenanceInput

    # Source assertion only.
    #
    # This MUST NOT be treated as compiler-assigned certainty.
    # Interpretation/normalization belongs to a later pass.
    source_asserted_certainty: NotRequired[str]


REQUIRED_FACT_KEYS: frozenset[str] = frozenset(
    {
        "fact_id",
        "field_id",
        "raw_value",
        "provenance",
    }
)

OPTIONAL_FACT_KEYS: frozenset[str] = frozenset(
    {
        "source_asserted_certainty",
    }
)

ALLOWED_FACT_KEYS: frozenset[str] = REQUIRED_FACT_KEYS | OPTIONAL_FACT_KEYS


REQUIRED_PROVENANCE_KEYS: frozenset[str] = frozenset(
    {
        "source_kind",
        "source_ref",
    }
)

ALLOWED_PROVENANCE_KEYS: frozenset[str] = REQUIRED_PROVENANCE_KEYS
```
