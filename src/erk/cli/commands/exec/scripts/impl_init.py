"""Initialize implementation by validating .impl/ folder.

This exec command validates .impl/ folder for /erk:plan-implement:
- Validates .impl/ folder structure (plan.md exists)
- Checks for GitHub issue tracking (issue.json)
- Parses "Related Documentation" section for skills and docs

Usage:
    erk exec impl-init --json

Output:
    JSON with validation status and related docs
    Always outputs JSON (for machine parsing by slash command)

Exit Codes:
    0: Success
    1: Validation error

Examples:
    $ erk exec impl-init --json
    {"valid": true, "has_plan_tracking": true, ...}
"""

import json
import re
from pathlib import Path
from typing import NoReturn

import click

from erk_shared.context.helpers import require_cwd, require_git
from erk_shared.impl_folder import read_plan_ref, resolve_impl_dir


def _error_json(error_type: str, message: str) -> NoReturn:
    """Output error as JSON and exit with code 1."""
    result = {"valid": False, "error_type": error_type, "message": message}
    click.echo(json.dumps(result))
    raise SystemExit(1)


def _validate_impl_folder(ctx: click.Context) -> Path:
    """Validate implementation folder exists and has required files.

    Uses resolve_impl_dir() for branch-scoped discovery.

    Args:
        ctx: Click context for dependency injection.

    Returns:
        Path to the validated impl directory.

    Raises:
        SystemExit: If validation fails
    """
    cwd = require_cwd(ctx)
    git = require_git(ctx)
    branch_name = git.branch.get_current_branch(cwd)

    impl_dir = resolve_impl_dir(cwd, branch_name=branch_name)

    if impl_dir is None:
        result = {
            "valid": False,
            "error_type": "no_impl_folder",
            "message": "No implementation folder found in current directory",
        }
        click.echo(json.dumps(result))
        raise SystemExit(1)

    plan_file = impl_dir / "plan.md"
    if not plan_file.exists():
        _error_json("no_plan_file", f"No plan.md found in {impl_dir.name}/ folder")

    return impl_dir


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
@click.pass_context
def impl_init(ctx: click.Context, json_output: bool) -> None:
    """Initialize implementation by validating .impl/ folder.

    Validates .impl/ folder for /erk:plan-implement.
    Returns structured JSON with validation status and related documentation.
    """
    # Validate folder structure
    impl_dir = _validate_impl_folder(ctx)

    # Get plan reference info
    plan_ref = read_plan_ref(impl_dir)
    has_plan_tracking = plan_ref is not None
    plan_number = int(plan_ref.plan_id) if plan_ref else None

    # Read plan content
    plan_file = impl_dir / "plan.md"
    plan_content = plan_file.read_text(encoding="utf-8")

    # Extract related documentation
    related_docs = _extract_related_docs(plan_content)

    # Build result
    result: dict = {
        "valid": True,
        "has_plan_tracking": has_plan_tracking,
        "related_docs": related_docs,
    }

    if plan_number is not None:
        result["plan_number"] = plan_number

    click.echo(json.dumps(result))
