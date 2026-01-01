"""Orphaned artifact detection for erk-managed .claude/ directories."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from erk.artifacts.detection import is_in_erk_repo
from erk.artifacts.discovery import (
    _compute_directory_hash,
    _compute_file_hash,
    _compute_hook_hash,
)
from erk.artifacts.models import ArtifactFileState, CompletenessCheckResult, OrphanCheckResult
from erk.artifacts.sync import get_bundled_claude_dir, get_bundled_github_dir
from erk.core.claude_settings import (
    ERK_EXIT_PLAN_HOOK_COMMAND,
    ERK_USER_PROMPT_HOOK_COMMAND,
    has_exit_plan_hook,
    has_user_prompt_hook,
)
from erk.core.release_notes import get_current_version

# Bundled artifacts that erk syncs to projects
BUNDLED_SKILLS = frozenset(
    {
        "dignified-python",
        "learned-docs",
        "erk-diff-analysis",
    }
)
BUNDLED_AGENTS = frozenset({"devrun"})
BUNDLED_WORKFLOWS = frozenset({"erk-impl.yml"})
# Hook configurations that erk adds to settings.json
BUNDLED_HOOKS = frozenset({"user-prompt-hook", "exit-plan-mode-hook"})


# Status types for per-artifact version tracking
ArtifactStatusType = Literal["up-to-date", "changed-upstream", "locally-modified", "not-installed"]


@dataclass(frozen=True)
class ArtifactStatus:
    """Per-artifact status comparing installed vs bundled state."""

    name: str  # e.g. "skills/dignified-python", "commands/erk/plan-implement.md"
    installed_version: str | None  # version at sync time, None if not tracked
    current_version: str  # current erk version
    installed_hash: str | None  # hash at sync time, None if not tracked
    current_hash: str | None  # current computed hash, None if not installed
    status: ArtifactStatusType


@dataclass(frozen=True)
class ArtifactHealthResult:
    """Result of per-artifact health check."""

    artifacts: list[ArtifactStatus]
    skipped_reason: Literal["erk-repo", "no-claude-dir", "no-bundled-dir"] | None


def _compute_bundled_skill_hash(bundled_claude_dir: Path, skill_name: str) -> str | None:
    """Compute hash of bundled skill directory."""
    skill_dir = bundled_claude_dir / "skills" / skill_name
    if not skill_dir.exists():
        return None
    return _compute_directory_hash(skill_dir)


def _compute_bundled_agent_hash(bundled_claude_dir: Path, agent_name: str) -> str | None:
    """Compute hash of bundled agent directory."""
    agent_dir = bundled_claude_dir / "agents" / agent_name
    if not agent_dir.exists():
        return None
    return _compute_directory_hash(agent_dir)


def _compute_bundled_command_hash(bundled_claude_dir: Path, cmd_filename: str) -> str | None:
    """Compute hash of bundled command file."""
    cmd_file = bundled_claude_dir / "commands" / "erk" / cmd_filename
    if not cmd_file.exists():
        return None
    return _compute_file_hash(cmd_file)


def _compute_bundled_workflow_hash(bundled_github_dir: Path, workflow_name: str) -> str | None:
    """Compute hash of bundled workflow file."""
    workflow_file = bundled_github_dir / "workflows" / workflow_name
    if not workflow_file.exists():
        return None
    return _compute_file_hash(workflow_file)


def _compute_installed_skill_hash(project_claude_dir: Path, skill_name: str) -> str | None:
    """Compute hash of installed skill directory."""
    skill_dir = project_claude_dir / "skills" / skill_name
    if not skill_dir.exists():
        return None
    return _compute_directory_hash(skill_dir)


def _compute_installed_agent_hash(project_claude_dir: Path, agent_name: str) -> str | None:
    """Compute hash of installed agent directory."""
    agent_dir = project_claude_dir / "agents" / agent_name
    if not agent_dir.exists():
        return None
    return _compute_directory_hash(agent_dir)


def _compute_installed_command_hash(project_claude_dir: Path, cmd_filename: str) -> str | None:
    """Compute hash of installed command file."""
    cmd_file = project_claude_dir / "commands" / "erk" / cmd_filename
    if not cmd_file.exists():
        return None
    return _compute_file_hash(cmd_file)


def _compute_installed_workflow_hash(project_workflows_dir: Path, workflow_name: str) -> str | None:
    """Compute hash of installed workflow file."""
    workflow_file = project_workflows_dir / workflow_name
    if not workflow_file.exists():
        return None
    return _compute_file_hash(workflow_file)


def _determine_status(
    installed_version: str | None,
    current_version: str,
    installed_hash: str | None,
    current_hash: str | None,
) -> ArtifactStatusType:
    """Determine artifact status from version/hash comparison.

    Logic:
    - current_hash is None → not installed
    - installed_hash != current_hash AND installed_version == current_version → locally modified
    - installed_version != current_version → changed upstream
    - Both match → up-to-date
    """
    if current_hash is None:
        return "not-installed"

    if installed_hash is None or installed_version is None:
        # No prior state recorded - treat as changed upstream
        return "changed-upstream"

    if installed_hash != current_hash:
        if installed_version == current_version:
            # Hash changed but version didn't → local modification
            return "locally-modified"
        # Hash changed and version changed → upstream change
        return "changed-upstream"

    if installed_version != current_version:
        # Version changed but hash didn't → still changed upstream
        return "changed-upstream"

    return "up-to-date"


def get_artifact_health(
    project_dir: Path, saved_files: dict[str, ArtifactFileState]
) -> ArtifactHealthResult:
    """Get per-artifact health status comparing installed vs bundled state.

    Args:
        project_dir: Path to the project root
        saved_files: Per-artifact state from .erk/state.toml (artifact key -> ArtifactFileState)

    Returns:
        ArtifactHealthResult with status for each bundled artifact
    """
    # Skip check in erk repo - artifacts are source, not synced
    if is_in_erk_repo(project_dir):
        return ArtifactHealthResult(artifacts=[], skipped_reason="erk-repo")

    # Skip if no .claude/ directory
    project_claude_dir = project_dir / ".claude"
    if not project_claude_dir.exists():
        return ArtifactHealthResult(artifacts=[], skipped_reason="no-claude-dir")

    bundled_claude_dir = get_bundled_claude_dir()
    if not bundled_claude_dir.exists():
        return ArtifactHealthResult(artifacts=[], skipped_reason="no-bundled-dir")

    project_workflows_dir = project_dir / ".github" / "workflows"
    current_version = get_current_version()

    artifacts: list[ArtifactStatus] = []

    # Check skills
    for skill_name in BUNDLED_SKILLS:
        key = f"skills/{skill_name}"
        saved = saved_files.get(key)
        installed_hash = _compute_installed_skill_hash(project_claude_dir, skill_name)

        artifacts.append(
            ArtifactStatus(
                name=key,
                installed_version=saved.version if saved else None,
                current_version=current_version,
                installed_hash=saved.hash if saved else None,
                current_hash=installed_hash,
                status=_determine_status(
                    saved.version if saved else None,
                    current_version,
                    saved.hash if saved else None,
                    installed_hash,
                ),
            )
        )

    # Check agents
    for agent_name in BUNDLED_AGENTS:
        key = f"agents/{agent_name}"
        saved = saved_files.get(key)
        installed_hash = _compute_installed_agent_hash(project_claude_dir, agent_name)

        artifacts.append(
            ArtifactStatus(
                name=key,
                installed_version=saved.version if saved else None,
                current_version=current_version,
                installed_hash=saved.hash if saved else None,
                current_hash=installed_hash,
                status=_determine_status(
                    saved.version if saved else None,
                    current_version,
                    saved.hash if saved else None,
                    installed_hash,
                ),
            )
        )

    # Check commands (enumerate erk commands from bundled source)
    bundled_erk_commands = bundled_claude_dir / "commands" / "erk"
    if bundled_erk_commands.exists():
        for cmd_file in sorted(bundled_erk_commands.glob("*.md")):
            key = f"commands/erk/{cmd_file.name}"
            saved = saved_files.get(key)
            installed_hash = _compute_installed_command_hash(project_claude_dir, cmd_file.name)

            artifacts.append(
                ArtifactStatus(
                    name=key,
                    installed_version=saved.version if saved else None,
                    current_version=current_version,
                    installed_hash=saved.hash if saved else None,
                    current_hash=installed_hash,
                    status=_determine_status(
                        saved.version if saved else None,
                        current_version,
                        saved.hash if saved else None,
                        installed_hash,
                    ),
                )
            )

    # Check workflows
    for workflow_name in BUNDLED_WORKFLOWS:
        key = f"workflows/{workflow_name}"
        saved = saved_files.get(key)
        installed_hash = _compute_installed_workflow_hash(project_workflows_dir, workflow_name)

        artifacts.append(
            ArtifactStatus(
                name=key,
                installed_version=saved.version if saved else None,
                current_version=current_version,
                installed_hash=saved.hash if saved else None,
                current_hash=installed_hash,
                status=_determine_status(
                    saved.version if saved else None,
                    current_version,
                    saved.hash if saved else None,
                    installed_hash,
                ),
            )
        )

    # Check hooks
    settings_path = project_claude_dir / "settings.json"
    if settings_path.exists():
        content = settings_path.read_text(encoding="utf-8")
        settings = json.loads(content)

        # user-prompt-hook
        key = "hooks/user-prompt-hook"
        saved = saved_files.get(key)
        hook_installed = has_user_prompt_hook(settings)
        hook_hash = _compute_hook_hash(ERK_USER_PROMPT_HOOK_COMMAND) if hook_installed else None

        artifacts.append(
            ArtifactStatus(
                name=key,
                installed_version=saved.version if saved else None,
                current_version=current_version,
                installed_hash=saved.hash if saved else None,
                current_hash=hook_hash,
                status=_determine_status(
                    saved.version if saved else None,
                    current_version,
                    saved.hash if saved else None,
                    hook_hash,
                ),
            )
        )

        # exit-plan-mode-hook
        key = "hooks/exit-plan-mode-hook"
        saved = saved_files.get(key)
        hook_installed = has_exit_plan_hook(settings)
        hook_hash = _compute_hook_hash(ERK_EXIT_PLAN_HOOK_COMMAND) if hook_installed else None

        artifacts.append(
            ArtifactStatus(
                name=key,
                installed_version=saved.version if saved else None,
                current_version=current_version,
                installed_hash=saved.hash if saved else None,
                current_hash=hook_hash,
                status=_determine_status(
                    saved.version if saved else None,
                    current_version,
                    saved.hash if saved else None,
                    hook_hash,
                ),
            )
        )
    else:
        # No settings.json - all hooks are not installed
        for hook_name in ["user-prompt-hook", "exit-plan-mode-hook"]:
            key = f"hooks/{hook_name}"
            saved = saved_files.get(key)

            artifacts.append(
                ArtifactStatus(
                    name=key,
                    installed_version=saved.version if saved else None,
                    current_version=current_version,
                    installed_hash=saved.hash if saved else None,
                    current_hash=None,
                    status="not-installed",
                )
            )

    return ArtifactHealthResult(artifacts=artifacts, skipped_reason=None)


def _find_orphaned_claude_artifacts(
    project_claude_dir: Path,
    bundled_claude_dir: Path,
) -> dict[str, list[str]]:
    """Find files in bundled .claude/ folders that exist locally but not in package.

    Compares bundled artifact directories with the local project's .claude/ directory
    to find orphaned files that should be removed.

    Args:
        project_claude_dir: Path to project's .claude/ directory
        bundled_claude_dir: Path to bundled .claude/ in erk package

    Returns:
        Dict mapping folder path (relative to .claude/) to list of orphaned filenames
    """
    orphans: dict[str, list[str]] = {}

    # Check commands/erk/ directory
    local_commands = project_claude_dir / "commands" / "erk"
    bundled_commands = bundled_claude_dir / "commands" / "erk"

    if local_commands.exists() and bundled_commands.exists():
        bundled_files = {f.name for f in bundled_commands.iterdir() if f.is_file()}
        for local_file in local_commands.iterdir():
            if not local_file.is_file():
                continue
            if local_file.name not in bundled_files:
                folder_key = "commands/erk"
                if folder_key not in orphans:
                    orphans[folder_key] = []
                orphans[folder_key].append(local_file.name)

    # Check bundled skill directories
    for skill_name in BUNDLED_SKILLS:
        local_skill = project_claude_dir / "skills" / skill_name
        bundled_skill = bundled_claude_dir / "skills" / skill_name

        if local_skill.exists() and bundled_skill.exists():
            # Get all files recursively from bundled
            bundled_files = {
                str(f.relative_to(bundled_skill)) for f in bundled_skill.rglob("*") if f.is_file()
            }
            # Check local files
            for local_file in local_skill.rglob("*"):
                if not local_file.is_file():
                    continue
                relative_path = str(local_file.relative_to(local_skill))
                if relative_path not in bundled_files:
                    folder_key = f"skills/{skill_name}"
                    if folder_key not in orphans:
                        orphans[folder_key] = []
                    orphans[folder_key].append(relative_path)

    # Check bundled agent directories
    for agent_name in BUNDLED_AGENTS:
        local_agent = project_claude_dir / "agents" / agent_name
        bundled_agent = bundled_claude_dir / "agents" / agent_name

        if local_agent.exists() and bundled_agent.exists():
            # Get all files recursively from bundled
            bundled_files = {
                str(f.relative_to(bundled_agent)) for f in bundled_agent.rglob("*") if f.is_file()
            }
            # Check local files
            for local_file in local_agent.rglob("*"):
                if not local_file.is_file():
                    continue
                relative_path = str(local_file.relative_to(local_agent))
                if relative_path not in bundled_files:
                    folder_key = f"agents/{agent_name}"
                    if folder_key not in orphans:
                        orphans[folder_key] = []
                    orphans[folder_key].append(relative_path)

    return orphans


def _find_orphaned_workflows(
    project_workflows_dir: Path,
    bundled_workflows_dir: Path,
) -> dict[str, list[str]]:
    """Find erk-managed workflow files that exist locally but not in package.

    Only checks files that are in BUNDLED_WORKFLOWS - we don't want to flag
    user workflows that erk doesn't manage.

    Args:
        project_workflows_dir: Path to project's .github/workflows/ directory
        bundled_workflows_dir: Path to bundled .github/workflows/ in erk package

    Returns:
        Dict mapping ".github/workflows" to list of orphaned workflow filenames
    """
    if not project_workflows_dir.exists():
        return {}
    if not bundled_workflows_dir.exists():
        return {}

    orphans: dict[str, list[str]] = {}

    # Only check erk-managed workflow files
    for workflow_name in BUNDLED_WORKFLOWS:
        local_workflow = project_workflows_dir / workflow_name
        bundled_workflow = bundled_workflows_dir / workflow_name

        # If file exists locally but not in bundled, it's orphaned
        if local_workflow.exists() and not bundled_workflow.exists():
            folder_key = ".github/workflows"
            if folder_key not in orphans:
                orphans[folder_key] = []
            orphans[folder_key].append(workflow_name)

    return orphans


def find_orphaned_artifacts(project_dir: Path) -> OrphanCheckResult:
    """Find orphaned files in erk-managed artifact directories.

    Compares local .claude/ and .github/ artifacts with bundled package to find files
    that exist locally but are not in the current erk package version.

    Args:
        project_dir: Path to the project root

    Returns:
        OrphanCheckResult with orphan status
    """
    # Skip check in erk repo - artifacts are source, not synced
    if is_in_erk_repo(project_dir):
        return OrphanCheckResult(
            orphans={},
            skipped_reason="erk-repo",
        )

    # Skip if no .claude/ directory
    project_claude_dir = project_dir / ".claude"
    if not project_claude_dir.exists():
        return OrphanCheckResult(
            orphans={},
            skipped_reason="no-claude-dir",
        )

    bundled_claude_dir = get_bundled_claude_dir()
    if not bundled_claude_dir.exists():
        return OrphanCheckResult(
            orphans={},
            skipped_reason="no-bundled-dir",
        )

    orphans = _find_orphaned_claude_artifacts(project_claude_dir, bundled_claude_dir)

    # Also check for orphaned workflows
    bundled_github_dir = get_bundled_github_dir()
    project_workflows_dir = project_dir / ".github" / "workflows"
    bundled_workflows_dir = bundled_github_dir / "workflows"
    orphans.update(_find_orphaned_workflows(project_workflows_dir, bundled_workflows_dir))

    return OrphanCheckResult(
        orphans=orphans,
        skipped_reason=None,
    )


def _find_missing_claude_artifacts(
    project_claude_dir: Path,
    bundled_claude_dir: Path,
) -> dict[str, list[str]]:
    """Find files in bundled .claude/ that are missing locally.

    Checks bundled → local direction (opposite of orphan detection).
    Returns dict mapping folder path to list of missing filenames.

    Args:
        project_claude_dir: Path to project's .claude/ directory
        bundled_claude_dir: Path to bundled .claude/ in erk package

    Returns:
        Dict mapping folder path (relative to .claude/) to list of missing filenames
    """
    missing: dict[str, list[str]] = {}

    # Check commands/erk/ directory
    bundled_commands = bundled_claude_dir / "commands" / "erk"
    local_commands = project_claude_dir / "commands" / "erk"

    if bundled_commands.exists():
        local_commands.mkdir(parents=True, exist_ok=True)
        local_files = {f.name for f in local_commands.iterdir() if f.is_file()}

        for bundled_file in bundled_commands.iterdir():
            if not bundled_file.is_file():
                continue
            if bundled_file.name not in local_files:
                folder_key = "commands/erk"
                if folder_key not in missing:
                    missing[folder_key] = []
                missing[folder_key].append(bundled_file.name)

    # Check bundled skills (dignified-python, learned-docs, erk-diff-analysis)
    for skill_name in BUNDLED_SKILLS:
        bundled_skill = bundled_claude_dir / "skills" / skill_name
        local_skill = project_claude_dir / "skills" / skill_name

        if bundled_skill.exists():
            local_skill.mkdir(parents=True, exist_ok=True)

            # Get all files recursively from bundled
            bundled_files = {
                str(f.relative_to(bundled_skill)) for f in bundled_skill.rglob("*") if f.is_file()
            }

            # Get all files recursively from local
            local_files = {
                str(f.relative_to(local_skill)) for f in local_skill.rglob("*") if f.is_file()
            }

            # Find missing
            missing_in_skill = bundled_files - local_files
            if missing_in_skill:
                folder_key = f"skills/{skill_name}"
                missing[folder_key] = sorted(missing_in_skill)

    # Check bundled agents (devrun)
    for agent_name in BUNDLED_AGENTS:
        bundled_agent = bundled_claude_dir / "agents" / agent_name
        local_agent = project_claude_dir / "agents" / agent_name

        if bundled_agent.exists():
            local_agent.mkdir(parents=True, exist_ok=True)

            bundled_files = {
                str(f.relative_to(bundled_agent)) for f in bundled_agent.rglob("*") if f.is_file()
            }

            local_files = {
                str(f.relative_to(local_agent)) for f in local_agent.rglob("*") if f.is_file()
            }

            missing_in_agent = bundled_files - local_files
            if missing_in_agent:
                folder_key = f"agents/{agent_name}"
                missing[folder_key] = sorted(missing_in_agent)

    return missing


def _find_missing_workflows(
    project_workflows_dir: Path,
    bundled_workflows_dir: Path,
) -> dict[str, list[str]]:
    """Find erk-managed workflows that exist in bundle but missing locally.

    Args:
        project_workflows_dir: Path to project's .github/workflows/ directory
        bundled_workflows_dir: Path to bundled .github/workflows/ in erk package

    Returns:
        Dict mapping ".github/workflows" to list of missing workflow filenames
    """
    if not bundled_workflows_dir.exists():
        return {}

    project_workflows_dir.mkdir(parents=True, exist_ok=True)
    missing: dict[str, list[str]] = {}

    for workflow_name in BUNDLED_WORKFLOWS:
        bundled_workflow = bundled_workflows_dir / workflow_name
        local_workflow = project_workflows_dir / workflow_name

        # If bundled but not local, it's missing
        if bundled_workflow.exists() and not local_workflow.exists():
            folder_key = ".github/workflows"
            if folder_key not in missing:
                missing[folder_key] = []
            missing[folder_key].append(workflow_name)

    return missing


def _find_missing_hooks(project_claude_dir: Path) -> dict[str, list[str]]:
    """Find erk-managed hooks that are missing from settings.json.

    Args:
        project_claude_dir: Path to project's .claude/ directory

    Returns:
        Dict mapping "settings.json" to list of missing hook names
    """
    settings_path = project_claude_dir / "settings.json"
    missing: dict[str, list[str]] = {}

    # If no settings.json, all hooks are missing
    if not settings_path.exists():
        return {"settings.json": sorted(BUNDLED_HOOKS)}

    content = settings_path.read_text(encoding="utf-8")
    settings = json.loads(content)

    missing_hooks: list[str] = []

    if not has_user_prompt_hook(settings):
        missing_hooks.append("user-prompt-hook")

    if not has_exit_plan_hook(settings):
        missing_hooks.append("exit-plan-mode-hook")

    if missing_hooks:
        missing["settings.json"] = sorted(missing_hooks)

    return missing


def find_missing_artifacts(project_dir: Path) -> CompletenessCheckResult:
    """Find bundled artifacts that are missing from local installation.

    Checks bundled → local direction to detect incomplete syncs.

    Args:
        project_dir: Path to the project root

    Returns:
        CompletenessCheckResult with missing artifact status
    """
    # Skip in erk repo - artifacts are source
    if is_in_erk_repo(project_dir):
        return CompletenessCheckResult(
            missing={},
            skipped_reason="erk-repo",
        )

    # Skip if no .claude/ directory
    project_claude_dir = project_dir / ".claude"
    if not project_claude_dir.exists():
        return CompletenessCheckResult(
            missing={},
            skipped_reason="no-claude-dir",
        )

    bundled_claude_dir = get_bundled_claude_dir()
    if not bundled_claude_dir.exists():
        return CompletenessCheckResult(
            missing={},
            skipped_reason="no-bundled-dir",
        )

    missing = _find_missing_claude_artifacts(project_claude_dir, bundled_claude_dir)

    # Check workflows
    bundled_github_dir = get_bundled_github_dir()
    project_workflows_dir = project_dir / ".github" / "workflows"
    bundled_workflows_dir = bundled_github_dir / "workflows"
    missing.update(_find_missing_workflows(project_workflows_dir, bundled_workflows_dir))

    # Check hooks in settings.json
    missing.update(_find_missing_hooks(project_claude_dir))

    return CompletenessCheckResult(
        missing=missing,
        skipped_reason=None,
    )
