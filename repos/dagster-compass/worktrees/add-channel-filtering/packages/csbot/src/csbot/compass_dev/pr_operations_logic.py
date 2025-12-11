"""
PR Operations utility logic for squash-and-update-pr workflow.
Handles mechanical git/GitHub operations efficiently.
"""

import json
import re
import subprocess
import sys
from typing import TypedDict


class FileChange(TypedDict):
    path: str
    status: str


class CommitDetails(TypedDict):
    commit_hash: str
    commit_subject: str
    commit_body: str
    file_changes: list[FileChange]


def run_command(cmd: str | list[str], capture_output: bool) -> subprocess.CompletedProcess:
    """Run shell command and return result.

    Args:
        cmd: Command as string (for shell=True) or list (for shell=False, safer)
        capture_output: Whether to capture stdout/stderr
    """
    try:
        if isinstance(cmd, list):
            # Use list form for safety (no shell injection)
            result = subprocess.run(
                cmd, shell=False, capture_output=capture_output, text=True, check=True
            )
        else:
            # Use string form only for simple commands
            result = subprocess.run(
                cmd, shell=True, capture_output=capture_output, text=True, check=True
            )
        return result
    except subprocess.CalledProcessError as e:
        cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
        print(f"Command failed: {cmd_str}", file=sys.stderr)
        print(f"Error: {e.stderr}", file=sys.stderr)
        sys.exit(1)


def get_branch_info() -> dict[str, str]:
    """Get branch information from Graphite."""
    result = run_command("gt branch info", capture_output=True)
    output = result.stdout

    # Extract parent branch
    parent_match = re.search(r"Parent:\s+(\S+)", output)
    if not parent_match:
        print("Error: Branch not tracked by Graphite. Run `gt branch track` first", file=sys.stderr)
        sys.exit(1)

    parent_branch = parent_match.group(1)

    # Get current branch name
    current_result = run_command("git branch --show-current", capture_output=True)
    current_branch = current_result.stdout.strip()

    return {"current_branch": current_branch, "parent_branch": parent_branch}


def get_pr_info() -> dict[str, str | int]:
    """Get PR information from GitHub."""
    try:
        result = run_command("gh pr view --json number,url", capture_output=True)
        pr_data = json.loads(result.stdout)
        return {"pr_number": pr_data["number"], "pr_url": pr_data["url"]}
    except subprocess.CalledProcessError:
        print("Error: No PR found for this branch", file=sys.stderr)
        sys.exit(1)


def get_commit_count(parent_branch: str) -> int:
    """Count commits ahead of parent branch."""
    result = run_command(
        ["git", "rev-list", "--count", "HEAD", f"^{parent_branch}"], capture_output=True
    )
    return int(result.stdout.strip())


def get_commit_details() -> CommitDetails:
    """Get detailed commit information."""
    # Get commit info without stat first
    commit_result = run_command(
        ["git", "show", "--pretty=format:%H%n%s%n%b", "-s"], capture_output=True
    )
    lines = commit_result.stdout.split("\n")

    commit_hash = lines[0] if lines else ""
    commit_subject = lines[1] if len(lines) > 1 else ""
    raw_commit_body = "\n".join(lines[2:]).strip() if len(lines) > 2 else ""

    # Filter out generated PR content from commit body to avoid duplication
    # Look for Claude attribution markers and PR URLs to identify generated content
    commit_body = ""
    if raw_commit_body:
        # Split by lines and filter out generated content
        body_lines = raw_commit_body.split("\n")
        filtered_lines = []
        in_generated_section = False

        for line in body_lines:
            # Skip lines that indicate generated content
            if (
                "🤖 Generated with [Claude Code]" in line
                or "Co-Authored-By: Claude" in line
                or line.startswith("PR: https://github.com/")
                or line.strip() == "## Summary"
                or line.strip() == "## Key Changes"
                or line.strip() == "## Commit Details"
            ):
                in_generated_section = True
                continue

            # If we hit these patterns, we're likely in generated content
            if (
                "**Added:**" in line
                or "**Modified:**" in line
                or "**Deleted:**" in line
                or "**Renamed:**" in line
            ):
                in_generated_section = True
                continue

            # If we see commit hash patterns, skip
            if line.strip().startswith("- **Commit:**") and len(line.strip()) > 15:
                continue

            # If we see file count patterns, skip
            if line.strip().startswith("- **Files changed:**"):
                continue

            # If not in generated section, keep the line
            if not in_generated_section:
                filtered_lines.append(line)

        commit_body = "\n".join(filtered_lines).strip()

    # Get file changes using --name-status for reliable parsing
    stat_result = run_command(
        ["git", "show", "--name-status", "--pretty=format:"], capture_output=True
    )
    file_changes = []

    for line in stat_result.stdout.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # Format: "M\tfile/path" or "A\tfile/path" or "D\tfile/path"
        parts = line.split("\t", 1)
        if len(parts) == 2:
            status, file_path = parts
            file_changes.append(FileChange(path=file_path, status=status))

    return CommitDetails(
        commit_hash=commit_hash,
        commit_subject=commit_subject,
        commit_body=commit_body,
        file_changes=file_changes,
    )


def squash_commits() -> dict[str, bool | str]:
    """Squash commits using Graphite."""
    try:
        run_command("gt squash --no-edit", capture_output=False)
        # Get new commit hash after squash
        result = run_command("git rev-parse HEAD", capture_output=True)
        new_hash = result.stdout.strip()
        return {"success": True, "new_commit_hash": new_hash}
    except subprocess.CalledProcessError as e:
        return {"success": False, "error": str(e)}


def prepare_data() -> dict:
    """Collect all data needed for PR operations."""
    print("Collecting branch and PR information...", file=sys.stderr)

    # Get branch info
    branch_info = get_branch_info()

    # Get PR info
    pr_info = get_pr_info()

    # Count commits
    commit_count = get_commit_count(branch_info["parent_branch"])
    needs_squash = commit_count > 1

    print(f"Found {commit_count} commits, squash needed: {needs_squash}", file=sys.stderr)

    # Squash if needed
    squash_result = None
    if needs_squash:
        print("Squashing commits...", file=sys.stderr)
        squash_result = squash_commits()
        if not squash_result["success"]:
            print(f"Squash failed: {squash_result['error']}", file=sys.stderr)
            sys.exit(1)

    # Get commit details (after potential squash)
    commit_details = get_commit_details()

    return {
        "branch_info": branch_info,
        "pr_info": pr_info,
        "commit_count": commit_count,
        "needs_squash": needs_squash,
        "squash_result": squash_result,
        "commit_details": commit_details,
    }


def generate_pr_title(commit_subject: str, file_changes: list[FileChange]) -> str:
    """Generate intelligent PR title based on commit and file changes."""
    generic_subjects = {"ci", "fix", "update", "cp", "wip", "tmp"}

    # If subject is not generic, use it as the title
    if commit_subject.lower() not in generic_subjects:
        return commit_subject

    # Analyze file changes for generic subjects
    rename_count = sum(1 for change in file_changes if change["status"] == "R")
    workflow_files = [change for change in file_changes if ".github/workflows/" in change["path"]]
    python_files = [change for change in file_changes if change["path"].endswith(".py")]
    config_doc_files = [
        change
        for change in file_changes
        if any(change["path"].endswith(ext) for ext in [".yml", ".yaml", ".md", ".json", ".toml"])
    ]

    total_changes = len(file_changes)

    # Decision logic
    if rename_count > total_changes * 0.5:  # Majority are renames
        return "Rename files across codebase"
    elif workflow_files:
        return "Enhance CI/CD workflows"
    elif python_files and len(python_files) > total_changes * 0.5:  # Majority Python
        return "Update Python implementation"
    elif config_doc_files and len(config_doc_files) > total_changes * 0.5:  # Majority config/docs
        return "Update configuration and documentation"
    else:
        return commit_subject  # Fallback to original subject


def generate_pr_description(commit_details: CommitDetails, pr_url: str) -> str:
    """Generate structured PR description."""
    title = generate_pr_title(commit_details["commit_subject"], commit_details["file_changes"])

    # Build description
    description_parts = []

    # Summary section
    if commit_details["commit_body"]:
        description_parts.append(f"## Summary\n\n{commit_details['commit_body']}")
    else:
        description_parts.append(f"## Summary\n\n{title}")

    # Key changes section
    if commit_details["file_changes"]:
        description_parts.append("## Key Changes")
        description_parts.append("")

        # Group changes by type
        by_status = {}
        for change in commit_details["file_changes"]:
            status = change["status"]
            if status not in by_status:
                by_status[status] = []
            by_status[status].append(change["path"])

        status_names = {"A": "Added", "M": "Modified", "D": "Deleted", "R": "Renamed"}
        for status, files in by_status.items():
            status_name = status_names.get(status, status)
            if len(files) <= 5:
                file_list = "\n".join(f"- `{file}`" for file in files)
            else:
                file_list = "\n".join(f"- `{file}`" for file in files[:3])
                file_list += f"\n- ... and {len(files) - 3} more files"
            description_parts.append(f"**{status_name}:**\n{file_list}")

    # Commit info and attribution
    description_parts.extend(
        [
            "## Commit Details",
            f"- **Commit:** `{commit_details['commit_hash'][:8]}`",
            f"- **Files changed:** {len(commit_details['file_changes'])}",
            "",
            "🤖 Generated with [Claude Code](https://claude.ai/code)",
            "",
            "Co-Authored-By: Claude <noreply@anthropic.com>",
        ]
    )

    return "\n\n".join(description_parts)


def execute_updates(title: str, description: str, pr_url: str) -> dict[str, bool]:
    """Execute PR and commit updates."""
    print("Updating PR and commit...", file=sys.stderr)

    # Update PR - use safe argument passing
    try:
        run_command(
            ["gh", "pr", "edit", "--title", title, "--body", description], capture_output=False
        )
        pr_updated = True
    except subprocess.CalledProcessError:
        pr_updated = False

    # Update commit message - use safe argument passing
    commit_message = f"{title}\n\n{description}\n\nPR: {pr_url}"
    try:
        run_command(["git", "commit", "--amend", "-m", commit_message], capture_output=False)
        commit_updated = True
    except subprocess.CalledProcessError:
        commit_updated = False

    return {"pr_updated": pr_updated, "commit_updated": commit_updated}


def auto_update_workflow() -> dict:
    """Execute the auto-update workflow and return analysis data."""
    print("Collecting branch and PR information...", file=sys.stderr)

    # Step 1: Prepare data
    data = prepare_data()

    # Step 2: Return data for analysis
    return data


def squash_push_draft_workflow() -> dict:
    """Execute squash-push-draft workflow and return data for analysis."""
    print("Squashing commits and preparing draft PR...", file=sys.stderr)

    # Check if PR exists first
    try:
        # Try to get existing PR info
        run_command("gh pr view --json number,url", capture_output=True)
        pr_exists = True
        print("Found existing PR, updating it...", file=sys.stderr)
    except subprocess.CalledProcessError:
        pr_exists = False
        print("No existing PR found, will create one...", file=sys.stderr)

    if pr_exists:
        # Use existing prepare_data which includes PR info
        data = prepare_data()
    else:
        # No PR exists, prepare data without trying to get PR info
        print("Collecting branch information...", file=sys.stderr)

        # Get branch info
        branch_info = get_branch_info()

        # Count commits and squash if needed
        commit_count = get_commit_count(branch_info["parent_branch"])
        needs_squash = commit_count > 1

        print(f"Found {commit_count} commits, squash needed: {needs_squash}", file=sys.stderr)

        # Squash if needed
        if needs_squash:
            print("Squashing commits...", file=sys.stderr)
            squash_result = squash_commits()
            if not squash_result["success"]:
                print(f"Squash failed: {squash_result['error']}", file=sys.stderr)
                sys.exit(1)

        # Get commit details (after potential squash)
        commit_details = get_commit_details()

        # Prepare data structure for analysis
        data = {
            "branch_info": branch_info,
            "commit_count": commit_count,
            "needs_squash": needs_squash,
            "commit_details": commit_details,
        }

    return data
