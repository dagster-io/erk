"""Discover artifacts installed in a project's .claude/ and .github/ directories."""

import hashlib
import json
from pathlib import Path

from erk.artifacts.models import ArtifactType, InstalledArtifact
from erk.core.claude_settings import (
    ERK_EXIT_PLAN_HOOK_COMMAND,
    ERK_USER_PROMPT_HOOK_COMMAND,
)


def _compute_file_hash(path: Path) -> str:
    """Compute SHA256 hash of single file content."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _compute_directory_hash(path: Path) -> str:
    """Compute combined hash of all files in directory.

    Includes relative path in hash to detect structural changes (renames, moves).
    Files are processed in sorted order for deterministic hashing.
    """
    hasher = hashlib.sha256()
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file():
            # Include relative path in hash for structural changes
            hasher.update(file_path.relative_to(path).as_posix().encode())
            hasher.update(file_path.read_bytes())
    return hasher.hexdigest()[:16]


def _compute_hook_hash(command: str) -> str:
    """Compute hash of hook command string."""
    return hashlib.sha256(command.encode()).hexdigest()[:16]


def _compute_content_hash(path: Path) -> str:
    """Compute SHA256 hash of file or directory content.

    For files: hashes the file content directly.
    For directories: hashes all files with their relative paths.
    """
    if path.is_dir():
        return _compute_directory_hash(path)
    return _compute_file_hash(path)


def _discover_skills(claude_dir: Path) -> list[InstalledArtifact]:
    """Discover skills in .claude/skills/ directory.

    Skills are identified by their SKILL.md entry point file.
    Pattern: skills/<skill-name>/SKILL.md

    Content hash is computed over the entire skill directory (all files),
    not just the SKILL.md entry point.
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
                    # Hash the entire skill directory, not just SKILL.md
                    content_hash=_compute_directory_hash(skill_dir),
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

    Supports two patterns:
    1. Directory-based: agents/<name>/<name>.md (hash computed over entire directory)
    2. Single-file: agents/<name>.md (hash computed over single file)

    Directory-based agents take precedence if both exist.
    """
    agents_dir = claude_dir / "agents"
    if not agents_dir.exists():
        return []

    artifacts: list[InstalledArtifact] = []

    # First, discover directory-based agents: agents/<name>/<name>.md
    for item in agents_dir.iterdir():
        if item.is_dir():
            agent_file = item / f"{item.name}.md"
            if agent_file.exists():
                artifacts.append(
                    InstalledArtifact(
                        name=item.name,
                        artifact_type="agent",
                        path=agent_file,
                        content_hash=_compute_directory_hash(item),
                    )
                )

    # Track discovered names to avoid duplicates
    discovered_names = {a.name for a in artifacts}

    # Second, discover single-file agents: agents/<name>.md
    for item in agents_dir.iterdir():
        if item.is_file() and item.suffix == ".md":
            name = item.stem
            if name not in discovered_names:
                artifacts.append(
                    InstalledArtifact(
                        name=name,
                        artifact_type="agent",
                        path=item,
                        content_hash=_compute_file_hash(item),
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


def _extract_hook_name(command: str) -> str:
    """Extract a meaningful name from a hook command.

    For erk hooks, returns the known name.
    For local hooks, returns the full command text for identification.
    """
    # Check for erk-managed hooks first
    if command == ERK_USER_PROMPT_HOOK_COMMAND:
        return "user-prompt-hook"
    if command == ERK_EXIT_PLAN_HOOK_COMMAND:
        return "exit-plan-mode-hook"

    # For local hooks, use the full command text as the identifier
    return command


def _discover_hooks(claude_dir: Path) -> list[InstalledArtifact]:
    """Discover all hooks configured in .claude/settings.json.

    Hooks are configuration entries in settings.json, not files.
    Discovers both erk-managed hooks and local/user-defined hooks.

    Pattern: hooks.<HookType>[].hooks[].command
    """
    settings_path = claude_dir / "settings.json"
    if not settings_path.exists():
        return []

    content = settings_path.read_text(encoding="utf-8")
    settings = json.loads(content)
    hooks_section = settings.get("hooks", {})
    if not hooks_section:
        return []

    artifacts: list[InstalledArtifact] = []
    seen_names: set[str] = set()

    # Iterate through all hook types (UserPromptSubmit, PreToolUse, etc.)
    for hook_entries in hooks_section.values():
        if not isinstance(hook_entries, list):
            continue
        for entry in hook_entries:
            if not isinstance(entry, dict):
                continue
            for hook in entry.get("hooks", []):
                if not isinstance(hook, dict):
                    continue
                command = hook.get("command")
                if not command:
                    continue

                name = _extract_hook_name(command)

                # Avoid duplicates
                if name in seen_names:
                    continue
                seen_names.add(name)

                artifacts.append(
                    InstalledArtifact(
                        name=name,
                        artifact_type="hook",
                        path=settings_path,
                        content_hash=_compute_hook_hash(command),
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
    - hooks: configured in .claude/settings.json
    """
    claude_dir = project_dir / ".claude"
    workflows_dir = project_dir / ".github" / "workflows"

    artifacts: list[InstalledArtifact] = []

    if claude_dir.exists():
        artifacts.extend(_discover_skills(claude_dir))
        artifacts.extend(_discover_commands(claude_dir))
        artifacts.extend(_discover_agents(claude_dir))
        artifacts.extend(_discover_hooks(claude_dir))

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
