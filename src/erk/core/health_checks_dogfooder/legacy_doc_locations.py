"""Check for legacy documentation locations that should be migrated.

This is a temporary check for early dogfooders. Delete this file once
all users have migrated their docs to .erk/docs/agent/ and .erk/docs/kits/.
"""

from dataclasses import dataclass
from pathlib import Path

from erk.core.health_checks import CheckResult
from erk.kits.io.state import load_project_config


@dataclass(frozen=True)
class LegacyDocLocation:
    """Information about a legacy documentation location."""

    path: Path
    description: str
    new_location: str


def detect_legacy_doc_locations(repo_root: Path) -> list[LegacyDocLocation]:
    """Detect legacy documentation directories at old locations.

    Checks for:
    - docs/agent/ (should be at .erk/docs/agent/)
    - .claude/docs/<kit>/ directories that match installed kit names
      (should be at .erk/docs/kits/<kit>/)

    Only flags directories in .claude/docs/ that match installed kit IDs from
    kits.toml. Non-kit directories (e.g., manually maintained docs) are ignored.

    Args:
        repo_root: Path to the repository root

    Returns:
        List of LegacyDocLocation objects for any legacy docs found
    """
    legacy_locations: list[LegacyDocLocation] = []

    # Check for docs/agent/ (legacy location)
    legacy_agent_docs = repo_root / "docs" / "agent"
    if legacy_agent_docs.exists() and legacy_agent_docs.is_dir():
        legacy_locations.append(
            LegacyDocLocation(
                path=legacy_agent_docs,
                description="agent docs at legacy location",
                new_location=".erk/docs/agent/",
            )
        )

    # Get installed kit IDs from kits.toml
    config = load_project_config(repo_root)
    installed_kit_ids: set[str] = set()
    if config is not None:
        installed_kit_ids = set(config.kits.keys())

    # Check for .claude/docs/<kit>/ directories (legacy kit docs location)
    # Only flag directories that match installed kit names
    claude_docs_dir = repo_root / ".claude" / "docs"
    if claude_docs_dir.exists() and claude_docs_dir.is_dir():
        for kit_dir in claude_docs_dir.iterdir():
            if kit_dir.is_dir() and kit_dir.name in installed_kit_ids:
                legacy_locations.append(
                    LegacyDocLocation(
                        path=kit_dir,
                        description=f"kit docs for '{kit_dir.name}' at legacy location",
                        new_location=f".erk/docs/kits/{kit_dir.name}/",
                    )
                )

    return legacy_locations


def check_legacy_doc_locations(repo_root: Path) -> CheckResult:
    """Check for legacy documentation locations that should be migrated.

    Detects documentation at old locations that should be moved to .erk/docs/.
    This is a warning-level check for early dogfooders.

    Args:
        repo_root: Path to the repository root

    Returns:
        CheckResult with warning if legacy docs found
    """
    # Detect any legacy docs
    legacy_locations = detect_legacy_doc_locations(repo_root)

    if not legacy_locations:
        return CheckResult(
            name="legacy docs",
            passed=True,
            message="No legacy documentation locations found",
        )

    # Build details with migration instructions
    details_lines: list[str] = ["Legacy documentation locations found:"]
    for loc in legacy_locations:
        details_lines.append(f"  - {loc.path} ({loc.description})")
        details_lines.append(f"    → Move to: {loc.new_location}")
    details_lines.append("")
    details_lines.append("Run 'erk kit install <kit-id> --force' after moving files.")

    return CheckResult(
        name="legacy docs",
        passed=True,  # Warning only - doesn't fail the check
        warning=True,
        message=f"Found {len(legacy_locations)} legacy doc location(s)",
        details="\n".join(details_lines),
    )
