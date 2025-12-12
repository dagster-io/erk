"""Create release branch and tag after bump-version."""

import subprocess
from pathlib import Path

import click

from erk_dev.cli.output import user_output
from erk_dev.commands.bump_version.command import find_repo_root, get_current_version


def _tag_exists(tag: str) -> bool:
    """Check if a git tag already exists."""
    result = subprocess.run(
        ["git", "tag", "-l", tag],
        capture_output=True,
        text=True,
        check=True,
    )
    return tag in result.stdout.strip().split("\n")


def _working_directory_clean() -> bool:
    """Check if working directory has uncommitted changes."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip() == ""


def _run_git_command(args: list[str], dry_run: bool, description: str) -> bool:
    """Run a git command, or print what would run in dry-run mode.

    Returns True if successful (or dry-run), False on failure.
    """
    cmd = ["git", *args]
    if dry_run:
        user_output(f"[DRY RUN] Would run: {' '.join(cmd)}")
        return True

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        user_output(f"Error: {description} failed")
        if result.stderr:
            user_output(result.stderr.strip())
        return False
    return True


@click.command("release")
@click.option("--dry-run", is_flag=True, help="Show what would be done")
def release_command(dry_run: bool) -> None:
    """Create release branch and tag after bump-version.

    This command creates a 'release' branch pointing to HEAD and creates
    an annotated tag for the current version. Both are then pushed to origin.

    Workflow:
        $ erk-dev bump-version           # Updates to 0.2.4
        # ... merge version bump into master using your preferred workflow ...
        $ erk co master                  # Switch to master and pull
        $ erk-dev release                # Creates release branch + tag, pushes both
    """
    # Validation (LBYL)
    repo_root = find_repo_root(Path.cwd())
    if repo_root is None:
        raise click.ClickException("Could not find repository root")

    version = get_current_version(repo_root)
    if version is None:
        raise click.ClickException("Could not detect current version from pyproject.toml")

    tag_name = f"v{version}"

    if _tag_exists(tag_name):
        raise click.ClickException(
            f"Version {version} already released (tag {tag_name} exists). "
            "Did you forget to run bump-version?"
        )

    if not _working_directory_clean():
        raise click.ClickException("Working directory has uncommitted changes")

    # Display validation status
    if dry_run:
        user_output("[DRY RUN MODE]\n")

    user_output("Validating...")
    user_output(f"  Current version: {version}")
    user_output(f"  Tag {tag_name} does not exist")
    user_output("  Working directory clean")
    user_output("")

    # Git operations
    operations = [
        (["branch", "-f", "release", "HEAD"], "create release branch"),
        (["tag", "-a", tag_name, "-m", f"Release {version}"], "create tag"),
        (["push", "origin", "release", "--force-with-lease"], "push release branch"),
        (["push", "origin", tag_name], "push tag"),
    ]

    for args, description in operations:
        if not _run_git_command(args, dry_run, description):
            raise click.ClickException(f"Failed to {description}")

    if dry_run:
        user_output(f"\nRelease {version} would be created")
    else:
        user_output(f"\nRelease {version} created successfully")
