"""Validate agent documentation frontmatter.

This command validates that all markdown files in docs/agent/ have valid
frontmatter with required fields: title and read_when.
"""

import subprocess
from pathlib import Path

import click

from erk.kits.cli.output import user_output
from erk.kits.operations.agent_docs import validate_agent_docs


@click.command(name="validate")
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show details for all files, not just errors.",
)
def validate_command(*, verbose: bool) -> None:
    """Validate agent documentation frontmatter.

    Checks that all markdown files in docs/agent/ have valid frontmatter:
    - title: Human-readable document title
    - read_when: List of conditions when agent should read this doc

    Index files (index.md) are skipped as they are auto-generated.

    Exit codes:
    - 0: All files are valid
    - 1: Validation errors found
    """
    # Find repository root
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    project_root = Path(result.stdout.strip())

    if not project_root.exists():
        user_output(click.style("✗ Error: Repository root not found", fg="red"))
        raise SystemExit(1)

    agent_docs_dir = project_root / "docs" / "agent"
    if not agent_docs_dir.exists():
        user_output(click.style("ℹ️  No docs/agent/ directory found", fg="cyan"))
        raise SystemExit(0)

    # Validate all files
    results = validate_agent_docs(project_root)

    if len(results) == 0:
        user_output(click.style("ℹ️  No agent documentation files found", fg="cyan"))
        raise SystemExit(0)

    valid_count = sum(1 for r in results if r.is_valid)
    invalid_count = len(results) - valid_count

    # Show results
    if verbose or invalid_count > 0:
        for result in results:
            if result.is_valid:
                if verbose:
                    status = click.style("✓", fg="green")
                    user_output(f"{status} {result.file_path}")
            else:
                status = click.style("✗", fg="red")
                user_output(f"{status} {result.file_path}")
                for error in result.errors:
                    user_output(f"    {error}")

    # Summary
    user_output()
    if invalid_count == 0:
        user_output(click.style("✓ Agent docs validation: PASSED", fg="green", bold=True))
        user_output()
        user_output(f"Files validated: {len(results)}")
        user_output("All files have valid frontmatter!")
    else:
        user_output(click.style("✗ Agent docs validation: FAILED", fg="red", bold=True))
        user_output()
        user_output(f"Files validated: {len(results)}")
        user_output(f"  ✓ Valid: {valid_count}")
        user_output(f"  ✗ Invalid: {invalid_count}")
        user_output()
        user_output("Required frontmatter format:")
        user_output("  ---")
        user_output("  title: Document Title")
        user_output("  read_when:")
        user_output('    - "when to read this doc"')
        user_output("  ---")
        raise SystemExit(1)
