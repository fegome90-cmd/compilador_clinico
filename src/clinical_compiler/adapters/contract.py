"""Frozen structured-feed input contract — single source of truth (design D8).

Freezes what a valid structured-feed record is per the recorded owner
decision ``INPUT_CONTRACT_DECISION = STRUCTURED_FEED_ONLY``
(APPROVAL-PHASE1.md): allowed record keys, required vs optional, the
per-``field_id`` raw-value types, provenance rules, and the pure mapping
onto the existing ``SourceFactIR``. Adapters and input validation enforce
exactly this table; contract changes REQUIRE a new recorded owner
decision.

Runtime value boundary (CRC-006 / ADJ-5 — ``ENFORCE_BOUNDED_VALUES_AT_RUNTIME``):
``ClinicalValue.value`` stays ``Any`` in the frozen core, but this
boundary admits only the exact types each field declares. Values are
checked by exact runtime type, so a ``bool`` never passes a numeric field
and an arbitrary Python object never becomes an admissible value.

Certainty authority model (CRC-002 — ``BOTH_SEPARATED``): a declared
``source_asserted_certainty`` is captured verbatim on
``StructuredFeedFact`` (role ``clinical_source_assertion``, authority
``PRESERVED``); it is optional and never invented, and it is never
conflated with any compiler-assigned certainty — this module assigns
none.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from clinical_compiler.core.diagnostics import Diagnostic, DiagnosticCode
from clinical_compiler.core.ir import SourceFactIR
from clinical_compiler.core.types import Certainty, Provenance

__all__ = [
    "ALLOWED_RECORD_KEYS",
    "ALLOWED_SOURCE_KINDS",
    "CONTRACT",
    "OPTIONAL_RECORD_KEYS",
    "REQUIRED_PROVENANCE_KEYS",
    "REQUIRED_RECORD_KEYS",
    "ContractEvaluation",
    "FieldContract",
    "StructuredFeedFact",
    "map_record",
]


@dataclass(frozen=True, slots=True)
class FieldContract:
    """Raw-value contract for one clinical ``field_id``.

    Attributes:
        field_id: Clinical field the contract governs.
        raw_value_types: Exact runtime types admissible as the field's
            ``raw_value``. Membership is checked by exact type, never by
            ``isinstance`` — a ``bool`` is an ``int`` subclass and must
            still be rejected for numeric fields.
    """

    field_id: str
    raw_value_types: tuple[type[object], ...]


CONTRACT: Final[Mapping[str, FieldContract]] = MappingProxyType(
    {
        "FC": FieldContract(field_id="FC", raw_value_types=(int, float)),
        "TA": FieldContract(field_id="TA", raw_value_types=(str,)),
    }
)

REQUIRED_RECORD_KEYS: Final[frozenset[str]] = frozenset(
    {"fact_id", "field_id", "raw_value", "provenance"}
)
OPTIONAL_RECORD_KEYS: Final[frozenset[str]] = frozenset(
    {"source_asserted_certainty"}
)
ALLOWED_RECORD_KEYS: Final[frozenset[str]] = (
    REQUIRED_RECORD_KEYS | OPTIONAL_RECORD_KEYS
)
REQUIRED_PROVENANCE_KEYS: Final[frozenset[str]] = frozenset(
    {"source_kind", "source_ref"}
)
ALLOWED_SOURCE_KINDS: Final[frozenset[str]] = frozenset(
    {"monitor", "lab", "clinical_note"}
)


@dataclass(frozen=True, slots=True)
class StructuredFeedFact:
    """An accepted record mapped onto the IR ladder entry.

    Attributes:
        fact: The mapped ``SourceFactIR`` (verbatim ``raw_value`` and
            provenance).
        source_asserted_certainty: The certainty the source itself
            declared, captured verbatim (CRC-002: authority ``PRESERVED``)
            — ``None`` when the source declared none; never invented and
            never a compiler assignment.
    """

    fact: SourceFactIR
    source_asserted_certainty: Certainty | None


@dataclass(frozen=True, slots=True)
class ContractEvaluation:
    """Outcome of mapping one candidate record through the contract.

    Exactly one of ``fact`` / ``diagnostic`` is set: an accepted record
    yields the mapped fact; a rejected one yields exactly one mapped
    diagnostic. Contract faults surface as diagnostics, never as
    exceptions (design M2.1).
    """

    fact: StructuredFeedFact | None
    diagnostic: Diagnostic | None


def _reject(code: DiagnosticCode, message: str) -> ContractEvaluation:
    """Build a rejected evaluation carrying one mapped diagnostic."""
    return ContractEvaluation(fact=None, diagnostic=Diagnostic(code, message))


def map_record(record: object) -> ContractEvaluation:
    """Map one candidate structured-feed record onto ``SourceFactIR``.

    Pure and deterministic: identical records evaluate identically,
    independent of key insertion order; the first contract violation is
    reported in a fixed check order with a deterministic message.
    Structural violations yield ``INPUT_CONTRACT_ERROR``; an otherwise
    conformant record whose ``raw_value`` type is invalid for its field
    yields ``TYPE_ERROR`` (fault corpus FC-01..FC-05).
    """
    if not isinstance(record, Mapping):
        return _reject(
            DiagnosticCode.INPUT_CONTRACT_ERROR,
            "record is not an object",
        )
    rec = cast(Mapping[str, object], record)
    keys = set(rec.keys())

    missing = sorted(REQUIRED_RECORD_KEYS - keys)
    if missing:
        return _reject(
            DiagnosticCode.INPUT_CONTRACT_ERROR,
            f"missing required key {missing[0]!r}",
        )
    unknown = sorted(keys - ALLOWED_RECORD_KEYS, key=repr)
    if unknown:
        return _reject(
            DiagnosticCode.INPUT_CONTRACT_ERROR,
            f"unknown key {unknown[0]!r}",
        )

    fact_id = rec["fact_id"]
    if not isinstance(fact_id, str):
        return _reject(
            DiagnosticCode.INPUT_CONTRACT_ERROR,
            "fact_id must be a string",
        )
    field_id = rec["field_id"]
    if not isinstance(field_id, str):
        return _reject(
            DiagnosticCode.INPUT_CONTRACT_ERROR,
            "field_id must be a string",
        )
    field_contract = CONTRACT.get(field_id)
    if field_contract is None:
        return _reject(
            DiagnosticCode.INPUT_CONTRACT_ERROR,
            f"field_id {field_id!r} outside the frozen contract",
        )

    provenance = rec["provenance"]
    if not isinstance(provenance, Mapping):
        return _reject(
            DiagnosticCode.INPUT_CONTRACT_ERROR,
            "provenance is not an object",
        )
    prov = cast(Mapping[str, object], provenance)
    if set(prov.keys()) != REQUIRED_PROVENANCE_KEYS:
        return _reject(
            DiagnosticCode.INPUT_CONTRACT_ERROR,
            "provenance must declare exactly 'source_kind' and 'source_ref'",
        )
    source_kind = prov["source_kind"]
    if not isinstance(source_kind, str):
        return _reject(
            DiagnosticCode.INPUT_CONTRACT_ERROR,
            "source_kind must be a string",
        )
    if source_kind not in ALLOWED_SOURCE_KINDS:
        return _reject(
            DiagnosticCode.INPUT_CONTRACT_ERROR,
            f"source_kind {source_kind!r} outside the frozen vocabulary",
        )
    source_ref = prov["source_ref"]
    if not isinstance(source_ref, str):
        return _reject(
            DiagnosticCode.INPUT_CONTRACT_ERROR,
            "source_ref must be a string",
        )

    source_asserted_certainty: Certainty | None = None
    if "source_asserted_certainty" in rec:
        declared = rec["source_asserted_certainty"]
        if not isinstance(declared, str):
            return _reject(
                DiagnosticCode.INPUT_CONTRACT_ERROR,
                "source_asserted_certainty must be a certainty name",
            )
        try:
            source_asserted_certainty = Certainty(declared)
        except ValueError:
            return _reject(
                DiagnosticCode.INPUT_CONTRACT_ERROR,
                f"source_asserted_certainty {declared!r} outside the taxonomy",
            )

    raw_value = rec["raw_value"]
    if raw_value is not None and type(raw_value) not in field_contract.raw_value_types:
        return _reject(
            DiagnosticCode.TYPE_ERROR,
            f"raw_value of type {type(raw_value).__name__!r} is not admissible"
            f" for field {field_id!r}",
        )

    fact = SourceFactIR(
        fact_id=fact_id,
        field_id=field_id,
        raw_value=raw_value,
        provenance=Provenance(source_kind=source_kind, source_ref=source_ref),
    )
    return ContractEvaluation(
        fact=StructuredFeedFact(
            fact=fact,
            source_asserted_certainty=source_asserted_certainty,
        ),
        diagnostic=None,
    )
