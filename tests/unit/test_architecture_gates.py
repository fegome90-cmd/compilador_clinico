"""Production-only import boundary gates for Clinical Compiler Stage 1."""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = ROOT / "src" / "clinical_compiler"
PACKAGE = "clinical_compiler"

PASS_FORBIDDEN_MODULES = frozenset(
    {
        "cli",
        "pipeline",
        "renderers",
        "linter",
        "os",
        "pathlib",
        "socket",
        "subprocess",
        "random",
        "time",
        "datetime",
        "locale",
        "urllib",
        "http",
    }
)
HOST_MODULES = frozenset({"cli", "api", "mcp", "host"})


def _module_name(path: Path) -> str:
    relative = path.relative_to(SOURCE_ROOT).with_suffix("")
    parts = (PACKAGE, *relative.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _resolve_import(current: str, node: ast.ImportFrom) -> str:
    if node.level == 0:
        return node.module or ""
    package_parts = current.split(".")[:-1]
    keep = max(0, len(package_parts) - (node.level - 1))
    base = package_parts[:keep]
    if node.module:
        base.extend(node.module.split("."))
    return ".".join(base)


def _known_internal_modules() -> frozenset[str]:
    return frozenset(_module_name(path) for path in SOURCE_ROOT.rglob("*.py"))


KNOWN_INTERNAL_MODULES = _known_internal_modules()


def _import_targets(current: str, node: ast.ImportFrom) -> tuple[str, ...]:
    base = _resolve_import(current, node)
    targets: list[str] = [base] if base else []
    for alias in node.names:
        candidate = f"{base}.{alias.name}" if base else alias.name
        if candidate in KNOWN_INTERNAL_MODULES:
            targets.append(candidate)
    return tuple(dict.fromkeys(targets))


def _imports(path: Path) -> Iterator[tuple[str, str]]:
    current = _module_name(path)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name, f"{path}:{node.lineno}"
        elif isinstance(node, ast.ImportFrom):
            for target in _import_targets(current, node):
                yield target, f"{path}:{node.lineno}"


def _production_imports() -> tuple[tuple[Path, str, str], ...]:
    return tuple(
        (path, target, location)
        for path in sorted(SOURCE_ROOT.rglob("*.py"))
        for target, location in _imports(path)
    )


def _internal_parts(target: str) -> tuple[str, ...]:
    if not target.startswith(f"{PACKAGE}."):
        return ()
    return tuple(target.split(".")[1:])


def test_production_import_boundaries_are_respected() -> None:
    """A1/A2/A3/A5 must hold without importing production modules."""
    violations: list[str] = []
    for path, target, location in _production_imports():
        parts = _internal_parts(target)
        relative = path.relative_to(SOURCE_ROOT)

        if (
            relative.parts
            and relative.parts[0] == "core"
            and parts
            and parts[0] != "core"
        ):
            violations.append(f"A1 core reverse edge: {location} -> {target}")

        if relative.parts and relative.parts[0] == "passes":
            if parts and parts[0] in PASS_FORBIDDEN_MODULES:
                violations.append(f"A2 forbidden pass edge: {location} -> {target}")
            if not parts and target.split(".", 1)[0] in PASS_FORBIDDEN_MODULES:
                violations.append(f"A2 forbidden pass import: {location} -> {target}")

        if relative.parts and relative.parts[0] in {"renderers", "linter"}:
            owner = relative.parts[0]
            if (
                parts
                and parts[0] in {"renderers", "linter", "pipeline", "passes", "cli"}
                and not (
                    (owner == "renderers" and parts[0] == "renderers")
                    or (owner == "linter" and parts[0] == "linter")
                )
            ):
                violations.append(f"A3 forbidden {owner} edge: {location} -> {target}")

        if relative.parts and relative.parts[0] != "cli" and parts and parts[0] in HOST_MODULES:
            violations.append(f"A5 reverse host edge: {location} -> {target}")

    assert violations == [], "\n".join(violations)


@pytest.mark.parametrize(
    ("owner", "imported", "expected"),
    (
        ("core", "pipeline", "clinical_compiler.pipeline"),
        ("passes", "cli", "clinical_compiler.cli"),
        ("renderers", "linter", "clinical_compiler.linter"),
        ("pipeline", "cli", "clinical_compiler.cli"),
    ),
)
def test_package_root_import_aliases_are_expanded_for_boundary_rules(
    owner: str, imported: str, expected: str
) -> None:
    """Package-root aliases must expose the internal module they import."""
    node = ast.ImportFrom(
        module=PACKAGE,
        names=[ast.alias(name=imported, asname=f"alias_{imported}")],
        level=0,
    )
    targets = _import_targets(f"{PACKAGE}.{owner}.module", node)
    assert expected in targets
