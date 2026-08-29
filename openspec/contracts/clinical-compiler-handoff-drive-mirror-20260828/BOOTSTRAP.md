---
id: ai-work-bootstrap-0.1
title: AI Work Bootstrap · v0.1
type: infrastructure
project: ai-work-wiki
authority: OPERATIONAL
document_tier: D0
status: active
migration_state: source-backed
canonical:
  control_plane: wiki
  content: editable-source
  pdf_generation: on-demand
artifact:
  kind: none
  role: no-release-artifact-required
relationships:
  governed_by:
    - ai-work-wiki-schema
  uses:
    - ai-work-wiki-index
    - ai-work-wiki-schema
audit:
  baseline_status: verified
  baseline_result: fail
  findings_open: []
  resolved_finding_ids:
    - LMA-20260809-015
tags: [ai-work, bootstrap, custom-instructions, d0]
---
# AI Work Bootstrap v0.1
## Purpose
Minimal entrypoint for fresh ChatGPT conversations that may be governed by the AI Work Library. It is **not** a second control plane, router, Kernel, Registry, method, or authority source. Its only job is to reach the active control plane safely before routing.
## Canonical bootstrap algorithm
When the current request could be governed by Library infrastructure:
1. **Consult the active control plane first.** Before routing or assuming operational rules, retrieve `/Infra/AI Work Wiki/v0.1/INDEX.md` and `/Infra/AI Work Wiki/v0.1/SCHEMA.md`.
2. **Discover minimally.** From that control plane, identify only the smallest set of potentially relevant documents needed for the current intent.
3. **Filter lifecycle and verification before governance.** Resolve the current Library path head before trusting lifecycle metadata; a still-readable historical file object is not proof that it remains current. A document can govern normal runtime only when its current persisted metadata makes it eligible. `status: active` is required. If an OS component declares `os_state`, implicit runtime use additionally requires `os_state: active`. When runtime eligibility depends on a promotion or verification contract, source-local active flags are necessary but not sufficient: require the applicable durable success evidence and fail closed on missing success evidence or contradictory `verification_failed` / `intervention_required` evidence.
4. **Fail closed on non-active infrastructure.** `draft`, `EXPERIMENTAL`, `candidate`, `shadow`, `quarantined`, `historical`, and `superseded` components may be read only for explicit testing, comparison, or audit. They must not be used as normal routing authorities.
5. **Registry/Kernel are not bootstrap dependencies while non-active or verification-ineligible.** Do not use `/Infra/AI Work Wiki/v0.1/os/REGISTRY.yaml`, Kernel, or another OS component as normal routing infrastructure unless its current persisted lifecycle and any applicable durable verification evidence make it active and runtime-eligible.
6. **Route from eligible active sources only.** Use applicable active authority/scope and the active source's own contract. Active Library sources outrank Memory and conversational recollection. Surface unresolved authority conflicts instead of reconciling them silently.
7. **Respect human ownership.** If the active governing method requires a human decision or hard stop, stop there.
8. **Graceful fallback.** If no eligible active owner is found, continue in normal ChatGPT mode; do not invent infrastructure.
9. **No fake invocation.** Never claim that a tool, plugin, skill, app, adapter, or method was invoked unless it was actually available and used.
## Custom Instructions deployment contract
The block below is the **deployment shim** for ChatGPT Custom Instructions. The Library copy is canonical; Custom Instructions are a host deployment surface, not the source of truth. Copy the block exactly.
Managed-block SHA-256: `sha256:06901235b0d0f75cf6790b6866244321125113103f59cc824789f4966df68b75`
```text
[AI WORK LIBRARY BOOTSTRAP v0.1]
When a request could be governed by my AI Work Library, do not route from memory or experimental infrastructure. Before choosing a method, policy, or workflow, retrieve and consult:
1) /Infra/AI Work Wiki/v0.1/INDEX.md
2) /Infra/AI Work Wiki/v0.1/SCHEMA.md
Then follow /Infra/AI Work Wiki/v0.1/BOOTSTRAP.md as the canonical bootstrap contract.
Only active/canonical sources may govern normal runtime. Never use draft, EXPERIMENTAL, candidate, shadow, quarantined, historical, or superseded components as normal routing authorities. If an OS component declares os_state, implicit use requires os_state: active. When runtime eligibility depends on promotion or verification, resolve the current Library path head and require the applicable durable success evidence; a historical file object, missing success evidence, or contradictory verification_failed/intervention_required evidence must block implicit use. If no eligible active owner exists, continue in normal ChatGPT mode. Respect human hard stops and never fake tool/plugin/skill invocation.
[/AI WORK LIBRARY BOOTSTRAP]
```
Deployment is not considered behaviorally verified until a genuinely new conversation passes `BOOTSTRAP-DISCOVERY-001` and an append-only receipt records the observed sources and routing.
## Non-goals
- Do not reproduce Registry routing tables.
- Do not promote Kernel/Registry or modify their lifecycle.
- Do not add plugin/app/vendor dependencies.
- Do not replace `INDEX.md` or `SCHEMA.md`.
- Do not make every conversation GOVERNED; normal fallback remains valid.
