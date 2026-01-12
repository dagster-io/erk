"""Publish to PyPI command."""

import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import click

from erk_dev.cli.output import user_output

# PyPI CDN propagation typically takes 3-5 seconds
PYPI_PROPAGATION_WAIT_SECONDS = 5


def normalize_package_name(name: str) -> str:
    """Normalize package name for artifact filenames."""
    return name.replace("-", "_")


@dataclass(frozen=True)
class PackageInfo:
    """Information about a publishable package."""

    name: str
    path: Path
    pyproject_path: Path


def run_command(cmd: list[str], cwd: Path | None = None, description: str = "") -> str:
    """Run a command and return stdout."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as error:
        user_output(f"✗ Failed: {description}")
        user_output(f"  Command: {' '.join(cmd)}")
        user_output(f"  Error: {error.stderr}")
        raise SystemExit(1) from error


def get_workspace_packages(repo_root: Path) -> list[PackageInfo]:
    """Get all publishable packages in workspace."""
    packages = [
        PackageInfo(
            name="erk-shared",
            path=repo_root / "packages" / "erk-shared",
            pyproject_path=repo_root / "packages" / "erk-shared" / "pyproject.toml",
        ),
        PackageInfo(
            name="erk-statusline",
            path=repo_root / "packages" / "erk-statusline",
            pyproject_path=repo_root / "packages" / "erk-statusline" / "pyproject.toml",
        ),
        PackageInfo(
            name="erk-bootstrap",
            path=repo_root / "packages" / "erk-bootstrap",
            pyproject_path=repo_root / "packages" / "erk-bootstrap" / "pyproject.toml",
        ),
        PackageInfo(
            name="erk",
            path=repo_root,
            pyproject_path=repo_root / "pyproject.toml",
        ),
    ]

    for pkg in packages:
        if not pkg.pyproject_path.exists():
            user_output(f"✗ Package not found: {pkg.name} at {pkg.path}")
            raise SystemExit(1)

    return packages


def get_current_version(pyproject_path: Path) -> str:
    """Parse current version from pyproject.toml."""
    if not pyproject_path.exists():
        user_output(f"✗ pyproject.toml not found at {pyproject_path}")
        raise SystemExit(1)

    content = pyproject_path.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)

    if not match:
        user_output("✗ Could not find version in pyproject.toml")
        raise SystemExit(1)

    return match.group(1)


def validate_version_consistency(packages: list[PackageInfo]) -> str:
    """Ensure all packages have the same version."""
    versions: dict[str, str] = {}
    for pkg in packages:
        versions[pkg.name] = get_current_version(pkg.pyproject_path)

    unique_versions = set(versions.values())
    if len(unique_versions) > 1:
        user_output("✗ Version mismatch across packages:")
        for name, version in versions.items():
            user_output(f"  {name}: {version}")
        raise SystemExit(1)

    return list(unique_versions)[0]


def build_package(package: PackageInfo, out_dir: Path, dry_run: bool) -> None:
    """Build a specific package in the workspace."""
    if dry_run:
        user_output(f"[DRY RUN] Would run: uv build --package {package.name} -o {out_dir}")
        return

    run_command(
        ["uv", "build", "--package", package.name, "-o", str(out_dir)],
        cwd=package.path if package.name == "erk" else package.path.parent.parent,
        description=f"build {package.name}",
    )


def build_all_packages(
    packages: list[PackageInfo],
    repo_root: Path,
    dry_run: bool,
) -> Path:
    """Build all packages to a staging directory."""
    staging_dir = repo_root / "dist"
    if staging_dir.exists() and not dry_run:
        for artifact in staging_dir.glob("*"):
            if artifact.is_dir():
                shutil.rmtree(artifact)
            else:
                artifact.unlink()
    elif not dry_run:
        staging_dir.mkdir(parents=True, exist_ok=True)

    user_output("\nBuilding packages...")
    for pkg in packages:
        build_package(pkg, staging_dir, dry_run)
        user_output(f"  ✓ Built {pkg.name}")

    return staging_dir


def validate_build_artifacts(
    packages: list[PackageInfo],
    staging_dir: Path,
    version: str,
    dry_run: bool,
) -> None:
    """Verify all expected artifacts exist."""
    if dry_run:
        user_output("[DRY RUN] Would validate artifacts exist")
        return

    for pkg in packages:
        normalized = normalize_package_name(pkg.name)
        wheel = staging_dir / f"{normalized}-{version}-py3-none-any.whl"
        sdist = staging_dir / f"{normalized}-{version}.tar.gz"

        if not wheel.exists():
            user_output(f"✗ Missing wheel: {wheel}")
            raise SystemExit(1)
        if not sdist.exists():
            user_output(f"✗ Missing sdist: {sdist}")
            raise SystemExit(1)

    user_output("  ✓ All artifacts validated")


def publish_package(package: PackageInfo, staging_dir: Path, version: str, dry_run: bool) -> None:
    """Publish a single package to PyPI."""
    if dry_run:
        user_output(f"[DRY RUN] Would publish {package.name} to PyPI")
        return

    normalized = normalize_package_name(package.name)
    artifacts = list(staging_dir.glob(f"{normalized}-{version}*"))

    if not artifacts:
        user_output(f"✗ No artifacts found for {package.name} {version}")
        raise SystemExit(1)

    run_command(
        ["uvx", "uv-publish"] + [str(artifact) for artifact in artifacts],
        cwd=staging_dir,
        description=f"publish {package.name}",
    )


def wait_for_pypi_availability(package: PackageInfo, version: str, dry_run: bool) -> None:
    """Wait for package to be available on PyPI."""
    if dry_run:
        user_output(f"[DRY RUN] Would wait for {package.name} {version} on PyPI")
        return

    user_output(f"  ⏳ Waiting {PYPI_PROPAGATION_WAIT_SECONDS}s for PyPI propagation...")
    time.sleep(PYPI_PROPAGATION_WAIT_SECONDS)


def publish_all_packages(
    packages: list[PackageInfo],
    staging_dir: Path,
    version: str,
    dry_run: bool,
) -> None:
    """Publish all packages in dependency order."""
    user_output("\nPublishing to PyPI...")

    for index, pkg in enumerate(packages):
        publish_package(pkg, staging_dir, version, dry_run)
        user_output(f"  ✓ Published {pkg.name} {version}")

        if index < len(packages) - 1:
            wait_for_pypi_availability(pkg, version, dry_run)


def get_git_status(repo_root: Path) -> str:
    """Get current git status."""
    return run_command(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        description="git status",
    )


def publish_workflow(dry_run: bool) -> None:
    """Execute the multi-package publishing workflow.

    This command assumes version bumping has already been done via `erk-dev bump-version`.
    It validates version consistency, builds packages, and publishes to PyPI.
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

    status = get_git_status(repo_root)
    if status:
        user_output("✗ Working directory has uncommitted changes:")
        for line in status.splitlines():
            user_output(f"  {line}")
        raise SystemExit(1)

    version = validate_version_consistency(packages)
    user_output(f"  ✓ Publishing version: {version}")

    staging_dir = build_all_packages(packages, repo_root, dry_run)
    validate_build_artifacts(packages, staging_dir, version, dry_run)
    publish_all_packages(packages, staging_dir, version, dry_run)

    user_output("\n✅ Successfully published:")
    for pkg in packages:
        user_output(f"  • {pkg.name} {version}")


def run_pep723_script(dry_run: bool) -> None:
    """Compatibility shim for tests expecting script execution entrypoint."""
    publish_workflow(dry_run)


@click.command(name="publish-to-pypi")
@click.option("--dry-run", is_flag=True, help="Show what would be done without making changes")
def publish_to_pypi_command(dry_run: bool) -> None:
    """Publish packages to PyPI."""
    try:
        run_pep723_script(dry_run)
    except KeyboardInterrupt:
        user_output("\n✗ Interrupted by user")
        raise SystemExit(130) from None
