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
from erk.artifacts.paths import get_bundled_claude_dir, get_bundled_github_dir
from erk.core.capabilities.registry import (
    get_capability,
    get_managed_artifacts,
    is_capability_managed,
)
from erk.core.claude_settings import (
    ERK_EXIT_PLAN_HOOK_COMMAND,
    ERK_USER_PROMPT_HOOK_COMMAND,
    has_exit_plan_hook,
    has_user_prompt_hook,
)
from erk.core.release_notes import get_current_version


def _get_bundled_by_type(
    artifact_type: str,
    *,
    installed_capabilities: frozenset[str] | None,
) -> frozenset[str]:
    """Get all artifact names of a given type that should be checked.

    Filtering logic:
    - If installed_capabilities is None: return all managed artifacts (erk repo case)
    - Otherwise: return only artifacts from required capabilities OR from
      explicitly installed capabilities

    Args:
        artifact_type: The artifact type (e.g., "skill", "hook", "workflow")
        installed_capabilities: Set of capability names installed in the repo,
            or None to skip filtering (check all)

    Returns:
        Frozenset of artifact names to check
    """
    managed = get_managed_artifacts()
    result: set[str] = set()

    for (name, atype), capability_name in managed.items():
        if atype != artifact_type:
            continue

        # No filtering - include all (erk repo case)
        if installed_capabilities is None:
            result.add(name)
            continue

        # Check if capability is required or installed
        capability = get_capability(capability_name)
        if capability is None:
            continue

        if capability.required:
            # Required capabilities are always checked
            result.add(name)
        elif capability_name in installed_capabilities:
            # Explicitly installed capabilities are checked
            result.add(name)

    return frozenset(result)


def is_erk_managed(artifact: InstalledArtifact) -> bool:
    """Check if artifact is managed by erk (bundled with erk package).

    Args:
        artifact: The artifact to check

    Returns:
        True if the artifact is bundled with erk, False if it's project-specific
    """
    # Commands use prefix matching (not capability-declared)
    if artifact.artifact_type == "command":
        return artifact.name.startswith("erk:")

    # All other artifacts: query capabilities as the single source of truth
    return is_capability_managed(artifact.name, artifact.artifact_type)


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
    project_dir: Path,
    saved_files: dict[str, ArtifactFileState],
    *,
    installed_capabilities: frozenset[str] | None,
) -> ArtifactHealthResult:
    """Get per-artifact health status comparing installed vs bundled state.

    Args:
        project_dir: Path to the project root
        saved_files: Per-artifact state from .erk/state.toml (artifact key -> ArtifactFileState)
        installed_capabilities: Set of capability names installed in the repo,
            or None to skip filtering and check all artifacts (erk repo case)

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
    for name in _get_bundled_by_type("skill", installed_capabilities=installed_capabilities):
        key = f"skills/{name}"
        path = project_claude_dir / "skills" / name
        installed_hash = _compute_path_hash(path, is_directory=True)
        artifacts.append(_build_artifact_status(key, installed_hash, saved_files, current_version))

    # Check agents (can be directory-based or single-file)
    # Key format depends on structure:
    #   - Directory: agents/{name} (like skills)
    #   - Single-file: agents/{name}.md (like commands)
    for name in _get_bundled_by_type("agent", installed_capabilities=installed_capabilities):
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
    for name in _get_bundled_by_type("workflow", installed_capabilities=installed_capabilities):
        workflow_name = f"{name}.yml"
        key = f"workflows/{workflow_name}"
        path = project_workflows_dir / workflow_name
        installed_hash = _compute_path_hash(path, is_directory=False)
        artifacts.append(_build_artifact_status(key, installed_hash, saved_files, current_version))

    # Check actions (always directory-based)
    for name in _get_bundled_by_type("action", installed_capabilities=installed_capabilities):
        key = f"actions/{name}"
        path = project_actions_dir / name
        installed_hash = _compute_path_hash(path, is_directory=True)
        artifacts.append(_build_artifact_status(key, installed_hash, saved_files, current_version))

    # Check reviews (always file-based, in .claude/reviews/)
    for name in _get_bundled_by_type("review", installed_capabilities=installed_capabilities):
        key = f"reviews/{name}.md"
        path = project_claude_dir / "reviews" / f"{name}.md"
        installed_hash = _compute_path_hash(path, is_directory=False)
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
    # Note: use installed_capabilities=None to check ALL managed artifacts
    # because we want to detect orphans even for capabilities that were removed
    for prefix, artifact_type in [("skills", "skill"), ("agents", "agent")]:
        for name in _get_bundled_by_type(artifact_type, installed_capabilities=None):
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

    Only checks files that are capability-managed workflows - we don't want to flag
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
    # Note: use installed_capabilities=None to check ALL managed workflows
    for name in _get_bundled_by_type("workflow", installed_capabilities=None):
        workflow_name = f"{name}.yml"
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
    # Note: use installed_capabilities=None to check ALL managed artifacts
    for prefix, artifact_type in [("skills", "skill"), ("agents", "agent")]:
        for name in _get_bundled_by_type(artifact_type, installed_capabilities=None):
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

    # Note: use installed_capabilities=None to check ALL managed workflows
    for name in _get_bundled_by_type("workflow", installed_capabilities=None):
        workflow_name = f"{name}.yml"
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

    # Note: use installed_capabilities=None to check ALL managed actions
    for action_name in _get_bundled_by_type("action", installed_capabilities=None):
        bundled_action = bundled_actions_dir / action_name
        local_action = project_actions_dir / action_name

        # If bundled but not local, it's missing
        if bundled_action.exists() and not local_action.exists():
            folder_key = ".github/actions"
            if folder_key not in missing:
                missing[folder_key] = []
            missing[folder_key].append(action_name)

    return missing


def _find_missing_reviews(
    project_reviews_dir: Path,
    bundled_reviews_dir: Path,
) -> dict[str, list[str]]:
    """Find erk-managed reviews that exist in bundle but missing locally.

    Args:
        project_reviews_dir: Path to project's .claude/reviews/ directory
        bundled_reviews_dir: Path to bundled .github/reviews/ in erk package

    Returns:
        Dict mapping ".claude/reviews" to list of missing review filenames
    """
    if not bundled_reviews_dir.exists():
        return {}

    missing: dict[str, list[str]] = {}

    # Note: use installed_capabilities=None to check ALL managed reviews
    for review_name in _get_bundled_by_type("review", installed_capabilities=None):
        review_filename = f"{review_name}.md"
        bundled_review = bundled_reviews_dir / review_filename
        local_review = project_reviews_dir / review_filename

        # If bundled but not local, it's missing
        if bundled_review.exists() and not local_review.exists():
            folder_key = ".claude/reviews"
            if folder_key not in missing:
                missing[folder_key] = []
            missing[folder_key].append(review_filename)

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
    # Note: hooks are always required, so installed_capabilities=None is fine
    bundled_hooks = _get_bundled_by_type("hook", installed_capabilities=None)

    # If no settings.json, all hooks are missing
    if not settings_path.exists():
        return {"settings.json": sorted(bundled_hooks)}

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

    # Check reviews (in .claude/reviews/, bundled from .github/reviews/)
    project_reviews_dir = project_claude_dir / "reviews"
    bundled_reviews_dir = bundled_github_dir / "reviews"
    missing.update(_find_missing_reviews(project_reviews_dir, bundled_reviews_dir))

    # Check hooks in settings.json
    missing.update(_find_missing_hooks(project_claude_dir))

    return CompletenessCheckResult(
        missing=missing,
        skipped_reason=None,
    )
