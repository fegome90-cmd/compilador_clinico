"""Golden determinism machinery — tasks 3.6/3.7/3.8 (APPROVAL-PHASE3
Unit 4; design Determinism Mechanism #5/#6).

Stdlib + clinical_compiler tooling for the committed golden corpus
under ``tests/golden/``. It has three jobs:

1. **Compose the real chain** over feed bytes
   (:func:`compile_feed`): parse → validate → normalize → admit →
   select → render → lint, the Phase-3 fixed stage order composed here
   because the Phase-4 ``pipeline.py`` composition root does not exist
   yet (same composition discipline as the Phase-2 chain tests). The
   policy is the FC-12 production path — the deferral-approved empty
   veto set (a RESOLVED policy by construction; the
   ``is_resolved`` branch owed by ``pipeline.py`` is therefore not
   reachable here). Golden scenarios are positive-path fixture sets:
   ANY diagnostic is a generation-time failure (fail-closed, never a
   partial golden).
2. **Verify the committed corpus** (:func:`verify_corpus` /
   :func:`assess_golden_evidence`): every manifest digest must match
   its committed document bytes, and recompiling the committed input
   must reproduce those bytes exactly (golden regression detection —
   any output-affecting change to any stage breaks at least one
   comparison). Evidence carries the M7.1 ``EVIDENCE_INTEGRITY``
   vocabulary (design #6): implementation-generated goldens are
   ``DEGRADED`` by definition; a self-consistent independently
   authored sample under ``independent/`` upgrades the evidence to
   ``VALID``; any verification failure is ``INVALID``. Absence of the
   independent sample keeps the evidence ``DEGRADED`` and the Phase 3
   determinism gate BLOCKED pending owner input — the executor NEVER
   authors that sample (task 3.7 / Unit 5).
3. **Serve as the subprocess CLI** for the cross-run SHA-256 gate
   (task 3.8): ``python golden_machinery.py digest <input.jsonl>``
   compiles one fixture set and prints the document's SHA-256 hex.
   Fresh-interpreter runs under ``python -I`` (which implies ``-E`` —
   ``PYTHON*`` env vars are ignored, so each isolated run rolls a
   fresh random hash seed) and seeded runs without ``-I``
   (``PYTHONHASHSEED=0`` vs unset) must all produce the same digest.

Independent-sample contract (shape of the committed
``tests/golden/independent/MANIFEST.json``; detection = this file
existing) — a multi-scenario manifest mirroring the golden-manifest
family shape: per-scenario ``input``/``document`` paths are relative
to ``tests/golden/`` (the corpus root)::

    {
      "schema": "clinical-compiler-r1/independent-sample/1",
      "author": "decision owner or owner-designated audit path",
      "scenarios": [
        {
          "name": "<golden scenario the expectation targets>",
          "input": "scenarios/<name>.input.jsonl",
          "input_sha256": "<SHA-256 of the committed input bytes>",
          "document": "independent/<name>.expected.txt",
          "sha256": "<SHA-256 of the expected document bytes>"
        }
      ]
    }

Self-consistency is checked per scenario in sorted-name order: the
referenced document and input files must exist and their bytes must
SHA-256 to the recorded digests. Whether the independently expected
bytes AGREE with the implementation's output is the Phase-3 gate
(task 3.9) computation; this module only detects presence and
self-consistency.

Determinism: no time/locale/random/env dependence; manifest
serialization is canonical (``sort_keys=True``, UTF-8, one final
newline). The ``clinical_compiler`` imports are lazy inside the chain
composer so that importing this module (including under ``python -I``
with no configured import path) is side-effect free.
"""

import hashlib
import json
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Final

GOLDEN_ROOT: Final[Path] = Path(__file__).resolve().parent
SCENARIO_DIR: Final[Path] = GOLDEN_ROOT / "scenarios"
MANIFEST_PATH: Final[Path] = GOLDEN_ROOT / "manifest.json"
INDEPENDENT_DIR: Final[Path] = GOLDEN_ROOT / "independent"
INDEPENDENT_MANIFEST_PATH: Final[Path] = INDEPENDENT_DIR / "MANIFEST.json"

MANIFEST_SCHEMA: Final[str] = "clinical-compiler-r1/golden-manifest/1"

_SRC_ROOT: Final[Path] = Path(__file__).resolve().parents[2] / "src"


def _ensure_src_on_path() -> None:
    """Make ``clinical_compiler`` importable in bare interpreters.

    pytest configures ``pythonpath = ["src"]`` for in-process runs;
    subprocess children (``python -I``, ``-P`` implies no path
    prepend) must locate the src tree explicitly. Inserting by absolute
    path is deterministic and environment-independent.
    """
    src = str(_SRC_ROOT)
    if src not in sys.path:
        sys.path.insert(0, src)


class EvidenceIntegrity(StrEnum):
    """M7.1 vocabulary for golden evidence (design Mechanism #6).

    - ``VALID``: verified corpus plus at least one self-consistent
      independently authored expected sample.
    - ``DEGRADED``: implementation-generated goldens only — the
      implementation would be writing its own exam.
    - ``INVALID``: verification failed (digest/file disagreement,
      recompile drift, or a self-inconsistent independent sample).
    """

    VALID = "VALID"
    DEGRADED = "DEGRADED"
    INVALID = "INVALID"


EVIDENCE_INTEGRITY_VOCABULARY: Final[tuple[str, ...]] = tuple(
    member.value for member in EvidenceIntegrity
)


def sha256_hex(data: bytes) -> str:
    """SHA-256 hex digest of ``data`` (the corpus digest primitive)."""
    return hashlib.sha256(data).hexdigest()


def lint_clean(document: bytes) -> bool:
    """Whether ``document`` passes the mode conformance linter."""
    _ensure_src_on_path()
    from clinical_compiler.linter.conformance import lint_conformance
    from clinical_compiler.passes.document_selection import (
        NURSING_RECORD_TELEGRAPHIC,
    )

    result = lint_conformance(document, NURSING_RECORD_TELEGRAPHIC)
    return not result.diagnostics


def compile_feed(data: bytes) -> bytes:
    """Run the full Phase-3 chain over feed bytes → document bytes.

    Stage order: parse_feed → input_validation →
    semantic_normalization → admissibility (deferral-approved empty
    veto set — the FC-12 production path) → ``CanonicalClinicalIR`` →
    document_selection → render → lint. Only a fully clean run yields
    bytes; ANY diagnostic raises (golden scenarios are positive-path
    fixture sets — a diagnostic means the input is not golden
    material, and generation must fail closed, never emit a partial
    document).
    """
    _ensure_src_on_path()
    from clinical_compiler.adapters.seed import (
        DEFERRED_BY_OWNER_DECISION,
        approved_empty_by_deferral,
    )
    from clinical_compiler.adapters.structured_feed import parse_feed
    from clinical_compiler.core.ir import CanonicalClinicalIR
    from clinical_compiler.linter.conformance import lint_conformance
    from clinical_compiler.passes.admissibility import run_admissibility
    from clinical_compiler.passes.document_selection import (
        NURSING_RECORD_TELEGRAPHIC,
        run_document_selection,
    )
    from clinical_compiler.passes.input_validation import run_input_validation
    from clinical_compiler.passes.semantic_normalization import (
        run_semantic_normalization,
    )
    from clinical_compiler.renderers.deterministic import render_document

    def _fail(stage: str, diagnostics: object) -> None:
        raise RuntimeError(
            f"golden scenario is not clean at {stage}: {diagnostics}"
        )

    feed = parse_feed(data)
    if feed.diagnostic is not None:
        _fail("parse_feed", feed.diagnostic)
    accepted = tuple(
        evaluation.fact
        for evaluation in feed.records
        if evaluation.diagnostic is None and evaluation.fact is not None
    )
    if len(accepted) != len(feed.records):
        _fail("parse_feed", feed.records)

    policy = approved_empty_by_deferral(DEFERRED_BY_OWNER_DECISION)
    validated = run_input_validation(
        tuple(wrapper.fact for wrapper in accepted)
    )
    if validated.diagnostics:
        _fail("input_validation", validated.diagnostics)
    normalized = run_semantic_normalization(validated.admitted)
    if normalized.diagnostics:
        _fail("semantic_normalization", normalized.diagnostics)
    source_ids = frozenset(fact.fact_id for fact in validated.admitted)
    admissible = run_admissibility(
        normalized.admitted, policy.terms, source_ids
    )
    if admissible.diagnostics:
        _fail("admissibility", admissible.diagnostics)

    ir = CanonicalClinicalIR(facts=admissible.admitted)
    selected = run_document_selection(ir, NURSING_RECORD_TELEGRAPHIC)
    if selected.diagnostics or not selected.admitted:
        _fail("document_selection", selected.diagnostics)
    rendered = render_document(selected.admitted[0], ir)
    if rendered.diagnostics or not rendered.admitted:
        _fail("render_document", rendered.diagnostics)
    linted = lint_conformance(rendered.admitted[0], NURSING_RECORD_TELEGRAPHIC)
    if linted.diagnostics or not linted.admitted:
        _fail("lint_conformance", linted.diagnostics)
    return linted.admitted[0]


# --- Corpus verification -------------------------------------------------


@dataclass(frozen=True)
class ScenarioVerification:
    """Verification outcome for one golden scenario.

    Attributes:
        name: Scenario name from the manifest.
        problems: Every detected fault, in fixed check order (input
            present → input digest → document present → document
            digest → recompile equality); empty iff verified.
    """

    name: str
    problems: tuple[str, ...]

    @property
    def ok(self) -> bool:
        """Whether the scenario verified with zero problems."""
        return not self.problems


def load_manifest(root: Path) -> dict[str, Any]:
    """Load the golden manifest under ``root`` (fails closed if absent)."""
    path = root / MANIFEST_PATH.name
    if not path.is_file():
        raise FileNotFoundError(f"golden manifest missing: {path}")
    manifest: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise ValueError(f"unknown golden manifest schema: {path}")
    return manifest


def verify_corpus(root: Path) -> tuple[ScenarioVerification, ...]:
    """Verify every manifest scenario against the files on disk.

    Per scenario, in fixed order: the input and document files exist;
    the recorded digests equal the actual file digests; and
    recompiling the committed input through the real chain reproduces
    the committed document bytes exactly (golden regression
    detection).
    """
    manifest = load_manifest(root)
    verifications: list[ScenarioVerification] = []
    for entry in sorted(manifest["scenarios"], key=lambda e: e["name"]):
        name = str(entry["name"])
        problems: list[str] = []

        input_path = root / str(entry["input"])
        document_path = root / str(entry["document"])
        if not input_path.is_file():
            problems.append(f"{name}: input fixture missing: {entry['input']}")
        else:
            if sha256_hex(input_path.read_bytes()) != entry["input_sha256"]:
                problems.append(
                    f"{name}: manifest input digest does not match the "
                    "committed input bytes"
                )
        if not document_path.is_file():
            problems.append(
                f"{name}: golden document missing: {entry['document']}"
            )
        else:
            committed = document_path.read_bytes()
            if sha256_hex(committed) != entry["sha256"]:
                problems.append(
                    f"{name}: manifest digest does not match the "
                    "committed document bytes"
                )
            elif not problems and compile_feed(input_path.read_bytes()) != committed:
                problems.append(
                    f"{name}: recompiling the fixture set no longer "
                    "reproduces the committed golden bytes (output-affecting "
                    "change detected)"
                )
        verifications.append(
            ScenarioVerification(name=name, problems=tuple(problems))
        )
    return tuple(verifications)


@dataclass(frozen=True)
class GoldenEvidenceAssessment:
    """EVIDENCE_INTEGRITY assessment of a golden corpus.

    Attributes:
        corpus_verified: Whether every scenario verified cleanly.
        independent_sample_present: Whether an independent-sample
            manifest exists under ``independent/``.
        overall_integrity: VALID | DEGRADED | INVALID per design #6.
        phase3_gate_blocked: Whether the Phase 3 determinism gate
            blocks on this evidence (INVALID, or DEGRADED pending the
            owner-authored independent sample).
        reason: Human-readable, deterministic assessment reason.
    """

    corpus_verified: bool
    independent_sample_present: bool
    overall_integrity: EvidenceIntegrity
    phase3_gate_blocked: bool
    reason: str


def _independent_problem(root: Path) -> str | None:
    """Self-consistency problem with the independent sample, if any.

    Returns ``None`` when absent or self-consistent. Presence requires
    ``independent/MANIFEST.json`` under ``root``. The committed sample
    manifest is MULTI-SCENARIO (``scenarios[]`` mirroring the golden
    manifest family shape; paths relative to the corpus root):
    self-consistency requires at least one scenario and, per scenario
    in sorted-name order, the referenced document and input files to
    exist and to SHA-256 to their recorded digests. Any other shape is
    a fail-closed self-consistency problem.
    """
    manifest_path = root / INDEPENDENT_MANIFEST_PATH.relative_to(GOLDEN_ROOT)
    if not manifest_path.is_file():
        return None
    sample: dict[str, Any] = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )
    scenarios = sample.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        return "independent sample manifest carries no scenarios"
    for entry in sorted(scenarios, key=lambda e: str(e.get("name", ""))):
        name = str(entry.get("name", "<unnamed>"))
        document_path = root / str(entry.get("document", ""))
        if not document_path.is_file():
            return f"independent sample document missing for scenario {name}"
        if sha256_hex(document_path.read_bytes()) != entry.get("sha256"):
            return (
                "independent sample manifest digest does not match its "
                f"document bytes for scenario {name}"
            )
        input_path = root / str(entry.get("input", ""))
        if not input_path.is_file():
            return f"independent sample input missing for scenario {name}"
        if sha256_hex(input_path.read_bytes()) != entry.get("input_sha256"):
            return (
                "independent sample manifest input digest does not match "
                f"the committed input bytes for scenario {name}"
            )
    return None


def assess_golden_evidence(root: Path) -> GoldenEvidenceAssessment:
    """Classify a golden corpus per design Mechanism #6.

    INVALID if any verification fails (corpus drift or a
    self-inconsistent independent sample); VALID if the corpus is
    verified AND a self-consistent independent sample is present;
    otherwise DEGRADED — implementation-generated goldens only, the
    Phase 3 gate BLOCKS pending owner input.
    """
    verifications = verify_corpus(root)
    corpus_verified = all(verification.ok for verification in verifications)
    present = (
        root / INDEPENDENT_MANIFEST_PATH.relative_to(GOLDEN_ROOT)
    ).is_file()
    problem = _independent_problem(root)

    if not corpus_verified:
        count = sum(
            len(verification.problems) for verification in verifications
        )
        return GoldenEvidenceAssessment(
            corpus_verified=False,
            independent_sample_present=present,
            overall_integrity=EvidenceIntegrity.INVALID,
            phase3_gate_blocked=True,
            reason=(
                f"golden corpus verification failed with {count} "
                "problem(s) — evidence is INVALID until the corpus and "
                "its manifest agree"
            ),
        )
    if problem is not None:
        return GoldenEvidenceAssessment(
            corpus_verified=True,
            independent_sample_present=True,
            overall_integrity=EvidenceIntegrity.INVALID,
            phase3_gate_blocked=True,
            reason=f"golden evidence is INVALID: {problem}",
        )
    if present:
        return GoldenEvidenceAssessment(
            corpus_verified=True,
            independent_sample_present=True,
            overall_integrity=EvidenceIntegrity.VALID,
            phase3_gate_blocked=False,
            reason=(
                "corpus verified and an independently authored expected "
                "sample is present — golden evidence is VALID"
            ),
        )
    return GoldenEvidenceAssessment(
        corpus_verified=True,
        independent_sample_present=False,
        overall_integrity=EvidenceIntegrity.DEGRADED,
        phase3_gate_blocked=True,
        reason=(
            "no independently authored expected sample under "
            "tests/golden/independent/ (design Determinism Mechanism "
            "#6): implementation-generated goldens are DEGRADED "
            "evidence and the Phase 3 determinism gate BLOCKS pending "
            "owner input"
        ),
    )


# --- Corpus generation (manual act — review the diff) ---------------------


def generate_corpus() -> dict[str, Any]:
    """(Re)generate the golden documents + manifest from the inputs.

    Manual, one-time/explicit act (never run by the test suite): reads
    every committed ``scenarios/*.input.jsonl`` fixture, compiles it
    through the real chain, writes the ``*.document.txt`` golden and
    the canonical ``manifest.json`` with the implementation-generated
    ``DEGRADED`` labels and the pending independent-sample slot.
    Regenerating produces a reviewable diff — a changed digest is a
    frozen-vocabulary change, never silently accepted.
    """
    SCENARIO_DIR.mkdir(parents=True, exist_ok=True)
    scenarios: list[dict[str, Any]] = []
    for input_path in sorted(SCENARIO_DIR.glob("*.input.jsonl")):
        name = input_path.name[: -len(".input.jsonl")]
        document = compile_feed(input_path.read_bytes())
        document_path = input_path.with_name(f"{name}.document.txt")
        document_path.write_bytes(document)
        scenarios.append(
            {
                "name": name,
                "input": f"scenarios/{input_path.name}",
                "input_sha256": sha256_hex(input_path.read_bytes()),
                "document": f"scenarios/{document_path.name}",
                "sha256": sha256_hex(document),
                "evidence_integrity": EvidenceIntegrity.DEGRADED.value,
                "provenance": (
                    "implementation-generated: produced by running the "
                    "real chain over the committed input (design "
                    "Mechanism #6: implementation-only goldens are "
                    "DEGRADED evidence)"
                ),
            }
        )
    manifest: dict[str, Any] = {
        "schema": MANIFEST_SCHEMA,
        "evidence_integrity_vocabulary": list(
            EVIDENCE_INTEGRITY_VOCABULARY
        ),
        "scenarios": scenarios,
        "independent_sample": {
            "status": (
                "PRESENT"
                if INDEPENDENT_MANIFEST_PATH.is_file()
                else "PENDING_OWNER_AUTHORSHIP"
            ),
            "required_path": "independent/",
            "manifest": "independent/MANIFEST.json",
            "expected_schema": "clinical-compiler-r1/independent-sample/1",
            "rule": (
                "Authored ONLY by the decision owner or an "
                "owner-designated audit path (design Determinism "
                "Mechanism #6 / task 3.7). The executor NEVER authors "
                "it. Absence keeps this corpus at "
                "EVIDENCE_INTEGRITY=DEGRADED and BLOCKS the Phase 3 "
                "determinism gate pending owner input."
            ),
        },
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main(argv: list[str]) -> int:
    """CLI: ``digest <input>`` | ``verify`` | ``generate``."""
    if len(argv) == 3 and argv[1] == "digest":
        document = compile_feed(Path(argv[2]).read_bytes())
        print(sha256_hex(document))
        return 0
    if len(argv) == 2 and argv[1] == "verify":
        assessment = assess_golden_evidence(GOLDEN_ROOT)
        print(f"corpus_verified={assessment.corpus_verified}")
        print(f"independent_sample_present={assessment.independent_sample_present}")
        print(f"overall_integrity={assessment.overall_integrity.value}")
        print(f"phase3_gate_blocked={assessment.phase3_gate_blocked}")
        print(f"reason={assessment.reason}")
        return 0 if not assessment.phase3_gate_blocked else 1
    if len(argv) == 2 and argv[1] == "generate":
        manifest = generate_corpus()
        print(f"generated {len(manifest['scenarios'])} golden scenario(s)")
        return 0
    print(
        "usage: golden_machinery.py digest <input.jsonl> | verify | generate",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
