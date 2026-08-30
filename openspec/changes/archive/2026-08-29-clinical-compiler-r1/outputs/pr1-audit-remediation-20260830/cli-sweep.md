# CLI exit-code sweep — AUDIT REMEDIATION run (2026-08-30, worktree of cec43d3)

All cases run through `clinical-compiler compile` (fresh `uv run --no-sync` interpreter per
case) in the detached worktree of `cec43d39212b46b105dae318e6e5ca96627285b3` with the two
remediation fixes in the working tree. Full raw transcript:
`battery/12-exit70-sweep.log`. Result: **29/29 mapped (27 prior + 2 new), stdout EMPTY on
every fault, ZERO exit 70.**

## The two new audit-defect cases (extended sweep)

| Case | Input (shape) | Exit | stderr (first diagnostic) | stdout |
|---|---|---|---|---|
| ws-only `source_ref` (NEW) | `provenance.source_ref = "  "` (whitespace-only — passes the frozen contract's non-empty check) | **10** | `LINT_FAILURE: line 2: provenance source_ref is empty or whitespace-only — an assessed line …` | EMPTY |
| U+2028 value (NEW) | `raw_value = "72\u2028FC: 999"` (JSON escape — one physical JSONL line) | **9** | `RENDER_ERROR: canonical fact 'TA:…' … contains canonical-breaking character U+2028 — no canonical single-line rendering …` | EMPTY — no fabricated `FC: 999` line |

### Reachability note (honest scoping of the linter fix)

- The **empty-ref** form (`""`) is rejected at the frozen input contract (exit 3,
  `INPUT_CONTRACT_ERROR: source_ref must be a non-empty string`) — the linter's new empty-ref
  rule remains **defense-in-depth** for that form, exercised by hand-injected bytes in
  `tests/unit/test_linter_conformance.py` (unreachable from real CLI input, by design).
- The **whitespace-only** form (`" "`) passes the contract (non-empty string) and previously
  reached the rendered document verbatim — with this remediation it is now **reachable
  end-to-end** and fails closed at the lint stage (exit 10, no document). The frozen contract
  was deliberately NOT narrowed to reject whitespace (owner-decision territory, same principle
  as the recorded decision not to narrow the contract for `\n` in the prior addendum).

## Prior invalid-input family (27 cases) — re-confirmed at this tree

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

**Exit-70 count: 0.** Sweep overall exit: 0. Every non-zero case also verified to leave
stdout EMPTY (document/diagnostics non-coexistence at the CLI boundary).

## Determinism byte-compare (battery item 5, this run)

| Case | PYTHONHASHSEED | exit | stdout |
|---|---|---|---|
| valid-baseline | 0 / 12345 / random | 0 / 0 / 0 | BYTE-IDENTICAL (`cmp`), sha256 `62aac281…`, 59 bytes |
| declared-certainty pair (p02-both) | 0 / 12345 / random | 0 / 0 / 0 | BYTE-IDENTICAL (`cmp`), sha256 `55eb0bfa…`, 60 bytes |
| golden standard_mixed via CLI | 0 / 12345 / random | 0 / 0 / 0 | BYTE-IDENTICAL (`cmp`), sha256 `e7b5b03f…` == committed golden document bytes (cmp vs `tests/golden/scenarios/standard_mixed.document.txt`: IDENTICAL) |

stderr byte-identical in every triple as well (`battery/05-determinism-hashseed.log`).
The golden corpus is plain printable ASCII — the renderer's new frozen charset never
triggers on it, so golden bytes are unchanged (battery item 4: all scenario digests MATCH
the committed documents and manifest under plain / seeded / `python -I` invocation).
