# Agent Entry Point

Repository-level instructions and routing for coding agents working in `compilador_clinico` (`clinical-record-compiler` v0.1.0).

---

## Sources of Truth

- Code, tests, manifests, and lockfiles describe observable implementation.
- `docs/agent/CONTEXT.md` describes project purpose, clinical domain model, missingness, and non-goals.
- `docs/agent/ARCHITECTURE.md` is the sole current architecture authority describing system composition, IR ownership, invariants, and evolution rules.
- `docs/agent/CODEMAP.md` provides shallow navigation and change-surface mapping.
- `docs/agent/RUNTIME.md` describes execution, CLI commands, exit codes, and operational constraints.
- `openspec/specs/` contains the current normative domain specifications.
- `openspec/changes/archive/2026-08-29-clinical-compiler-r1/` contains historical audit records and R1 design lineage.
- SDD artifacts own current plans, tasks, progress, and work-unit acceptance state.

If code and specifications disagree, identify the discrepancy rather than silently reconciling or guessing.

## Context Routing

| Intent | Read |
|---|---|
| Understand product & clinical domain | `docs/agent/CONTEXT.md` |
| Inspect or evolve system architecture | `docs/agent/ARCHITECTURE.md` |
| Locate implementation & change surfaces | `docs/agent/CODEMAP.md` |
| Run CLI, tests, or check exit semantics | `docs/agent/RUNTIME.md` |
| Inspect or change CI / repository verification | `.github/workflows/ci.yml` + `docs/agent/RUNTIME.md` |
| Consult normative domain specifications | `openspec/specs/` |
| Inspect historical R1 design decisions | `openspec/changes/archive/2026-08-29-clinical-compiler-r1/` |
| Track active feature plans and tasks | active SDD work unit |

## Working Rules

- Inspect live implementation before editing. Keep changes minimal, typed, and reversible.
- Respect the dependency hierarchy: `cli -> pipeline -> {passes, renderers, linter} -> {adapters, pipeline_types} -> core -> types`. Direct imports are explicitly bounded (see `docs/agent/ARCHITECTURE.md`); `core` is a leaf domain layer with zero dependencies on outer compiler layers (intra-core imports between types and IR are permitted).
- Preserve safety invariants: zero runtime dependencies; immutable `tuple` collections; explicit codepoint sort `(field_id, clinical_fact_id)`; LF-only UTF-8 bytes.
- Never conflate source-declared certainty (`source_asserted_certainty`) with compiler certainty (`ClinicalValue.certainty`). `source_kind` informs provenance only.
- Never mutate/populate `core.policy.NEVER_AUTO_TERMS`; effective veto terms come only from an owner-authored policy seed (`PolicyResolution.terms`) or approved-empty deferral (`DEFERRED_BY_OWNER_DECISION`).
- Do not mutate protected paths (`src/clinical_compiler/core/`, `tests/`, `openspec/specs/`, `openspec/changes/archive/`) unless explicitly authorized in the active change plan.
- Update documentation only when the semantic contract owned by that document changes.

## Verification Commands (`--no-sync`)

```bash
# fast feedback
uv run --no-sync pytest -q

# full test suite with branch coverage gate (>= 95.0%)
uv run --no-sync pytest --cov=clinical_compiler --cov-report=term-missing --strict-markers

# linting and strict type checking
uv run --no-sync ruff check src tests
uv run --no-sync mypy --strict src

# structural context validation (requires ACS v1.1 skill tooling)
python "${ACS_ROOT:-$HOME/.claude/skills/agent-context-system}/scripts/validate_agent_context.py" . --strict-generated
```

Success criteria: 0 failed tests, branch coverage >= 95.0%, 0 mypy errors, 0 ruff errors, structural context valid, and CI gate (`gate` job in `.github/workflows/ci.yml`) reporting green. Live protected-`main` enforcement requires the `gate` status check only as confirmed by branch-protection readback.

## References

- `README.md` — user-facing product overview and quick start.
- `docs/agent/ARCHITECTURE.md` — canonical current architecture narrative.
- `docs/architecture.md` — non-authoritative compatibility stub redirecting to canonical docs.
- `docs/compiler-file-guide.md` — detailed static inventory and wayfinding.
- `openspec/specs/` — normative domain specifications.
- `openspec/changes/archive/2026-08-29-clinical-compiler-r1/` — immutable R1 archive.
