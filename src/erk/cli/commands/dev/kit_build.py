"""Build kit packages by copying artifacts from source locations."""

from dataclasses import dataclass, field
from pathlib import Path

import click

import erk_kits
from erk.kits.io.git import find_git_root


@dataclass(frozen=True)
class ArtifactValidationError:
    """Error during artifact validation."""

    artifact_path: str
    source_path: Path
    error: str


@dataclass
class BuildResult:
    """Result of building a kit."""

    kit_name: str
    copied: list[str] = field(default_factory=list)
    errors: list[ArtifactValidationError] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if build succeeded without errors."""
        return len(self.errors) == 0


@dataclass(frozen=True)
class DiscoveredArtifact:
    """An artifact discovered from source files."""

    source_path: Path
    artifact_type: str
    relative_target: str  # Relative path within kit (e.g., "commands/erk/foo.md")


def _discover_source_artifacts(repo_root: Path) -> list[DiscoveredArtifact]:
    """Discover artifacts from source files by directory structure.

    Scans source directories (.claude/, .erk/docs/kits/) for all markdown files.
    All artifacts are collected for the single bundled kit.

    Args:
        repo_root: Repository root directory

    Returns:
        List of discovered artifacts with source paths and target paths
    """
    artifacts: list[DiscoveredArtifact] = []

    # Source directories and their artifact type mappings
    # (source_dir, artifact_type, target_prefix)
    source_mappings: list[tuple[Path, str, str]] = [
        (repo_root / ".claude" / "commands", "command", "commands"),
        (repo_root / ".claude" / "skills", "skill", "skills"),
        (repo_root / ".claude" / "agents", "agent", "agents"),
        (repo_root / ".erk" / "docs" / "kits", "doc", "docs"),
    ]

    for source_dir, artifact_type, target_prefix in source_mappings:
        if not source_dir.exists():
            continue

        for md_file in source_dir.rglob("*.md"):
            # Compute relative target path
            rel_to_source = md_file.relative_to(source_dir)
            relative_target = f"{target_prefix}/{rel_to_source}"

            artifacts.append(
                DiscoveredArtifact(
                    source_path=md_file,
                    artifact_type=artifact_type,
                    relative_target=relative_target,
                )
            )

    return artifacts


def build_kit(
    kit_name: str,
    kit_path: Path,
    repo_root: Path,
    check_only: bool,
    verbose: bool,
) -> BuildResult:
    """Build a kit by copying artifacts from source locations.

    Discovers artifacts by scanning source directories for all markdown files,
    then copies them to the kit package directory.

    Args:
        kit_name: Name of the kit to build
        kit_path: Path to kit directory in packages/erk-kits/
        repo_root: Repository root directory
        check_only: If True, only validate, don't copy
        verbose: If True, print verbose output

    Returns:
        BuildResult with copied files and any errors
    """
    result = BuildResult(kit_name=kit_name)

    # Discover artifacts from source files
    artifacts = _discover_source_artifacts(repo_root)

    if not artifacts:
        # No artifacts found for this kit
        return result

    # Process each discovered artifact
    for artifact in artifacts:
        target_path = kit_path / artifact.relative_target

        if check_only:
            result.copied.append(artifact.relative_target)
            continue

        # Copy artifact
        if not target_path.parent.exists():
            target_path.parent.mkdir(parents=True, exist_ok=True)

        content = artifact.source_path.read_text(encoding="utf-8")
        target_path.write_text(content, encoding="utf-8")
        result.copied.append(artifact.relative_target)

    return result


def _get_kit_names(kits_dir: Path) -> list[str]:
    """Get list of kit names from the kits directory.

    A kit is identified by having a directory with at least one subdirectory
    (commands, skills, agents, docs).

    Args:
        kits_dir: Path to kits directory

    Returns:
        List of kit directory names
    """
    if not kits_dir.exists():
        return []

    kit_names = []
    for d in kits_dir.iterdir():
        if d.is_dir() and d.name != "__pycache__":
            kit_names.append(d.name)
    return kit_names


@click.command(name="kit-build")
@click.option(
    "--kit",
    "-k",
    "kit_name",
    help="Build only this specific kit (by name)",
)
@click.option(
    "--check",
    is_flag=True,
    help="Validate only, don't copy files",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show verbose output",
)
def kit_build(kit_name: str | None, check: bool, verbose: bool) -> None:
    """Build kit packages by copying artifacts from source locations.

    This command discovers artifacts by scanning source locations (.claude/,
    .erk/docs/kits/) and copies them into the kit package directories in
    packages/erk-kits/.

    Examples:

        # Build all kits
        erk dev kit-build

        # Build specific kit
        erk dev kit-build --kit erk

        # Validate without copying
        erk dev kit-build --check

        # Verbose output
        erk dev kit-build -v
    """
    # Find repo root
    repo_root = find_git_root(Path.cwd())
    if repo_root is None:
        click.echo("Error: Not in a git repository", err=True)
        raise SystemExit(1)

    kits_dir = erk_kits.get_kits_dir()
    kit_names = _get_kit_names(kits_dir)

    if not kit_names:
        click.echo("No bundled kits found")
        return

    if kit_name is not None:
        if kit_name not in kit_names:
            available = ", ".join(sorted(kit_names))
            click.echo(f"Kit '{kit_name}' not found. Available kits: {available}")
            raise SystemExit(1)
        kit_names = [kit_name]

    mode = "Checking" if check else "Building"
    click.echo(f"{mode} kits...")
    click.echo()

    all_valid = True
    total_copied = 0
    total_errors = 0

    for name in sorted(kit_names):
        kit_path = erk_kits.get_kits_dir() / name
        if not kit_path.exists():
            continue

        result = build_kit(
            kit_name=name,
            kit_path=kit_path,
            repo_root=repo_root,
            check_only=check,
            verbose=verbose,
        )

        if result.is_valid:
            status = "OK" if check else f"OK ({len(result.copied)} artifacts)"
            click.echo(f"  {name}: {status}")
            total_copied += len(result.copied)

            if verbose:
                for artifact in result.copied:
                    click.echo(f"    {artifact}")
        else:
            all_valid = False
            total_errors += len(result.errors)
            click.echo(f"  {name}: FAILED")
            for error in result.errors:
                click.echo(f"    {error.artifact_path}: {error.error}")

    click.echo()
    if all_valid:
        if check:
            click.echo("All kits validated successfully")
        else:
            click.echo(f"Built {total_copied} artifacts across {len(kit_names)} kits")
    else:
        click.echo(f"Found {total_errors} error(s)")
        raise SystemExit(1)
