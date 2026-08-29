"""Driving structured-feed adapter — bytes/record → candidate source facts.

Branch A of the recorded owner decision ``INPUT_CONTRACT_DECISION =
STRUCTURED_FEED_ONLY`` (APPROVAL-PHASE1.md; design Module Map): turns feed
bytes into candidate records and maps each through the frozen Unit-1
contract (:mod:`clinical_compiler.adapters.contract`), yielding one
``StructuredFeedFact`` XOR one mapped ``Diagnostic`` per record. The
adapter performs NO semantic normalization, NO policy, and NO
admissibility — those belong to later phases — so a contract-valid but
semantically odd value passes through untouched.

Wire format (minimal reading of the frozen bundle): one JSON record
object per non-blank line (JSONL). The bundle pins no feed-level
envelope, Unit 1 froze only record-level keys, and the fault corpus
marks a top-level JSON array as an FC-03 fault — JSONL is the minimal
format consistent with all three; flagged as a design-clarification
note in the Unit-2 apply report.

Stage ownership of faults (design D1 per-record quarantine):
- Bytes-level (FC-03 ``undecodable bytes``): a feed that is not UTF-8
  faults as a whole — no record exists to quarantine — yielding exactly
  one ``INPUT_CONTRACT_ERROR`` on ``FeedEvaluation.diagnostic`` and an
  empty record sequence.
- Record-level (FC-01..FC-05, free text FC-04): each non-blank line is
  quarantined independently — an unparseable or non-object line, and any
  record the frozen contract rejects, yields that record's diagnostic
  while the remaining records keep mapping.
"""

import json
from dataclasses import dataclass

from clinical_compiler.core.diagnostics import Diagnostic, DiagnosticCode

from .contract import ContractEvaluation, map_record

__all__ = ["FeedEvaluation", "parse_feed"]


@dataclass(frozen=True, slots=True)
class FeedEvaluation:
    """Outcome of parsing one structured feed.

    Exactly one of ``records`` / ``diagnostic`` is meaningful: a
    decodable feed yields one :class:`ContractEvaluation` per candidate
    record (one per non-blank line, in encounter order — each itself
    fact-XOR-diagnostic); a bytes-level fault yields exactly one
    feed-level diagnostic and NO records. Faults surface as diagnostics,
    never as exceptions (design M2.1).
    """

    records: tuple[ContractEvaluation, ...]
    diagnostic: Diagnostic | None


def parse_feed(data: bytes) -> FeedEvaluation:
    """Parse feed ``bytes`` into per-record contract evaluations.

    Pure and deterministic: identical bytes parse identically. Blank
    lines carry no record; every remaining line must be one JSON record
    object, which is mapped through the frozen contract unchanged.
    """
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return FeedEvaluation(
            records=(),
            diagnostic=Diagnostic(
                DiagnosticCode.INPUT_CONTRACT_ERROR,
                "bytes are not valid UTF-8",
            ),
        )

    evaluations: list[ContractEvaluation] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        parsed: object
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            evaluations.append(
                ContractEvaluation(
                    fact=None,
                    diagnostic=Diagnostic(
                        DiagnosticCode.INPUT_CONTRACT_ERROR,
                        f"line {line_number} is not valid JSON",
                    ),
                ),
            )
            continue
        evaluations.append(map_record(parsed))
    return FeedEvaluation(records=tuple(evaluations), diagnostic=None)
