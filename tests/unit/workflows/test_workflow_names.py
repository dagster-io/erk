"""Tests to validate GitHub Actions workflow naming conventions.

All workflow files must:
1. Have a `name:` field in kebab-case
2. Have `name:` match the filename (without .yml)
3. Have valid workflow_run.workflows references (if any)
4. Have autofix triggers match AUTOFIX_TRIGGER_WORKFLOWS constant
"""

import re
from pathlib import Path

from erk.cli.constants import AUTOFIX_TRIGGER_WORKFLOWS


def _workflows_dir() -> Path:
    """Return path to .github/workflows directory."""
    repo_root = Path(__file__).parent.parent.parent.parent
    return repo_root / ".github" / "workflows"


def _extract_workflow_name(path: Path) -> str | None:
    """Extract workflow name using regex (more robust than full YAML parsing).

    This handles files with complex embedded scripts that break YAML parsers.
    """
    content = path.read_text(encoding="utf-8")
    match = re.search(r"^name:\s*(.+)$", content, re.MULTILINE)
    if match:
        name = match.group(1).strip()
        if name.startswith('"') and name.endswith('"'):
            return name[1:-1]
        if name.startswith("'") and name.endswith("'"):
            return name[1:-1]
        return name
    return None


def _extract_workflow_run_workflows(path: Path) -> list[str]:
    """Extract workflow_run.workflows list using regex.

    Handles cases where full YAML parsing fails due to complex scripts.
    """
    content = path.read_text(encoding="utf-8")
    match = re.search(r"workflow_run:\s*\n\s+workflows:\s*\[([^\]]+)\]", content, re.MULTILINE)
    if match:
        workflows_str = match.group(1)
        workflows: list[str] = []
        for item in workflows_str.split(","):
            item = item.strip().strip('"').strip("'")
            if item:
                workflows.append(item)
        return workflows
    return []


def _is_kebab_case(s: str) -> bool:
    """Check if string is kebab-case (lowercase with hyphens)."""
    return bool(re.match(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$", s))


def test_workflow_names_are_kebab_case() -> None:
    """All workflow name: fields must be kebab-case."""
    workflows_dir = _workflows_dir()
    if not workflows_dir.exists():
        return

    errors: list[str] = []
    for workflow_file in workflows_dir.glob("*.yml"):
        name = _extract_workflow_name(workflow_file)
        if name is None:
            errors.append(f"{workflow_file.name}: missing 'name' field")
            continue
        if not _is_kebab_case(name):
            errors.append(f"{workflow_file.name}: name '{name}' is not kebab-case")

    if errors:
        raise AssertionError("Workflow naming errors:\n  " + "\n  ".join(errors))


def test_workflow_names_match_filenames() -> None:
    """All workflow name: fields must match filename (without .yml)."""
    workflows_dir = _workflows_dir()
    if not workflows_dir.exists():
        return

    errors: list[str] = []
    for workflow_file in workflows_dir.glob("*.yml"):
        name = _extract_workflow_name(workflow_file)
        expected_name = workflow_file.stem

        if name is None:
            continue

        if name != expected_name:
            errors.append(f"{workflow_file.name}: name '{name}' != expected '{expected_name}'")

    if errors:
        raise AssertionError("Workflow name/filename mismatches:\n  " + "\n  ".join(errors))


def test_workflow_run_references_exist() -> None:
    """All workflow_run.workflows references must point to existing workflows."""
    workflows_dir = _workflows_dir()
    if not workflows_dir.exists():
        return

    all_workflow_names: set[str] = set()
    for workflow_file in workflows_dir.glob("*.yml"):
        name = _extract_workflow_name(workflow_file)
        if name:
            all_workflow_names.add(name)

    errors: list[str] = []
    for workflow_file in workflows_dir.glob("*.yml"):
        referenced_workflows = _extract_workflow_run_workflows(workflow_file)
        for ref in referenced_workflows:
            if ref not in all_workflow_names:
                errors.append(f"{workflow_file.name}: references unknown workflow '{ref}'")

    if errors:
        raise AssertionError("Invalid workflow_run references:\n  " + "\n  ".join(errors))


def test_autofix_triggers_match_constant() -> None:
    """autofix.yml workflow_run triggers must match AUTOFIX_TRIGGER_WORKFLOWS."""
    workflows_dir = _workflows_dir()
    autofix_path = workflows_dir / "autofix.yml"

    if not autofix_path.exists():
        return

    referenced_workflows = set(_extract_workflow_run_workflows(autofix_path))

    if referenced_workflows != AUTOFIX_TRIGGER_WORKFLOWS:
        missing = AUTOFIX_TRIGGER_WORKFLOWS - referenced_workflows
        extra = referenced_workflows - AUTOFIX_TRIGGER_WORKFLOWS

        errors: list[str] = []
        if missing:
            errors.append(f"Missing from autofix.yml: {sorted(missing)}")
        if extra:
            errors.append(f"Extra in autofix.yml: {sorted(extra)}")

        raise AssertionError(
            "autofix.yml triggers don't match AUTOFIX_TRIGGER_WORKFLOWS:\n  " + "\n  ".join(errors)
        )
