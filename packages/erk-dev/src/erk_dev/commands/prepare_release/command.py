"""Prepare release command - version bump and build artifacts."""

from pathlib import Path

import click

from erk_dev.cli.output import user_output
from erk_dev.commands.publish_to_pypi.shared import (
    build_all_packages,
    bump_patch_version,
    ensure_branch_is_in_sync,
    filter_git_status,
    get_git_status,
    get_workspace_packages,
    run_git_pull,
    run_uv_sync,
    synchronize_versions,
    validate_build_artifacts,
    validate_version_consistency,
)


def prepare_release_workflow(dry_run: bool) -> None:
    """Execute the prepare phase: version bump and build artifacts."""
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

    # Validate git status - fail early
    status = get_git_status(repo_root)
    if status:
        excluded_files = {
            "pyproject.toml",
            "uv.lock",
            "packages/dot-agent-kit/pyproject.toml",
        }
        lines = filter_git_status(status, excluded_files)

        if lines:
            user_output("✗ Working directory has uncommitted changes:")
            for line in lines:
                user_output(f"  {line}")
            raise SystemExit(1)

    user_output("\nStarting prepare workflow...\n")

    # Ensure branch is in sync with upstream
    ensure_branch_is_in_sync(repo_root, dry_run)
    run_git_pull(repo_root, dry_run)

    # Version consistency check
    old_version = validate_version_consistency(packages)
    user_output(f"  ✓ Current version: {old_version} (consistent)")

    # Bump version
    new_version = bump_patch_version(old_version)
    user_output(f"\nBumping version: {old_version} → {new_version}")
    synchronize_versions(packages, old_version, new_version, dry_run)

    # Sync dependencies
    run_uv_sync(repo_root, dry_run)

    # Build packages
    staging_dir = build_all_packages(packages, repo_root, dry_run)
    validate_build_artifacts(packages, staging_dir, new_version, dry_run)

    user_output("\n✅ Prepare complete!")
    user_output(f"  Version bumped: {old_version} → {new_version}")
    user_output("  Build artifacts ready in dist/")
    user_output("\nNext steps:")
    user_output("  1. Review changes: git diff")
    user_output(f'  2. Commit changes: git add -A && git commit -m "Bump version to {new_version}"')
    user_output("  3. Publish to PyPI: make publish")


@click.command(name="prepare-release")
@click.option("--dry-run", is_flag=True, help="Show what would be done without making changes")
def prepare_release_command(dry_run: bool) -> None:
    """Prepare release: bump version and build artifacts.

    This command performs the prepare phase of the release workflow:
    - Validates git status and branch sync
    - Pulls latest changes
    - Bumps patch version
    - Synchronizes versions across packages
    - Runs uv sync
    - Builds all packages to dist/

    After running this command, review changes and commit manually.
    Then run 'make publish' to upload to PyPI.
    """
    try:
        prepare_release_workflow(dry_run)
    except KeyboardInterrupt:
        user_output("\n✗ Interrupted by user")
        raise SystemExit(130) from None
