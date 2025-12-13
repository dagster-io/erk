"""
PR Landing Logic using Graphite workflow.

Automates the complete PR landing workflow using Graphite (gt) and GitHub CLI (gh).
Handles both single PR and multi-PR stack scenarios with robust conflict resolution.
"""

import json
import re
import subprocess
import sys
from typing import TypedDict


class BranchInfo(TypedDict):
    current_branch: str
    parent_branch: str


class PRInfo(TypedDict):
    number: int
    title: str
    state: str
    body: str


def run_command(
    cmd: list[str], capture_output: bool = True, check: bool = True
) -> subprocess.CompletedProcess[str]:
    """Run shell command and return result.

    Args:
        cmd: Command as list (safer, prevents shell injection)
        capture_output: Whether to capture stdout/stderr
        check: Whether to raise exception on non-zero exit code
    """
    try:
        result = subprocess.run(
            cmd, shell=False, capture_output=capture_output, text=True, check=check
        )
        return result
    except subprocess.CalledProcessError as e:
        cmd_str = " ".join(cmd)
        print(f"Command failed: {cmd_str}", file=sys.stderr)
        if e.stderr:
            print(f"Error: {e.stderr}", file=sys.stderr)
        if check:
            sys.exit(1)
        # Convert CalledProcessError to CompletedProcess for consistent return type
        return subprocess.CompletedProcess(
            args=e.cmd, returncode=e.returncode, stdout=e.stdout or "", stderr=e.stderr or ""
        )


def get_current_branch() -> str:
    """Get the current branch name."""
    result = run_command(["git", "branch", "--show-current"])
    return result.stdout.strip()


def get_branch_info() -> BranchInfo:
    """Get branch information from Graphite."""
    try:
        result = run_command(["gt", "branch", "info"])
        output = result.stdout

        # Extract parent branch

        parent_match = re.search(r"Parent:\s+(\S+)", output)
        if not parent_match:
            print(
                "Error: Branch not tracked by Graphite. Run `gt branch track` first",
                file=sys.stderr,
            )
            sys.exit(1)

        parent_branch = parent_match.group(1)
        current_branch = get_current_branch()

        return BranchInfo(current_branch=current_branch, parent_branch=parent_branch)
    except subprocess.CalledProcessError:
        print(
            "Error: Failed to get branch info from Graphite. Ensure branch is tracked.",
            file=sys.stderr,
        )
        sys.exit(1)


def get_pr_info() -> PRInfo:
    """Get PR information from GitHub."""
    try:
        result = run_command(["gh", "pr", "view", "--json", "number,title,state,body"])
        pr_data = json.loads(result.stdout)
        return PRInfo(
            number=pr_data["number"],
            title=pr_data["title"],
            state=pr_data["state"],
            body=pr_data["body"] or "",
        )
    except subprocess.CalledProcessError:
        print("Error: No PR found for this branch", file=sys.stderr)
        sys.exit(1)


def is_trunk_branch(branch_name: str) -> bool:
    """Check if the given branch is a trunk branch (main/master)."""
    return branch_name in ["main", "master"]


def pre_flight_checks() -> tuple[BranchInfo, PRInfo]:
    """Perform pre-flight checks before landing PR."""
    print("🔍 Performing pre-flight checks...")

    # Get current branch info
    branch_info = get_branch_info()
    current_branch = branch_info["current_branch"]

    # Check we're not already on trunk
    if is_trunk_branch(current_branch):
        print(
            f"Error: Already on trunk branch '{current_branch}'. Switch to a feature branch first.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Get PR info
    pr_info = get_pr_info()

    # Check PR is open
    if pr_info["state"] != "OPEN":
        print(f"Error: PR #{pr_info['number']} is {pr_info['state']}, not OPEN", file=sys.stderr)
        sys.exit(1)

    print(f"✅ Branch: {current_branch}")
    print(f"✅ PR #{pr_info['number']}: {pr_info['title']}")
    print(f"✅ Parent: {branch_info['parent_branch']}")

    return branch_info, pr_info


def pre_merge_restack() -> None:
    """Perform pre-merge restack with conflict resolution."""
    print("🔄 Performing pre-merge restack...")

    try:
        result = run_command(["gt", "restack"], check=False)
        if result.returncode == 0:
            print("✅ Restack completed successfully")
            return
        else:
            print("⚠️  Merge conflicts detected during restack")
            print("\nPlease resolve conflicts manually:")
            print("1. Fix conflicts in your editor")
            print("2. Run: git add .")
            print("3. Run: git rebase --continue")
            print("4. Re-run this command to continue landing")
            sys.exit(1)
    except subprocess.CalledProcessError:
        print("❌ Restack failed unexpectedly", file=sys.stderr)
        sys.exit(1)


def format_commit_message(pr_info: PRInfo) -> str:
    """Format enhanced commit message with PR title and summary."""
    title = pr_info["title"]
    number = pr_info["number"]
    body = pr_info["body"]

    # Start with title and PR number
    commit_msg = f"{title} (#{number})\n\n"

    # Add the PR body (description/summary) if it exists
    if body.strip():
        commit_msg += f"{body.strip()}"

    return commit_msg


def sync_with_graphite() -> None:
    """Sync with Graphite to detect merged PRs and clean up branches.

    Uses gt sync to detect merged branches and automatically delete them.
    This eliminates the race condition between GitHub API and Graphite state.
    """
    print("🔄 Syncing with Graphite to detect merge and cleanup...")

    try:
        run_command(["gt", "sync", "-f", "--no-restack", "--no-interactive"])
        print("✅ Graphite sync completed")
    except subprocess.CalledProcessError:
        print("❌ Failed to sync with Graphite", file=sys.stderr)
        sys.exit(1)


def merge_pr(pr_info: PRInfo) -> None:
    """Merge the PR using squash merge with enhanced commit message."""
    print(f"🚀 Merging PR #{pr_info['number']} with squash merge...")

    # Format the enhanced commit message
    commit_message = format_commit_message(pr_info)

    try:
        run_command(["gh", "pr", "merge", "-s", "-m", commit_message])
        print("✅ PR merged successfully with enhanced commit message")
    except subprocess.CalledProcessError:
        print("❌ Failed to merge PR. Check GitHub for details.", file=sys.stderr)
        sys.exit(1)


def check_final_location() -> str:
    """Check where we ended up after the sync and return current branch."""
    print("📍 Checking final location...")

    current_branch = get_current_branch()
    print(f"✅ Currently on: {current_branch}")

    return current_branch


def finalize_stack(current_branch: str) -> None:
    """Finalize the stack after merge."""
    if is_trunk_branch(current_branch):
        print(f"🎉 Successfully landed PR! Now on {current_branch}")
        print("Single PR stack - landing complete.")
    else:
        print(f"🔄 Now on {current_branch} - performing final restack...")
        try:
            run_command(["gt", "restack"])
            print(f"🎉 Successfully landed PR! Now on {current_branch}")
            print("Multi-PR stack - ready for next PR in stack.")
        except subprocess.CalledProcessError:
            print(
                "⚠️  Final restack failed. You may need to resolve conflicts manually.",
                file=sys.stderr,
            )
            print(f"Currently on: {current_branch}")


def execute_pr_landing(dry_run: bool) -> bool:
    """Execute the complete PR landing workflow.

    Args:
        dry_run: If True, show what operations would be performed without executing them

    Returns:
        True if landing was successful, False otherwise
    """
    if dry_run:
        print("🔍 DRY RUN - Showing operations that would be performed:")
        try:
            # Get info but don't perform actions
            branch_info, pr_info = pre_flight_checks()
            print("🔄 Would perform pre-merge restack")
            print(f"🚀 Would merge PR #{pr_info['number']} with squash merge")
            print("🔄 Would sync with Graphite to detect merge and cleanup")
            print("📍 Would check final location and finalize stack")
            return True
        except SystemExit:
            return False

    print("🛬 Starting PR landing process...")

    try:
        # Pre-flight checks
        branch_info, pr_info = pre_flight_checks()

        # Pre-merge restack
        pre_merge_restack()

        # Merge PR
        merge_pr(pr_info)

        # Sync with Graphite to detect merge and cleanup
        sync_with_graphite()

        # Check where we ended up
        current_branch = check_final_location()

        # Finalize
        finalize_stack(current_branch)

        return True

    except SystemExit:
        return False
