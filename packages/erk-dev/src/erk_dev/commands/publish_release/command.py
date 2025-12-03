"""Publish release command - upload to PyPI and push to remote."""

from pathlib import Path

import click

from erk_dev.cli.output import user_output
from erk_dev.commands.publish_to_pypi.shared import (
    PackageInfo,
    get_current_version,
    get_workspace_packages,
    normalize_package_name,
    publish_all_packages,
    push_to_remote,
)


def validate_artifacts_exist(packages: list[PackageInfo], staging_dir: Path, version: str) -> None:
    """Validate that build artifacts exist for the current version.

    Exits with error if artifacts are missing, directing user to run 'make prepare'.
    """
    if not staging_dir.exists():
        user_output("✗ No dist/ directory found")
        user_output("  Run 'make prepare' first to bump version and build packages")
        raise SystemExit(1)

    missing_artifacts: list[str] = []
    for pkg in packages:
        normalized = normalize_package_name(pkg.name)
        wheel = staging_dir / f"{normalized}-{version}-py3-none-any.whl"
        sdist = staging_dir / f"{normalized}-{version}.tar.gz"

        if not wheel.exists():
            missing_artifacts.append(f"  • {wheel.name}")
        if not sdist.exists():
            missing_artifacts.append(f"  • {sdist.name}")

    if missing_artifacts:
        user_output(f"✗ Missing build artifacts for version {version}:")
        for artifact in missing_artifacts:
            user_output(artifact)
        user_output("\nRun 'make prepare' first to bump version and build packages")
        raise SystemExit(1)

    user_output(f"  ✓ All artifacts found for version {version}")


def publish_release_workflow(dry_run: bool) -> None:
    """Execute the publish phase: upload to PyPI and push to remote."""
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
    version = get_current_version(packages[0].pyproject_path)
    user_output(f"  ✓ Current version: {version}")

    # Validate artifacts exist
    staging_dir = repo_root / "dist"
    user_output("\nValidating build artifacts...")
    validate_artifacts_exist(packages, staging_dir, version)

    user_output("\nStarting publish workflow...\n")

    # Publish to PyPI
    publish_all_packages(packages, staging_dir, version, dry_run)

    # Push to remote
    user_output("\nPushing to remote...")
    push_to_remote(repo_root, dry_run)
    user_output("  ✓ Pushed to origin")

    user_output("\n✅ Successfully published:")
    for pkg in packages:
        user_output(f"  • {pkg.name} {version}")


@click.command(name="publish-release")
@click.option("--dry-run", is_flag=True, help="Show what would be done without making changes")
def publish_release_command(dry_run: bool) -> None:
    """Publish release: upload to PyPI and push to remote.

    This command performs the publish phase of the release workflow:
    - Validates build artifacts exist in dist/
    - Publishes all packages to PyPI
    - Pushes changes to remote

    Prerequisites:
    - Must run 'make prepare' first to bump version and build artifacts
    - Must manually commit changes before running this command

    The command will exit with an error if artifacts are missing.
    """
    try:
        publish_release_workflow(dry_run)
    except KeyboardInterrupt:
        user_output("\n✗ Interrupted by user")
        raise SystemExit(130) from None
