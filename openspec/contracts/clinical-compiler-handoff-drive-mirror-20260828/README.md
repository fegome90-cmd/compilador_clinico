# Clinical Compiler Handoff — Drive Mirror Export

## Status

This archive is a **read-only export from the Google Drive discovery mirror** of the AI Work Library. The mirror is not a new control plane and is not itself canonical. The source of truth remains ChatGPT Library at `/Infra/AI Work Wiki/v0.1`.

When ChatGPT Library is available, resolve and verify the current Library path heads before treating these files as authoritative. When it is unavailable, this bundle is suitable for bootstrap discovery only and must preserve fail-closed behavior for consequential work.

## Reading order

1. `INDEX.md`
2. `SCHEMA.md`
3. `BOOTSTRAP.md`
4. `hybrid-agent-method-1.1-rc2.md` when the task requires the active D0 method
5. `ai-work-agent-execution-contract-0.3.md` when the selected active owner requires the D1 execution contract

`MIRROR_MANIFEST.md` is provenance metadata only; it must not be treated as governance.

## Codebase boundary

Explore the codebase separately in the local repository:

`/Users/felipe_gonzalez/Developer/compilador_clinico`

This archive contains governance/bootstrap documents only. It does not include the codebase and does not authorize edits, commits, pushes, deployments, or runtime changes.

## Drive provenance

The five requested documents were read from native Google Drive documents. Their Drive IDs and current Drive revision IDs at export time are recorded below. The Library identifiers in `MIRROR_MANIFEST.md` describe the mirror's recorded source heads at mirror creation; they were not independently revalidated through the ChatGPT Library from this Codex runtime.

| Exported file | Drive document ID | Drive revision ID | Extracted size |
|---|---|---|---|
| `INDEX.md` | `1afwKK3SFr7MozCncZIxGBYVtqsMGLcqqL4VRrHy2G1s` | `AIroW35AXV8R3jerXear7g495aBViEHjf8Gen7REtLv7GMLP3fVyns8kVyrT5AruAht90FuamBLbGTN6Dgszq-jSXbE-uQXsmol3DH963Qw` | 2113 chars |
| `SCHEMA.md` | `13uABJGwJ3WVjQuykoTNqYajcj8m7lMpJbc3MrXO8jzM` | `AIroW36Ltlpy4iSyuNMejxwAES0q-5upJinW9OVnI389srj6mSaSwDuvoLNorjByKnmH6ewF16E7KrjSAk-UUN3zdQBHLa5tK4e7EHtxGIg` | 1140 chars |
| `BOOTSTRAP.md` | `1DVFE1ZZ-XccrHjd7_y92kyVaU-KaIj9-KgvL7zSrK4A` | `AIroW358oekdOP9rKCP5wO94fPfVZ2qnnHLiO4ZFM-JMUB4yair1Es28NvKoeZcvgHcS4U4K8G5f0tJqy_BzDAYMIRIyrv1USK_8ERBS3Q4` | 5319 chars |
| `hybrid-agent-method-1.1-rc2.md` | `1bMyx0g1nc1pxGbGhDXed3IgA0BJ6h1YXVn7HUCrUe0w` | `AIroW37JcM-CzYskkVeF5tj-gE346KKiPYfczqYcJWnhO73Ze_Cf4FVVERU1wkgD-709JuBo8pqavLvz386ZPJfEY0ymIsRl2T15JOeS6wM` | 2002 chars |
| `ai-work-agent-execution-contract-0.3.md` | `1mZm9dXr4vilK-Q9rUcccp5tWJPZApNpYzE3EHbH_54c` | `AIroW36F-avVOMrGz8mNDTWCp80CAoqG9mpT-YxwmQVrCJ_VSgXWpN0tEpPMFq0p9qBGKTPnNCT3k_1qiXGi9sAUfcJXlL0bXm_tx9J4bg8` | 28506 chars |

## Authority observations

- The mirror manifest declares `status: mirror`, `canonical: false`, and `source_of_truth: ChatGPT Library /Infra/AI Work Wiki/v0.1`.
- The mirrored `BOOTSTRAP.md` declares `status: active` but also records `baseline_result: fail`; follow its fail-closed algorithm and require current-head/evidence checks.
- The mirrored execution contract declares `status: active` but `baseline_result: pending-deep-baseline`; do not infer a completed baseline from its active flag.
- The Hybrid Agent Method mirror records an active D0 baseline pass and declares the execution contract as a dependency.
- No source document was modified. This archive contains exported copies plus this README and provenance copy.
