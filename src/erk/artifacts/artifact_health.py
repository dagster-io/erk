"""Orphaned artifact detection for erk-managed .claude/ directories."""

import json
from pathlib import Path

from erk.artifacts.detection import is_in_erk_repo
from erk.artifacts.models import CompletenessCheckResult, OrphanCheckResult
from erk.artifacts.sync import get_bundled_claude_dir, get_bundled_github_dir
from erk.core.claude_settings import has_exit_plan_hook, has_user_prompt_hook

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
