"""Get commits for changelog update since last "As of" marker."""

import json
import re
import subprocess
from pathlib import Path

import click

from erk_dev.cli.output import machine_output, user_output


def parse_changelog_marker(changelog_path: Path) -> str | None:
    """Parse CHANGELOG.md to find 'As of <commit>' marker.

    Returns the commit hash if found, None otherwise.
    """
    if not changelog_path.exists():
        return None

    content = changelog_path.read_text(encoding="utf-8")

    # Look for "As of `<commit_hash>`" pattern in the Unreleased section
    # The hash is typically 9 characters but could vary
    match = re.search(r"As of `([a-f0-9]{7,40})`", content)
    if match:
        return match.group(1)

    return None


def extract_pr_number(subject: str) -> int | None:
    """Extract PR number from commit subject if present.

    Looks for pattern like (#NNNN) at the end of the subject.
    """
    match = re.search(r"\(#(\d+)\)\s*$", subject)
    if match:
        return int(match.group(1))
    return None


def get_commit_details(commit_hash: str) -> dict[str, str | list[str] | int | None]:
    """Get detailed information about a commit."""
    # Get subject and body
    result = subprocess.run(
        ["git", "show", "--format=%s%n%n%b", "--no-patch", commit_hash],
        capture_output=True,
        text=True,
        check=True,
    )
    output = result.stdout.strip()
    lines = output.split("\n", 2)
    subject = lines[0] if lines else ""
    body = lines[2] if len(lines) > 2 else ""

    # Get files changed
    files_result = subprocess.run(
        ["git", "show", "--format=", "--name-only", commit_hash],
        capture_output=True,
        text=True,
        check=True,
    )
    files_changed = [f for f in files_result.stdout.strip().split("\n") if f]

    return {
        "hash": commit_hash,
        "subject": subject,
        "body": body,
        "files_changed": files_changed,
        "pr_number": extract_pr_number(subject),
    }


def get_commits_since_marker(
    marker_commit: str,
) -> list[dict[str, str | list[str] | int | None]]:
    """Get commits since the marker commit using --first-parent.

    Excludes paths: .claude/, docs/learned/, .impl/
    """
    result = subprocess.run(
        [
            "git",
            "log",
            "--oneline",
            "--first-parent",
            f"{marker_commit}..HEAD",
            "--",
            ".",
            ":!.claude",
            ":!docs/learned",
            ":!.impl",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    commits = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        # Parse "hash subject" format
        parts = line.split(" ", 1)
        if parts:
            commit_hash = parts[0]
            commits.append(get_commit_details(commit_hash))

    return commits


@click.command(name="changelog-commits")
@click.option(
    "--json-output",
    is_flag=True,
    help="Output as JSON for machine consumption",
)
def changelog_commits_command(json_output: bool) -> None:
    """Get commits for changelog update since last 'As of' marker.

    Reads CHANGELOG.md, finds the 'As of <commit>' marker, and returns
    all commits since that point that should be considered for changelog entries.
    """
    changelog_path = Path("CHANGELOG.md")

    # Check changelog exists
    if not changelog_path.exists():
        error_msg = "CHANGELOG.md not found in current directory"
        if json_output:
            machine_output(json.dumps({"success": False, "error": error_msg}))
        else:
            user_output(f"Error: {error_msg}")
        raise SystemExit(1)

    # Parse marker from changelog
    marker_commit = parse_changelog_marker(changelog_path)
    if marker_commit is None:
        error_msg = "No 'As of <commit>' marker found in CHANGELOG.md Unreleased section"
        if json_output:
            machine_output(json.dumps({"success": False, "error": error_msg}))
        else:
            user_output(f"Error: {error_msg}")
        raise SystemExit(1)

    # Verify marker commit exists
    verify_result = subprocess.run(
        ["git", "cat-file", "-t", marker_commit],
        capture_output=True,
        text=True,
        check=False,
    )
    if verify_result.returncode != 0:
        error_msg = f"Marker commit {marker_commit} not found in repository"
        if json_output:
            machine_output(json.dumps({"success": False, "error": error_msg}))
        else:
            user_output(f"Error: {error_msg}")
        raise SystemExit(1)

    # Get HEAD commit
    head_result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    head_commit = head_result.stdout.strip()

    # Get commits since marker
    commits = get_commits_since_marker(marker_commit)

    result = {
        "success": True,
        "since_commit": marker_commit,
        "head_commit": head_commit,
        "commits": commits,
    }

    if json_output:
        machine_output(json.dumps(result, indent=2))
    else:
        if not commits:
            user_output(f"No new commits since {marker_commit}")
        else:
            user_output(f"Found {len(commits)} commits since {marker_commit}:")
            for commit in commits:
                pr_info = f" (#{commit['pr_number']})" if commit.get("pr_number") else ""
                user_output(f"  {commit['hash']} - {commit['subject']}{pr_info}")
