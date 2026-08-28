"""Intermediate representations for the compilation pipeline."""

from dataclasses import dataclass

from .types import ClinicalValue, Provenance


@dataclass(frozen=True)
class SourceFactIR:
    """A fact as extracted verbatim from one source.

    Attributes:
        fact_id: Identifier of the extracted fact.
        field_id: Clinical field the fact belongs to.
        raw_value: Untransformed value as found in the source.
        provenance: Attribution to the source of the fact.
    """

    fact_id: str
    field_id: str
    raw_value: object
    provenance: Provenance


@dataclass(frozen=True)
class CanonicalClinicalFact:
    """A normalized clinical fact with references to its sources.

    Attributes:
        clinical_fact_id: Identifier of the canonical fact.
        field_id: Clinical field the fact belongs to.
        value: Normalized clinical value with certainty and
            provenance.
        source_fact_refs: Identifiers of the ``SourceFactIR`` records
            supporting this canonical fact.
    """

    clinical_fact_id: str
    field_id: str
    value: ClinicalValue
    source_fact_refs: tuple[str, ...]


@dataclass(frozen=True)
class DocumentEntry:
    """One entry of a compiled document, referencing a canonical fact.

    Attributes:
        clinical_fact_ref: Identifier of the referenced
            ``CanonicalClinicalFact``.
        presentation_role: Role the fact plays in the presentation of
            the document.
    """

    clinical_fact_ref: str
    presentation_role: str


@dataclass(frozen=True)
class DocumentIR:
    """Intermediate representation of a compiled clinical document.

    Entries reference canonical facts by identifier; the IR never
    stores clinical values, keeping a single authority for each fact.

    Attributes:
        document_mode: Presentation mode of the document.
        entries: Ordered document entries.
    """

    document_mode: str
    entries: tuple[DocumentEntry, ...]
