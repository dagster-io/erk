"""Mechanical pre-scan for tripwire pattern matching.

Parses tripwire definition files, determines applicable categories from
changed files, runs Tier 1 regex patterns mechanically against the diff,
and outputs compact JSON with results for the review agent.

Usage:
    erk exec tripwire-scan --base origin/main

Output:
    JSON with Tier 1 match results and Tier 2 entries for LLM evaluation.

Exit Codes:
    0: Scan succeeded
    1: Scan failed (e.g., git errors)
"""

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import click

from erk_shared.context.helpers import require_repo_root
from erk_shared.subprocess_utils import copied_env_for_git_subprocess
from erk_shared.tripwire_scan_result import (
    Tier1MatchDict,
    Tier1ResultDict,
    Tier2EntryDict,
    TripwireScanErrorDict,
    TripwireScanSuccessDict,
)

# Regex to parse tripwire entries from markdown.
# Tier 1: **action** [pattern: `regex`] -> Read [Name](path) first. Summary
# Tier 2: **action** -> Read [Name](path) first. Summary
_ENTRY_RE = re.compile(
    r"\*\*(.+?)\*\*"  # action text
    r"(?:\s+\[pattern:\s+`(.+?)`\])?"  # optional Tier 1 pattern
    r"\s*→\s*Read\s+\[.+?\]\((.+?)\)\s+first\.\s*"  # doc path
    r"(.*)"  # summary (rest of line)
)

# Category-to-path-prefix mapping for determining which tripwire files to load.
CATEGORY_PATH_RULES: list[tuple[str, list[str]]] = [
    ("architecture", ["src/erk/gateway/", "packages/erk-shared/src/"]),
    ("cli", ["src/erk/cli/"]),
    ("testing", ["tests/"]),
    ("ci", [".github/"]),
    ("tui", ["src/erk/tui/"]),
    ("planning", [".impl/", ".erk/impl-context/"]),
    ("objectives", ["src/erk/cli/commands/exec/scripts/objective"]),
    ("hooks", [".claude/hooks/"]),
    ("commands", [".claude/commands/"]),
    ("desktop-dash", ["desktop-dash/"]),
]


@dataclass(frozen=True)
class TripwireEntry:
    """A parsed tripwire entry from a markdown file."""

    action: str
    pattern: str | None
    doc_path: str
    summary: str
    category: str


@dataclass(frozen=True)
class AddedLine:
    """A line added in the diff."""

    file: str
    line: int
    text: str


def _detect_base_branch(repo_root: Path) -> str:
    """Detect the trunk branch name via git."""
    env = copied_env_for_git_subprocess()
    for candidate in ["main", "master"]:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", f"origin/{candidate}"],
            capture_output=True,
            text=True,
            cwd=repo_root,
            env=env,
            check=False,
        )
        if result.returncode == 0:
            return f"origin/{candidate}"
    return "origin/main"


def _get_merge_base(repo_root: Path, base: str) -> str:
    """Get the merge-base between base and HEAD."""
    env = copied_env_for_git_subprocess()
    result = subprocess.run(
        ["git", "merge-base", base, "HEAD"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        msg = f"git merge-base failed: {result.stderr.strip()}"
        raise RuntimeError(msg)
    return result.stdout.strip()


def _get_changed_files(repo_root: Path, merge_base: str) -> list[str]:
    """Get list of changed files between merge-base and HEAD."""
    env = copied_env_for_git_subprocess()
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{merge_base}...HEAD"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        msg = f"git diff --name-only failed: {result.stderr.strip()}"
        raise RuntimeError(msg)
    return [f for f in result.stdout.strip().splitlines() if f]


def _get_diff_added_lines(repo_root: Path, merge_base: str) -> list[AddedLine]:
    """Parse unified diff to extract added lines with file/line info."""
    env = copied_env_for_git_subprocess()
    result = subprocess.run(
        ["git", "diff", "-U0", f"{merge_base}...HEAD"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        msg = f"git diff failed: {result.stderr.strip()}"
        raise RuntimeError(msg)
    return _parse_unified_diff(result.stdout)


def _parse_unified_diff(diff_text: str) -> list[AddedLine]:
    """Parse unified diff output into AddedLine entries.

    Only extracts lines starting with '+' (added lines), skipping
    the +++ header lines. Tracks current file and line number from
    @@ hunk headers.
    """
    added_lines: list[AddedLine] = []
    current_file: str | None = None
    current_line = 0

    for line in diff_text.splitlines():
        # Track current file from +++ header
        if line.startswith("+++ b/"):
            current_file = line[6:]
            continue

        # Skip --- header and other diff metadata
        if line.startswith("---") or line.startswith("diff "):
            continue

        # Parse @@ hunk header for line numbers
        if line.startswith("@@"):
            # Format: @@ -old,count +new,count @@
            match = re.search(r"\+(\d+)", line)
            if match:
                current_line = int(match.group(1))
            continue

        # Track added lines (skip +++ already handled above)
        if line.startswith("+") and current_file is not None:
            added_lines.append(
                AddedLine(
                    file=current_file,
                    line=current_line,
                    text=line[1:],  # Strip the leading '+'
                )
            )
            current_line += 1
            continue

        # Context lines and removed lines advance the new-file line counter
        # for context lines only (not removed lines which start with -)
        if not line.startswith("-"):
            current_line += 1

    return added_lines


def _match_categories(changed_files: list[str]) -> list[str]:
    """Map changed file paths to tripwire categories."""
    matched: set[str] = set()
    for category, prefixes in CATEGORY_PATH_RULES:
        for changed_file in changed_files:
            for prefix in prefixes:
                if changed_file.startswith(prefix):
                    matched.add(category)
                    break
    return sorted(matched)


def _parse_tripwire_file(path: Path, category: str) -> list[TripwireEntry]:
    """Parse a single tripwire markdown file and extract entries."""
    if not path.exists():
        return []

    content = path.read_text(encoding="utf-8")
    entries: list[TripwireEntry] = []

    for line in content.splitlines():
        match = _ENTRY_RE.match(line.strip())
        if match is None:
            continue
        action, pattern, doc_path, summary = match.groups()
        entries.append(
            TripwireEntry(
                action=action.strip(),
                pattern=pattern.strip() if pattern else None,
                doc_path=doc_path.strip(),
                summary=summary.strip(),
                category=category,
            )
        )

    return entries


def _scan_tier1(
    entries: list[TripwireEntry],
    added_lines: list[AddedLine],
) -> tuple[list[Tier1ResultDict], list[Tier1ResultDict]]:
    """Run Tier 1 regex patterns against added lines.

    Returns (matches, clean) where matches have hits and clean have none.
    """
    tier1_matches: list[Tier1ResultDict] = []
    tier1_clean: list[Tier1ResultDict] = []

    tier1_entries = [e for e in entries if e.pattern is not None]

    for entry in tier1_entries:
        assert entry.pattern is not None  # type narrowing
        try:
            compiled = re.compile(entry.pattern)
        except re.error:
            # Skip invalid regex patterns
            continue

        hits: list[Tier1MatchDict] = []
        for added_line in added_lines:
            if compiled.search(added_line.text):
                hits.append(
                    Tier1MatchDict(
                        file=added_line.file,
                        line=added_line.line,
                        text=added_line.text.strip(),
                    )
                )

        result = Tier1ResultDict(
            action=entry.action,
            pattern=entry.pattern,
            doc_path=entry.doc_path,
            matches=hits,
        )

        if hits:
            tier1_matches.append(result)
        else:
            tier1_clean.append(result)

    return tier1_matches, tier1_clean


def _collect_tier2(entries: list[TripwireEntry]) -> list[Tier2EntryDict]:
    """Collect Tier 2 entries (no pattern) for LLM evaluation."""
    return [
        Tier2EntryDict(
            category=entry.category,
            action=entry.action,
            doc_path=entry.doc_path,
            summary=entry.summary,
        )
        for entry in entries
        if entry.pattern is None
    ]


@click.command(name="tripwire-scan")
@click.option(
    "--base",
    default=None,
    help="Base ref for diff (default: auto-detect trunk)",
)
@click.pass_context
def tripwire_scan(ctx: click.Context, *, base: str | None) -> None:
    """Mechanical pre-scan of tripwire patterns against the current diff.

    Parses tripwire definition files, determines applicable categories,
    runs Tier 1 regex patterns mechanically, and outputs JSON with results.

    Examples:
        erk exec tripwire-scan
        erk exec tripwire-scan --base origin/main
    """
    repo_root = require_repo_root(ctx)

    # Detect base branch if not provided
    effective_base = base if base is not None else _detect_base_branch(repo_root)

    try:
        merge_base = _get_merge_base(repo_root, effective_base)
        changed_files = _get_changed_files(repo_root, merge_base)
        added_lines = _get_diff_added_lines(repo_root, merge_base)
    except RuntimeError as e:
        error_result: TripwireScanErrorDict = {
            "success": False,
            "error": "git_error",
            "message": str(e),
        }
        click.echo(json.dumps(error_result, indent=2))
        raise SystemExit(1) from None

    # Determine which categories apply
    categories = _match_categories(changed_files)

    # Parse tripwire files for matched categories
    docs_dir = repo_root / "docs" / "learned"
    all_entries: list[TripwireEntry] = []
    for category in categories:
        tripwire_path = docs_dir / category / "tripwires.md"
        all_entries.extend(_parse_tripwire_file(tripwire_path, category))

    # Run Tier 1 mechanical matching
    tier1_matches, tier1_clean = _scan_tier1(all_entries, added_lines)

    # Collect Tier 2 entries for LLM
    tier2_entries = _collect_tier2(all_entries)

    success_result: TripwireScanSuccessDict = {
        "success": True,
        "tier1_matches": tier1_matches,
        "tier1_clean": tier1_clean,
        "tier2_entries": tier2_entries,
        "categories_loaded": categories,
        "changed_files": changed_files,
    }
    click.echo(json.dumps(success_result, indent=2))
