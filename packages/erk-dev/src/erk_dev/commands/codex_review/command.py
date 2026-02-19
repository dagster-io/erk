"""Codex code review command."""

import subprocess
from datetime import datetime
from pathlib import Path

import click

from erk_dev.cli.output import user_output

PROMPT_FILENAME = "prompt.txt"


def detect_base_branch(explicit_base: str | None) -> str:
    """Return the branch to use as the diff base."""
    if explicit_base:
        return explicit_base

    current = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    if current in ("main", "master"):
        return "HEAD~1"

    parent = subprocess.run(
        ["gt", "parent", "--no-interactive"],
        capture_output=True,
        text=True,
        check=False,
    )
    if parent.returncode == 0 and parent.stdout.strip():
        return parent.stdout.strip()

    return "main"


def generate_output_filename(current_branch: str, custom_output: str | None) -> str:
    """Generate an output filename based on branch name and timestamp."""
    if custom_output:
        return custom_output

    sanitized_branch = current_branch.replace("/", "__").replace(":", "__")
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"code-review-{sanitized_branch}-{timestamp}.md"


def load_prompt_template(template_path: Path) -> str:
    """Load the Codex prompt template from disk."""
    if not template_path.exists():
        user_output(f"✗ Prompt template not found: {template_path}")
        raise SystemExit(1)

    return template_path.read_text(encoding="utf-8")


def format_prompt(
    template: str,
    base_branch: str,
    current_branch: str,
    output_file: str,
) -> str:
    """Fill in the template placeholders used by Codex."""
    date = datetime.now().strftime("%a %b %d %H:%M:%S %Z %Y")

    return template.format(
        base_branch=base_branch,
        current_branch=current_branch,
        output_file=output_file,
        date=date,
    )


def current_branch_name() -> str:
    """Return the name of the currently checked out branch."""
    return subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def run_codex_review(base_branch: str | None, output: str | None, option_base: str | None) -> None:
    """Execute the Codex review workflow."""
    current = current_branch_name()
    base = detect_base_branch(option_base or base_branch)
    output_file = generate_output_filename(current, output)

    user_output(f"Reviewing: {current} vs {base}")
    user_output(f"Output: {output_file}\n")

    template_path = Path(__file__).parent / PROMPT_FILENAME
    template = load_prompt_template(template_path)
    codex_prompt = format_prompt(template, base, current, output_file)

    result = subprocess.run(
        ["codex", "exec", "--sandbox", "workspace-write", codex_prompt],
        check=True,
    )

    if result.returncode == 0:
        user_output(f"\n✓ Review complete! Saved to {output_file}")


@click.command(name="codex-review")
@click.argument("base_branch", required=False)
@click.option("--base", help="Explicit base branch for comparison")
@click.option("--output", "-o", help="Output file path (default: auto-generated)")
def codex_review_command(base_branch: str | None, base: str | None, output: str | None) -> None:
    """Perform code review using Codex against repository standards."""
    try:
        run_codex_review(base_branch, output, base)
    except KeyboardInterrupt:
        user_output("\n✗ Interrupted by user")
        raise SystemExit(130) from None
