"""AI-powered pull request update functionality."""

import re
import subprocess
import sys


class PRUpdateError(Exception):
    """Exception raised during PR update process."""

    pass


def run_command(cmd: list[str], capture_output: bool) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(cmd, capture_output=capture_output, text=True, check=True)
        return result
    except subprocess.CalledProcessError as e:
        raise PRUpdateError(f"Command failed: {' '.join(cmd)}\nError: {e.stderr}") from e
    except FileNotFoundError as e:
        raise PRUpdateError(f"Command not found: {cmd[0]}. Please ensure it's installed.") from e


def get_previous_branch() -> str:
    """
    Step 1: Identify the previous branch using gt ls -s.

    The previous branch is the one that appears immediately AFTER the ◉ (current branch)
    in the gt ls -s output.
    """
    result = run_command(["gt", "ls", "-s"], capture_output=True)
    lines = result.stdout.strip().split("\n")

    current_branch_found = False
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Current branch is marked with ◉
        if line.startswith("◉"):
            current_branch_found = True
            continue

        # The next branch after current (marked with ◯) is our previous branch
        if current_branch_found and line.startswith("◯"):
            # Extract branch name - it's after the ◯ marker
            branch_match = re.match(r"◯\s+(\S+)", line)
            if branch_match:
                return branch_match.group(1)

    raise PRUpdateError("Could not identify previous branch from gt ls -s output")


def get_current_branch_changes(previous_branch: str) -> tuple[str, str]:
    """
    Step 2: Get changes for current branch only.

    Returns tuple of (diff_output, commit_log)
    """
    # Get diff for current branch only
    diff_result = run_command(["git", "diff", f"{previous_branch}..HEAD"], capture_output=True)

    # Get commit messages for current branch only
    log_result = run_command(
        ["git", "log", "--oneline", f"{previous_branch}..HEAD"], capture_output=True
    )

    return diff_result.stdout, log_result.stdout


def generate_pr_summary(diff_output: str, commit_log: str) -> str:
    """
    Step 3a: Generate PR summary based on git diff output.

    The git diff output is the ONLY source of truth for what changes to include.
    """
    # Analyze diff to create summary
    lines = diff_output.split("\n")

    # Extract basic information about changes
    files_changed = set()
    additions = 0
    deletions = 0

    for line in lines:
        if line.startswith("+++") or line.startswith("---"):
            # Extract filename
            if line.startswith("+++") and not line.endswith("/dev/null"):
                filename = line[4:].strip()  # Remove +++ prefix
                if filename.startswith("b/"):
                    filename = filename[2:]  # Remove b/ prefix
                files_changed.add(filename)
        elif line.startswith("+") and not line.startswith("+++"):
            additions += 1
        elif line.startswith("-") and not line.startswith("---"):
            deletions += 1

    # Generate summary content based on changes
    summary_parts = []

    if files_changed:
        if len(files_changed) == 1:
            summary_parts.append(f"Updates `{next(iter(files_changed))}`")
        else:
            summary_parts.append(f"Updates {len(files_changed)} files")

    if additions > 0 and deletions > 0:
        summary_parts.append(f"({additions} additions, {deletions} deletions)")
    elif additions > 0:
        summary_parts.append(f"({additions} additions)")
    elif deletions > 0:
        summary_parts.append(f"({deletions} deletions)")

    # Create the basic summary
    if summary_parts:
        main_summary = " ".join(summary_parts)
    else:
        main_summary = "Minor changes"

    # Look for code samples or new APIs in the diff
    code_sample = ""
    if "def " in diff_output or "class " in diff_output:
        # Try to extract a simple code example
        for line in lines:
            if line.startswith("+") and ("def " in line or "class " in line):
                code_sample = f"\n\n```python\n{line[1:].strip()}\n```"
                break

    # Generate the full PR summary
    pr_summary = f"""## Summary & Motivation

{main_summary}.{code_sample}

## How I Tested These Changes

Existing test suite.

## Changelog

[Remove this section if no public-facing API was changed and no bug was fixed]"""

    return pr_summary


def update_pr_and_commit(pr_summary: str) -> None:
    """
    Step 3b: Update PR and commit message.
    """
    # Check if there's a current PR
    try:
        run_command(["gh", "pr", "view"], capture_output=True)
    except PRUpdateError:
        raise PRUpdateError("No PR found for current branch. Please create a PR first.")

    # Generate a concise title from the summary
    summary_lines = pr_summary.split("\n")
    first_content_line = None
    for line in summary_lines:
        if line.strip() and not line.startswith("#"):
            first_content_line = line.strip()
            break

    if first_content_line:
        # Remove trailing period and limit length
        title = first_content_line.rstrip(".")
        if len(title) > 72:
            title = title[:69] + "..."
    else:
        title = "Update implementation"

    # Update PR title and body
    run_command(["gh", "pr", "edit", "--title", title], capture_output=False)
    run_command(["gh", "pr", "edit", "--body", pr_summary], capture_output=False)

    # Update the latest commit message
    commit_message = f"{title}\n\n{pr_summary}"
    run_command(["git", "commit", "--amend", "-m", commit_message], capture_output=False)

    print(f"✅ Updated PR title: {title}")
    print("✅ Updated PR description")
    print("✅ Updated commit message")


def main() -> None:
    """Main entry point for AI PR update command."""
    try:
        print("🔍 Step 1: Identifying previous branch...")
        previous_branch = get_previous_branch()
        print(f"   Previous branch: {previous_branch}")

        print("📊 Step 2: Getting changes for current branch...")
        diff_output, commit_log = get_current_branch_changes(previous_branch)

        # Verify we have a reasonable number of commits
        commit_count = len([line for line in commit_log.strip().split("\n") if line.strip()])
        print(f"   Found {commit_count} commit(s) in current branch")

        if commit_count > 5:
            print(
                f"⚠️  Warning: Found {commit_count} commits. "
                f"Double-check that '{previous_branch}' is the correct previous branch."
            )

        print("✍️  Step 3: Generating and updating PR summary...")
        pr_summary = generate_pr_summary(diff_output, commit_log)
        update_pr_and_commit(pr_summary)

        print("🎉 PR update completed successfully!")

    except PRUpdateError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n❌ Cancelled by user", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
