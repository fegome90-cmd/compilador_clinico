# Phase 3 Close — Gate 3.9 Report (change: clinical-compiler-r1)

Executor: sdd-apply Unit 6 (PHASE_3 CLOSE), closed by the bounded
residuals unit (R-3.9a + R-3.9b + gate-3.9 recompute; nothing else).
R-3.9c subsequently RESOLVED_BY_OWNER_ADJUDICATION (2026-08-29, option
A — bracket form `[<source_kind> <source_ref>]`); its corroboration
verified by the R-3.9c-OPTION-A close-out unit — writes: this report
+ one engram save, nothing else (no commit). Residuals-unit writes: `tests/unit/test_integration_golden_determinism.py`
(R-3.9a — the 3 stale tests), `tests/golden/golden_machinery.py`
(R-3.9b — independent-manifest reader), `tests/golden/manifest.json`
(R-3.9b — `independent_sample.status` wording, implementation-side
manifest, not hash-bound), and this report. Read-only for `src/`, the
hash-bound bundle, APPROVAL-*, `state.yaml`,
`tests/golden/independent/*` (untouchable — digests re-verified
unchanged AFTER), and `tests/golden/scenarios/*`. No commit.

All commands run 2026-08-29 (UTC range 19:50-20:07Z; the residuals
unit's runs 19:58-20:07Z; the R-3.9c-OPTION-A close-out runs
20:28-20:35Z), every `uv` invocation `--no-sync` (no
environment mutation; no install/sync attempted; zero `UNKNOWN`
outcomes). Every verdict below is computed from captured evidence —
nothing assumed. Gate semantics per `specs/phase0-verification/spec.md`
and the tasks.md result vocabulary: `UNKNOWN` never yields PASS; a
named gate item that is unmet blocks the gate and is enumerated —
never silently passed.

## Gate 3.9 — item-by-item evidence table (RECOMPUTED after R-3.9a/b)

Literal gate definition (tasks.md task 3.9, verbatim): *"golden
digests committed; ≥1 independently authored expected sample present
under `tests/golden/independent/` (golden evidence `EVIDENCE_INTEGRITY`
status recorded); cross-run SHA-256 equality; `RENDER_ERROR` yields no
partial document; quality suite green."* — five items.

| # | Gate item (tasks.md 3.9) | Command(s) + run ID | Exit | Key evidence | Verdict |
|---|--------------------------|---------------------|------|--------------|---------|
| 1 | Golden digests committed | `pytest tests/unit/test_integration_golden_determinism.py -k "cross_run or recompile or manifest_records" -q` (`3.9-R/03`, 2026-08-29T20:04Z, 7 passed) · `git status --porcelain` (`3.9-R/06`, 20:06Z) | 0 | 7 scoped tests passed: manifest schema + all 3 scenario digests equal the committed document bytes (input digests too), and recompiling each committed fixture set through the real chain reproduces the golden bytes exactly (golden regression detection). Corpus: `tests/golden/manifest.json` + `scenarios/{pc1_unassessed_fc,pc2_assessed_absence_ta,standard_mixed}.{input.jsonl,document.txt}`. NOTE: files are present and digest-verified but git-UNTRACKED — executor commits are prohibited (APPROVAL-PHASE3 "Executor commits"), so the git commit is the owner's pending act (P3-F11; residual risk, not a gate failure). | PASS (digests verified; git-commit pending owner) |
| 2 | ≥1 independently authored expected sample present + `EVIDENCE_INTEGRITY` status recorded | `python tests/golden/golden_machinery.py verify` plain and `-I` (`3.9-R/01`, 19:58Z) · fresh divergence recomputation (`3.9-R/04`, 20:05Z) | 0 / 0 | Sample PRESENT: `tests/golden/independent/` carries `MANIFEST.json` + 3 expected documents (author "independent-spec-derived (subagent, 2026-08-29)" — ratification flag P3-F10). After R-3.9b the machinery READS the multi-scenario shape (`scenarios[]`, paths relative to the corpus root): per-scenario document + input digests all verify → self-consistent → machinery computes `corpus_verified=True`, `independent_sample_present=True`, `overall_integrity=VALID` (the frozen vocabulary's presence+self-consistency arm), `phase3_gate_blocked=False`, exit 0 — plain AND isolated `python -I`. Status recorded at residuals time (gate level, fail-closed):
INVALID-pending-adjudication while 3/3 glyph divergences stood
(history — resolved below). **Current recorded status: VALID
(corroborated, post-R-3.9c)** — the owner adjudicated the A1 spec
silence on 2026-08-29 as option A (bracket form
`[<source_kind> <source_ref>]`, the implementation's frozen form);
the independent sample was RE-DERIVED under the closed rule and fresh
evidence (`3.9-C/01..03`, 20:28-20:35Z) shows machinery
`overall_integrity=VALID` exit 0 plain AND `-I`, all 3 independent
expected digests equal to the expected values (the implementation
golden digests), and 3/3 `cmp` MATCH byte-identical. The machinery's
own contract assigns the agreement question to THIS gate computation
— now answered in favor of agreement; no fourth vocabulary state was
ever invented. | PASS on the letter AND on corroboration (present +
status recorded = VALID; independent bytes corroborate the goldens
byte-for-byte) |
| 3 | Cross-run SHA-256 equality | scoped pytest above (`3.9-R/03`, includes `-k cross_run`) | 0 | `test_cross_run_digests_equal_and_match_committed_golden` ×3 scenarios: each compiled 4× in fresh interpreters — `python -I` twice (implies `-E`: fresh random hash seed per run), `PYTHONHASHSEED=0`, seed unset — all 4 digests equal AND equal to the committed golden digest. Full suite also ran them (337 passed included them). Task 3.8's `-I`/`-E` note is pinned in the U4 module docstring and honored by the union coverage. | PASS |
| 4 | `RENDER_ERROR` yields no partial document | `pytest tests/unit/test_renderers_deterministic.py -q` (`3.9-R/02`, 20:04Z) | 0 | 20 passed incl. `test_fc10_dangling_ref_yields_render_error_and_no_partial_document` (FC-10 injected dangling ref → `admitted == ()`, never partial) plus the bijection arms (duplicate ref, silently-omitted fact) and the non-canonical-value-type arm (`dict`/`set` would leak iteration order → fail closed). Spec scenario "Render failure": `RENDER_ERROR` emitted, no partial document — covered. | PASS |
| 5 | Quality suite green | `uv run --no-sync pytest` (`3.9-R/05`, 20:05Z) · `mypy src` · `ruff check src tests` (`3.9-R/05`) | 0 / 0 / 0 | **337 passed, 0 failed** (was 3 failed / 334 passed before R-3.9a); coverage 100.00% (477 stmts, 180 branches, 0 missed — ≥ 95.0). mypy strict: `Success: no issues found in 20 source files`. ruff: `All checks passed!`. The 3 former failures are closed by R-3.9a (see below); the golden-determinism module is 16/16 green, including the updated presence test and both tmp-corpus simulations. | PASS |

**GATE_3_9 = PASS (5/5).** Previous computation (pre-residuals, runs
`3.9/01-08`): 4/5, BLOCKED on item 5. The block is cleared by R-3.9a;
item 2's machinery reading is repaired by R-3.9b. Item 2 passes on its
letter (presence + status recorded) exactly as the previous
computation already held — at that time the recorded status remained
INVALID-pending-adjudication (R-3.9c), which the gate recorded, not
suppressed. R-3.9c-OPTION-A close-out (2026-08-29, runs
`3.9-C/01..05`): the owner's option-A ruling + the re-derived
independent sample close item 2's corroboration arm — the recorded
gate-level status is now VALID. Nothing `UNKNOWN`; no environment
mutation.

## Residuals — disposition

- **R-3.9a — RESOLVED (this unit).** The 3 stale U4 tests in
  `tests/unit/test_integration_golden_determinism.py`:
  (1) `test_absence_of_independent_sample_is_detected_as_pending_block`
  → replaced by
  `test_independent_sample_presence_upgrades_evidence_to_valid` — the
  VALID-branch assertion its own failure message prescribed (sample
  present → `assess_golden_evidence` → `VALID` /
  `phase3_gate_blocked=False` on the REAL corpus), with the
  DEGRADED-pending-owner arm preserved against a tmp-corpus copy with
  the sample removed (test count unchanged: 337). (2)+(3)
  `test_present_independent_sample_upgrades_evidence_to_valid` and
  `test_self_inconsistent_independent_sample_is_invalid`
  (`FileExistsError` root cause): `_install_independent_sample` now
  REMOVES the `independent/` dir that `_corpus_copy` carries over from
  the real corpus before creating the simulation (full isolation), and
  the simulated manifest now mirrors the committed multi-scenario
  shape (previously the legacy single-sample shape the machinery no
  longer reads).
- **R-3.9b — RESOLVED (this unit, machinery side ONLY).**
  `golden_machinery._independent_problem` now reads the independent
  MANIFEST's multi-scenario shape: `scenarios[]` (fail-closed when
  absent/empty), per-scenario document path + sha256 (paths relative
  to the corpus root, mirroring the golden-manifest family shape) and
  per-scenario input path + input_sha256, checked in sorted-name
  order. The documented contract (machinery docstring) is rewritten to
  the multi-scenario shape; the implementation-side
  `tests/golden/manifest.json` `independent_sample.status` wording is
  updated `PENDING_OWNER_AUTHORSHIP` → `PRESENT` (minimal, matching
  reality; `generate_corpus` now derives it from actual presence so
  regeneration stays coherent). **The independent MANIFEST.json and
  all `independent/*` bytes are UNTOUCHED** (digests re-verified AFTER
  all writes — see Side-effect budget).
- **R-3.9c — RESOLVED_BY_OWNER_ADJUDICATION (2026-08-29).** The owner
  closed spec silence A1 by ruling option A: the provenance bracket
  form `[<source_kind> <source_ref>]` — exactly the implementation's
  frozen form. Because the implementation form was UPHELD (not
  changed), the glyph is NOT an output-affecting change: the goldens
  stand as committed (digests re-verified unchanged: `31d58796…`,
  `6387f1af…`, `e7b5b03f…`) and the independent sample was re-derived
  by its author under the closed rule (`(kind:ref)` → `[kind ref]`)
  instead of a golden re-freeze. Fresh verification (`3.9-C/01..03`,
  20:28-20:35Z): machinery verify VALID exit 0 plain and `-I`; all 3
  independent expected digests equal the expected values; `cmp` MATCH
  3/3, byte-identical (Unit B below). The former "(glyph change →
  golden re-freeze + re-verify)" branch did not trigger — the
  corroboration is fresh evidence of a re-derivation, not an
  auto-fix.

## Unit B — Independent-sample comparison (evidence, NOT auto-fix)

Per scenario: independent expected bytes vs the implementation
goldens for the SAME committed input. History (residuals unit,
`3.9-R/04` = original `3.9/05`): 3/3 DIVERGENCE on exactly ONE glyph
family — independent `(kind:ref)` vs implementation `[kind ref]` on
the 5 fact-backed lines; missingness brackets, values, sort order,
and line set all matched; the frozen PC-1 line
`FC: unknown [not_assessed]` was byte-IDENTICAL throughout. After
the owner's option-A ruling, the sample was re-derived under the
closed rule and the comparison recomputed fresh (`3.9-C/02/03`,
20:29Z):

| Scenario | Independent sha256 | Implementation sha256 | Verdict |
|----------|-------------------|----------------------|---------|
| pc1_unassessed_fc | `31d58796158fc876dc49434008586788938b0d9b5b46a9368ab37aac7ccddb99` | `31d58796158fc876dc49434008586788938b0d9b5b46a9368ab37aac7ccddb99` | MATCH (byte-identical) |
| pc2_assessed_absence_ta | `6387f1afe79e6c20ec6f828e323ff45ea9c46207cea7f0e7327b4ca604dad909` | `6387f1afe79e6c20ec6f828e323ff45ea9c46207cea7f0e7327b4ca604dad909` | MATCH (byte-identical) |
| standard_mixed | `e7b5b03fa6d9f150c081684846fb481b7dfda02ebdd24992a7fba164c88b8abc` | `e7b5b03fa6d9f150c081684846fb481b7dfda02ebdd24992a7fba164c88b8abc` | MATCH (byte-identical) |

Findings (post-R-3.9c):

1. **3/3 MATCH — the corroboration is now byte-for-byte.** The
   re-derived independent expected files SHA-256 to exactly the
   expected digests (the committed implementation golden digests);
   `cmp` reports no differing bytes in any scenario.
2. **Root cause closed**: spec silence A1 / design Open Question 4 is
   answered by the owner's option-A ruling (bracket form
   `[<source_kind> <source_ref>]`) — the task-3.7
   first-golden-file freeze reading is upheld, so NO output-affecting
   change occurred and no golden re-freeze was needed; the
   independent side re-derived instead.
3. **Self-consistency holds on both sides** (`3.9-C/01`): every
   independent recorded digest matches its (re-derived) bytes
   (document AND input digests, enforced by the machinery after
   R-3.9b); every golden-manifest digest matches its committed
   document; the implementation recompile is byte-identical to its
   goldens. No side is internally corrupted.
4. **Authorship note (P3-F10 still applies)**: the re-derived
   MANIFEST author reads "independent-spec-derived (subagent
   re-derivation under closed rule A, 2026-08-29)" — implementation-
   independent by construction, but still requiring the owner's
   ratification of the authorship path (or substitution by a
   hand-authored sample, permitted at any time).

## EVIDENCE_INTEGRITY — resulting state (after R-3.9b)

Frozen semantics (design Determinism Mechanism #6 + the machinery's
committed implementation): `VALID` = corpus verified + a self-consistent
independent sample present; `INVALID` = verification failure (corpus
drift, or a self-inconsistent independent sample); `DEGRADED` =
implementation-only goldens (blocks the gate pending owner input). The
frozen text is SILENT on "sample present and self-consistent but its
bytes DIVERGE from the implementation pending adjudication" — and the
machinery docstring explicitly assigns the agreement question to THIS
gate computation, not to the vocabulary.

- **Machinery computation (frozen vocabulary, authoritative for its
  arm): `VALID`, exit 0** — corpus verified + independent sample
  present and self-consistent (the manifest-shape mismatch that
  produced the spurious "document missing" INVALID is repaired by
  R-3.9b). `DEGRADED` no longer applies (absence branch closed; still
  exercised in tests via the tmp-corpus simulation).
- **Gate-level recorded status: VALID (corroborated) — post-R-3.9c.**
  History: at residuals time the gate-level status was recorded
  INVALID-pending-adjudication (fail-closed) — VALID-on-presence was
  NOT forced while the sample's bytes diverged in 3/3 scenarios on
  the provenance glyph. The owner's 2026-08-29 option-A ruling closed
  R-3.9c; the independent sample was re-derived under the closed rule
  and now corroborates the implementation goldens BYTE-FOR-BYTE
  (`3.9-C/02/03`). Honest corroboration is established by agreement,
  not presence alone: machinery VALID and gate-level VALID now agree,
  no fourth vocabulary state was ever invented, and nothing was
  mutated to force agreement (the corroboration is fresh evidence of
  a re-derivation, not an auto-fix). The Final Receipt (task 4.7)
  carries VALID.

## Unit summary (APPROVAL-PHASE3 work-unit sequence, owner-defined)

All Phase-3 code sits UNCOMMITTED in the working tree (owner-HEAD is
`470fef5`, the Phase-2 payload commit; executor commits prohibited).
Phase-3 payload: 3 tracked M (`state.yaml`,
`linter/conformance.py`, `renderers/deterministic.py`,
`passes/document_selection.py`) + 13 untracked (APPROVAL-PHASE3.md,
golden machinery + corpus + independent sample, 5 test files).

| Unit | Scope (tasks) | Result | Tests | Files |
|------|---------------|--------|-------|-------|
| P3-U1 | `passes/document_selection.py` — DocumentIR from refs+roles only; `DOCUMENT_SELECTION_ERROR`; FC-09 (3.1/3.2) | PASS | 12 in `test_passes_document_selection.py` | + module (uncommitted) |
| P3-U2 | `renderers/deterministic.py` — canonical bytes; FC-10 `RENDER_ERROR` no-partial; PC-1 unknown line (3.3 + 3.5 renderer half + 3.6 render leg) | PASS | 20 in `test_renderers_deterministic.py` | + module (uncommitted) |
| P3-U3 | `linter/conformance.py` — mode rules; FC-11 injected-bytes `LINT_FAILURE`; only lint-clean accepted (3.4 + 3.5 linter half) | PASS | 32 in `test_linter_conformance.py` | + module (uncommitted) |
| P3-U4 | Determinism machinery — golden corpus + manifest + cross-run SHA-256 gate + `EVIDENCE_INTEGRITY` vocabulary (3.6/3.7/3.8) | PASS | 16 in `test_integration_golden_determinism.py` — **16/16 green after R-3.9a** | + `golden_machinery.py`, `manifest.json`, 6 scenario files (uncommitted) |
| P3-U5 | Independent expected sample under `independent/` (3.7) | PRESENT + self-consistent + CORROBORATING: re-derived under closed rule A (R-3.9c owner adjudication, option A) — 3/3 byte-MATCH with the implementation goldens | — (evidence artifacts) | + `MANIFEST.json` + 3 `.expected.txt` (uncommitted) |
| P3-U6 | Minimal Phase-3 integration + gate 3.9 + this report (3.9 + chain-level 3.6) | PASS — gate recomputed 5/5 after the residuals unit | 6 in `test_integration_phase3_chain.py` | + test file, this report |
| P3-U6R | Bounded residuals: R-3.9a (3 tests) + R-3.9b (machinery reader) + gate recompute | RESOLVED (R-3.9a/b); R-3.9c remains owner adjudication | same 337-suite, now 337/337 | `test_integration_golden_determinism.py`, `golden_machinery.py`, `manifest.json` (status wording), this report |
| P3-U6C | R-3.9c-OPTION-A close-out: fresh-evidence corroboration + this receipt update (nothing else) | VERIFIED — R-3.9c RESOLVED_BY_OWNER_ADJUDICATION; 3/3 cmp MATCH; machinery VALID plain/-I; gate-level EVIDENCE_INTEGRITY = VALID | pytest 337/337 · mypy 0 · ruff 0 · machinery verify exit 0 (plain and `-I`) | this report only (+ one engram save) |

Phase-3 test arithmetic: 12 + 20 + 32 + 16 + 6 = 86 cases across the
five test files; suite 337 = 251 (Phase-2 close) + 86 — matches the
observed `337 passed`.

Task-row coverage check (R-2.7 lesson — EVERY Phase-3 row 3.1-3.9):
3.1 ✓U1 · 3.2 ✓U1 (file named `test_passes_document_selection.py` —
naming-convention deviation, flag P3-F1) · 3.3 ✓U2 · 3.4 ✓U3 ·
3.5 ✓U2+U3 (FC-10 renderer test named above; FC-11 via the linter's
injected-bytes suite — vocabulary families + real-renderer newline
injections) · 3.6 ✓U4 (`test_glyph_vocabulary_frozen_by_the_golden_corpus`
pins the exact `FC: unknown [not_assessed]` line) + U6 (end-to-end
`test_pc1_unassessed_fc_renders_explicit_unknown`, byte-equal to the
committed pc1 golden) · 3.7 ✓U4+U5 (goldens frozen; independent sample
present + machinery-read after R-3.9b) · 3.8 ✓U4 (cross-run test,
re-run green this unit) · 3.9 ✓U6+U6R (gate recomputed from fresh
evidence — 5/5). **No uncovered row.**

## Consolidated owner-adjudication flags (Phase 3)

None blocks the recomputed gate (all five items PASS by their letter);
`risk_policy: ask_on_risk` — reported, not silently resolved. P3-F9
(= R-3.9c) is CLOSED by the owner's 2026-08-29 option-A ruling; the
remaining flags carry.

| # | Flag | Origin | Substance |
|---|------|--------|-----------|
| P3-F1 | Role vocabulary + naming | U1 | uniform `telegraphic_entry` role (no frozen field-to-role table — inventing one would be executor-authored clinical content); mode/role constants placed in `document_selection.py` for lack of a frozen shared home; test file named `test_passes_document_selection.py` vs tasks.md 3.2's `test_document_selection.py` |
| P3-F2 | Renderer I/O + glyph freeze + bijection arms | U2 | `render_document(document, facts)` takes the aggregate alongside the DocumentIR (single value authority); glyph vocabulary frozen BY THE IMPLEMENTATION via the first golden file (design Open Question 4 route) — now contested by the independent sample's divergent glyph (R-3.9c); duplicate/omission bijection arms are fail-closed readings beyond corpus-frozen FC-10 |
| P3-F3 | Linter I/O + duplicated tables | U3 | linter consumes bytes+mode (never IR); glyph/missingness table duplicated from the renderer deliberately (independent net — a shared table would let a renderer bug validate itself); mode constant re-declared (D5 forbids importing passes); unknown-mode `LINT_FAILURE` is defense-in-depth after selection already blocked it |
| P3-F4 | `python -I`/`-E` note + machinery placement | U4 | `-I` implies `-E` so `PYTHONHASHSEED=0 python -I` is a no-op seed — the gate therefore unions isolated `-I` runs with non-isolated seeded/unseeded runs; machinery lives at `tests/golden/golden_machinery.py` (stdlib-only, doubles as the subprocess CLI) — placement not prescribed by the frozen bundle |
| P3-F5..F8 | Spec ambiguities A2-A7 (sample side) | U5 | A2 uniform `[present]` bracket grammar (MATCHES the implementation); A3 no certainty glyph on the document surface; A4 `missing` token for assessed absence (matches); A5 no mode banner; A6 `80.5` minimal float form (matches); A7 render every contract field exercised by the scenario family |
| P3-F9 | Provenance-glyph divergence (= R-3.9c) — **RESOLVED** | U5 vs U2/U4 | RESOLVED_BY_OWNER_ADJUDICATION 2026-08-29: option A adopted — bracket form `[<source_kind> <source_ref>]` (the implementation's frozen form upheld → NO golden re-freeze needed); the independent sample was re-derived under the closed rule → 3/3 byte-MATCH (`3.9-C/02/03`); gate-level EVIDENCE_INTEGRITY recomputes to VALID |
| P3-F10 | Independent-authorship ratification | U5 | MANIFEST author = "independent-spec-derived (subagent, 2026-08-29)" — task 3.7 requires "decision owner or an owner-designated audit path, NEVER the executor/implementation". The sample is implementation-independent by construction (no src read, no goldens read — per its recorded method); the owner should ratify this authorship path as a designated audit path (or substitute his own hand-authored sample, which the task explicitly permits at any time) |
| P3-F11 | Golden-corpus git commit | U4/U5/U6 | corpus + sample digest-verified but untracked; commit is the owner's act (executor commits prohibited) |

## Side-effect budget note

- BEFORE/AFTER tracked-tree snapshots: the working tree carries
  exactly the Phase-3 payload enumerated above, plus the declared unit
  writes (`tests/unit/test_integration_phase3_chain.py`, this report)
  and the residuals unit's three declared code writes
  (`tests/unit/test_integration_golden_determinism.py`,
  `tests/golden/golden_machinery.py`, `tests/golden/manifest.json`).
  No src/ write; no venv, installs, network, or process starts beyond
  `pytest`/`mypy`/`ruff`/one-shot `python` over the repo; `uv` always
  `--no-sync` (no failures ⇒ no `UNKNOWN`).
- **Independent artifact untouched — verified by digests AFTER all
  writes** (`3.9-R/07`, 20:06Z): `MANIFEST.json`
  `a6664a19…d91382`, `pc1_unassessed_fc.expected.txt` `a07e7aaa…586718`,
  `pc2_assessed_absence_ta.expected.txt` `1f3c3d07…2a414`,
  `standard_mixed.expected.txt` `0c7b484a…1d6733` — all four equal to
  the BEFORE snapshot; `scenarios/*` unchanged likewise (only
  `manifest.json`'s `independent_sample.status` wording changed, by
  design, R-3.9b).
- **R-3.9c-OPTION-A close-out unit (2026-08-29, 20:28-20:35Z):** the
  only write is this report's R-3.9c update (+ one engram save);
  everything else read-only (src, tests, goldens, bundle, approvals,
  state.yaml untouched). `git status --porcelain` BEFORE == AFTER
  (same 3 tracked M + untracked set; this report is untracked, so its
  content edit is invisible to git). Independent artifacts untouched
  by this unit — digests at close-out: `MANIFEST.json`
  `1d0b40ba…151ffa`, pc1 expected `31d58796…ccddb99`, pc2 expected
  `6387f1af…4dad909`, standard_mixed expected `e7b5b03f…88b8abc` (the
  three expected-file digests now equal the implementation golden
  digests BY DESIGN of the owner-side re-derivation; the MANIFEST
  digest differs from the residuals-era `a6664a19…` snapshot because
  the re-derivation happened before this unit started).
- The 3 tracked M + 13 untracked files are the complete Phase-3
  payload awaiting the owner's commit decision (same posture as
  Phase 2 at its close).

## Phase report (contract vocabulary: done|partial|blocked|failed)

```text
phase_report:
  phase: 3
  status: done
  executive_summary: Bounded residuals unit closed R-3.9a (the 3 stale U4 tests: absence-test replaced by its own message-prescribed VALID-branch assertion with the DEGRADED arm preserved on a tmp corpus; both tmp-corpus simulations isolated from the copied real independent/ dir, simulated manifest aligned to the committed multi-scenario shape) and R-3.9b (golden_machinery._independent_problem now reads the independent MANIFEST's scenarios[] — per-sample document+input paths and digests, paths relative to the corpus root, fail-closed on shape anomalies; documented contract rewritten; implementation-side manifest.json independent_sample.status wording PENDING_OWNER_AUTHORSHIP -> PRESENT with generate_corpus deriving it; the independent artifact bytes untouched, digests re-verified after) and recomputed gate 3.9 from fresh evidence: 5/5 PASS — items 1/3/4 re-proven (7 scoped golden tests, 20 renderer tests), item 2 PASS on its letter (sample present; machinery now reads it: corpus_verified=True, present=True, overall_integrity=VALID-on-presence, exit 0 plain AND python -I; gate-level status RECORDED as INVALID-pending-adjudication because 3/3 scenarios still diverge on exactly the provenance glyph (kind:ref) vs [kind ref] — R-3.9c owner adjudication, NOT forced VALID), item 5 now green (337/337 passed, coverage 100.00%, mypy strict clean, ruff clean). R-3.9c subsequently RESOLVED_BY_OWNER_ADJUDICATION (2026-08-29): owner ruled option A — bracket form [<source_kind> <source_ref>] (the implementation's frozen form upheld, so NO output-affecting change and NO golden re-freeze); the independent sample was re-derived under the closed rule and the close-out unit verified fresh corroboration — machinery verify VALID exit 0 plain AND python -I, all 3 independent expected digests equal to the expected values, 3/3 cmp MATCH byte-identical — gate-level EVIDENCE_INTEGRITY recomputes to VALID; PHASE_3 = done stands with P3-F10 + P3-F11 carried as enumerated owner items.
  artifacts: [tests/unit/test_integration_golden_determinism.py, tests/golden/golden_machinery.py, tests/golden/manifest.json, openspec/changes/clinical-compiler-r1/outputs/phase3-close.md]
  evidence: [3.9-R/01 machinery verify plain + -I 19:58Z: corpus_verified=True independent_sample_present=True overall_integrity=VALID phase3_gate_blocked=False exit 0 (previously INVALID exit 1 on the shape mismatch) · 3.9-R/02 pytest test_renderers_deterministic.py 20 passed exit 0 20:04Z · 3.9-R/03 scoped pytest golden (cross_run+recompile+manifest_records) 7 passed exit 0 20:04Z · 3.9-R/04 fresh divergence recomputation 20:05Z: 3/3 DIVERGENCE on the provenance glyph only (identical to 3.9/05), all independent input digests OK · 3.9-R/05 full pytest "337 passed" coverage 100.00% exit 0 20:05Z; mypy src "Success: no issues found in 20 source files" exit 0; ruff check src tests "All checks passed!" exit 0 · 3.9-R/06 git status AFTER = BEFORE + the 3 declared residuals writes · 3.9-R/07 shasum independent/* + scenarios/* + manifest.json AFTER: independent bytes byte-identical to BEFORE · 3.9-C/01 machinery verify plain + -I 20:28Z: corpus_verified=True independent_sample_present=True overall_integrity=VALID phase3_gate_blocked=False exit 0 BOTH · 3.9-C/02 shasum independent expected files 20:29Z: pc1=31d58796158fc876dc49434008586788938b0d9b5b46a9368ab37aac7ccddb99 pc2=6387f1afe79e6c20ec6f828e323ff45ea9c46207cea7f0e7327b4ca604dad909 standard_mixed=e7b5b03fa6d9f150c081684846fb481b7dfda02ebdd24992a7fba164c88b8abc — each equals its expected value AND the committed implementation golden digest · 3.9-C/03 cmp independent/*.expected.txt vs scenarios/*.document.txt: 3/3 MATCH byte-identical 20:29Z · 3.9-C/04 pytest 337 passed cov 100.00% exit 0 20:33Z; mypy src "Success: no issues found in 20 source files" exit 0; ruff check src tests "All checks passed!" exit 0 · 3.9-C/05 git status BEFORE == AFTER this unit — write set = this report only]
  failures_recovery: [R-3.9a RESOLVED: 3 stale U4 tests updated (VALID-branch presence test incl. preserved DEGRADED arm; _install_independent_sample removes the copied real independent/ dir before mkdir and writes the multi-scenario shape) — suite 337/337 · R-3.9b RESOLVED: machinery reads the multi-scenario independent manifest (per-sample document+digest from scenarios[], input digest enforced, fail-closed); machinery docstring contract rewritten to the multi-scenario shape; manifest.json independent_sample.status wording PRESENT; independent artifact untouched · R-3.9c RESOLVED_BY_OWNER_ADJUDICATION (2026-08-29, close-out unit): owner ruled option A — bracket form [<source_kind> <source_ref>] upheld; sample re-derived owner-side; unit verified corroboration read-only (no renderer/golden/sample mutation) and re-ran the suite 337/337 + mypy 0 + ruff 0]
  human_decisions: [APPROVAL-PHASE3.md — PHASE_3 authorized work-unit mode, units 1-6; APPROVAL-PHASE1.md POLICY_SEED_DECISION=DEFERRED_BY_OWNER (the FC-12 production path used by every chain composition); owner CRC adjudications 2026-08-28 (CRC-004 dangling-ref absorption — P4 impossible-by-construction + renderer defense-in-depth); glyph adjudication R-3.9c CLOSED 2026-08-29: owner ruled option A — bracket form [<source_kind> <source_ref>] (implementation form upheld, no re-freeze); pending: P3-F10 independent-authorship ratification (the re-derived sample is again subagent-authored under the closed rule) + P3-F11 commit + remaining minor P3-F* flags]
  residual_risk: [gate-level EVIDENCE_INTEGRITY = VALID (corroborated) after the R-3.9c option-A ruling + byte-for-byte re-derivation corroboration — the Final Receipt (4.7) may carry VALID; Phase-3 payload entirely uncommitted pending owner commit (P3-F11); independent-authorship ratification pending (P3-F10) — a substituted owner-authored sample would re-verify against the same digests; `is_resolved` policy branch still test-only until Phase-4 pipeline.py (carried flag)]
  next_recommended: owner ratifies P3-F10 (independent-authorship path, or substitutes a hand-authored sample re-verified against the same digests), then commits the Phase-3 payload (P3-F11) → Phase 4 activation requires a new owner approval record naming Phase 4
```

**GATE_3_9 = PASS (5/5 — recomputed after R-3.9a/R-3.9b; corroboration
closed by the R-3.9c-OPTION-A unit, 2026-08-29). PHASE_3 = done.**
Faithful per the result vocabulary: every item computed from fresh
evidence, R-3.9c RESOLVED_BY_OWNER_ADJUDICATION (option A — bracket
form `[<source_kind> <source_ref>]`), the re-derived independent
sample corroborates the implementation goldens byte-for-byte
(gate-level EVIDENCE_INTEGRITY = VALID), and the close-out unit
mutated nothing but this report.
