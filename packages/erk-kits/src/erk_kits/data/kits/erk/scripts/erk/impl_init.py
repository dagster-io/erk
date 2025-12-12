"""Initialize implementation by validating .impl/ folder and extracting phases.

This kit CLI command combines validation and initialization for /erk:plan-implement:
- Validates .impl/ folder structure (plan.md, progress.md exist)
- Checks for GitHub issue tracking (issue.json)
- Extracts phases from plan.md
- Parses "Related Documentation" section for skills and docs

Usage:
    erk kit exec erk impl-init --json

Output:
    JSON with validation status, phases, and related docs
    Always outputs JSON (for machine parsing by slash command)

Exit Codes:
    0: Success
    1: Validation error

Examples:
    $ erk kit exec erk impl-init --json
    {"valid": true, "impl_type": "impl", "has_issue_tracking": true, ...}
"""

import json
import re
from pathlib import Path
from typing import NoReturn

import click

from erk_shared.impl_folder import (
    parse_progress_frontmatter,
    read_issue_reference,
)


def _error_json(error_type: str, message: str) -> NoReturn:
    """Output error as JSON and exit with code 1."""
    result = {"valid": False, "error_type": error_type, "message": message}
    click.echo(json.dumps(result))
    raise SystemExit(1)


def _validate_impl_folder() -> tuple[Path, str]:
    """Validate .impl/ or .worker-impl/ folder exists and has required files.

    Returns:
        Tuple of (impl_dir Path, impl_type string)

    Raises:
        SystemExit: If validation fails
    """
    cwd = Path.cwd()

    # Check .impl/ first, then .worker-impl/
    impl_dir = cwd / ".impl"
    impl_type = "impl"

    if not impl_dir.exists():
        impl_dir = cwd / ".worker-impl"
        impl_type = "worker-impl"

    if not impl_dir.exists():
        _error_json(
            "no_impl_folder",
            "No .impl/ or .worker-impl/ folder found in current directory",
        )

    plan_file = impl_dir / "plan.md"
    if not plan_file.exists():
        _error_json("no_plan_file", f"No plan.md found in {impl_dir.name}/ folder")

    progress_file = impl_dir / "progress.md"
    if not progress_file.exists():
        _error_json("no_progress_file", f"No progress.md found in {impl_dir.name}/ folder")

    return impl_dir, impl_type


def _extract_phases_from_frontmatter(impl_dir: Path) -> list[dict[str, str | int]]:
    """Extract phases from progress.md frontmatter steps array.

    Args:
        impl_dir: Path to .impl/ directory

    Returns:
        List of phase dicts with 'number' and 'text' keys
    """
    progress_file = impl_dir / "progress.md"
    content = progress_file.read_text(encoding="utf-8")
    frontmatter = parse_progress_frontmatter(content)

    if frontmatter is None:
        return []

    steps = frontmatter.get("steps", [])
    phases = []
    for i, step in enumerate(steps, start=1):
        if isinstance(step, dict) and "text" in step:
            phases.append({"number": i, "text": step["text"]})

    return phases


def _extract_related_docs(plan_content: str) -> dict[str, list[str]]:
    """Extract Related Documentation section from plan content.

    Parses markdown like:
    ## Related Documentation

    **Skills:**
    - `dignified-python-313`

    **Docs:**
    - [Kit CLI Testing](docs/agent/testing/kit-cli-testing.md)

    Args:
        plan_content: Full plan markdown content

    Returns:
        Dict with 'skills' and 'docs' lists
    """
    result: dict[str, list[str]] = {"skills": [], "docs": []}

    # Find Related Documentation section
    related_docs_pattern = re.compile(
        r"##\s+Related Documentation\s*\n(.*?)(?=\n##|\Z)",
        re.DOTALL | re.IGNORECASE,
    )
    match = related_docs_pattern.search(plan_content)

    if match is None:
        return result

    section = match.group(1)

    # Extract skills (backtick-enclosed names after bullet points)
    skills_section = re.search(r"\*\*Skills:\*\*\s*\n(.*?)(?=\*\*|\Z)", section, re.DOTALL)
    if skills_section:
        skill_pattern = re.compile(r"-\s*`([^`]+)`")
        result["skills"] = skill_pattern.findall(skills_section.group(1))

    # Extract docs (markdown links or plain paths)
    docs_section = re.search(r"\*\*Docs:\*\*\s*\n(.*?)(?=\*\*|\Z)", section, re.DOTALL)
    if docs_section:
        # Match markdown links [text](path) or backtick paths `path`
        link_pattern = re.compile(r"-\s*(?:\[[^\]]*\]\(([^)]+)\)|`([^`]+)`)")
        for m in link_pattern.finditer(docs_section.group(1)):
            doc_path = m.group(1) or m.group(2)
            if doc_path:
                result["docs"].append(doc_path)

    return result


@click.command(name="impl-init")
@click.option("--json", "json_output", is_flag=True, default=True, help="Output JSON (default)")
def impl_init(json_output: bool) -> None:
    """Initialize implementation by validating .impl/ folder and extracting phases.

    Combines validation (check-impl) with phase extraction for /erk:plan-implement.
    Returns structured JSON with validation status, phases, and related documentation.
    """
    # Validate folder structure
    impl_dir, impl_type = _validate_impl_folder()

    # Get issue reference info
    issue_ref = read_issue_reference(impl_dir)
    has_issue_tracking = issue_ref is not None
    issue_number = issue_ref.issue_number if issue_ref else None

    # Read plan content
    plan_file = impl_dir / "plan.md"
    plan_content = plan_file.read_text(encoding="utf-8")

    # Extract phases from progress.md frontmatter
    phases = _extract_phases_from_frontmatter(impl_dir)

    # Extract related documentation
    related_docs = _extract_related_docs(plan_content)

    # Build result
    result: dict = {
        "valid": True,
        "impl_type": impl_type,
        "has_issue_tracking": has_issue_tracking,
        "phases": phases,
        "related_docs": related_docs,
    }

    if issue_number is not None:
        result["issue_number"] = issue_number

    click.echo(json.dumps(result))
