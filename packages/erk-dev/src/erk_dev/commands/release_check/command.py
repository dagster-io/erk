"""Validate CHANGELOG.md structure."""

import re
from dataclasses import dataclass
from pathlib import Path

import click

from erk_dev.commands.bump_version.command import find_repo_root

# Standard Keep a Changelog categories
STANDARD_CATEGORIES = frozenset({"Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"})


@dataclass
class ValidationIssue:
    """A validation issue found in CHANGELOG.md."""

    level: str  # "error" or "warning"
    message: str
    line: int | None = None


@dataclass
class VersionInfo:
    """Information about a version section in the changelog."""

    version: str
    date: str | None
    category_count: int
    bullet_count: int


def validate_changelog(content: str) -> list[ValidationIssue]:
    """Validate CHANGELOG.md content and return list of issues.

    Args:
        content: Raw content of CHANGELOG.md

    Returns:
        List of ValidationIssue objects (errors and warnings)
    """
    issues: list[ValidationIssue] = []
    lines = content.split("\n")

    # Check for Unreleased section
    if "## [Unreleased]" not in content:
        issues.append(ValidationIssue("error", "Missing [Unreleased] section"))

    # Track version headers and categories
    version_pattern = re.compile(r"^## \[([^\]]+)\](?:\s*-\s*(\d{4}-\d{2}-\d{2}))?$")
    category_pattern = re.compile(r"^### (.+)$")
    bullet_pattern = re.compile(r"^(\s*)- ")

    prev_indent_level = 0

    for line_num, line in enumerate(lines, start=1):
        # Check version headers
        version_match = version_pattern.match(line)
        if version_match:
            version = version_match.group(1)
            date = version_match.group(2)

            # Skip Unreleased - it doesn't need a date
            if version != "Unreleased":
                # Validate version format
                if not re.match(r"^\d+\.\d+\.\d+$", version):
                    issues.append(
                        ValidationIssue(
                            "error",
                            f"Invalid version format: {version} (expected X.Y.Z)",
                            line_num,
                        )
                    )
                # Validate date exists for versioned releases
                if date is None:
                    issues.append(
                        ValidationIssue(
                            "warning",
                            f"Version {version} missing date",
                            line_num,
                        )
                    )

        # Check category headers
        category_match = category_pattern.match(line)
        if category_match:
            category = category_match.group(1)
            if category not in STANDARD_CATEGORIES:
                issues.append(
                    ValidationIssue(
                        "warning",
                        f"Non-standard category: {category}",
                        line_num,
                    )
                )

        # Check bullet indentation
        bullet_match = bullet_pattern.match(line)
        if bullet_match:
            indent = len(bullet_match.group(1))
            indent_level = indent // 2

            # Check for odd indentation (not multiple of 2)
            if indent % 2 != 0:
                issues.append(
                    ValidationIssue(
                        "error",
                        f"Odd indentation ({indent} spaces) - use 2-space increments",
                        line_num,
                    )
                )
            # Check for indentation jumps (going from level 0 to level 2)
            elif indent_level > prev_indent_level + 1:
                issues.append(
                    ValidationIssue(
                        "error",
                        f"Indentation jumps from level {prev_indent_level} to {indent_level}",
                        line_num,
                    )
                )

            prev_indent_level = indent_level
        elif line.strip() and not line.startswith("#"):
            # Reset indent tracking on non-bullet, non-header lines
            prev_indent_level = 0

    return issues


def extract_version_info(content: str) -> list[VersionInfo]:
    """Extract information about each version section.

    Args:
        content: Raw content of CHANGELOG.md

    Returns:
        List of VersionInfo objects for each version section
    """
    versions: list[VersionInfo] = []

    # Match version headers
    version_pattern = re.compile(r"^## \[([^\]]+)\](?:\s*-\s*(\d{4}-\d{2}-\d{2}))?", re.MULTILINE)
    matches = list(version_pattern.finditer(content))

    for i, match in enumerate(matches):
        version = match.group(1)
        date = match.group(2)

        # Extract content between this header and the next
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        section_content = content[start:end]

        # Count categories and bullets
        category_count = len(re.findall(r"^### ", section_content, re.MULTILINE))
        bullet_count = len(re.findall(r"^\s*- ", section_content, re.MULTILINE))

        versions.append(
            VersionInfo(
                version=version,
                date=date,
                category_count=category_count,
                bullet_count=bullet_count,
            )
        )

    return versions


@click.command("release-check")
def release_check_command() -> None:
    """Validate CHANGELOG.md structure.

    Checks for:
    - [Unreleased] section exists
    - Version headers have valid format (X.Y.Z - YYYY-MM-DD)
    - Categories are standard (Added, Changed, Deprecated, Removed, Fixed, Security)
    - Bullet indentation uses 2-space increments without jumps

    Exit codes:
    - 0: All checks passed (warnings are OK)
    - 1: Errors found
    """
    repo_root = find_repo_root(Path.cwd())
    if repo_root is None:
        click.echo(click.style("Error: Could not find repository root", fg="red"))
        raise SystemExit(1)

    changelog_path = repo_root / "CHANGELOG.md"

    # Check file exists
    click.echo("Checking CHANGELOG.md...")

    if not changelog_path.exists():
        click.echo(click.style("  ✗ File not found", fg="red"))
        raise SystemExit(1)
    click.echo(click.style("  ✓ File exists", fg="green"))

    # Validate content
    content = changelog_path.read_text(encoding="utf-8")
    issues = validate_changelog(content)

    # Extract and display version info
    versions = extract_version_info(content)
    versioned_count = sum(1 for v in versions if v.version != "Unreleased")
    click.echo(click.style(f"  ✓ {versioned_count} version sections found", fg="green"))
    click.echo()

    # Display each version's details
    for info in versions:
        if info.version == "Unreleased":
            version_str = click.style("[Unreleased]", bold=True)
        else:
            version_str = click.style(f"[{info.version}]", bold=True)
            if info.date:
                version_str += f" - {info.date}"

        # Build details string
        details: list[str] = []
        if info.category_count > 0:
            details.append(f"{info.category_count} categories")
        details.append(f"{info.bullet_count} items")

        click.echo(f"    {version_str}: {', '.join(details)}")

    # Report issues
    errors = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level == "warning"]

    for issue in issues:
        if issue.level == "error":
            prefix = click.style("  ✗", fg="red")
        else:
            prefix = click.style("  ⚠", fg="yellow")

        location = f"Line {issue.line}: " if issue.line else ""
        click.echo(f"{prefix} {location}{issue.message}")

    # Summary
    click.echo()
    if errors:
        click.echo(
            click.style(
                f"Failed with {len(errors)} error(s) and {len(warnings)} warning(s)",
                fg="red",
            )
        )
        raise SystemExit(1)
    elif warnings:
        click.echo(click.style(f"Passed with {len(warnings)} warning(s)", fg="yellow"))
    else:
        click.echo(click.style("All checks passed", fg="green"))
