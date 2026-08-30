"""Tests for the Phase-4 composition root (tasks 4.1 — APPROVAL-PHASE4
Unit 1): ``pipeline.run`` / ``CompileRequest`` / ``CompileResult`` /
``derive_exit_code`` and the ``StageResult`` re-export.

The composition must reproduce EXACTLY the chain semantics pinned by the
Phase-2/3 helper tests (``test_integration_phase2_chain.py`` /
``test_integration_phase3_chain.py``) and the golden machinery
(``tests/golden/golden_machinery.py`` ``compile_feed``): every stage runs
on the survivors of the previous stage, diagnostics accumulate, and the
whole-run emission gate admits a document IFF the accumulated set is
empty (design D1). The D7 carried flag is pinned here at production
level: an UNRESOLVED policy runs NO admissibility (spy) and yields no
document — never a silent empty-veto-set continue.

``derive_exit_code`` is tested as the frozen pure total function of the
diagnostic SET (design Exit-Code Table): min stage-order code among
3–10 present, 0 iff empty — NOT ``DiagnosticCode`` declaration order
(``PROVENANCE_ERROR`` is declared last yet ranks 7). Exit 2 (usage) and
70 (unexpected exception) are CLI-boundary mappings, outside this
function's diagnostic-set domain (design M2.1).

Golden expectations follow the implementation corpus committed at task
3.7 (glyph-vocabulary freeze); a re-freeze under an owner-recorded
decision is expected to break the byte assertions and require
re-verification — never silently accepted.
"""

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Final

import pytest

from clinical_compiler import pipeline
from clinical_compiler.adapters.seed import (
    DEFERRED_BY_OWNER_DECISION,
    PolicyResolution,
    PolicyResolutionState,
    PolicySeedFault,
    approved_empty_by_deferral,
    load_policy_seed,
)
from clinical_compiler.core.diagnostics import Diagnostic, DiagnosticCode
from clinical_compiler.core.types import Certainty
from clinical_compiler.linter.conformance import (
    lint_conformance as real_lint_conformance,
)
from clinical_compiler.passes.document_selection import (
    NURSING_RECORD_TELEGRAPHIC,
)
from clinical_compiler.pipeline import (
    CompileRequest,
    CompileResult,
    StageResult,
    derive_exit_code,
    run,
)
from clinical_compiler.pipeline_types import StageResult as LeafStageResult
from clinical_compiler.renderers.deterministic import (
    render_document as real_render_document,
)

pytestmark = pytest.mark.integration

VALID_RECORD: dict[str, object] = {
    "fact_id": "raw-1",
    "field_id": "FC",
    "raw_value": 72,
    "provenance": {"source_kind": "monitor", "source_ref": "m-9"},
}

_GOLDEN_ROOT: Final[Path] = Path(__file__).resolve().parents[1] / "golden"

_SEED_FIXTURE: Final[Path] = (
    Path(__file__).resolve().parents[1] / "fixtures" / "policy-seed-sample.json"
)

_MACHINERY_PATH: Final[Path] = _GOLDEN_ROOT / "golden_machinery.py"


def _record(**overrides: object) -> dict[str, object]:
    """Build a contract-conformant FC record with the given overrides."""
    record = dict(VALID_RECORD)
    record.update(overrides)
    return record


def _record_missing(key: str) -> dict[str, object]:
    """Build an FC record LACKING one required key (FC-01)."""
    record = dict(VALID_RECORD)
    del record[key]
    return record


def _line(record: object) -> str:
    """Encode one record as a JSONL line."""
    return json.dumps(record)


def _feed(*lines: str) -> bytes:
    """Encode the given lines as feed bytes."""
    return "\n".join(lines).encode("utf-8")


def _deferred_empty_policy() -> PolicyResolution:
    """Build the approved-empty veto set citing the durable deferral."""
    return approved_empty_by_deferral(DEFERRED_BY_OWNER_DECISION)


def _request(data: bytes, policy: PolicyResolution | None = None) -> CompileRequest:
    """Build a compile request for the R1 mode over the given bytes."""
    return CompileRequest(
        data=data,
        document_mode=NURSING_RECORD_TELEGRAPHIC,
        policy=_deferred_empty_policy() if policy is None else policy,
    )


def _load_machinery() -> ModuleType:
    """Load ``golden_machinery.py`` by file path (the task-3.8 pattern)."""
    spec = importlib.util.spec_from_file_location("golden_machinery", _MACHINERY_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _golden_scenarios() -> tuple[tuple[str, bytes, bytes], ...]:
    """The committed golden scenarios: (name, input bytes, document bytes)."""
    manifest = json.loads((_GOLDEN_ROOT / "manifest.json").read_text(encoding="utf-8"))
    return tuple(
        (
            str(entry["name"]),
            (_GOLDEN_ROOT / str(entry["input"])).read_bytes(),
            (_GOLDEN_ROOT / str(entry["document"])).read_bytes(),
        )
        for entry in sorted(manifest["scenarios"], key=lambda e: e["name"])
    )


# --- 1. Happy path --------------------------------------------------------


def test_happy_path_emits_document_with_empty_diagnostics_and_exit_zero() -> None:
    """Valid FC+TA feed: lint-clean bytes, (), and exit code 0."""
    data = _feed(
        _line(_record(fact_id="std-fc-1", raw_value=80.5)),
        _line(
            _record(
                fact_id="std-ta-1",
                field_id="TA",
                raw_value="120/80",
            )
        ),
    )
    result = run(_request(data))

    assert result.diagnostics == ()
    assert result.policy.is_resolved
    assert result.document is not None
    assert result.document.decode("utf-8").splitlines() == [
        "FC: 80.5 [present] [monitor m-9]",
        "TA: 120/80 [present] [monitor m-9]",
    ]
    assert derive_exit_code(result.diagnostics) == 0


def test_two_identical_runs_produce_identical_results() -> None:
    """Determinism: identical request → identical CompileResult, twice."""
    data = _feed(
        _line(_record(fact_id="raw-fc", raw_value=72)),
        _line(_record(fact_id="raw-ta", field_id="TA", raw_value="120/80")),
    )
    first = run(_request(data))
    second = run(_request(data))
    assert first == second
    assert first.document is not None and second.document is not None
    assert first.document == second.document


def test_accept_r1_001_reversed_feeds_render_identical_documents() -> None:
    """ACCEPT-R1-001: exact A/B feeds differ only in record order."""
    monitor = _record(
        fact_id="accept-r1-001-monitor",
        raw_value=72,
        provenance={"source_kind": "monitor", "source_ref": "monitor-primary"},
    )
    lab = _record(
        fact_id="accept-r1-001-lab",
        raw_value=72,
        provenance={"source_kind": "lab", "source_ref": "lab-corroborating"},
    )
    feed_a = _feed(_line(monitor), _line(lab))
    feed_b = _feed(_line(lab), _line(monitor))

    result_a = run(_request(feed_a))
    result_b = run(_request(feed_b))

    assert result_a.diagnostics == result_b.diagnostics == ()
    assert result_a.document is not None and result_b.document is not None
    assert result_a.document == result_b.document
    assert derive_exit_code(result_a.diagnostics) == derive_exit_code(
        result_b.diagnostics
    ) == 0


# --- 2. Golden equivalence: the production composition IS the chain -------


@pytest.mark.parametrize("scenario", [scenario[0] for scenario in _golden_scenarios()])
def test_pipeline_reproduces_golden_machinery_and_committed_bytes(
    scenario: str,
) -> None:
    """Every golden scenario: pipeline bytes == machinery bytes == corpus."""
    scenarios = {name: (data, doc) for name, data, doc in _golden_scenarios()}
    data, committed = scenarios[scenario]
    machinery = _load_machinery()
    compile_feed = machinery.compile_feed

    result = run(_request(data))

    assert result.diagnostics == ()
    assert result.document is not None
    assert result.document == committed
    assert result.document == compile_feed(data)
    assert derive_exit_code(result.diagnostics) == 0


# --- 3. Fault corpus end to end: emission gate + family exit codes --------


@pytest.mark.parametrize(
    ("label", "data", "policy", "expected_code", "expected_exit"),
    [
        (
            "FC-01 missing required key",
            _feed(_line(_record_missing("field_id"))),
            None,
            DiagnosticCode.INPUT_CONTRACT_ERROR,
            3,
        ),
        (
            "FC-02 unknown key",
            _feed(_line(_record(x_priority="high"))),
            None,
            DiagnosticCode.INPUT_CONTRACT_ERROR,
            3,
        ),
        (
            "FC-03 top-level JSON array",
            _feed(_line([dict(VALID_RECORD)])),
            None,
            DiagnosticCode.INPUT_CONTRACT_ERROR,
            3,
        ),
        (
            "FC-03 undecodable bytes",
            b"\xff\xfe not utf-8",
            None,
            DiagnosticCode.INPUT_CONTRACT_ERROR,
            3,
        ),
        (
            "FC-05 bool raw_value for numeric FC",
            _feed(_line(_record(raw_value=True))),
            None,
            DiagnosticCode.TYPE_ERROR,
            4,
        ),
        (
            "FC-06 conflicting equal-authority FC readings",
            _feed(
                _line(_record(fact_id="fc-a", raw_value=72)),
                _line(_record(fact_id="fc-b", raw_value=80)),
            ),
            None,
            DiagnosticCode.SEMANTIC_AMBIGUITY_BLOCK,
            5,
        ),
        (
            "FC-07 vetoed term under the owner seed",
            _feed(
                _line(
                    _record(
                        fact_id="ta-vetoed",
                        field_id="TA",
                        raw_value="TA: test-veto-term-alpha de noche",
                    )
                ),
            ),
            load_policy_seed(_SEED_FIXTURE),
            DiagnosticCode.POLICY_VIOLATION,
            6,
        ),
        (
            "FC-09 empty feed — selection fails closed",
            b"",
            None,
            DiagnosticCode.DOCUMENT_SELECTION_ERROR,
            8,
        ),
        (
            "P1-1 empty fact_id — mapped input fault, never an IR exception",
            _feed(_line(_record(fact_id=""))),
            None,
            DiagnosticCode.INPUT_CONTRACT_ERROR,
            3,
        ),
        (
            "P1-1 empty source_ref — mapped input fault",
            _feed(
                _line(_record(provenance={"source_kind": "monitor", "source_ref": ""}))
            ),
            None,
            DiagnosticCode.INPUT_CONTRACT_ERROR,
            3,
        ),
    ],
)
def test_any_diagnostic_yields_no_document_and_the_family_exit_code(
    label: str,
    data: bytes,
    policy: PolicyResolution | None,
    expected_code: DiagnosticCode,
    expected_exit: int,
) -> None:
    """One blocked fact blocks the whole run: no bytes, family code out."""
    result = run(_request(data, policy))

    codes = tuple(diagnostic.code for diagnostic in result.diagnostics)
    assert result.document is None, label
    assert expected_code in codes, label
    assert derive_exit_code(result.diagnostics) == expected_exit


def test_contract_valid_multiline_value_cannot_inject_second_clinical_line() -> None:
    """P0-1 (injection closure, fail-closed): a contract-VALID TA value
    containing a line break must never emit a second clinical line that
    borrows the document's line grammar and another fact's provenance.
    The renderer refuses the verbatim value (RENDER_ERROR) and the run
    emits NO document — so no fabricated ``FC: 200`` line can exist
    anywhere in the output (the injected line resolves to no source
    fact; provenance traceability spec)."""
    result = run(
        _request(
            _feed(
                _line(
                    _record(
                        fact_id="ta-multi",
                        field_id="TA",
                        raw_value="72 [present]\nFC: 200",
                    )
                )
            )
        )
    )

    assert result.document is None
    assert DiagnosticCode.RENDER_ERROR in tuple(
        diagnostic.code for diagnostic in result.diagnostics
    )


# --- 3b. P0-2: declared-certainty traceability at the run() boundary ----------


def test_source_asserted_certainty_is_traceable_across_the_run() -> None:
    """P0-2: a source-declared certainty survives the whole run, per
    SOURCE fact, observable on the result — declared CONFIRMED /
    PROBABLE in, the same values out, codepoint-sorted by fact id,
    never merged and never dropped (input-contract spec: the declared
    certainty is never silently dropped)."""
    result = run(
        _request(
            _feed(
                _line(
                    _record(
                        fact_id="raw-ta-1",
                        field_id="TA",
                        raw_value="120/80",
                        source_asserted_certainty="confirmed",
                    )
                ),
                _line(
                    _record(
                        fact_id="raw-fc-1",
                        raw_value=72,
                        source_asserted_certainty="probable",
                    )
                ),
            )
        )
    )

    assert result.document is not None
    assert result.source_asserted_certainties == (
        ("raw-fc-1", Certainty.PROBABLE),
        ("raw-ta-1", Certainty.CONFIRMED),
    )


def test_undeclared_facts_contribute_no_certainty_entry() -> None:
    """P0-2: the slot is never invented — a fact without a declaration
    contributes nothing to the traceability exposure."""
    result = run(_request(_feed(_line(_record(fact_id="raw-1")))))

    assert result.document is not None
    assert result.source_asserted_certainties == ()


def test_corroborating_facts_keep_their_own_declarations() -> None:
    """P0-2: declarations are per SOURCE fact — even when two facts
    corroborate into ONE canonical fact, their declarations stay
    distinct entries on the traceability axis (never merged)."""
    result = run(
        _request(
            _feed(
                _line(
                    _record(
                        fact_id="raw-a",
                        raw_value=72,
                        source_asserted_certainty="confirmed",
                    )
                ),
                _line(
                    _record(
                        fact_id="raw-b",
                        raw_value=72.0,
                        source_asserted_certainty="probable",
                    )
                ),
            )
        )
    )

    assert result.document is not None
    assert result.source_asserted_certainties == (
        ("raw-a", Certainty.CONFIRMED),
        ("raw-b", Certainty.PROBABLE),
    )


def test_both_certainty_authorities_stay_distinct_at_the_run_boundary() -> None:
    """P0-2 / CRC-001+002: the two certainty axes never merge — the
    source's declaration is observable per fact in
    ``source_asserted_certainties`` while the compiler-assigned axis
    is untouched (every ``ClinicalValue.certainty`` stays UNRESOLVED,
    pinned at the normalizer unit; observably here: no certainty word
    ever reaches the rendered document)."""
    result = run(
        _request(
            _feed(
                _line(
                    _record(
                        fact_id="raw-fc-1",
                        raw_value=72,
                        source_asserted_certainty="confirmed",
                    )
                )
            )
        )
    )

    assert result.source_asserted_certainties == (("raw-fc-1", Certainty.CONFIRMED),)
    assert result.document is not None
    assert b"confirmed" not in result.document


# --- 4. Min-precedence across stages (earliest fault explains the rest) ---


def test_mixed_feed_enumerates_every_quarantine_and_takes_the_minimum() -> None:
    """TYPE_ERROR record + conflicting FC pair: every diagnostic is
    enumerated (no silent omission) and the exit code is the minimum
    stage-order code (4 beats 5), NOT the encounter order."""
    data = _feed(
        _line(_record(fact_id="bad-type", raw_value=True)),
        _line(_record(fact_id="fc-a", raw_value=72)),
        _line(_record(fact_id="fc-b", raw_value=80)),
    )
    result = run(_request(data))

    codes = tuple(diagnostic.code for diagnostic in result.diagnostics)
    assert codes.count(DiagnosticCode.TYPE_ERROR) == 1
    assert codes.count(DiagnosticCode.SEMANTIC_AMBIGUITY_BLOCK) == 2
    assert result.document is None
    assert derive_exit_code(result.diagnostics) == 4


def test_blocked_upstream_fact_is_never_consumed_downstream() -> None:
    """FC-02 record + one clean FC record: the clean fact survives every
    stage but the whole-run gate still refuses the document; the only
    diagnostic is the quarantined record's (no double reporting, no
    silent omission either way)."""
    data = _feed(
        _line(_record(fact_id="raw-bad", x_priority="high")),
        _line(_record(fact_id="raw-ok", raw_value=72)),
    )
    result = run(_request(data))

    assert result.document is None
    assert tuple(d.code for d in result.diagnostics) == (
        DiagnosticCode.INPUT_CONTRACT_ERROR,
    )
    assert derive_exit_code(result.diagnostics) == 3


def test_empty_survivors_surface_both_upstream_and_selection_faults() -> None:
    """A feed whose ONLY record is invalid: the upstream code (3) wins
    over the selection code (8) — min stage-order precedence across
    stages on one real run."""
    result = run(_request(_feed(_line(_record(x_priority="high")))))

    codes = frozenset(d.code for d in result.diagnostics)
    assert codes == {
        DiagnosticCode.INPUT_CONTRACT_ERROR,
        DiagnosticCode.DOCUMENT_SELECTION_ERROR,
    }
    assert result.document is None
    assert derive_exit_code(result.diagnostics) == 3


# --- 5. The D7 carried flag: unresolved policy blocks the gate ------------


def test_unresolved_policy_runs_no_admissibility_and_blocks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing seed: the production composition runs NO admissibility
    (spy), so no selection/render/lint either (diagnostics stay empty),
    and yields an explicit blocked outcome — never
    empty-set-and-continue."""
    calls: list[tuple[object, ...]] = []

    def _spy(*args: object) -> object:
        calls.append(args)
        raise AssertionError("admissibility must not run on unresolved policy")

    monkeypatch.setattr(pipeline, "run_admissibility", _spy)
    policy = load_policy_seed(_SEED_FIXTURE.parent / "no-such-seed.json")
    assert policy.state is PolicyResolutionState.UNRESOLVED_POLICY
    assert policy.fault is PolicySeedFault.MISSING_FILE

    result = run(_request(_feed(_line(_record(fact_id="raw-1"))), policy))

    assert calls == []
    assert result.document is None
    assert result.diagnostics == ()
    assert result.policy.is_resolved is False
    assert result.policy.state is PolicyResolutionState.UNRESOLVED_POLICY


def test_blocked_empty_outcome_is_unrepresentable_for_a_resolved_policy() -> None:
    """A resolved policy with no document and no diagnostics is the
    silent-empty-success D7 forbids: CompileResult refuses to hold it."""
    with pytest.raises(ValueError):
        CompileResult(
            document=None,
            diagnostics=(),
            policy=_deferred_empty_policy(),
        )


def test_document_with_diagnostics_is_unrepresentable() -> None:
    """Fail-closed emission: a result carrying both bytes and
    diagnostics can never be constructed."""
    with pytest.raises(ValueError):
        CompileResult(
            document=b"FC: 72 [present] [monitor m-9]\n",
            diagnostics=(Diagnostic(DiagnosticCode.INPUT_CONTRACT_ERROR, "x"),),
            policy=_deferred_empty_policy(),
        )


# --- 6. derive_exit_code — the frozen pure total function -----------------


@pytest.mark.parametrize(
    ("code", "expected_exit"),
    [
        (DiagnosticCode.INPUT_CONTRACT_ERROR, 3),
        (DiagnosticCode.TYPE_ERROR, 4),
        (DiagnosticCode.SEMANTIC_AMBIGUITY_BLOCK, 5),
        (DiagnosticCode.POLICY_VIOLATION, 6),
        (DiagnosticCode.PROVENANCE_ERROR, 7),
        (DiagnosticCode.DOCUMENT_SELECTION_ERROR, 8),
        (DiagnosticCode.RENDER_ERROR, 9),
        (DiagnosticCode.LINT_FAILURE, 10),
    ],
)
def test_each_diagnostic_family_maps_to_its_frozen_code(
    code: DiagnosticCode, expected_exit: int
) -> None:
    """Total over the 8-code taxonomy — including PROVENANCE_ERROR (7),
    declared LAST in the enum yet ranked by STAGE order, and the
    defense-in-depth RENDER/LINT codes unreachable from clean bytes."""
    assert derive_exit_code((Diagnostic(code, "message"),)) == expected_exit


def test_empty_diagnostic_set_maps_to_zero() -> None:
    """0 iff the diagnostic set is empty."""
    assert derive_exit_code(()) == 0


def test_min_stage_order_code_wins_regardless_of_encounter_order() -> None:
    """The mapping is a pure function of the SET: order-independent, and
    the minimum stage-order code present wins."""
    first = (
        Diagnostic(DiagnosticCode.LINT_FAILURE, "late"),
        Diagnostic(DiagnosticCode.INPUT_CONTRACT_ERROR, "early"),
    )
    second = (
        Diagnostic(DiagnosticCode.INPUT_CONTRACT_ERROR, "early"),
        Diagnostic(DiagnosticCode.LINT_FAILURE, "late"),
    )
    assert derive_exit_code(first) == 3
    assert derive_exit_code(second) == 3


def test_provenance_ranks_above_selection_despite_enum_declaration() -> None:
    """PROVENANCE_ERROR (declared last) outranks DOCUMENT_SELECTION_ERROR
    (declared fifth): the table is stage order, never enum order."""
    diagnostics = (
        Diagnostic(DiagnosticCode.DOCUMENT_SELECTION_ERROR, "selection"),
        Diagnostic(DiagnosticCode.PROVENANCE_ERROR, "provenance"),
    )
    assert derive_exit_code(diagnostics) == 7


def test_derive_exit_code_is_total_and_deterministic_over_a_mixed_set() -> None:
    """A diagnostic set spanning early and late stages maps once, and
    re-deriving maps identically (identical set → identical code)."""
    diagnostics = (
        Diagnostic(DiagnosticCode.POLICY_VIOLATION, "veto"),
        Diagnostic(DiagnosticCode.SEMANTIC_AMBIGUITY_BLOCK, "conflict"),
        Diagnostic(DiagnosticCode.RENDER_ERROR, "render"),
    )
    assert derive_exit_code(diagnostics) == 5
    assert derive_exit_code(diagnostics) == derive_exit_code(diagnostics)


# --- 7. G-1/D10: the StageResult re-export --------------------------------


def test_stage_result_is_reexported_from_the_leaf_module() -> None:
    """``pipeline.StageResult`` IS ``pipeline_types.StageResult`` — the
    G-1 adjudicated re-export, not a shadowing declaration."""
    assert StageResult is LeafStageResult


def test_blocked_accumulator_never_reaches_render_or_lint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Render/lint are reached ONLY on a clean accumulator: with
    upstream diagnostics present, neither stage ever runs (spy)."""

    def _render_spy(*args: object) -> object:
        raise AssertionError("render must not run on a blocked accumulator")

    def _lint_spy(*args: object) -> object:
        raise AssertionError("lint must not run on a blocked accumulator")

    monkeypatch.setattr(pipeline, "render_document", _render_spy)
    monkeypatch.setattr(pipeline, "lint_conformance", _lint_spy)

    data = _feed(_line(_record(x_priority="high")))
    result = run(_request(data))

    assert result.document is None
    assert result.diagnostics != ()


def test_clean_accumulator_reaches_render_and_lint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mutation sensitivity: on a clean run render and lint ARE invoked
    (spies delegate to the real stages) — removing either call from the
    composition fails this test."""
    real_render = real_render_document
    real_lint = real_lint_conformance
    render_calls: list[object] = []
    lint_calls: list[object] = []

    def _render_spy(*args: object) -> object:
        render_calls.append(args)
        return real_render(*args)  # type: ignore[arg-type]

    def _lint_spy(*args: object) -> object:
        lint_calls.append(args)
        return real_lint(*args)  # type: ignore[arg-type]

    monkeypatch.setattr(pipeline, "render_document", _render_spy)
    monkeypatch.setattr(pipeline, "lint_conformance", _lint_spy)

    data = _feed(
        _line(_record(fact_id="raw-fc", raw_value=72)),
        _line(_record(fact_id="raw-ta", field_id="TA", raw_value="120/80")),
    )
    result = run(_request(data))

    assert len(render_calls) == 1
    assert len(lint_calls) == 1
    assert result.document is not None
    assert result.diagnostics == ()


# --- 8. Defense-in-depth legs: injected render/lint faults (FC-10/FC-11) --


def test_injected_render_fault_blocks_the_run_before_lint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FC-10 at the composition seam: a render stage reporting
    RENDER_ERROR yields no document, no lint call, and exit code 9 —
    the defense-in-depth leg is wired, never silently absorbed."""
    lint_calls: list[object] = []

    def _faulty_render(*args: object) -> object:
        return StageResult(
            admitted=(),
            diagnostics=(Diagnostic(DiagnosticCode.RENDER_ERROR, "injected"),),
        )

    def _lint_spy(*args: object) -> object:
        lint_calls.append(args)
        raise AssertionError("lint must not run after a render fault")

    monkeypatch.setattr(pipeline, "render_document", _faulty_render)
    monkeypatch.setattr(pipeline, "lint_conformance", _lint_spy)

    data = _feed(_line(_record(fact_id="raw-fc", raw_value=72)))
    result = run(_request(data))

    assert result.document is None
    assert tuple(d.code for d in result.diagnostics) == (DiagnosticCode.RENDER_ERROR,)
    assert lint_calls == []
    assert derive_exit_code(result.diagnostics) == 9


def test_injected_lint_failure_blocks_the_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FC-11 at the composition seam: only lint-clean output is accepted
    as final — a lint stage reporting LINT_FAILURE yields no document
    and exit code 10."""
    real_render = real_render_document
    render_calls: list[object] = []

    def _render_spy(*args: object) -> object:
        render_calls.append(args)
        return real_render(*args)  # type: ignore[arg-type]

    def _failing_lint(*args: object) -> object:
        return StageResult(
            admitted=(),
            diagnostics=(Diagnostic(DiagnosticCode.LINT_FAILURE, "injected"),),
        )

    monkeypatch.setattr(pipeline, "render_document", _render_spy)
    monkeypatch.setattr(pipeline, "lint_conformance", _failing_lint)

    data = _feed(_line(_record(fact_id="raw-fc", raw_value=72)))
    result = run(_request(data))

    assert len(render_calls) == 1
    assert result.document is None
    assert tuple(d.code for d in result.diagnostics) == (DiagnosticCode.LINT_FAILURE,)
    assert derive_exit_code(result.diagnostics) == 10
