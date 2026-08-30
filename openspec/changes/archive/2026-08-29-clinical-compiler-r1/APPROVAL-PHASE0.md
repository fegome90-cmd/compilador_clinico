# APPROVAL-PHASE0 — change: clinical-compiler-r1

OWNER INSTRUCTION (verbatim, 2026-08-29): **"sdd apply ahora"**

This durable record binds that instruction to the exact candidate below and
authorizes `sdd-apply` for **PHASE_0 ONLY**.

## Context

- Owner CRC adjudication received 2026-08-28 and applied (engram #7251); the
  five-step protocol the owner required before any apply (apply adjudications →
  re-hash → consistency check → update state.yaml → present open questions) was
  completed and reported the same day. The owner's earlier "do not interpret as
  authorization" caveat was conditional on that protocol, which is now complete.
- This instruction postdates the completed protocol and is the owner's explicit
  authorization.

## Approved scope

- PHASE_0 of `tasks.md` — strictly read-only (no installs, no process
  start/stop, no writes outside `openspec/changes/clinical-compiler-r1/`,
  no source mutations, no commits).

## NOT authorized

- Phases 1–4 implementation — contingent on the Phase 0 decision gate
  (owner-authored).
- Any git mutation, dependency installation, or runtime change.

## Bound candidate (SHA-256, computed 2026-08-28, unchanged)

```text
bundle_manifest = 7a7d3a28afa749c362a2091f4ea0c60d25745f0ede49ac311b5e8d8511e0737d
proposal.md                     04ed8dafa60d85a15b693de984984eed1845c5d96643c0de20b79e99814dd840
design.md                       75335698149cee43243c2db6ef45d6d716c07de6dd60903fc19ac5ed45c7d9ef
tasks.md                        086e7884d4904f15900bb76af18500467ed44a29d724a5d11c109ba231cd9f0f
specs/cli-surface/spec.md       580b1d2a0d20c4a9582b1451ba5e4f469622364ab70aee7a9a598c1e7a48f1cc
specs/clinical-fact-model       90ab38d41ad7112a1dfca1186d8e160d35bddec01f11c00820f49b530d392e54
specs/determinism-rendering     3a09007bad60e639d9ebdeee60b0379af4927e94d099d98b489dbd8229ad9c78
specs/diagnostics-policy        ee9852b388cef55dfac37fef0ffca931795cb13eb0ca2871be28094397f50f23
specs/input-contract            7ffd272d5182ef5b09e13a9fb08bef75bfd310481c002d37c7f7f8a0930fdd7a
specs/phase0-verification       f0314a15a3dee6c78f4b56519520a82d3148f5fd519b40d2dbd4ca137b991600
specs/pipeline-passes           0aa5627c3e73e8d034dcb41510f720bb14adb4757fe06689873f72eca0036147
```

## Validation receipt

- Contract conformance audit (engram #7246) + repair #7247 — PASS after repair.
- CRC ticket-coverage fixes #7250 + consistency check — PASS.
- Owner CRC adjudication #7251 + post-adjudication consistency check — PASS.

## Open at PHASE_0 start (closed by owner at the Phase 0 decision gate)

Recorded owner recommendations (pending formal close at the gate):
1. Input contract — structured feed for R1; free-text deferred to R2.
2. `NEVER_AUTO_TERMS` — `DEFERRED_BY_OWNER` with durable state + test-local seeds.
3. CLI surface — accept `clinical-compiler compile …` as designed.

## Authority

Decision owner: Felipe Gonzalez. Reviewer must be distinct from executor.
This record authorizes NOTHING beyond PHASE_0.
