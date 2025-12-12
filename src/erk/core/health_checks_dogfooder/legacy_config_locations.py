"""Check for legacy config.toml files that should be migrated.

This is a temporary check for early dogfooders. Delete this file once
all users have migrated their config to .erk/config.toml.
"""

from dataclasses import dataclass
from pathlib import Path

from erk.core.health_checks import CheckResult


@dataclass(frozen=True)
class LegacyConfigLocation:
    """Information about a legacy config.toml location."""

    path: Path
    description: str


def detect_legacy_config_locations(
    repo_root: Path,
    metadata_dir: Path | None,
) -> list[LegacyConfigLocation]:
    """Detect legacy config.toml files at old locations.

    Checks for config files at:
    - repo_root/config.toml (legacy location)
    - metadata_dir/config.toml (legacy location)

    Args:
        repo_root: Path to the repository root
        metadata_dir: Path to ~/.erk/repos/<repo>/ metadata directory, if known

    Returns:
        List of LegacyConfigLocation objects for any legacy configs found
    """
    legacy_locations: list[LegacyConfigLocation] = []

    # Check for config at repo root (legacy location)
    repo_root_config = repo_root / "config.toml"
    if repo_root_config.exists():
        legacy_locations.append(
            LegacyConfigLocation(
                path=repo_root_config,
                description="repo root (legacy location)",
            )
        )

    # Check for config in ~/.erk/repos/<repo>/ (legacy location)
    if metadata_dir is not None:
        metadata_dir_config = metadata_dir / "config.toml"
        if metadata_dir_config.exists():
            legacy_locations.append(
                LegacyConfigLocation(
                    path=metadata_dir_config,
                    description="~/.erk/repos/ metadata dir (legacy location)",
                )
            )

    return legacy_locations


def check_legacy_config_locations(
    repo_root: Path,
    metadata_dir: Path | None,
) -> CheckResult:
    """Check for legacy config.toml files that should be migrated.

    Detects config files at old locations (repo root, metadata dir) that should
    be moved to .erk/config.toml. This is a warning-level check for early dogfooders.

    Args:
        repo_root: Path to the repository root
        metadata_dir: Path to ~/.erk/repos/<repo>/ metadata directory, if known

    Returns:
        CheckResult with warning if legacy configs found
    """
    # Skip if primary location exists (config already migrated)
    primary_path = repo_root / ".erk" / "config.toml"
    if primary_path.exists():
        return CheckResult(
            name="legacy config",
            passed=True,
            message="Config at primary location (.erk/config.toml)",
        )

    # Detect any legacy configs
    legacy_locations = detect_legacy_config_locations(repo_root, metadata_dir)

    if not legacy_locations:
        return CheckResult(
            name="legacy config",
            passed=True,
            message="No legacy config files found",
        )

    # Build details with migration instructions
    details_lines: list[str] = ["Legacy config files found:"]
    for loc in legacy_locations:
        details_lines.append(f"  - {loc.path} ({loc.description})")
    details_lines.append("")
    details_lines.append(f"Move to: {primary_path}")

    return CheckResult(
        name="legacy config",
        passed=True,  # Warning only - doesn't fail the check
        warning=True,
        message=f"Found {len(legacy_locations)} legacy config file(s)",
        details="\n".join(details_lines),
    )
