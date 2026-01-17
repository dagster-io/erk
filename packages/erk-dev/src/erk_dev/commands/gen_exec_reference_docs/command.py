"""Generate erk exec commands reference documentation."""

import subprocess
from pathlib import Path

import click

from erk_dev.exec_reference.generate import collect_exec_commands, generate_exec_reference


def find_repo_root(start: Path) -> Path | None:
    """Walk up to find repo root (contains pyproject.toml with [tool.uv.workspace])."""
    current = start
    while current != current.parent:
        pyproject = current / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text(encoding="utf-8")
            if "[tool.uv.workspace]" in content:
                return current
        current = current.parent
    return None


def _run_prettier(file_path: Path) -> bool:
    """Run prettier on a file to format it. Returns True if successful."""
    result = subprocess.run(
        ["prettier", "--write", str(file_path)],
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


@click.command("gen-exec-reference-docs")
@click.option("--check", is_flag=True, help="Check if file is up to date (for CI)")
def gen_exec_reference_docs_command(*, check: bool) -> None:
    """Generate erk exec commands reference documentation.

    This command introspects the `erk exec` command group and generates
    a skill at .claude/skills/erk-exec-reference/SKILL.md.

    The file is formatted with prettier after generation to match CI style.
    Use --check in CI to verify the document is in sync.
    """
    repo_root = find_repo_root(Path.cwd())
    if repo_root is None:
        raise click.ClickException("Could not find repository root")

    output_path = repo_root / ".claude" / "skills" / "erk-exec-reference" / "SKILL.md"

    # Collect and generate
    commands = collect_exec_commands()
    content = generate_exec_reference(commands)

    if check:
        # Check mode: write to temp file, format, then compare
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        # Format the temp file
        _run_prettier(tmp_path)
        formatted_content = tmp_path.read_text(encoding="utf-8")
        tmp_path.unlink()

        if not output_path.exists():
            click.echo(f"FAIL: {output_path.relative_to(repo_root)} does not exist")
            click.echo("Run 'erk-dev gen-exec-reference-docs' to generate it.")
            raise SystemExit(1)

        existing = output_path.read_text(encoding="utf-8")
        if existing != formatted_content:
            click.echo(f"FAIL: {output_path.relative_to(repo_root)} is out of date")
            click.echo("Run 'erk-dev gen-exec-reference-docs' to regenerate it.")
            raise SystemExit(1)

        click.echo(f"OK: {output_path.relative_to(repo_root)} is up to date")
    else:
        # Generate mode: write the file and format with prettier
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")

        # Format with prettier
        if _run_prettier(output_path):
            click.echo(f"Generated {output_path.relative_to(repo_root)} (formatted)")
        else:
            click.echo(f"Generated {output_path.relative_to(repo_root)} (prettier failed)")

        click.echo(f"  {len(commands)} top-level commands documented")
