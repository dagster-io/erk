"""List command for showing installed kits."""

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import click
import pathspec

from erk.kits.cli.list_formatting import (
    format_item_name,
    format_kit_reference,
    format_metadata,
    format_section_header,
    format_source_indicator,
    format_subsection_header,
)
from erk.kits.cli.output import user_output
from erk.kits.io.git import resolve_project_dir
from erk.kits.io.state import require_project_config
from erk.kits.models.artifact import (
    ARTIFACT_TYPE_PLURALS,
    ArtifactSource,
    ArtifactTypePlural,
    InstalledArtifact,
)
from erk.kits.models.config import ProjectConfig
from erk.kits.repositories.artifact_repository import ArtifactRepository
from erk.kits.repositories.filesystem_artifact_repository import FilesystemArtifactRepository

# Reusable option decorator
artifacts_option = click.option(
    "--artifacts",
    "-a",
    is_flag=True,
    help="Show artifact-level detail view",
)


@dataclass(frozen=True)
class ArtifactDisplayData:
    """Captures display information for an artifact to avoid recalculating."""

    artifact: InstalledArtifact
    folder_path: str
    file_counts: str
    source: str


def _format_source(artifact: InstalledArtifact) -> str:
    """Format the source attribution string for an artifact.

    Args:
        artifact: The artifact to format

    Returns:
        Formatted source string like "[devrun@0.1.0]" or "[local]"
    """
    if artifact.source == ArtifactSource.LOCAL:
        return format_source_indicator(None, None)
    return format_source_indicator(artifact.kit_id, artifact.kit_version)


def _find_project_root(start_path: Path) -> Path:
    """Find the project root by searching for .git directory.

    Args:
        start_path: Directory to start searching from

    Returns:
        Project root directory (directory containing .git) or start_path if not found
    """
    if start_path.exists():
        current = start_path.resolve()
    else:
        current = start_path

    home = Path.home()

    while current != current.parent and current != home:
        git_dir = current / ".git"
        if git_dir.exists():
            return current
        current = current.parent

    return start_path


def _count_files_by_extension(artifact_dir: Path, project_root: Path) -> str:
    """Count files in artifact directory grouped by extension, respecting .gitignore.

    Args:
        artifact_dir: Directory containing the artifact files
        project_root: Project root directory for gitignore resolution

    Returns:
        Formatted string like "5 .md, 3 .py, 2 .json, 3 others"
    """
    # Check if artifact directory exists
    if not artifact_dir.exists():
        return ""

    # Read .gitignore from project root if it exists
    gitignore_path = project_root / ".gitignore"
    spec: pathspec.PathSpec | None = None

    if gitignore_path.exists():
        gitignore_content = gitignore_path.read_text(encoding="utf-8")
        spec = pathspec.PathSpec.from_lines("gitwildmatch", gitignore_content.splitlines())

    # Count files by extension
    extension_counts: Counter[str] = Counter()

    for file_path in artifact_dir.rglob("*"):
        # Skip directories
        if not file_path.is_file():
            continue

        # Get relative path from project root for gitignore matching
        if file_path.exists() and project_root.exists():
            relative_path = file_path.resolve().relative_to(project_root.resolve())

            # Check if file matches gitignore patterns
            if spec is not None and spec.match_file(str(relative_path)):
                continue

        # Count by extension
        extension = file_path.suffix if file_path.suffix else ""
        extension_counts[extension] += 1

    # Format output: top 3 extensions + others
    if not extension_counts:
        return ""

    # Sort by count descending to find the most common extensions
    sorted_by_count = sorted(extension_counts.items(), key=lambda item: -item[1])

    # Take top 3 most common extensions
    top_3_by_count = sorted_by_count[:3]
    remaining = sorted_by_count[3:]

    # Sort the top 3 alphabetically by extension name for consistent display
    top_3_sorted = sorted(top_3_by_count, key=lambda item: item[0])

    # Format top 3
    parts = [
        f"{ext.lstrip('.')} ({count})" if ext else f"no-ext ({count})"
        for ext, count in top_3_sorted
    ]

    # Add remaining count if any
    if remaining:
        remaining_count = sum(count for _, count in remaining)
        parts.append(f"others ({remaining_count})")

    return ", ".join(parts)


def _list_artifacts(
    config: ProjectConfig,
    project_dir: Path,
    repository: ArtifactRepository,
) -> None:
    """List all installed artifacts in artifact-focused format.

    Args:
        config: Project configuration
        project_dir: Project directory for artifact discovery
        repository: Repository for artifact discovery
    """
    # Discover all artifacts using the provided repository
    artifacts = repository.discover_all_artifacts(project_dir, config)

    if not artifacts:
        user_output("No artifacts installed")
        return

    # Find project root for gitignore resolution
    project_root = _find_project_root(project_dir)

    # Group artifacts by kit, then by type
    # Structure: {kit_key: {artifact_type_plural: [artifacts]}}
    kits_with_artifacts: dict[str, dict[ArtifactTypePlural, list[InstalledArtifact]]] = {}

    for artifact in artifacts:
        # Determine kit key
        if artifact.source == ArtifactSource.LOCAL:
            kit_key = "local"
        elif artifact.kit_id and artifact.kit_version:
            kit_key = f"{artifact.kit_id}@{artifact.kit_version}"
        elif artifact.kit_id:
            kit_key = artifact.kit_id
        else:
            kit_key = "unknown"

        # Initialize kit if not present
        if kit_key not in kits_with_artifacts:
            kits_with_artifacts[kit_key] = {
                "skills": [],
                "commands": [],
                "agents": [],
                "hooks": [],
                "docs": [],
            }

        # Add artifact to appropriate type list
        # Convert singular type to plural for dictionary key
        plural_type = ARTIFACT_TYPE_PLURALS[artifact.artifact_type]
        kits_with_artifacts[kit_key][plural_type].append(artifact)

    # Create display data for all skills across all kits
    skills_data_by_kit: dict[str, list[ArtifactDisplayData]] = {}

    for kit_key, artifact_types in kits_with_artifacts.items():
        skills_data_by_kit[kit_key] = []

        for skill in artifact_types["skills"]:
            folder_path = str(skill.file_path.parent) + "/"
            # Artifact file_path is relative to .claude/, so prepend .claude/
            artifact_dir = project_dir / ".claude" / skill.file_path.parent
            file_counts = _count_files_by_extension(artifact_dir, project_root)
            source = _format_source(skill)

            display_data = ArtifactDisplayData(
                artifact=skill,
                folder_path=folder_path,
                file_counts=file_counts,
                source=source,
            )
            skills_data_by_kit[kit_key].append(display_data)

    # Calculate column widths for alignment
    max_name_len = 0
    max_path_len = 0  # For commands and agents (file path)
    max_folder_len = 0  # For skills (folder path)
    max_counts_len = 0  # For skills (file counts)

    # Calculate max name length across all artifacts
    for artifact in artifacts:
        max_name_len = max(max_name_len, len(artifact.artifact_name))

    # Calculate widths for skills
    for kit_skills_data in skills_data_by_kit.values():
        for data in kit_skills_data:
            max_folder_len = max(max_folder_len, len(data.folder_path))
            max_counts_len = max(max_counts_len, len(data.file_counts))

    # Calculate widths for commands, agents, hooks, and docs (file paths)
    for artifact_types in kits_with_artifacts.values():
        for artifact in (
            artifact_types["commands"]
            + artifact_types["agents"]
            + artifact_types["hooks"]
            + artifact_types["docs"]
        ):
            max_path_len = max(max_path_len, len(str(artifact.file_path)))

    # Ensure minimum widths
    max_name_len = max(max_name_len, 20)
    max_path_len = max(max_path_len, 30)
    max_folder_len = max(max_folder_len, 30)
    max_counts_len = max(max_counts_len, 20)

    # Sort kits: installed kits alphabetically, then local
    def _sort_kit_key(kit_key: str) -> tuple[int, str]:
        """Sort key function: local last, others alphabetically."""
        if kit_key == "local":
            return (1, kit_key)
        else:
            return (0, kit_key)

    sorted_kit_keys = sorted(kits_with_artifacts.keys(), key=_sort_kit_key)

    # Display artifacts grouped by kit
    for kit_key in sorted_kit_keys:
        artifact_types = kits_with_artifacts[kit_key]

        # Check if kit has any artifacts
        plural_types: list[ArtifactTypePlural] = ["skills", "commands", "agents", "hooks", "docs"]
        has_artifacts = any(len(artifact_types[atype]) > 0 for atype in plural_types)

        if not has_artifacts:
            continue

        # Display kit header
        if kit_key == "local":
            user_output(format_section_header("[local]:"))
        else:
            # Extract kit_id and version from key
            if "@" in kit_key:
                kit_id, version = kit_key.split("@", 1)
                header = f"{format_item_name(kit_id)} {format_kit_reference(kit_id, version)}"
                user_output(format_section_header(header + ":"))
            else:
                user_output(format_section_header(f"{format_item_name(kit_key)}:"))

        # Display skills for this kit
        kit_skills_data = skills_data_by_kit.get(kit_key, [])
        if kit_skills_data:
            user_output(format_subsection_header("  Skills", len(kit_skills_data)) + ":")
            for data in sorted(kit_skills_data, key=lambda d: d.artifact.artifact_name):
                name = format_item_name(data.artifact.artifact_name).ljust(max_name_len)
                folder_path = format_metadata(data.folder_path).ljust(max_folder_len)
                file_counts = format_metadata(data.file_counts)
                user_output(f"    {name} {folder_path} {file_counts}")

        # Display commands for this kit
        kit_commands = artifact_types["commands"]
        if kit_commands:
            user_output(format_subsection_header("  Commands", len(kit_commands)) + ":")
            for command in sorted(kit_commands, key=lambda a: a.artifact_name):
                name = format_item_name(command.artifact_name).ljust(max_name_len)
                file_path = format_metadata(str(command.file_path))
                user_output(f"    {name} {file_path}")

        # Display agents for this kit
        kit_agents = artifact_types["agents"]
        if kit_agents:
            user_output(format_subsection_header("  Agents", len(kit_agents)) + ":")
            for agent in sorted(kit_agents, key=lambda a: a.artifact_name):
                name = format_item_name(agent.artifact_name).ljust(max_name_len)
                file_path = format_metadata(str(agent.file_path))
                user_output(f"    {name} {file_path}")

        # Display hooks for this kit
        kit_hooks = artifact_types["hooks"]
        if kit_hooks:
            user_output(format_subsection_header("  Hooks", len(kit_hooks)) + ":")
            for hook in sorted(kit_hooks, key=lambda a: a.artifact_name):
                name = format_item_name(hook.artifact_name).ljust(max_name_len)
                file_path = format_metadata(str(hook.file_path))
                user_output(f"    {name} {file_path}")

        # Display docs for this kit
        kit_docs = artifact_types["docs"]
        if kit_docs:
            user_output(format_subsection_header("  Docs", len(kit_docs)) + ":")
            for doc in sorted(kit_docs, key=lambda a: a.artifact_name):
                name = format_item_name(doc.artifact_name).ljust(max_name_len)
                file_path = format_metadata(str(doc.file_path))
                user_output(f"    {name} {file_path}")

        # Add spacing between kits
        user_output()

    user_output("Use 'dot-agent artifact list' to see installed artifacts from kits")


def _list_kits_impl(artifacts: bool) -> None:
    """Implementation of list command logic."""
    project_dir = resolve_project_dir(Path.cwd())
    config = require_project_config(project_dir)

    if len(config.kits) == 0:
        user_output("No kits installed")
        return

    # If --artifacts flag is provided, show artifact-level detail
    if artifacts:
        repository = FilesystemArtifactRepository()
        _list_artifacts(config, project_dir, repository)
        return

    # Default kit-level view
    user_output(format_section_header(f"Installed Kits ({len(config.kits)}):"))
    user_output()

    for kit_id, installed_kit in config.kits.items():
        name = format_item_name(kit_id).ljust(25)
        version = format_kit_reference(kit_id, installed_kit.version).ljust(20)
        source_type = format_metadata(installed_kit.source_type)
        user_output(f"  {name} {version} {source_type}")


@click.command(name="list")
@artifacts_option
def list_installed_kits(artifacts: bool) -> None:
    """List all installed kits in the current project (alias: ls)."""
    _list_kits_impl(artifacts)


@click.command(name="ls", hidden=True)
@artifacts_option
def ls(artifacts: bool) -> None:
    """List all installed kits in the current project (alias for list)."""
    _list_kits_impl(artifacts)
