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


@dataclass(frozen=True, slots=True)
class CanonicalClinicalIR:
    """Adjudicated aggregate of the admissible canonical fact set.

    Explicit lightweight carrier (CRC-003 / design D10, owner
    adjudication 2026-08-28) for the fact set crossing the
    admissibility → document-selection boundary — never an implicit
    bare tuple. Construction is fail-closed and deterministic: it
    rejects duplicated ``clinical_fact_id`` values and facts whose
    lineage (``source_fact_refs``) does not validate, and it stores
    the facts in the canonical ``(field_id, clinical_fact_id)``
    codepoint order so the same fact set always constructs to the
    same representation. The aggregate carries clinical facts only —
    no document prose and no ``document_mode`` (mode selection is a
    downstream concern).

    Attributes:
        facts: The admissible canonical facts, canonically ordered.

    Raises:
        ValueError: If two facts share a ``clinical_fact_id``, or a
            fact carries no resolvable lineage (empty
            ``source_fact_refs``, or a ref that is an empty string).
    """

    facts: tuple[CanonicalClinicalFact, ...]

    def __post_init__(self) -> None:
        seen_ids: set[str] = set()
        for fact in self.facts:
            clinical_fact_id = fact.clinical_fact_id
            if clinical_fact_id in seen_ids:
                raise ValueError(
                    "duplicate clinical_fact_id in canonical fact set:"
                    f" {clinical_fact_id!r}"
                )
            seen_ids.add(clinical_fact_id)
            if not fact.source_fact_refs:
                raise ValueError(
                    f"canonical fact {clinical_fact_id!r} has no"
                    " source_fact_refs — lineage does not validate"
                )
            for source_fact_ref in fact.source_fact_refs:
                if not source_fact_ref:
                    raise ValueError(
                        f"canonical fact {clinical_fact_id!r} carries an"
                        " empty source_fact_ref — lineage does not validate"
                    )
        object.__setattr__(
            self,
            "facts",
            tuple(
                sorted(
                    self.facts,
                    key=lambda fact: (fact.field_id, fact.clinical_fact_id),
                )
            ),
        )
