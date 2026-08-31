# Runtime and Toolchain

## Canonical Runtime Sources

Live dependencies and toolchain configuration are defined in:
- `pyproject.toml` — build system, entry point, empty runtime dependencies, and dev tool settings.
- `uv.lock` — pinned development dependencies for reproduction.

## Runtime Topology

The clinical compiler operates as a single synchronous command-line process.

| Process | Role | Interface | Depends on |
|---|---|---|---|
| `clinical-compiler` | Deterministic CLI compiler process | CLI arguments (`INPUT`, `--mode`, `--policy-seed`, `--output`), standard streams (stdin, stdout, stderr), and exit codes | Local filesystem and Python standard library only |

No daemon, background worker, web server, database connection, or network socket is spawned.

## Technology Roles

### Python Runtime
- **Role:** Python 3.11+ standard library execution environment.
- **Owns:** Core domain models, transformation passes, deterministic rendering, and conformance linting.
- **Do not use it for:** External network requests or dynamically evaluated code (`eval`, `exec`).

### uv Package Manager
- **Role:** Development environment management and toolchain execution.
- **Owns:** Dependency resolution and executing dev tools via `uv run --no-sync`.
- **Do not use it for:** Production runtime packaging; runtime dependencies remain strictly empty.

### Developer Tooling (`ruff`, `mypy`, `pytest`)
- **Role:** Code formatting, linting, strict static typing, unit testing, and coverage gates.
- **Owns:** Pre-merge verification and static quality assurance.
- **Do not use it for:** Core compiler logic.

## Development Environment

- Runtime: Python >= 3.11
- Package Manager: `uv`
- Build Backend: `setuptools.build_meta`
- Platform: macOS / Linux (POSIX compatible)

## Commands

### Execution & Compilation
- **Compile file to stdout:** `clinical-compiler compile input.jsonl`
- **Compile to output file:** `clinical-compiler compile input.jsonl --output out.txt`
- **Compile with custom policy seed:** `clinical-compiler compile input.jsonl --policy-seed seed.json`
- **Specify document mode:** `clinical-compiler compile input.jsonl --mode NURSING_RECORD_TELEGRAPHIC`

### Verification & Quality Gates (`--no-sync`)
- **Fast tests:** `uv run --no-sync pytest -q`
- **Full tests with branch coverage:** `uv run --no-sync pytest --cov=clinical_compiler --cov-report=term-missing --strict-markers`
- **Golden determinism tests:** `uv run --no-sync pytest tests/unit/test_integration_golden_determinism.py -v`
- **Linting:** `uv run --no-sync ruff check src tests`
- **Strict type checking:** `uv run --no-sync mypy --strict src`

## Exit Behavior and Codes

The compiler maps execution outcomes to strict process exit codes:
- `0`: Success (clean document compiled and emitted).
- `2`: CLI usage error, invalid options, or unresolved policy from an invalid/malformed `--policy-seed`.
- `3`: Input contract fault (`INPUT_CONTRACT_ERROR` — malformed JSON, unknown keys, invalid schema).
- `4`: Field type mismatch (`TYPE_ERROR` — non-conforming exact runtime type).
- `5`: Semantic ambiguity (`SEMANTIC_AMBIGUITY_BLOCK` — multiple interpretations without disambiguator).
- `6`: Policy violation (`POLICY_VIOLATION` — vetoed term present).
- `7`: Provenance fault (`PROVENANCE_ERROR` — unresolvable source fact reference).
- `8`: Document selection fault (`DOCUMENT_SELECTION_ERROR` — no admissible entries for target mode).
- `9`: Rendering fault (`RENDER_ERROR` — internal IR / rendering inconsistency).
- `10`: Conformance lint failure (`LINT_FAILURE` — rendered bytes violate mode grammar/vocabulary).
- `70`: Unexpected internal compiler failure or unhandled runtime exception.

## Output and Atomic Writes

- **Stdout:** Emits generated UTF-8 document bytes only when execution succeeds with exit code 0 and `--output` is not specified.
- **Stderr:** Emits structured diagnostics on any quarantined fact, policy rejection, or syntax error.
- **File Output (`--output PATH`):** Writes output atomically using a temporary file in the target directory followed by flush, `os.fsync`, and atomic `os.replace`. Failed runs leave target destination untouched.

## Environment Contract

The production compiler defines zero required or optional environment variables.

- **`PYTHONHASHSEED`:** Used exclusively in the test harness (`tests/unit/test_cli.py` and `tests/unit/test_integration_golden_determinism.py`) to verify that dictionary/hash order variations across sub-interpreters do not alter deterministic byte output. It is not an operational or deployment configuration variable.

## Observability

- **Diagnostics:** Emitted to `sys.stderr` in stable diagnostic format (`CODE: message` or `CODE: message (path)`).
- **Audit Lineage:** Every canonical fact references constituent source facts (`source_fact_refs`).
- **Telemetry / Logs / Metrics:** No external logging daemon, APM, or remote telemetry is present or permitted.
