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
from erk.artifacts.models import (
    ArtifactFileState,
    CompletenessCheckResult,
    InstalledArtifact,
    OrphanCheckResult,
)
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
BUNDLED_WORKFLOWS = frozenset({"erk-impl.yml", "learn-dispatch.yml"})
# Actions (composite GitHub actions) that erk syncs
BUNDLED_ACTIONS = frozenset({"setup-claude-code", "setup-claude-erk"})
# Hook configurations that erk adds to settings.json
BUNDLED_HOOKS = frozenset({"user-prompt-hook", "exit-plan-mode-hook"})


def is_erk_managed(artifact: InstalledArtifact) -> bool:
    """Check if artifact is managed by erk (bundled with erk package).

    Args:
        artifact: The artifact to check

    Returns:
        True if the artifact is bundled with erk, False if it's project-specific
    """
    if artifact.artifact_type == "command":
        return artifact.name.startswith("erk:")
    if artifact.artifact_type == "skill":
        return artifact.name in BUNDLED_SKILLS
    if artifact.artifact_type == "agent":
        return artifact.name in BUNDLED_AGENTS
    if artifact.artifact_type == "workflow":
        return f"{artifact.name}.yml" in BUNDLED_WORKFLOWS
    if artifact.artifact_type == "action":
        return artifact.name in BUNDLED_ACTIONS
    if artifact.artifact_type == "hook":
        return artifact.name in BUNDLED_HOOKS
    return False


# Status types for per-artifact version tracking
ArtifactStatusType = Literal["up-to-date", "changed-upstream", "locally-modified", "not-installed"]


@dataclass(frozen=True)
class ArtifactStatus:
    """Per-artifact status comparing installed vs bundled state."""

    name: str  # e.g. "skills/dignified-python", "commands/erk/system/impl-execute.md"
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


def _compute_path_hash(path: Path, is_directory: bool) -> str | None:
    """Compute hash of a path, returning None if it doesn't exist.

    Args:
        path: Path to the file or directory
        is_directory: True for directory hash, False for file hash
    """
    if not path.exists():
        return None
    if is_directory:
        return _compute_directory_hash(path)
    return _compute_file_hash(path)


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


def _build_artifact_status(
    key: str,
    current_hash: str | None,
    saved_files: dict[str, ArtifactFileState],
    current_version: str,
) -> ArtifactStatus:
    """Build ArtifactStatus from key, hash, and saved state."""
    saved = saved_files.get(key)
    return ArtifactStatus(
        name=key,
        installed_version=saved.version if saved else None,
        current_version=current_version,
        installed_hash=saved.hash if saved else None,
        current_hash=current_hash,
        status=_determine_status(
            saved.version if saved else None,
            current_version,
            saved.hash if saved else None,
            current_hash,
        ),
    )


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
    # Skip if no .claude/ directory
    project_claude_dir = project_dir / ".claude"
    if not project_claude_dir.exists():
        return ArtifactHealthResult(artifacts=[], skipped_reason="no-claude-dir")

    bundled_claude_dir = get_bundled_claude_dir()
    if not bundled_claude_dir.exists():
        return ArtifactHealthResult(artifacts=[], skipped_reason="no-bundled-dir")

    project_workflows_dir = project_dir / ".github" / "workflows"
    project_actions_dir = project_dir / ".github" / "actions"
    current_version = get_current_version()

    artifacts: list[ArtifactStatus] = []

    # Check skills (always directory-based)
    for name in BUNDLED_SKILLS:
        key = f"skills/{name}"
        path = project_claude_dir / "skills" / name
        installed_hash = _compute_path_hash(path, is_directory=True)
        artifacts.append(_build_artifact_status(key, installed_hash, saved_files, current_version))

    # Check agents (can be directory-based or single-file)
    # Key format depends on structure:
    #   - Directory: agents/{name} (like skills)
    #   - Single-file: agents/{name}.md (like commands)
    for name in BUNDLED_AGENTS:
        dir_path = project_claude_dir / "agents" / name
        file_path = project_claude_dir / "agents" / f"{name}.md"

        # Check bundled structure to determine canonical key format
        bundled_dir = bundled_claude_dir / "agents" / name
        bundled_file = bundled_claude_dir / "agents" / f"{name}.md"

        # Directory-based takes precedence, then single-file
        if bundled_dir.exists() and bundled_dir.is_dir():
            key = f"agents/{name}"
            installed_hash = _compute_path_hash(dir_path, is_directory=True)
        elif bundled_file.exists() and bundled_file.is_file():
            key = f"agents/{name}.md"
            installed_hash = _compute_path_hash(file_path, is_directory=False)
        elif dir_path.exists() and dir_path.is_dir():
            # Fallback: check installed structure
            key = f"agents/{name}"
            installed_hash = _compute_path_hash(dir_path, is_directory=True)
        elif file_path.exists() and file_path.is_file():
            key = f"agents/{name}.md"
            installed_hash = _compute_path_hash(file_path, is_directory=False)
        else:
            # Not installed anywhere - use single-file key as default for new agents
            key = f"agents/{name}.md"
            installed_hash = None

        artifacts.append(_build_artifact_status(key, installed_hash, saved_files, current_version))

    # Check commands (enumerate erk commands from bundled source, including nested dirs)
    bundled_erk_commands = bundled_claude_dir / "commands" / "erk"
    if bundled_erk_commands.exists():
        for cmd_file in sorted(bundled_erk_commands.rglob("*.md")):
            # Compute relative path (e.g., "system/impl-execute.md" or "plan-save.md")
            relative_path = cmd_file.relative_to(bundled_erk_commands)
            key = f"commands/erk/{relative_path}"
            path = project_claude_dir / "commands" / "erk" / relative_path
            installed_hash = _compute_path_hash(path, is_directory=False)
            artifacts.append(
                _build_artifact_status(key, installed_hash, saved_files, current_version)
            )

    # Check workflows
    for workflow_name in BUNDLED_WORKFLOWS:
        key = f"workflows/{workflow_name}"
        path = project_workflows_dir / workflow_name
        installed_hash = _compute_path_hash(path, is_directory=False)
        artifacts.append(_build_artifact_status(key, installed_hash, saved_files, current_version))

    # Check actions (always directory-based)
    for name in BUNDLED_ACTIONS:
        key = f"actions/{name}"
        path = project_actions_dir / name
        installed_hash = _compute_path_hash(path, is_directory=True)
        artifacts.append(_build_artifact_status(key, installed_hash, saved_files, current_version))

    # Check hooks
    settings_path = project_claude_dir / "settings.json"
    if settings_path.exists():
        content = settings_path.read_text(encoding="utf-8")
        settings = json.loads(content)

        hook_checks = [
            ("hooks/user-prompt-hook", has_user_prompt_hook, ERK_USER_PROMPT_HOOK_COMMAND),
            ("hooks/exit-plan-mode-hook", has_exit_plan_hook, ERK_EXIT_PLAN_HOOK_COMMAND),
        ]
        for key, check_fn, command in hook_checks:
            hook_hash = _compute_hook_hash(command) if check_fn(settings) else None
            artifacts.append(_build_artifact_status(key, hook_hash, saved_files, current_version))
    else:
        # No settings.json - all hooks are not installed
        for hook_name in ["user-prompt-hook", "exit-plan-mode-hook"]:
            artifacts.append(
                _build_artifact_status(f"hooks/{hook_name}", None, saved_files, current_version)
            )

    return ArtifactHealthResult(artifacts=artifacts, skipped_reason=None)


def _find_orphaned_in_directory(local_dir: Path, bundled_dir: Path, folder_key: str) -> list[str]:
    """Find orphaned files in a directory (files in local but not in bundled)."""
    if not local_dir.exists() or not bundled_dir.exists():
        return []

    bundled_files = {str(f.relative_to(bundled_dir)) for f in bundled_dir.rglob("*") if f.is_file()}
    orphans: list[str] = []
    for local_file in local_dir.rglob("*"):
        if local_file.is_file():
            relative_path = str(local_file.relative_to(local_dir))
            if relative_path not in bundled_files:
                orphans.append(relative_path)
    return orphans


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
    cmd_orphans = _find_orphaned_in_directory(
        project_claude_dir / "commands" / "erk",
        bundled_claude_dir / "commands" / "erk",
        "commands/erk",
    )
    if cmd_orphans:
        orphans["commands/erk"] = cmd_orphans

    # Check directory-based artifacts (skills, agents)
    for prefix, names in [("skills", BUNDLED_SKILLS), ("agents", BUNDLED_AGENTS)]:
        for name in names:
            folder_key = f"{prefix}/{name}"
            dir_orphans = _find_orphaned_in_directory(
                project_claude_dir / prefix / name,
                bundled_claude_dir / prefix / name,
                folder_key,
            )
            if dir_orphans:
                orphans[folder_key] = dir_orphans

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


def _find_missing_in_directory(bundled_dir: Path, local_dir: Path) -> list[str]:
    """Find missing files in a directory (files in bundled but not in local)."""
    if not bundled_dir.exists():
        return []

    local_dir.mkdir(parents=True, exist_ok=True)
    bundled_files = {str(f.relative_to(bundled_dir)) for f in bundled_dir.rglob("*") if f.is_file()}
    local_files = {str(f.relative_to(local_dir)) for f in local_dir.rglob("*") if f.is_file()}
    return sorted(bundled_files - local_files)


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
    cmd_missing = _find_missing_in_directory(
        bundled_claude_dir / "commands" / "erk",
        project_claude_dir / "commands" / "erk",
    )
    if cmd_missing:
        missing["commands/erk"] = cmd_missing

    # Check directory-based artifacts (skills, agents)
    for prefix, names in [("skills", BUNDLED_SKILLS), ("agents", BUNDLED_AGENTS)]:
        for name in names:
            folder_key = f"{prefix}/{name}"
            dir_missing = _find_missing_in_directory(
                bundled_claude_dir / prefix / name,
                project_claude_dir / prefix / name,
            )
            if dir_missing:
                missing[folder_key] = dir_missing

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


def _find_missing_actions(
    project_actions_dir: Path,
    bundled_actions_dir: Path,
) -> dict[str, list[str]]:
    """Find erk-managed actions that exist in bundle but missing locally.

    Args:
        project_actions_dir: Path to project's .github/actions/ directory
        bundled_actions_dir: Path to bundled .github/actions/ in erk package

    Returns:
        Dict mapping ".github/actions" to list of missing action names
    """
    if not bundled_actions_dir.exists():
        return {}

    missing: dict[str, list[str]] = {}

    for action_name in BUNDLED_ACTIONS:
        bundled_action = bundled_actions_dir / action_name
        local_action = project_actions_dir / action_name

        # If bundled but not local, it's missing
        if bundled_action.exists() and not local_action.exists():
            folder_key = ".github/actions"
            if folder_key not in missing:
                missing[folder_key] = []
            missing[folder_key].append(action_name)

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

    # Check workflows and actions
    bundled_github_dir = get_bundled_github_dir()
    project_workflows_dir = project_dir / ".github" / "workflows"
    bundled_workflows_dir = bundled_github_dir / "workflows"
    missing.update(_find_missing_workflows(project_workflows_dir, bundled_workflows_dir))

    project_actions_dir = project_dir / ".github" / "actions"
    bundled_actions_dir = bundled_github_dir / "actions"
    missing.update(_find_missing_actions(project_actions_dir, bundled_actions_dir))

    # Check hooks in settings.json
    missing.update(_find_missing_hooks(project_claude_dir))

    return CompletenessCheckResult(
        missing=missing,
        skipped_reason=None,
    )
