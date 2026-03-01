"""Check status of erk-managed artifacts."""

from dataclasses import dataclass
from pathlib import Path

from erk.artifacts.artifact_health import (
    ArtifactHealthResult,
    ArtifactStatusType,
    get_artifact_health,
)
from erk.artifacts.models import ArtifactFileState
from erk.artifacts.paths import ErkPackageInfo
from erk.artifacts.state import load_artifact_state
from erk.core.health_checks.models import CheckResult


def _worst_status(statuses: list[ArtifactStatusType]) -> ArtifactStatusType:
    """Determine worst status from a list of statuses.

    Priority: not-installed > locally-modified > changed-upstream > up-to-date
    """
    if "not-installed" in statuses:
        return "not-installed"
    if "locally-modified" in statuses:
        return "locally-modified"
    if "changed-upstream" in statuses:
        return "changed-upstream"
    return "up-to-date"


def _extract_artifact_type(name: str) -> str:
    """Extract artifact type from artifact name.

    Examples:
        skills/dignified-python -> skills
        commands/erk/plan-implement.md -> commands
        agents/devrun -> agents
        workflows/erk-impl.yml -> workflows
        actions/setup-claude-erk -> actions
        hooks/user-prompt-hook -> hooks
    """
    return name.split("/")[0]


def _status_icon(status: ArtifactStatusType) -> str:
    """Get status icon for artifact status."""
    if status == "up-to-date":
        return "\u2705"
    if status == "locally-modified" or status == "changed-upstream":
        return "\u26a0\ufe0f"
    return "\u274c"


def _status_description(status: ArtifactStatusType, count: int) -> str:
    """Get human-readable status description."""
    if status == "not-installed":
        if count == 1:
            return "not installed"
        return f"{count} not installed"
    if status == "locally-modified":
        if count == 1:
            return "locally modified"
        return f"{count} locally modified"
    if status == "changed-upstream":
        if count == 1:
            return "changed upstream"
        return f"{count} changed upstream"
    return ""


def _build_erk_repo_artifacts_result(result: ArtifactHealthResult) -> CheckResult:
    """Build CheckResult for erk repo case (all artifacts from source)."""
    # Group artifacts by type, storing names
    by_type: dict[str, list[str]] = {}
    for artifact in result.artifacts:
        artifact_type = _extract_artifact_type(artifact.name)
        # Extract display name (e.g. "skills/dignified-python" -> "dignified-python")
        display_name = artifact.name.split("/", 1)[1] if "/" in artifact.name else artifact.name
        by_type.setdefault(artifact_type, []).append(display_name)

    # Build per-type summary (all checkmarks) and verbose details with individual names
    type_summaries: list[str] = []
    verbose_summaries: list[str] = []
    type_order = ["skills", "commands", "agents", "workflows", "actions", "hooks"]
    for artifact_type in type_order:
        if artifact_type not in by_type:
            continue
        names = sorted(by_type[artifact_type])
        type_summaries.append(f"   \u2705 {artifact_type} ({len(names)})")
        verbose_summaries.append(f"   \u2705 {artifact_type} ({len(names)})")
        for name in names:
            verbose_summaries.append(f"      {name}")

    details = "\n".join(type_summaries)
    verbose_details = "\n".join(verbose_summaries)

    return CheckResult(
        name="managed-artifacts",
        passed=True,
        message="Managed artifacts (from source)",
        details=details,
        verbose_details=verbose_details,
    )


@dataclass(frozen=True)
class _ArtifactInfo:
    """Internal: artifact name and status for grouping."""

    name: str
    status: ArtifactStatusType


def _build_managed_artifacts_result(result: ArtifactHealthResult) -> CheckResult:
    """Build CheckResult from ArtifactHealthResult."""
    # Group artifacts by type, storing name and status
    by_type: dict[str, list[_ArtifactInfo]] = {}
    for artifact in result.artifacts:
        artifact_type = _extract_artifact_type(artifact.name)
        # Extract display name (e.g. "skills/dignified-python" -> "dignified-python")
        display_name = artifact.name.split("/", 1)[1] if "/" in artifact.name else artifact.name
        by_type.setdefault(artifact_type, []).append(
            _ArtifactInfo(name=display_name, status=artifact.status)
        )

    # Build per-type summary and verbose details
    type_summaries: list[str] = []
    verbose_summaries: list[str] = []
    overall_worst: ArtifactStatusType = "up-to-date"
    has_issues = False

    # Determine if workflows are installed (actions are only required if workflows are installed)
    workflows_installed = "workflows" in by_type and any(
        a.status != "not-installed" for a in by_type.get("workflows", [])
    )

    # Consistent type ordering
    type_order = ["skills", "commands", "agents", "workflows", "actions", "hooks"]
    for artifact_type in type_order:
        if artifact_type not in by_type:
            continue

        artifacts = by_type[artifact_type]
        statuses: list[ArtifactStatusType] = [a.status for a in artifacts]
        count = len(statuses)
        worst = _worst_status(statuses)

        # Special case: actions not-installed is informational (not error) when workflows
        # aren't installed, since actions are only needed by workflows
        actions_optional = (
            artifact_type == "actions" and worst == "not-installed" and not workflows_installed
        )

        # Track overall worst for header (skip actions if optional)
        if not actions_optional:
            if overall_worst == "up-to-date":
                overall_worst = worst
            elif worst == "not-installed":
                overall_worst = "not-installed"
            elif worst in ("locally-modified", "changed-upstream") and overall_worst not in (
                "not-installed",
            ):
                overall_worst = worst

        # Use info icon for optional actions, otherwise status icon
        if actions_optional:
            icon = "\u2139\ufe0f"
        else:
            icon = _status_icon(worst)
        line = f"   {icon} {artifact_type} ({count})"

        # Add issue description if not up-to-date
        if worst != "up-to-date":
            # Only mark has_issues if this isn't an optional actions case
            if not actions_optional:
                has_issues = True
            issue_count = sum(1 for s in statuses if s == worst)
            desc = _status_description(worst, issue_count)
            # Add clarifying note for optional actions
            if actions_optional:
                line += f" - {desc} (install workflows first)"
            else:
                line += f" - {desc}"

        type_summaries.append(line)
        verbose_summaries.append(line)

        # Add individual artifact names to verbose output
        for artifact_info in sorted(artifacts, key=lambda a: a.name):
            if artifact_info.status == "up-to-date":
                status_indicator = ""
            else:
                status_indicator = f" ({artifact_info.status})"
            verbose_summaries.append(f"      {artifact_info.name}{status_indicator}")

    details = "\n".join(type_summaries)

    # Add status explanations when issues exist
    statuses_present = {a.status for artifacts_list in by_type.values() for a in artifacts_list}
    status_explanations: list[str] = []
    if "changed-upstream" in statuses_present:
        status_explanations.append(
            "   (changed-upstream): erk has newer versions of these artifacts"
        )
    if "locally-modified" in statuses_present:
        status_explanations.append("   (locally-modified): these artifacts were edited locally")
    if "not-installed" in statuses_present:
        status_explanations.append(
            "   (not-installed): these artifacts are missing from the project"
        )

    if status_explanations:
        verbose_summaries.append("")  # blank line
        verbose_summaries.extend(status_explanations)

    verbose_details = "\n".join(verbose_summaries)

    # Determine remediation
    remediation: str | None = None
    if overall_worst == "not-installed":
        remediation = "Run 'erk artifact sync' to restore missing artifacts"
    elif overall_worst == "changed-upstream":
        remediation = "Run 'erk artifact sync' to update to latest erk version"
    elif overall_worst == "locally-modified":
        remediation = "Run 'erk artifact sync --force' to restore erk defaults"

    # Determine overall result
    if overall_worst == "not-installed":
        return CheckResult(
            name="managed-artifacts",
            passed=False,
            message="Managed artifacts have issues",
            details=details,
            verbose_details=verbose_details,
            remediation=remediation,
        )
    elif has_issues:
        return CheckResult(
            name="managed-artifacts",
            passed=True,
            warning=True,
            message="Managed artifacts have issues",
            details=details,
            verbose_details=verbose_details,
            remediation=remediation,
        )
    else:
        return CheckResult(
            name="managed-artifacts",
            passed=True,
            message="Managed artifacts healthy",
            details=details,
            verbose_details=verbose_details,
        )


def check_managed_artifacts(
    repo_root: Path,
    *,
    package: ErkPackageInfo,
    installed_capabilities: frozenset[str] | None,
) -> CheckResult:
    """Check status of erk-managed artifacts.

    Shows a summary of artifact status by type (skills, commands, agents, etc.)
    with per-type counts and status indicators.

    Args:
        repo_root: Path to the repository root
        package: Package info for the repository
        installed_capabilities: Installed capabilities for filtering, or None for erk repo

    Returns:
        CheckResult with artifact health status
    """
    # Check for .claude/ directory
    claude_dir = repo_root / ".claude"
    if not claude_dir.exists():
        return CheckResult(
            name="managed-artifacts",
            passed=True,
            message="No .claude/ directory (nothing to check)",
        )

    # Load saved artifact state
    state = load_artifact_state(repo_root)
    saved_files: dict[str, ArtifactFileState] = dict(state.files) if state else {}

    # Get artifact health
    result = get_artifact_health(
        repo_root,
        saved_files,
        installed_capabilities=installed_capabilities,
        package=package,
    )

    # Handle skipped cases from get_artifact_health
    if result.skipped_reason == "no-claude-dir":
        return CheckResult(
            name="managed-artifacts",
            passed=True,
            message="No .claude/ directory (nothing to check)",
        )

    if result.skipped_reason == "no-bundled-dir":
        return CheckResult(
            name="managed-artifacts",
            passed=True,
            message="Bundled .claude/ not found (skipping check)",
        )

    # No artifacts to check
    if not result.artifacts:
        return CheckResult(
            name="managed-artifacts",
            passed=True,
            message="No managed artifacts found",
        )

    # In erk repo, show counts without status comparison (all from source)
    if package.in_erk_repo:
        return _build_erk_repo_artifacts_result(result)

    return _build_managed_artifacts_result(result)
