"""Sync artifacts from erk package to project's .claude/ directory."""

import json
import shutil
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from erk.artifacts.detection import is_in_erk_repo
from erk.artifacts.models import ArtifactState
from erk.artifacts.state import save_artifact_state
from erk.core.claude_settings import add_erk_hooks, has_exit_plan_hook, has_user_prompt_hook
from erk.core.release_notes import get_current_version


@dataclass(frozen=True)
class SyncResult:
    """Result of artifact sync operation."""

    success: bool
    artifacts_installed: int
    message: str


@cache
def _get_erk_package_dir() -> Path:
    """Get the erk package directory (where erk/__init__.py lives)."""
    # __file__ is .../erk/artifacts/sync.py, so parent.parent is erk/
    return Path(__file__).parent.parent


def _is_editable_install() -> bool:
    """Check if erk is installed in editable mode.

    Editable: erk package is in src/ layout (e.g., .../src/erk/)
    Wheel: erk package is in site-packages (e.g., .../site-packages/erk/)
    """
    return "site-packages" not in str(_get_erk_package_dir().resolve())


@cache
def get_bundled_claude_dir() -> Path:
    """Get path to bundled .claude/ directory in installed erk package.

    For wheel installs: .claude/ is bundled as package data at erk/data/claude/
    via pyproject.toml force-include.

    For editable installs: .claude/ is at the erk repo root (no wheel is built,
    so erk/data/ doesn't exist).
    """
    erk_package_dir = _get_erk_package_dir()

    if _is_editable_install():
        # Editable: erk package is at src/erk/, repo root is ../..
        erk_repo_root = erk_package_dir.parent.parent
        return erk_repo_root / ".claude"

    # Wheel install: data is bundled at erk/data/claude/
    return erk_package_dir / "data" / "claude"


@cache
def get_bundled_github_dir() -> Path:
    """Get path to bundled .github/ directory in installed erk package.

    For wheel installs: .github/ is bundled as package data at erk/data/github/
    via pyproject.toml force-include.

    For editable installs: .github/ is at the erk repo root.
    """
    erk_package_dir = _get_erk_package_dir()

    if _is_editable_install():
        # Editable: erk package is at src/erk/, repo root is ../..
        erk_repo_root = erk_package_dir.parent.parent
        return erk_repo_root / ".github"

    # Wheel install: data is bundled at erk/data/github/
    return erk_package_dir / "data" / "github"


def _copy_directory_contents(source_dir: Path, target_dir: Path) -> int:
    """Copy directory contents recursively, returning count of files copied."""
    if not source_dir.exists():
        return 0

    count = 0
    for source_path in source_dir.rglob("*"):
        if source_path.is_file():
            relative = source_path.relative_to(source_dir)
            target_path = target_dir / relative
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target_path)
            count += 1
    return count


def _sync_skills(source_skills_dir: Path, target_skills_dir: Path) -> int:
    """Sync bundled skills to project. Only syncs BUNDLED_SKILLS."""
    # Inline import: artifact_health.py imports get_bundled_*_dir from this module
    from erk.artifacts.artifact_health import BUNDLED_SKILLS

    if not source_skills_dir.exists():
        return 0

    copied = 0
    for skill_name in BUNDLED_SKILLS:
        source = source_skills_dir / skill_name
        if source.exists():
            target = target_skills_dir / skill_name
            copied += _copy_directory_contents(source, target)
    return copied


def _sync_agents(source_agents_dir: Path, target_agents_dir: Path) -> int:
    """Sync bundled agents to project. Only syncs BUNDLED_AGENTS."""
    # Inline import: artifact_health.py imports get_bundled_*_dir from this module
    from erk.artifacts.artifact_health import BUNDLED_AGENTS

    if not source_agents_dir.exists():
        return 0

    copied = 0
    for agent_name in BUNDLED_AGENTS:
        source = source_agents_dir / agent_name
        if source.exists():
            target = target_agents_dir / agent_name
            copied += _copy_directory_contents(source, target)
    return copied


def _sync_commands(source_commands_dir: Path, target_commands_dir: Path) -> int:
    """Sync bundled commands to project. Only syncs erk namespace."""
    if not source_commands_dir.exists():
        return 0

    source = source_commands_dir / "erk"
    if source.exists():
        target = target_commands_dir / "erk"
        return _copy_directory_contents(source, target)
    return 0


def _sync_workflows(bundled_github_dir: Path, target_workflows_dir: Path) -> int:
    """Sync erk-managed workflows to project's .github/workflows/ directory.

    Only syncs files listed in BUNDLED_WORKFLOWS registry.
    """
    # Inline import: artifact_health.py imports get_bundled_*_dir from this module
    from erk.artifacts.artifact_health import BUNDLED_WORKFLOWS

    source_workflows_dir = bundled_github_dir / "workflows"
    if not source_workflows_dir.exists():
        return 0

    count = 0
    for workflow_name in BUNDLED_WORKFLOWS:
        source_path = source_workflows_dir / workflow_name
        if source_path.exists():
            target_workflows_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_workflows_dir / workflow_name
            shutil.copy2(source_path, target_path)
            count += 1
    return count


def _sync_hooks(target_claude_dir: Path) -> int:
    """Sync erk-managed hooks to project's .claude/settings.json.

    Hooks are configuration entries, not files. This adds missing hooks
    to settings.json using the existing add_erk_hooks() function.

    Returns:
        Number of hooks added (0, 1, or 2)
    """
    settings_path = target_claude_dir / "settings.json"

    # Read existing settings or start with empty
    if settings_path.exists():
        content = settings_path.read_text(encoding="utf-8")
        settings = json.loads(content)
    else:
        settings = {}

    # Count hooks before adding
    had_user_prompt = has_user_prompt_hook(settings)
    had_exit_plan = has_exit_plan_hook(settings)

    # Add missing hooks
    updated_settings = add_erk_hooks(settings)

    # Write updated settings
    target_claude_dir.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(updated_settings, indent=2), encoding="utf-8")

    # Count hooks added
    added = 0
    if not had_user_prompt:
        added += 1
    if not had_exit_plan:
        added += 1
    return added


def sync_artifacts(project_dir: Path, force: bool) -> SyncResult:
    """Sync artifacts from erk package to project's .claude/ and .github/ directories.

    When running in the erk repo itself, skips sync since artifacts
    are read directly from source.
    """
    # Skip sync in erk repo - artifacts are already at source
    if is_in_erk_repo(project_dir):
        return SyncResult(
            success=True,
            artifacts_installed=0,
            message="Skipped: running in erk repo (artifacts read from source)",
        )

    bundled_claude_dir = get_bundled_claude_dir()
    if not bundled_claude_dir.exists():
        return SyncResult(
            success=False,
            artifacts_installed=0,
            message=f"Bundled .claude/ not found at {bundled_claude_dir}",
        )

    target_claude_dir = project_dir / ".claude"
    target_claude_dir.mkdir(parents=True, exist_ok=True)

    total_copied = 0

    # Sync filtered artifact folders (only bundled items, not all dev artifacts)
    total_copied += _sync_skills(bundled_claude_dir / "skills", target_claude_dir / "skills")
    total_copied += _sync_agents(bundled_claude_dir / "agents", target_claude_dir / "agents")
    total_copied += _sync_commands(bundled_claude_dir / "commands", target_claude_dir / "commands")

    # Sync workflows from .github/
    bundled_github_dir = get_bundled_github_dir()
    if bundled_github_dir.exists():
        target_workflows_dir = project_dir / ".github" / "workflows"
        total_copied += _sync_workflows(bundled_github_dir, target_workflows_dir)

    # Sync hooks to settings.json
    total_copied += _sync_hooks(target_claude_dir)

    # Save state with current version
    save_artifact_state(project_dir, ArtifactState(version=get_current_version()))

    return SyncResult(
        success=True,
        artifacts_installed=total_copied,
        message=f"Synced {total_copied} artifact files",
    )
