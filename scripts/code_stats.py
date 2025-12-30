#!/usr/bin/env python3
"""Analyze merged PRs by category with net lines of code statistics."""

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass
class DiffIndicators:
    cli_command: bool = False
    slash_command: bool = False
    skill: bool = False
    hook: bool = False
    docs_only: bool = False
    internal_api: bool = False
    test_only: bool = False
    config_migration: bool = False
    bug_fix: bool = False


@dataclass
class DiffStats:
    py_add: int = 0
    py_del: int = 0
    py_test_add: int = 0
    py_test_del: int = 0
    md_add: int = 0
    md_del: int = 0

    @property
    def py_net(self) -> int:
        return self.py_add - self.py_del

    @property
    def py_test_net(self) -> int:
        return self.py_test_add - self.py_test_del

    @property
    def md_net(self) -> int:
        return self.md_add - self.md_del

    @property
    def total_net(self) -> int:
        return self.py_net + self.py_test_net + self.md_net


@dataclass
class CategoryStats:
    prs: list
    py: int = 0
    py_test: int = 0
    md: int = 0

    @property
    def total(self) -> int:
        return self.py + self.py_test + self.md


def analyze_diff(sha: str) -> tuple[DiffIndicators, list[str]]:
    """Analyze diff content to determine category indicators."""
    diff_result = subprocess.run(
        ["git", "diff", f"{sha}^..{sha}", "--name-only"],
        capture_output=True,
        text=True,
    )
    files = diff_result.stdout.strip().split("\n") if diff_result.stdout.strip() else []

    full_diff_result = subprocess.run(
        ["git", "diff", f"{sha}^..{sha}"],
        capture_output=True,
        text=True,
    )
    full_diff = full_diff_result.stdout

    indicators = DiffIndicators()

    py_files = [f for f in files if f.endswith(".py") and "test" not in f.lower()]
    test_files = [f for f in files if f.endswith(".py") and "test" in f.lower()]
    md_files = [f for f in files if f.endswith(".md")]

    if md_files and not py_files:
        indicators.docs_only = True
    if test_files and not py_files:
        indicators.test_only = True

    cli_patterns = [r"@app\.command\(", r"@.*\.command\("]
    if any(re.search(p, full_diff) for p in cli_patterns):
        if "+@app.command" in full_diff:
            indicators.cli_command = True

    if any(".claude/commands/" in f for f in files):
        indicators.slash_command = True

    files_joined = " ".join(files)
    for f in files:
        if "skill" in f.lower() and f.endswith(".md"):
            if ".claude/" in files_joined or ".agent/" in files_joined:
                indicators.skill = True
                break

    for f in files:
        if "hook" in f.lower():
            if "settings.json" in files_joined or ".claude/" in files_joined:
                indicators.hook = True
                break

    internal_patterns = ["abc.py", "gateway", "interface", "_internal", "fake.py", "dry_run.py"]
    if any(any(p in f for p in internal_patterns) for f in py_files):
        indicators.internal_api = True

    migration_patterns = ["migrate", ".erk/", ".agent/", "rename", "DOT_AGENT", "ERK_"]
    if any(p.lower() in full_diff.lower() for p in migration_patterns):
        indicators.config_migration = True

    bug_patterns = [r"\bfix\b", r"\bbug\b"]
    if any(re.search(p, full_diff, re.I) for p in bug_patterns):
        indicators.bug_fix = True

    return indicators, files


def get_diff_stats(sha: str) -> DiffStats:
    """Get line count statistics for a commit."""
    diff_result = subprocess.run(
        ["git", "diff", "--numstat", f"{sha}^..{sha}", "--", "*.py", "*.md"],
        capture_output=True,
        text=True,
    )

    stats = DiffStats()

    for line in diff_result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) != 3 or parts[0] == "-":
            continue

        add, delete, path = int(parts[0]), int(parts[1]), parts[2]

        if path.endswith(".md"):
            stats.md_add += add
            stats.md_del += delete
        elif "test" in path or "/tests/" in path:
            stats.py_test_add += add
            stats.py_test_del += delete
        else:
            stats.py_add += add
            stats.py_del += delete

    return stats


def categorize_by_content(title: str, indicators: DiffIndicators) -> str:
    """Categorize PR based on diff content analysis."""
    t = title.lower()

    # User-facing features
    if indicators.slash_command:
        return "user_feature"
    if indicators.cli_command and not indicators.internal_api:
        if any(x in t for x in ["erk ", "stack", "pr ", "plan", "worktree"]):
            return "user_feature"
    if indicators.skill:
        return "user_feature"

    # Bug fixes
    words = t.split()
    if words and "fix" in words[0]:
        return "bug_fix"
    if indicators.bug_fix and "fix" in t:
        return "bug_fix"

    # Documentation only
    if indicators.docs_only:
        return "docs"

    # Migrations
    if indicators.config_migration:
        if any(x in t for x in ["migrate", "rename", "move", "replace", "update terminology"]):
            return "migration"

    # Internal API changes
    if indicators.internal_api:
        return "internal"

    # Refactoring
    refactor_keywords = [
        "refactor",
        "consolidate",
        "reorganize",
        "simplify",
        "clean",
        "eliminate",
        "standardize",
        "canonicalize",
        "unify",
        "deprecate",
        "delete",
        "remove",
        "reduce",
        "push down",
    ]
    if any(x in t for x in refactor_keywords):
        return "refactor"

    # Internal additions
    if t.startswith("add "):
        internal_indicators = [
            "abstraction",
            "method",
            "interface",
            "abc",
            "gateway",
            "pattern",
            "erkcontext",
            "github",
            "session",
        ]
        if any(x in t for x in internal_indicators):
            return "internal"

    # Improvements
    if any(x in t for x in ["improve", "enhance", "extend", "optimize"]):
        if any(x in t for x in ["command", "workflow", "pr ", "stack"]):
            return "user_improvement"
        return "internal"

    # User-facing commands
    user_facing_keywords = ["command", "slash", "/erk:", "workflow", "hook"]
    if any(x in t for x in user_facing_keywords):
        if any(x in t for x in ["add", "create", "implement"]):
            return "user_feature"

    # Default internal for "add" or "implement"
    if t.startswith("add ") or "implement" in t:
        return "internal"

    return "other"


def fmt_num(n: int) -> str:
    """Format number with sign and thousands separator."""
    if n >= 0:
        return f"+{n:,}"
    return f"{n:,}"


# Category display data: (display_text, key, emoji)
# All emojis must have:
#   - String length 1 (single codepoint, no variation selectors)
#   - East Asian Width 'W' (Wide) for display width 2
CATEGORY_DATA = [
    ("User-Facing Features", "user_feature", "🚀"),
    ("User-Facing Improvements", "user_improvement", "✨"),
    ("Bug Fixes", "bug_fix", "🐛"),
    ("Documentation", "docs", "📚"),
    ("Refactoring", "refactor", "🔧"),
    ("Migrations/Renames", "migration", "🔄"),
    ("Internal/Infrastructure", "internal", "🏭"),
    ("Other", "other", "📦"),
]


class InvalidDateFormat(Exception):
    """Raised when a date string cannot be parsed."""


def parse_since_date(value: str) -> datetime:
    """Parse a date/time string into a datetime object.

    Supports:
    - ISO date: 2025-12-28
    - ISO datetime: 2025-12-28T14:30:00

    Raises:
        InvalidDateFormat: If the value cannot be parsed.
    """
    # Try ISO date format first
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        pass

    # Try ISO datetime format
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        pass

    raise InvalidDateFormat(f"Cannot parse date: {value}")


def fetch_merged_prs(since_date: str, until_date: str | None = None) -> list[dict]:
    """Fetch merged PRs from GitHub for a date range."""
    if until_date:
        search = f"merged:>={since_date} merged:<={until_date}"
    else:
        search = f"merged:>={since_date}"
    result = subprocess.run(
        [
            "gh",
            "pr",
            "list",
            "--state",
            "merged",
            "--search",
            search,
            "--json",
            "number,title,mergeCommit",
            "--limit",
            "1000",
        ],
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def local_to_utc(dt: datetime) -> datetime:
    """Convert a naive local datetime to UTC."""
    # Treat naive datetime as local time, then convert to UTC
    local_dt = dt.astimezone()  # Adds local timezone
    return local_dt.astimezone(UTC)


def fetch_all_merged_prs(since: datetime) -> list[dict]:
    """Fetch all merged PRs using pagination by date ranges to avoid 1000 limit.

    Args:
        since: A naive datetime in local time.
    """
    # Convert local times to UTC for GitHub API queries
    since_utc = local_to_utc(since)
    end_utc = local_to_utc(datetime.now())

    all_prs: list[dict] = []
    seen_numbers: set[int] = set()

    # Paginate in 2-week chunks
    current = since_utc
    while current < end_utc:
        chunk_end = min(current + timedelta(days=14), end_utc)
        chunk_start_str = current.strftime("%Y-%m-%dT%H:%M:%S")
        chunk_end_str = chunk_end.strftime("%Y-%m-%dT%H:%M:%S")

        prs = fetch_merged_prs(chunk_start_str, chunk_end_str)
        for pr in prs:
            if pr["number"] not in seen_numbers:
                seen_numbers.add(pr["number"])
                all_prs.append(pr)

        current = chunk_end + timedelta(days=1)

    return all_prs


CATEGORY_KEYS = [
    "user_feature",
    "user_improvement",
    "bug_fix",
    "docs",
    "refactor",
    "migration",
    "internal",
    "other",
]


def analyze_prs(prs: list[dict]) -> dict[str, CategoryStats]:
    """Analyze PRs and categorize them."""
    categories = {k: CategoryStats(prs=[]) for k in CATEGORY_KEYS}

    for pr in prs:
        merge_commit = pr.get("mergeCommit")
        if not merge_commit:
            categories["other"].prs.append(pr)
            continue

        sha = merge_commit["oid"]
        indicators, _ = analyze_diff(sha)
        cat = categorize_by_content(pr["title"], indicators)
        categories[cat].prs.append(pr)

        stats = get_diff_stats(sha)
        categories[cat].py += stats.py_net
        categories[cat].py_test += stats.py_test_net
        categories[cat].md += stats.md_net

    return categories


def print_report(categories: dict[str, CategoryStats], since: datetime) -> None:
    """Print the formatted report."""
    total_prs = sum(len(c.prs) for c in categories.values())
    total_loc = sum(c.total for c in categories.values())
    total_py = sum(c.py for c in categories.values())
    total_py_test = sum(c.py_test for c in categories.values())
    total_md = sum(c.md for c in categories.values())

    # Format datetime for display - use ISO format with time if not midnight
    if since.hour == 0 and since.minute == 0 and since.second == 0:
        display_date = since.strftime("%Y-%m-%d")
    else:
        display_date = since.strftime("%Y-%m-%dT%H:%M:%S")
    print(f"## PRs Merged Since {display_date}\n")
    header = (
        "| Category                        "
        "| PRs |    % |       Py | Py (test) |  Markdown | Net LOC |    % |"
    )
    print(header)
    print(
        "|---------------------------------|----:|-----:|---------:|----------:|----------:|--------:|-----:|"
    )

    for text, cat, emoji in CATEGORY_DATA:
        c = categories[cat]
        n = len(c.prs)
        pct = (n / total_prs * 100) if total_prs else 0
        tot = c.total
        lpct = (tot / total_loc * 100) if total_loc else 0
        print(
            f"| {emoji}  {text:<27} | {n:>3} | {pct:>3.0f}% | "
            f"{fmt_num(c.py):>8} | {fmt_num(c.py_test):>9} | {fmt_num(c.md):>9} | "
            f"{fmt_num(tot):>7} | {lpct:>3.0f}% |"
        )

    print(
        "|---------------------------------|----:|-----:|---------:|----------:|----------:|--------:|-----:|"
    )
    print(
        f"| **TOTAL**                       | {total_prs:>3} | 100% | "
        f"{fmt_num(total_py):>8} | {fmt_num(total_py_test):>9} | {fmt_num(total_md):>9} | "
        f"{fmt_num(total_loc):>7} | 100% |"
    )


def main() -> None:
    """Main entry point."""
    since_input = sys.argv[1] if len(sys.argv) > 1 else "2025-12-08"
    since = parse_since_date(since_input)

    prs = fetch_all_merged_prs(since)
    categories = analyze_prs(prs)
    print_report(categories, since)


if __name__ == "__main__":
    main()
