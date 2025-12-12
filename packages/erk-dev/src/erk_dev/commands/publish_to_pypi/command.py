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


def run_git_pull(repo_root: Path, dry_run: bool) -> None:
    """Pull latest changes from remote."""
    if dry_run:
        user_output("[DRY RUN] Would run: git pull")
        return
    run_command(["git", "pull"], cwd=repo_root, description="git pull")
    user_output("✓ Pulled latest changes")


def ensure_branch_is_in_sync(repo_root: Path, dry_run: bool) -> None:
    """Validate that the current branch tracks its upstream and is up to date."""
    if dry_run:
        user_output("[DRY RUN] Would run: git fetch --prune")
    else:
        run_command(
            ["git", "fetch", "--prune"],
            cwd=repo_root,
            description="git fetch --prune",
        )

    status_output = run_command(
        ["git", "status", "--short", "--branch"],
        cwd=repo_root,
        description="git status --short --branch",
    )

    if not status_output:
        return

    first_line = status_output.splitlines()[0]
    if not first_line.startswith("## "):
        return

    branch_summary = first_line[3:]
    if "..." not in branch_summary:
        user_output("✗ Current branch is not tracking a remote upstream")
        user_output("  Run `git push -u origin <branch>` before publishing")
        raise SystemExit(1)

    local_branch, remote_section = branch_summary.split("...", 1)
    remote_name = remote_section
    tracking_info = ""

    if " [" in remote_section:
        remote_name, tracking_info = remote_section.split(" [", 1)
        tracking_info = tracking_info.rstrip("]")

    remote_name = remote_name.strip()
    tracking_info = tracking_info.strip()

    ahead = 0
    behind = 0
    remote_gone = False

    if tracking_info:
        for token in tracking_info.split(","):
            item = token.strip()
            if item.startswith("ahead "):
                ahead = int(item.split(" ", 1)[1])
            elif item.startswith("behind "):
                behind = int(item.split(" ", 1)[1])
            elif item == "gone":
                remote_gone = True

    if remote_gone:
        user_output("✗ Upstream branch is gone")
        user_output(f"  Local branch: {local_branch}")
        user_output(f"  Last known upstream: {remote_name}")
        user_output("  Re-create or change the upstream before publishing")
        raise SystemExit(1)

    if behind > 0:
        user_output("✗ Current branch is behind its upstream")
        user_output(f"  Local branch: {local_branch}")
        user_output(f"  Upstream: {remote_name}")
        if ahead > 0:
            user_output(f"  Diverged by ahead {ahead} / behind {behind} commit(s)")
        else:
            user_output(f"  Behind by {behind} commit(s)")
        user_output("  Pull and reconcile changes (e.g., `git pull --rebase`) before publishing")
        raise SystemExit(1)


def get_workspace_packages(repo_root: Path) -> list[PackageInfo]:
    """Get all publishable packages in workspace."""
    packages = [
        PackageInfo(
            name="erk-kits",
            path=repo_root / "packages" / "erk-kits",
            pyproject_path=repo_root / "packages" / "erk-kits" / "pyproject.toml",
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


def bump_patch_version(version: str) -> str:
    """Increment the patch version number."""
    parts = version.split(".")
    if len(parts) != 3:
        user_output(f"✗ Invalid version format: {version}")
        raise SystemExit(1)

    if not parts[2].isdigit():
        user_output(f"✗ Invalid patch version: {parts[2]}")
        raise SystemExit(1)

    parts[2] = str(int(parts[2]) + 1)
    return ".".join(parts)


def update_version(pyproject_path: Path, old_version: str, new_version: str, dry_run: bool) -> None:
    """Update version in pyproject.toml."""
    content = pyproject_path.read_text(encoding="utf-8")
    old_line = f'version = "{old_version}"'
    new_line = f'version = "{new_version}"'

    if old_line not in content:
        user_output(f"✗ Could not find version line in pyproject.toml: {old_line}")
        raise SystemExit(1)

    if dry_run:
        user_output(f"[DRY RUN] Would update {pyproject_path.name}: {old_line} -> {new_line}")
        return

    updated_content = content.replace(old_line, new_line)
    pyproject_path.write_text(updated_content, encoding="utf-8")


def update_version_py(
    version_py_path: Path, old_version: str, new_version: str, dry_run: bool
) -> bool:
    """Update __version__ string in version.py if it exists.

    Returns True if version was updated, False if version.py not found.
    """
    if not version_py_path.exists():
        return False

    content = version_py_path.read_text(encoding="utf-8")
    old_line = f'__version__ = "{old_version}"'
    new_line = f'__version__ = "{new_version}"'

    if old_line not in content:
        return False

    if dry_run:
        user_output(f"[DRY RUN] Would update {version_py_path.name}: {old_line} -> {new_line}")
        return True

    updated_content = content.replace(old_line, new_line)
    version_py_path.write_text(updated_content, encoding="utf-8")
    return True


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


def synchronize_versions(
    packages: list[PackageInfo],
    old_version: str,
    new_version: str,
    dry_run: bool,
) -> None:
    """Update version in all package pyproject.toml files and version.py files."""
    for pkg in packages:
        # Update pyproject.toml
        update_version(pkg.pyproject_path, old_version, new_version, dry_run)
        if not dry_run:
            user_output(f"  ✓ Updated {pkg.name}: {old_version} → {new_version}")

        # Update version.py if it exists
        package_name = pkg.name.replace("-", "_")
        version_py_path = pkg.path / "src" / package_name / "version.py"

        if update_version_py(version_py_path, old_version, new_version, dry_run):
            if not dry_run:
                user_output(f"  ✓ Updated {version_py_path.name} for {pkg.name}")


def run_uv_sync(repo_root: Path, dry_run: bool) -> None:
    """Update lockfile with uv sync."""
    if dry_run:
        user_output("[DRY RUN] Would run: uv sync")
        return
    run_command(["uv", "sync"], cwd=repo_root, description="uv sync")
    user_output("✓ Dependencies synced")


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


def commit_changes(
    repo_root: Path,
    packages: list[PackageInfo],
    version: str,
    dry_run: bool,
) -> str:
    """Commit version bump changes for all packages."""
    commit_message = f"""Published packages {version}

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"""

    files_to_add = [str(pkg.pyproject_path.relative_to(repo_root)) for pkg in packages]
    files_to_add.append("uv.lock")

    # Add version.py files if they exist
    for pkg in packages:
        package_name = pkg.name.replace("-", "_")
        version_py_path = pkg.path / "src" / package_name / "version.py"
        if version_py_path.exists():
            files_to_add.append(str(version_py_path.relative_to(repo_root)))

    if dry_run:
        user_output(f"[DRY RUN] Would run: git add {' '.join(files_to_add)}")
        user_output(f'[DRY RUN] Would run: git commit -m "Published {version}..."')
        return "abc123f"

    run_command(
        ["git", "add"] + files_to_add,
        cwd=repo_root,
        description="git add",
    )

    run_command(
        ["git", "commit", "-m", commit_message],
        cwd=repo_root,
        description="git commit",
    )

    return run_command(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=repo_root,
        description="get commit SHA",
    )


def push_to_remote(repo_root: Path, dry_run: bool) -> None:
    """Push commits to remote repository."""
    if dry_run:
        user_output("[DRY RUN] Would run: git push")
        return
    run_command(["git", "push"], cwd=repo_root, description="git push")


def get_git_status(repo_root: Path) -> str:
    """Get current git status."""
    return run_command(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        description="git status",
    )


def filter_git_status(status: str, excluded_files: set[str]) -> list[str]:
    """Filter git status output to exclude specific files."""
    lines: list[str] = []
    for line in status.splitlines():
        if len(line) >= 4:
            filename = line[3:]
            if filename not in excluded_files:
                lines.append(line)
    return lines


def publish_workflow(dry_run: bool) -> None:
    """Execute the synchronized multi-package publishing workflow."""
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
        excluded_files = {
            "pyproject.toml",
            "uv.lock",
            "packages/erk-kits/pyproject.toml",
        }
        lines = filter_git_status(status, excluded_files)

        if lines:
            user_output("✗ Working directory has uncommitted changes:")
            for line in lines:
                user_output(f"  {line}")
            raise SystemExit(1)

    user_output("\nStarting synchronized publish workflow...\n")

    ensure_branch_is_in_sync(repo_root, dry_run)
    run_git_pull(repo_root, dry_run)

    old_version = validate_version_consistency(packages)
    user_output(f"  ✓ Current version: {old_version} (consistent)")

    new_version = bump_patch_version(old_version)
    user_output(f"\nBumping version: {old_version} → {new_version}")
    synchronize_versions(packages, old_version, new_version, dry_run)

    run_uv_sync(repo_root, dry_run)

    staging_dir = build_all_packages(packages, repo_root, dry_run)
    validate_build_artifacts(packages, staging_dir, new_version, dry_run)

    publish_all_packages(packages, staging_dir, new_version, dry_run)

    sha = commit_changes(repo_root, packages, new_version, dry_run)
    user_output(f'\n✓ Committed: {sha} "Published {new_version}"')

    push_to_remote(repo_root, dry_run)
    user_output("✓ Pushed to origin")

    user_output("\n✅ Successfully published:")
    for pkg in packages:
        user_output(f"  • {pkg.name} {new_version}")


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
