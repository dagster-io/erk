"""Discover artifacts installed in a project's .claude/ directory."""

import hashlib
from pathlib import Path

from erk.artifacts.models import ArtifactType, InstalledArtifact


def _compute_content_hash(path: Path) -> str:
    """Compute SHA256 hash of file content."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _discover_skills(claude_dir: Path) -> list[InstalledArtifact]:
    """Discover skills in .claude/skills/ directory.

    Skills are identified by their SKILL.md entry point file.
    Pattern: skills/<skill-name>/SKILL.md
    """
    skills_dir = claude_dir / "skills"
    if not skills_dir.exists():
        return []

    artifacts: list[InstalledArtifact] = []
    for skill_dir in skills_dir.iterdir():
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if skill_file.exists():
            artifacts.append(
                InstalledArtifact(
                    name=skill_dir.name,
                    artifact_type="skill",
                    path=skill_file,
                    content_hash=_compute_content_hash(skill_file),
                )
            )
    return artifacts


def _discover_commands(claude_dir: Path) -> list[InstalledArtifact]:
    """Discover commands in .claude/commands/ directory.

    Commands are organized by namespace.
    Pattern: commands/<namespace>/<command>.md
    """
    commands_dir = claude_dir / "commands"
    if not commands_dir.exists():
        return []

    artifacts: list[InstalledArtifact] = []
    for namespace_dir in commands_dir.iterdir():
        if not namespace_dir.is_dir():
            continue
        for cmd_file in namespace_dir.glob("*.md"):
            # Name includes namespace: "local:fast-ci" or "erk:plan-implement"
            name = f"{namespace_dir.name}:{cmd_file.stem}"
            artifacts.append(
                InstalledArtifact(
                    name=name,
                    artifact_type="command",
                    path=cmd_file,
                    content_hash=_compute_content_hash(cmd_file),
                )
            )
    return artifacts


def _discover_agents(claude_dir: Path) -> list[InstalledArtifact]:
    """Discover agents in .claude/agents/ directory.

    Pattern: agents/<agent-name>/<agent-name>.md
    """
    agents_dir = claude_dir / "agents"
    if not agents_dir.exists():
        return []

    artifacts: list[InstalledArtifact] = []
    for agent_dir in agents_dir.iterdir():
        if not agent_dir.is_dir():
            continue
        # Agent file has same name as directory
        agent_file = agent_dir / f"{agent_dir.name}.md"
        if agent_file.exists():
            artifacts.append(
                InstalledArtifact(
                    name=agent_dir.name,
                    artifact_type="agent",
                    path=agent_file,
                    content_hash=_compute_content_hash(agent_file),
                )
            )
    return artifacts


def discover_artifacts(claude_dir: Path) -> list[InstalledArtifact]:
    """Scan .claude/ directory and return all installed artifacts.

    Discovers:
    - skills: skills/<name>/SKILL.md
    - commands: commands/<namespace>/<name>.md
    - agents: agents/<name>/<name>.md
    """
    if not claude_dir.exists():
        return []

    artifacts: list[InstalledArtifact] = []
    artifacts.extend(_discover_skills(claude_dir))
    artifacts.extend(_discover_commands(claude_dir))
    artifacts.extend(_discover_agents(claude_dir))

    # Sort by type then name for consistent output
    return sorted(artifacts, key=lambda a: (a.artifact_type, a.name))


def get_artifact_by_name(
    claude_dir: Path, name: str, artifact_type: ArtifactType | None
) -> InstalledArtifact | None:
    """Find a specific artifact by name.

    If artifact_type is provided, only search that type.
    Otherwise, search all types and return first match.
    """
    artifacts = discover_artifacts(claude_dir)
    for artifact in artifacts:
        if artifact.name == name:
            if artifact_type is None or artifact.artifact_type == artifact_type:
                return artifact
    return None
