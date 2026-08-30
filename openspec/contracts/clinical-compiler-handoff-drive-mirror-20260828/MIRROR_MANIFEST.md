---
id: ai-work-wiki-drive-mirror-okf-20260822
title: AI Work Wiki · Drive discovery mirror for OKF planner
status: mirror
canonical: false
source_of_truth: ChatGPT Library /Infra/AI Work Wiki/v0.1
created_at: 2026-08-22
purpose: discovery-only
---
# AI Work Wiki · Drive discovery mirror
This folder is a discovery mirror for agents operating only on Google Drive during the OKF Clinical Compiler planning/cutover work.
## Authority rule
This Drive copy is NOT a new control plane and MUST NOT supersede the ChatGPT Library. When the Library is available, resolve and use the current Library path head. If Library is unavailable, this mirror may be used to discover the bootstrap contract and the relevant active documents, but any consequential promotion/cutover must still preserve the original authority/lifecycle semantics and fail closed on uncertainty.
## Mirrored current heads at creation
- /Infra/AI Work Wiki/v0.1/INDEX.md — Library file_id file_00000000f228820ebb198b0fc58d039b — version 11
- /Infra/AI Work Wiki/v0.1/SCHEMA.md — Library file_id file_00000000f2bc820ea301e7560325809e
- /Infra/AI Work Wiki/v0.1/BOOTSTRAP.md — Library file_id file_00000000d450820ea99d1855a3855eeb — version 2
- /Infra/AI Work Wiki/v0.1/AUTHORING_STANDARD.md — Library file_id file_00000000e3c0820e85ce8f0e639e4790 — version 5
- /Infra/AI Work Wiki/v0.1/documents/ai-work-agent-execution-contract-0.3.md — Library file_id file_00000000d524820ebc2337982baf43d1 — version 1
- /Infra/AI Work Wiki/v0.1/documents/hybrid-agent-method-1.1-rc2.md — Library file_id file_000000005b30820eac8482555dd38849 — version 1
## Expected agent bootstrap
1. Read INDEX.md.
2. Read SCHEMA.md.
3. Read BOOTSTRAP.md.
4. Load only the smallest relevant active documents.
5. For OKF planning/cutover, the mirrored Hybrid Agent Method and Agent Execution Contract are available under documents/.
6. Do not treat this mirror as evidence that a runtime cutover, clinical validation, or authority promotion occurred.
