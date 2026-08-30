# CLI exit-code sweep — FULL_ANTIDRIFT re-verification (target 7d089513)

All cases run through `clinical-compiler compile` (fresh `uv run --no-sync` interpreter per
case) against the committed tree at `7d0895133d0ca74a889e3f3270f3a4b9f497f4cd`.
Full raw transcript: `battery/12-exit70-sweep.log`. Result: **27/27 mapped, ZERO exit 70.**

## Defect reproductions (Phase A)

| Case | Input (shape) | Exit | stderr (first diagnostic) | stdout |
|---|---|---|---|---|
| P0-1 value LF injection | `raw_value` = `"120/80 [present] [monitor injected]\nFC: 999"` (JSON-escaped — one physical JSONL line) | 9 | `RENDER_ERROR: … carries a value of type 'str' that contains a line break … (P0-1)` | EMPTY — no fabricated `FC: 999` line |
| P0-1 value CR injection | `\r` inside `raw_value` | 9 | `RENDER_ERROR: … contains a line break …` | EMPTY |
| P0-1 source_ref LF injection | `\n` inside `provenance.source_ref` | 9 | `RENDER_ERROR: … carries a source_ref containing a line break … (P0-1)` | EMPTY |
| P0-1 source_ref CR injection | `\r` inside `provenance.source_ref` | 9 | `RENDER_ERROR: … source_ref containing a line break …` | EMPTY |
| P0-2 declared certainties | two corroborating FC facts with `source_asserted_certainty` = `confirmed` / `probable` | 0 | (none) | document rendered; at the `run()` boundary `CompileResult.source_asserted_certainties == (("p02-a", CONFIRMED), ("p02-b", PROBABLE))`, canonical `ClinicalValue.certainty` stays `UNRESOLVED` (verified in-process, fresh interpreter) |
| P0-3 seed `{"terms": []}` | `--policy-seed` zero-term JSON | 2 | `UNRESOLVED_POLICY: … carries no terms — the empty veto set is only ever an APPROVED-BY-DEFERRAL state …` | EMPTY |
| P1-1 `fact_id: ""` | empty identifier | 3 | `INPUT_CONTRACT_ERROR: fact_id must be a non-empty string` | EMPTY |
| P1-1 `source_ref: ""` | empty identifier | 3 | `INPUT_CONTRACT_ERROR: source_ref must be a non-empty string` | EMPTY |

P0-3 API invariants (fresh interpreter, in-process): `populated_policy(frozenset())` raises
`ValueError`; direct `PolicyResolution(POPULATED, frozenset(), …)` raises; `approved_empty_by_deferral`
without a `DEFERRED_BY_OWNER` citation raises; only the cited deferral yields a resolved-empty
policy; `load_policy_seed` zero-term → `UNRESOLVED_POLICY` with typed fault `EMPTY_TERMS`.
P1-1 invariant: the rejected record never yields a fact — nothing invalid reaches
`CanonicalClinicalIR` (quarantined at the adapter AND re-checked in `input_validation`).

## Full invalid-input family sweep (battery item 12)

| Case | Expected | Actual |
|---|---|---|
| empty fact_id | 3 | 3 OK |
| empty source_ref | 3 | 3 OK |
| bad certainty name (`"definitely"`) | 3 | 3 OK |
| field_id outside contract (`ZZ`) | 3 | 3 OK |
| source_kind outside vocabulary (`psychic`) | 3 | 3 OK |
| missing required key | 3 | 3 OK |
| unknown key | 3 | 3 OK |
| bad UTF-8 feed | 3 | 3 OK |
| invalid JSONL line | 3 | 3 OK |
| bool raw_value on numeric field FC | 4 | 4 OK |
| str raw_value on numeric field FC | 4 | 4 OK |
| seed `terms: []` | 2 | 2 OK |
| seed empty-string term | 2 | 2 OK |
| seed non-string term | 2 | 2 OK |
| seed wrong shape | 2 | 2 OK |
| seed malformed JSON | 2 | 2 OK |
| seed `terms` not a list | 2 | 2 OK |
| seed file missing | 2 | 2 OK |
| input file missing | 2 | 2 OK |
| no arguments | 2 | 2 OK |
| unknown subcommand | 2 | 2 OK |
| unknown `--mode` | 2 | 2 OK |
| injection: value LF | 9 | 9 OK |
| injection: source_ref LF | 9 | 9 OK |
| veto hit (populated seed, value contains term) | 6 | 6 OK |
| valid run | 0 | 0 OK |
| valid run, absent `--policy-seed` flag (deferral path) | 0 | 0 OK |

**Exit-70 count: 0.** Sweep overall exit: 0.

## Determinism byte-compare (battery item 5)

| Case | PYTHONHASHSEED | exit | stdout |
|---|---|---|---|
| valid-baseline | 0 / 12345 / random | 0 / 0 / 0 | BYTE-IDENTICAL (`cmp`), sha256 `62aac281…` |
| declared-certainty pair (p02-both) | 0 / 12345 / random | 0 / 0 / 0 | BYTE-IDENTICAL (`cmp`), sha256 `55eb0bfa…` |
| golden standard_mixed via CLI | 0 / 12345 / random | 0 / 0 / 0 | BYTE-IDENTICAL (`cmp`), sha256 `e7b5b03f…` (== committed golden digest) |

stderr byte-identical in every triple as well (battery/05 log records the `cmp` checks).
