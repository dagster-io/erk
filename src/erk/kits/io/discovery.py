"""Filesystem discovery utilities for installed artifacts."""

from pathlib import Path

from erk.kits.models.artifact import (
    ArtifactLevel,
    ArtifactSource,
    ArtifactType,
    InstalledArtifact,
)
from erk.kits.models.config import InstalledKit, ProjectConfig


def discover_installed_artifacts(
    project_dir: Path, config: ProjectConfig | None = None
) -> dict[str, set[str]]:
    """Discover artifacts present in .claude/ and .github/workflows/ directories.

    Scans the .claude/ directory structure to identify which kits have
    artifacts installed, and .github/workflows/ for workflow artifacts.

    Args:
        project_dir: Project root directory
        config: Optional project configuration for kit prefix detection

    Returns:
        Dictionary mapping kit_id to set of artifact types found.
        Example: {"devrun": {"agent", "skill"}, "gt": {"command", "skill", "workflow"}}
    """
    discovered: dict[str, set[str]] = {}

    # Scan .claude/ for standard artifacts
    claude_dir = project_dir / ".claude"

    # Scan each artifact type directory
    for artifact_type in ["agents", "commands", "skills"]:
        type_dir = claude_dir / artifact_type
        if not type_dir.exists():
            continue

        # Scan subdirectories to identify kits
        for item in type_dir.iterdir():
            if not item.is_dir():
                continue

            # For agents and commands, the parent directory name is the kit
            # For skills, we need to check if there's a SKILL.md file
            if artifact_type == "skills":
                # Skills have format: .claude/skills/skill-name/SKILL.md
                skill_file = item / "SKILL.md"
                if skill_file.exists():
                    # Extract kit from skill name prefix
                    # Examples: "devrun-make" -> "devrun", "gt-graphite" -> "gt"
                    kit_id = _extract_kit_from_skill_name(item.name, config)
                    if kit_id:
                        if kit_id not in discovered:
                            discovered[kit_id] = set()
                        discovered[kit_id].add("skill")
            elif artifact_type == "commands":
                # Commands have format: .claude/commands/kit-name/command.md
                kit_id = item.name
                if any(item.glob("*.md")):
                    if kit_id not in discovered:
                        discovered[kit_id] = set()
                    discovered[kit_id].add("command")
            elif artifact_type == "agents":
                # Agents have format: .claude/agents/kit-name/agent.md
                kit_id = item.name
                if any(item.glob("*.md")):
                    if kit_id not in discovered:
                        discovered[kit_id] = set()
                    discovered[kit_id].add("agent")

    # Workflows are in .github/workflows/<kit_name>/ directories
    workflows_base = project_dir / ".github" / "workflows"
    if workflows_base.exists():
        for kit_dir in workflows_base.iterdir():
            if not kit_dir.is_dir():
                continue
            kit_id = kit_dir.name
            # Check for workflow files in the kit subdirectory
            has_workflows = any(kit_dir.glob("*.yml")) or any(kit_dir.glob("*.yaml"))
            if has_workflows:
                discovered.setdefault(kit_id, set()).add("workflow")

    return discovered


def _extract_kit_from_skill_name(skill_name: str, config: ProjectConfig | None) -> str | None:
    """Extract kit ID from skill name.

    Skills are named with kit prefix, like:
    - "devrun-make" -> "devrun"
    - "devrun-pytest" -> "devrun"
    - "gt-graphite" -> "gt"

    For skills without a clear kit prefix (standalone skills), returns the
    full skill name as the kit ID.

    Args:
        skill_name: Full skill directory name
        config: Optional project configuration for kit prefix detection

    Returns:
        Kit ID - either extracted prefix or full skill name
    """
    # Use configured kit IDs as prefixes if config is provided
    if config is not None:
        kit_prefixes = list(config.kits.keys())

        # Check if skill starts with a configured kit prefix
        for prefix in kit_prefixes:
            if skill_name.startswith(f"{prefix}-"):
                return prefix

    # For skills without matching prefix, treat as standalone "kit"
    # This handles skills like "gh", "erk", "skill-creator", etc.
    return skill_name


def discover_all_artifacts(project_dir: Path, config: ProjectConfig) -> list[InstalledArtifact]:
    """Discover all installed artifacts with their metadata.

    Scans the .claude/ directory for all artifacts and enriches them with
    source information (managed, unmanaged, or local).

    Args:
        project_dir: Project root directory
        config: Project configuration from kits.toml

    Returns:
        List of all installed artifacts with metadata
    """
    claude_dir = project_dir / ".claude"
    if not claude_dir.exists():
        return []

    artifacts: list[InstalledArtifact] = []

    # Map of artifact paths to installed kits for tracking managed status
    managed_artifacts: dict[str, InstalledKit] = {}
    for kit in config.kits.values():
        for artifact_path in kit.artifacts:
            managed_artifacts[artifact_path] = kit

    # Scan skills directory
    skills_dir = claude_dir / "skills"
    if skills_dir.exists():
        for skill_dir in skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue

            artifact = _create_artifact_from_file(
                skill_file, "skill", skill_dir.name, managed_artifacts, config
            )
            if artifact:
                artifacts.append(artifact)

    # Scan commands directory
    commands_dir = claude_dir / "commands"
    if commands_dir.exists():
        for item in commands_dir.iterdir():
            if item.is_file() and item.suffix == ".md":
                # Direct command file: commands/command-name.md
                name = item.stem
                artifact = _create_artifact_from_file(
                    item, "command", name, managed_artifacts, config
                )
                if artifact:
                    artifacts.append(artifact)
            elif item.is_dir():
                # Kit commands directory: commands/kit-name/*.md
                for cmd_file in item.glob("*.md"):
                    # Format as "kit:command-name"
                    name = f"{item.name}:{cmd_file.stem}"
                    artifact = _create_artifact_from_file(
                        cmd_file, "command", name, managed_artifacts, config
                    )
                    if artifact:
                        artifacts.append(artifact)

    # Scan agents directory
    agents_dir = claude_dir / "agents"
    if agents_dir.exists():
        for item in agents_dir.iterdir():
            if item.is_file() and item.suffix == ".md":
                # Direct agent file: agents/agent-name.md
                name = item.stem
                artifact = _create_artifact_from_file(
                    item, "agent", name, managed_artifacts, config
                )
                if artifact:
                    artifacts.append(artifact)
            elif item.is_dir():
                # Kit agents directory: agents/kit-name/*.md
                for agent_file in item.glob("*.md"):
                    name = agent_file.stem
                    artifact = _create_artifact_from_file(
                        agent_file, "agent", name, managed_artifacts, config
                    )
                    if artifact:
                        artifacts.append(artifact)

    return artifacts


def _create_artifact_from_file(
    file_path: Path,
    artifact_type: ArtifactType,
    display_name: str,
    managed_artifacts: dict[str, InstalledKit],
    config: ProjectConfig,
) -> InstalledArtifact | None:
    """Create an InstalledArtifact from a file.

    Args:
        file_path: Path to the artifact file
        artifact_type: Type of artifact (skill, command, agent)
        display_name: Display name for the artifact
        managed_artifacts: Map of artifact paths to installed kits
        config: Project configuration

    Returns:
        InstalledArtifact or None if file doesn't exist
    """
    if not file_path.exists():
        return None

    # Get relative path from .claude/ directory
    claude_dir = file_path.parent
    while claude_dir.name != ".claude" and claude_dir.parent != claude_dir:
        claude_dir = claude_dir.parent
    relative_path = file_path.relative_to(claude_dir)

    # Determine source and kit info
    source = ArtifactSource.LOCAL
    kit_id = None
    kit_version = None

    # Check if it's a managed artifact
    # Config paths may include ".claude/" prefix, so check both variations
    for artifact_path, kit in managed_artifacts.items():
        normalized_artifact = artifact_path.replace(".claude/", "").replace("\\", "/")
        normalized_relative = str(relative_path).replace("\\", "/")

        if normalized_relative == normalized_artifact:
            source = ArtifactSource.MANAGED
            kit_id = kit.kit_id
            kit_version = kit.version
            break

    # If not managed, it's a local artifact

    return InstalledArtifact(
        artifact_type=artifact_type,
        artifact_name=display_name,
        file_path=relative_path,
        source=source,
        level=ArtifactLevel.PROJECT,
        kit_id=kit_id,
        kit_version=kit_version,
    )
