"""Check AGENTS.md standard compliance command.

This command validates that repositories follow the AGENTS.md standard where:
- AGENTS.md is the primary context file
- CLAUDE.md contains '@AGENTS.md' reference for backwards compatibility

See: https://code.claude.com/docs/en/claude-code-on-the-web
"""

import subprocess
from pathlib import Path

import click

from erk_shared.output.output import user_output


@click.command(name="check")
def check_command() -> None:
    """Validate AGENTS.md standard compliance in the repository.

    Checks that:
    - Every CLAUDE.md file has a peer AGENTS.md file
    - Every CLAUDE.md file contains '@AGENTS.md' reference

    Exit codes:
    - 0: All checks passed
    - 1: Violations found
    """
    # Find repository root
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    repo_root_str = result.stdout.strip()
    repo_root_path = Path(repo_root_str)

    if not repo_root_path.exists():
        user_output(click.style("✗ Error: Repository root not found", fg="red"))
        raise SystemExit(1)

    # Find all CLAUDE.md and AGENTS.md files
    claude_files = list(repo_root_path.rglob("CLAUDE.md"))
    agents_files = list(repo_root_path.rglob("AGENTS.md"))

    if len(claude_files) == 0 and len(agents_files) == 0:
        message = "ℹ️  No CLAUDE.md or AGENTS.md files found in repository"
        user_output(click.style(message, fg="cyan"))
        raise SystemExit(0)

    # Track violations
    missing_agents: list[Path] = []  # CLAUDE.md without peer AGENTS.md
    missing_claude: list[Path] = []  # AGENTS.md without peer CLAUDE.md
    invalid_content: list[Path] = []

    for claude_path in claude_files:
        # Check for peer AGENTS.md
        agents_path = claude_path.parent / "AGENTS.md"
        if not agents_path.exists():
            missing_agents.append(claude_path.parent)
            continue

        # Check CLAUDE.md content
        content = claude_path.read_text(encoding="utf-8")
        if content.strip() != "@AGENTS.md":
            invalid_content.append(claude_path)

    # Check that all AGENTS.md files have peer CLAUDE.md
    for agents_path in agents_files:
        claude_path = agents_path.parent / "CLAUDE.md"
        if not claude_path.exists():
            missing_claude.append(agents_path.parent)

    # Report results
    violation_count = len(missing_agents) + len(missing_claude) + len(invalid_content)
    if violation_count == 0:
        user_output(click.style("✓ AGENTS.md standard: PASSED", fg="green", bold=True))
        user_output()
        user_output("All CLAUDE.md and AGENTS.md files properly paired.")
        user_output()
        user_output(f"CLAUDE.md files checked: {len(claude_files)}")
        user_output("Violations: 0")
        raise SystemExit(0)

    # Found violations
    user_output(click.style("✗ AGENTS.md standard: FAILED", fg="red", bold=True))
    user_output()
    plural = "s" if violation_count != 1 else ""
    user_output(f"Found {violation_count} violation{plural}:")
    user_output()

    if len(missing_agents) > 0:
        user_output(click.style("Missing AGENTS.md:", fg="yellow"))
        for path in missing_agents:
            rel_path = path.relative_to(repo_root_path)
            user_output(f"  • {click.style(str(rel_path) + '/', fg='cyan')}")
        user_output()

    if len(missing_claude) > 0:
        user_output(click.style("Missing CLAUDE.md:", fg="yellow"))
        for path in missing_claude:
            rel_path = path.relative_to(repo_root_path)
            user_output(f"  • {click.style(str(rel_path) + '/', fg='cyan')}")
        user_output()

    if len(invalid_content) > 0:
        user_output(click.style("Invalid CLAUDE.md content:", fg="yellow"))
        for path in invalid_content:
            rel_path = path.relative_to(repo_root_path)
            content = path.read_text(encoding="utf-8")
            styled_path = click.style(str(rel_path), fg="cyan")
            user_output(f"  • {styled_path}: Content is '{content.strip()}', expected '@AGENTS.md'")
        user_output()

    user_output("Fix these issues and run again.")
    raise SystemExit(1)
