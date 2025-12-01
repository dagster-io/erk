"""Publish release command - upload prepared artifacts to PyPI."""

from pathlib import Path

import click

from erk_dev.cli.output import user_output
from erk_dev.commands.publish_to_pypi.shared import (
    get_current_version,
    get_workspace_packages,
    normalize_package_name,
    publish_all_packages,
    push_to_remote,
)


def validate_artifacts_exist(
    packages: list,
    staging_dir: Path,
    version: str,
    dry_run: bool,
) -> None:
    """Verify all expected artifacts exist for the current version.

    Unlike validate_build_artifacts in shared.py, this provides a user-friendly
    error message directing them to run 'make prepare' first.
    """
    if dry_run:
        user_output("[DRY RUN] Would validate artifacts exist")
        return

    if not staging_dir.exists():
        user_output(f"✗ No artifacts found in {staging_dir}")
        user_output("  Run 'make prepare' first to bump version and build packages")
        raise SystemExit(1)

    for pkg in packages:
        normalized = normalize_package_name(pkg.name)
        wheel = staging_dir / f"{normalized}-{version}-py3-none-any.whl"
        sdist = staging_dir / f"{normalized}-{version}.tar.gz"

        if not wheel.exists():
            user_output(f"✗ Missing wheel for {pkg.name} version {version}")
            user_output(f"  Expected: {wheel}")
            user_output("  Run 'make prepare' first to bump version and build packages")
            raise SystemExit(1)
        if not sdist.exists():
            user_output(f"✗ Missing sdist for {pkg.name} version {version}")
            user_output(f"  Expected: {sdist}")
            user_output("  Run 'make prepare' first to bump version and build packages")
            raise SystemExit(1)

    user_output("  ✓ All artifacts validated")


def publish_release_workflow(dry_run: bool) -> None:
    """Execute the publish phase of the release workflow.

    This requires artifacts to have been previously built by 'erk-dev prepare-release'.

    This includes:
    - Validate artifacts exist for current version
    - Publish all packages to PyPI
    - Push to remote

    Does NOT commit - assumes user already committed after prepare phase.
    """
    if dry_run:
        user_output("[DRY RUN MODE - No changes will be made]\n")

    repo_root = Path.cwd()
    if not (repo_root / "pyproject.toml").exists():
        user_output("✗ Not in repository root (pyproject.toml not found)")
        user_output("  Run this command from the repository root directory")
        raise SystemExit(1)

    user_output("Discovering workspace packages...")
    packages = get_workspace_packages(repo_root)
    user_output(f"  ✓ Found {len(packages)} packages: {', '.join(pkg.name for pkg in packages)}")

    # Get current version from pyproject.toml
    version = get_current_version(repo_root / "pyproject.toml")
    user_output(f"  ✓ Current version: {version}")

    # Validate artifacts exist for this version
    staging_dir = repo_root / "dist"
    user_output("\nValidating artifacts...")
    validate_artifacts_exist(packages, staging_dir, version, dry_run)

    # Publish to PyPI
    publish_all_packages(packages, staging_dir, version, dry_run)

    # Push to remote
    push_to_remote(repo_root, dry_run)
    user_output("✓ Pushed to origin")

    # Summary
    user_output("\n✅ Successfully published:")
    for pkg in packages:
        user_output(f"  • {pkg.name} {version}")


@click.command(name="publish-release")
@click.option("--dry-run", is_flag=True, help="Show what would be done without making changes")
def publish_release_command(dry_run: bool) -> None:
    """Publish prepared artifacts to PyPI.

    This command handles the publish phase of the release workflow:
    - Validates that artifacts exist for the current version
    - Publishes all packages to PyPI
    - Pushes to remote

    Requires 'erk-dev prepare-release' (or 'make prepare') to have been run first
    to bump versions and build artifacts.

    If artifacts are missing or version mismatch is detected, exits with an error
    message directing user to run 'make prepare' first.
    """
    try:
        publish_release_workflow(dry_run)
    except KeyboardInterrupt:
        user_output("\n✗ Interrupted by user")
        raise SystemExit(130) from None
