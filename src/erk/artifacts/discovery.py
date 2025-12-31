"""Discover artifacts installed in a project's .claude/ and .github/ directories."""

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

    Commands can be:
    - Top-level: commands/<command>.md (no namespace)
    - Namespaced: commands/<namespace>/<command>.md
    """
    commands_dir = claude_dir / "commands"
    if not commands_dir.exists():
        return []

    artifacts: list[InstalledArtifact] = []

    # Discover top-level commands (no namespace)
    for cmd_file in commands_dir.glob("*.md"):
        artifacts.append(
            InstalledArtifact(
                name=cmd_file.stem,
                artifact_type="command",
                path=cmd_file,
                content_hash=_compute_content_hash(cmd_file),
            )
        )

    # Discover namespaced commands
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


def _discover_workflows(workflows_dir: Path) -> list[InstalledArtifact]:
    """Discover all workflows in .github/workflows/ directory.

    Discovers all .yml and .yaml files in the workflows directory.

    Pattern: .github/workflows/<name>.yml
    """
    if not workflows_dir.exists():
        return []

    artifacts: list[InstalledArtifact] = []
    for workflow_file in workflows_dir.iterdir():
        if not workflow_file.is_file():
            continue
        if workflow_file.suffix not in (".yml", ".yaml"):
            continue
        artifacts.append(
            InstalledArtifact(
                name=workflow_file.stem,
                artifact_type="workflow",
                path=workflow_file,
                content_hash=_compute_content_hash(workflow_file),
            )
        )
    return artifacts


def discover_artifacts(project_dir: Path) -> list[InstalledArtifact]:
    """Scan project directory and return all installed artifacts.

    Discovers:
    - skills: .claude/skills/<name>/SKILL.md
    - commands: .claude/commands/<namespace>/<name>.md
    - agents: .claude/agents/<name>/<name>.md
    - workflows: .github/workflows/<name>.yml (all workflows)
    """
    claude_dir = project_dir / ".claude"
    workflows_dir = project_dir / ".github" / "workflows"

    artifacts: list[InstalledArtifact] = []

    if claude_dir.exists():
        artifacts.extend(_discover_skills(claude_dir))
        artifacts.extend(_discover_commands(claude_dir))
        artifacts.extend(_discover_agents(claude_dir))

    artifacts.extend(_discover_workflows(workflows_dir))

    # Sort by type then name for consistent output
    return sorted(artifacts, key=lambda a: (a.artifact_type, a.name))


def get_artifact_by_name(
    project_dir: Path, name: str, artifact_type: ArtifactType | None
) -> InstalledArtifact | None:
    """Find a specific artifact by name.

    If artifact_type is provided, only search that type.
    Otherwise, search all types and return first match.
    """
    artifacts = discover_artifacts(project_dir)
    for artifact in artifacts:
        if artifact.name == name:
            if artifact_type is None or artifact.artifact_type == artifact_type:
                return artifact
    return None
