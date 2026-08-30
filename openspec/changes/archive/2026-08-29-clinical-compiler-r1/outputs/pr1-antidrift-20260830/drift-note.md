# Drift note — concurrent writer detected during evidence freeze (2026-08-30)

## What happened

While the FULL_ANTIDRIFT executor was freezing evidence (all battery items complete,
verify-report appended), the Phase-E fence detected an **unauthorized, external
modification** to source:

- `src/clinical_compiler/adapters/contract.py`, one line (map_record provenance check):

```diff
-    if set(prov.keys()) != REQUIRED_PROVENANCE_KEYS:
+    if frozenset(prov.keys()) != REQUIRED_PROVENANCE_KEYS:
```

## Timeline (UTC, from file mtimes + embedded battery-log status lines)

| Time | Event |
|---|---|
| ≤ 10:21:59 | All 12 battery items executed — every log's `working_tree_status` captured **0** modified tracked files at `7d089513` (battery evidence binds to the committed SHA) |
| ~10:21:59 | `battery/12-exit70-sweep.log`'s embedded `working_tree_detail` recorded two stray untracked files `?? .ve-dark-full.jpeg`, `?? .ve-light-full.jpeg` — viewport screenshots NOT created by this session; both were gone by 10:24 (created AND deleted externally) |
| 10:22:15 | `preflight.txt` captured — tree clean |
| **10:24:15** | **`contract.py` mtime — the foreign edit lands** (this session issued no Write/Edit to `src/` at any point; every mutation command in this session targeted the evidence dir or `verify-report.md`) |
| 10:24:35 | verify-report.md appended (this session) |
| 10:24:46 | sha256sums.txt generated (this session) |
| 10:25:xx | Phase-E fence: `git status --short` → ` M src/clinical_compiler/adapters/contract.py` — FENCE EXCEPTION |

## Assessment

- **Not authored by this session.** Writer identity: EXTERNAL_CONCURRENT_PROCESS (most
  plausibly a parallel agent/editor session performing a determinism touch-up — the
  `set` → `frozenset` swap and the transient screenshot files are consistent with that).
- **Behavior-preserving:** content-based set equality is identical for `set` and
  `frozenset`; scoped post-hoc check (`test_adapters_contract.py` +
  `test_integration_feed_validation.py`, 56 tests) PASSES with the change present —
  recorded here as a **post-freeze drift observation, NOT battery evidence**.
- **Does NOT invalidate the frozen evidence:** every battery command predates 10:24:15;
  each log's `target_sha`/`working_tree_status` lines attest execution against the clean
  committed tree at `7d0895133d0ca74a889e3f3270f3a4b9f497f4cd`.

## Disposition (per the executing brief's constraints)

- The brief forbids `git restore/checkout/reset` — the foreign edit is NOT reverted by this
  session.
- The brief forbids committing unattributed source changes — the foreign edit is NOT
  staged. The Phase-E commit is **selectively staged** to this evidence directory +
  `verify-report.md` only; the commit content remains a pure evidence append on top of
  `7d089513`.
- After the commit, the working tree is expected to still carry
  ` M src/clinical_compiler/adapters/contract.py` — that residue belongs to the external
  writer and MUST be dispositioned by the owner (accept as a follow-up determinism commit
  under the owner's own authority, or discard). It is flagged in the verify-report's
  FULL_ANTIDRIFT section companion verdict.
