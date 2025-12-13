"""Get release information from CHANGELOG.md for automation."""

import json
import re
from pathlib import Path

import click

from erk_dev.commands.bump_version.command import find_repo_root, get_current_version
from erk_dev.context import ErkDevContext
from erk_shared.git.abc import Git


def get_version_tag(git: Git, repo_root: Path, version: str) -> str | None:
    """Get the git tag for a version if it exists.

    Args:
        git: Git gateway for tag operations
        repo_root: Repository root path
        version: Version string (e.g., '0.2.6')

    Returns:
        Tag name (e.g., 'v0.2.6') if it exists, None otherwise.
    """
    tag_name = f"v{version}"
    if git.tag_exists(repo_root, tag_name):
        return tag_name
    return None


def parse_last_release(changelog_path: Path) -> tuple[str, str] | None:
    """Parse the most recent versioned release from CHANGELOG.md.

    Returns (version, date) tuple or None if no releases found.
    Skips [Unreleased] section.
    """
    if not changelog_path.exists():
        return None

    content = changelog_path.read_text(encoding="utf-8")

    # Match versioned release headers: ## [X.Y.Z] - YYYY-MM-DD
    pattern = r"## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})"
    match = re.search(pattern, content)

    if match is None:
        return None

    return (match.group(1), match.group(2))


@click.command("release-info")
@click.option("--json-output", "json_output", is_flag=True, help="Output as JSON")
@click.pass_context
def release_info_command(ctx: click.Context, json_output: bool) -> None:
    """Get release information from CHANGELOG.md.

    Outputs current version (from pyproject.toml) and last released
    version/date (from CHANGELOG.md) for use in release automation.
    """
    erk_ctx: ErkDevContext = ctx.obj
    git = erk_ctx.git

    repo_root = find_repo_root(Path.cwd())
    if repo_root is None:
        if json_output:
            click.echo(json.dumps({"success": False, "error": "Could not find repository root"}))
        else:
            click.echo("Error: Could not find repository root", err=True)
        raise SystemExit(1)

    current_version = get_current_version(repo_root)
    changelog_path = repo_root / "CHANGELOG.md"
    last_release = parse_last_release(changelog_path)

    # Check for version tag
    current_tag = get_version_tag(git, repo_root, current_version) if current_version else None

    if json_output:
        result = {
            "success": True,
            "current_version": current_version,
            "current_version_tag": current_tag,
            "last_version": last_release[0] if last_release else None,
            "last_date": last_release[1] if last_release else None,
        }
        click.echo(json.dumps(result))
    else:
        click.echo(f"Current version: {current_version or 'unknown'}")
        if current_tag:
            click.echo(f"Current version tag: {current_tag}")
        else:
            click.echo("Current version tag: not found (run `erk-dev release-tag` to create)")
        if last_release:
            click.echo(f"Last release: {last_release[0]} ({last_release[1]})")
        else:
            click.echo("Last release: none found in CHANGELOG.md")
