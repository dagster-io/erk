"""Check for legacy kit.yaml files.

This is a temporary check for early dogfooders. Delete this file once
all users have removed their kit.yaml files.
"""

from pathlib import Path

from erk.core.health_checks import CheckResult


def find_legacy_kit_yaml_files(repo_root: Path) -> list[Path]:
    """Find legacy kit.yaml files in the repository.

    Searches for kit.yaml files in:
    - .claude/**
    - .erk/kits/**

    Args:
        repo_root: Path to the repository root

    Returns:
        List of paths to kit.yaml files found
    """
    kit_yaml_files: list[Path] = []

    # Check .claude/ directory
    claude_dir = repo_root / ".claude"
    if claude_dir.exists():
        kit_yaml_files.extend(claude_dir.glob("**/kit.yaml"))

    # Check .erk/kits/ directory
    erk_kits_dir = repo_root / ".erk" / "kits"
    if erk_kits_dir.exists():
        kit_yaml_files.extend(erk_kits_dir.glob("**/kit.yaml"))

    return kit_yaml_files


def check_legacy_kit_yaml(repo_root: Path) -> CheckResult:
    """Check for legacy kit.yaml files.

    Detects kit.yaml files which are no longer used. Frontmatter-based
    discovery is now used instead of kit manifests.

    Args:
        repo_root: Path to the repository root

    Returns:
        CheckResult with warning if legacy kit.yaml files found
    """
    kit_yaml_files = find_legacy_kit_yaml_files(repo_root)

    if not kit_yaml_files:
        return CheckResult(
            name="legacy-kit-yaml",
            passed=True,
            message="No legacy kit.yaml files found",
        )

    # Build details with file list
    details_lines: list[str] = ["Legacy kit.yaml manifests found:"]
    for kit_yaml in kit_yaml_files[:5]:  # Limit display to first 5
        relative_path = kit_yaml.relative_to(repo_root)
        details_lines.append(f"  - {relative_path}")
    if len(kit_yaml_files) > 5:
        details_lines.append(f"  ... and {len(kit_yaml_files) - 5} more")
    details_lines.append("")
    details_lines.append("Kit manifests are no longer used (frontmatter discovery is now used).")
    details_lines.append("You can safely delete these files.")

    return CheckResult(
        name="legacy-kit-yaml",
        passed=True,  # Warning only, doesn't fail
        warning=True,
        message=f"Found {len(kit_yaml_files)} legacy kit.yaml file(s)",
        details="\n".join(details_lines),
    )
