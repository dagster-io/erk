"""Check AGENTS.md standard compliance command.

This command validates that repositories follow the AGENTS.md standard where:
- AGENTS.md is the primary context file
- CLAUDE.md contains '@AGENTS.md' reference for backwards compatibility
- (Optional) All @ file references point to existing files with valid fragments

See: https://code.claude.com/docs/en/claude-code-on-the-web
"""

import fnmatch
import subprocess
from pathlib import Path

import click

from erk.kits.cli.output import user_output
from erk.kits.io.link_validation import BrokenLink, validate_links_in_file

# Default exclusion patterns - always excluded unless explicitly included
DEFAULT_EXCLUSIONS = [
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
]


def _matches_exclusion(file_path: Path, repo_root: Path, exclusions: list[str]) -> bool:
    """Check if a file matches any exclusion pattern.

    Patterns can be:
    - Simple directory names (e.g., "node_modules") - matches anywhere in path
    - Glob patterns (e.g., "packages/*/src/*/data/kits") - matches from repo root

    Args:
        file_path: Absolute path to the file
        repo_root: Repository root path
        exclusions: List of exclusion patterns

    Returns:
        True if file should be excluded
    """
    rel_path = file_path.relative_to(repo_root)
    rel_path_str = str(rel_path)

    for pattern in exclusions:
        # If pattern contains path separators or wildcards, treat as glob from repo root
        if "/" in pattern or "*" in pattern:
            if fnmatch.fnmatch(rel_path_str, pattern):
                return True
            # Also check if it matches as a prefix (for directory patterns)
            if fnmatch.fnmatch(rel_path_str, f"{pattern}/*"):
                return True
            if fnmatch.fnmatch(rel_path_str, f"{pattern}/**"):
                return True
        else:
            # Simple name - check if it appears as a path component
            if pattern in rel_path.parts:
                return True

    return False


def _discover_markdown_files(repo_root: Path, exclusions: list[str] | None = None) -> list[Path]:
    """Discover all markdown files to check for @ references.

    Discovers all .md files in the repository, excluding:
    - Files matching patterns in the exclusions list
    - Files in default excluded directories (.git, node_modules, etc.)

    Args:
        repo_root: Repository root path
        exclusions: Additional exclusion patterns (glob-style)

    Returns:
        List of unique markdown file paths to check
    """
    all_exclusions = DEFAULT_EXCLUSIONS.copy()
    if exclusions:
        all_exclusions.extend(exclusions)

    files: list[Path] = []

    for md_file in repo_root.rglob("*.md"):
        if not _matches_exclusion(md_file, repo_root, all_exclusions):
            files.append(md_file)

    return sorted(files)


@click.command(name="check")
@click.option(
    "--check-links",
    is_flag=True,
    default=False,
    help="Also validate that @ file references point to existing files.",
)
@click.option(
    "--exclude",
    multiple=True,
    help="Exclude files matching pattern (can be specified multiple times). "
    "Patterns can be directory names (e.g., 'vendor') or glob patterns "
    "(e.g., 'packages/*/src/*/data/kits').",
)
def check_command(*, check_links: bool, exclude: tuple[str, ...]) -> None:
    """Validate AGENTS.md standard compliance in the repository.

    Checks that:
    - Every CLAUDE.md file has a peer AGENTS.md file
    - Every CLAUDE.md file contains '@AGENTS.md' reference

    With --check-links:
    - All @ file references in markdown files point to existing files
    - All # fragment anchors reference valid headings

    Default exclusions (always applied):
    .git, node_modules, __pycache__, .venv, venv, .tox, .mypy_cache,
    .pytest_cache, .ruff_cache

    Exit codes:
    - 0: All checks passed
    - 1: Violations found
    """
    # Find repository root
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    repo_root_str = result.stdout.strip()
    repo_root_path = Path(repo_root_str)

    if not repo_root_path.exists():
        user_output(click.style("✗ Error: Repository root not found", fg="red"))
        raise SystemExit(1)

    # Find all CLAUDE.md files
    claude_files = list(repo_root_path.rglob("CLAUDE.md"))

    if len(claude_files) == 0:
        user_output(click.style("ℹ️  No CLAUDE.md files found in repository", fg="cyan"))
        raise SystemExit(0)

    # Track violations
    missing_agents: list[Path] = []
    invalid_content: list[Path] = []
    broken_links: list[BrokenLink] = []

    for claude_path in claude_files:
        # Check for peer AGENTS.md
        agents_path = claude_path.parent / "AGENTS.md"
        if not agents_path.exists():
            missing_agents.append(claude_path.parent)
            continue

        # Check CLAUDE.md content
        content = claude_path.read_text(encoding="utf-8")
        if content.strip() != "@AGENTS.md":
            invalid_content.append(claude_path)

    # Optionally validate @ references
    all_md_files: list[Path] = []
    if check_links:
        exclusions = list(exclude) if exclude else None
        all_md_files = _discover_markdown_files(repo_root_path, exclusions)
        for md_file in all_md_files:
            broken_links.extend(validate_links_in_file(md_file, repo_root_path))

    # Report results
    violation_count = len(missing_agents) + len(invalid_content) + len(broken_links)
    if violation_count == 0:
        user_output(click.style("✓ AGENTS.md standard: PASSED", fg="green", bold=True))
        user_output()
        user_output("All CLAUDE.md files properly reference AGENTS.md.")
        if check_links:
            user_output("All @ references are valid.")
        user_output()
        user_output(f"CLAUDE.md files checked: {len(claude_files)}")
        if check_links:
            user_output(f"Markdown files checked for @ references: {len(all_md_files)}")
        user_output("Violations: 0")
        raise SystemExit(0)

    # Found violations
    user_output(click.style("✗ AGENTS.md standard: FAILED", fg="red", bold=True))
    user_output()
    plural = "s" if violation_count != 1 else ""
    user_output(f"Found {violation_count} violation{plural}:")
    user_output()

    if len(missing_agents) > 0:
        user_output(click.style("Missing AGENTS.md:", fg="yellow"))
        for path in missing_agents:
            rel_path = path.relative_to(repo_root_path)
            user_output(f"  • {click.style(str(rel_path) + '/', fg='cyan')}")
        user_output()

    if len(invalid_content) > 0:
        user_output(click.style("Invalid CLAUDE.md content:", fg="yellow"))
        for path in invalid_content:
            rel_path = path.relative_to(repo_root_path)
            content = path.read_text(encoding="utf-8")
            styled_path = click.style(str(rel_path), fg="cyan")
            user_output(f"  • {styled_path}: Content is '{content.strip()}', expected '@AGENTS.md'")
        user_output()

    if len(broken_links) > 0:
        user_output(click.style("Broken @ references:", fg="yellow"))
        for broken in broken_links:
            source_rel = broken.source_file.relative_to(repo_root_path)
            styled_source = click.style(f"{source_rel}:{broken.reference.line_number}", fg="cyan")
            if broken.error_type == "missing_file":
                user_output(f"  • {styled_source}: File not found: {broken.reference.raw_text}")
            elif broken.error_type == "missing_fragment":
                user_output(f"  • {styled_source}: Fragment not found: #{broken.error_detail}")
        user_output()

    user_output("Fix these issues and run again.")
    raise SystemExit(1)
