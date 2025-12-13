"""Build kit packages by copying artifacts from source locations."""

from dataclasses import dataclass, field
from pathlib import Path

import click

from erk.kits.io.frontmatter import parse_artifact_frontmatter
from erk.kits.io.git import find_git_root
from erk.kits.io.manifest import load_kit_manifest
from erk.kits.sources.bundled import BundledKitSource


@dataclass
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


def _get_source_location(artifact_type: str, artifact_path: str, repo_root: Path) -> Path:
    """Get source location for an artifact based on its type.

    Args:
        artifact_type: Type of artifact (command, skill, agent, doc, workflow)
        artifact_path: Relative path from kit.yaml artifacts section
        repo_root: Repository root directory

    Returns:
        Absolute path to source file
    """
    # Map artifact types to source directories
    # Paths in kit.yaml are like "commands/erk/plan-implement.md"
    # Source locations are:
    #   command -> .claude/commands/
    #   skill -> .claude/skills/
    #   agent -> .claude/agents/
    #   doc -> .erk/docs/kits/
    #   workflow -> .github/workflows/

    if artifact_type == "command":
        return repo_root / ".claude" / artifact_path
    elif artifact_type == "skill":
        return repo_root / ".claude" / artifact_path
    elif artifact_type == "agent":
        return repo_root / ".claude" / artifact_path
    elif artifact_type == "doc":
        return repo_root / ".erk" / "docs" / "kits" / artifact_path.removeprefix("docs/")
    elif artifact_type == "workflow":
        return repo_root / ".github" / artifact_path
    else:
        # Default to .claude/ for unknown types
        return repo_root / ".claude" / artifact_path


def _validate_artifact_frontmatter(
    source_path: Path, expected_kit: str
) -> ArtifactValidationError | None:
    """Validate that artifact has correct kit frontmatter.

    Args:
        source_path: Path to source artifact file
        expected_kit: Expected kit name in frontmatter

    Returns:
        Error if validation fails, None if valid
    """
    if not source_path.exists():
        return ArtifactValidationError(
            artifact_path=str(source_path),
            source_path=source_path,
            error="Source file does not exist",
        )

    content = source_path.read_text(encoding="utf-8")
    frontmatter = parse_artifact_frontmatter(content)

    if frontmatter is None:
        return ArtifactValidationError(
            artifact_path=str(source_path),
            source_path=source_path,
            error="Missing frontmatter",
        )

    if frontmatter.kit != expected_kit:
        return ArtifactValidationError(
            artifact_path=str(source_path),
            source_path=source_path,
            error=f"Expected kit: {expected_kit}, found kit: {frontmatter.kit}",
        )

    return None


def build_kit(
    kit_name: str,
    kit_path: Path,
    repo_root: Path,
    check_only: bool = False,
    verbose: bool = False,
) -> BuildResult:
    """Build a kit by copying artifacts from source locations.

    Args:
        kit_name: Name of the kit to build
        kit_path: Path to kit directory (containing kit.yaml)
        repo_root: Repository root directory
        check_only: If True, only validate, don't copy
        verbose: If True, print verbose output

    Returns:
        BuildResult with copied files and any errors
    """
    result = BuildResult(kit_name=kit_name)

    manifest_path = kit_path / "kit.yaml"
    if not manifest_path.exists():
        result.errors.append(
            ArtifactValidationError(
                artifact_path="kit.yaml",
                source_path=manifest_path,
                error="kit.yaml not found",
            )
        )
        return result

    manifest = load_kit_manifest(manifest_path)

    # Process each artifact type
    for artifact_type, paths in manifest.artifacts.items():
        for artifact_rel in paths:
            source_path = _get_source_location(artifact_type, artifact_rel, repo_root)
            target_path = kit_path / artifact_rel

            # Validate frontmatter
            error = _validate_artifact_frontmatter(source_path, kit_name)
            if error is not None:
                result.errors.append(error)
                continue

            if check_only:
                result.copied.append(artifact_rel)
                continue

            # Copy artifact
            if not target_path.parent.exists():
                target_path.parent.mkdir(parents=True, exist_ok=True)

            content = source_path.read_text(encoding="utf-8")
            target_path.write_text(content, encoding="utf-8")
            result.copied.append(artifact_rel)

    return result


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

    This command copies artifacts from their source locations (.claude/,
    .erk/docs/kits/, .github/workflows/) into the kit package directories
    in packages/erk-kits/.

    Before copying, it validates that each artifact has the correct
    `kit:` field in its frontmatter matching the kit it belongs to.

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

    bundled_source = BundledKitSource()
    kit_names = bundled_source.list_available()

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
        kit_path = bundled_source._get_bundled_kit_path(name)
        if kit_path is None:
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
