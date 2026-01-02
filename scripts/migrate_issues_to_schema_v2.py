#!/usr/bin/env python3
"""Migrate all plan issues to schema v2 format.

This script:
1. Fetches all issues with the erk-plan label
2. For each issue without a plan-header metadata block:
   - Creates a plan-header block with metadata derived from the issue
   - Prepends the metadata block to the issue body
   - Updates the issue on GitHub
"""

import json
import subprocess
import sys

from erk_shared.github.metadata import (
    create_plan_header_block,
    find_metadata_block,
    render_metadata_block,
)
from erk_shared.naming import sanitize_branch_component


def run_gh_command(cmd: list[str]) -> dict:
    """Run gh CLI command and return JSON output."""
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def get_plan_issues() -> list[dict]:
    """Get all issues with erk-plan label."""
    cmd = [
        "gh",
        "issue",
        "list",
        "--label",
        "erk-plan",
        "--state",
        "all",
        "--limit",
        "1000",
        "--json",
        "number,title,body,author,createdAt",
    ]
    return run_gh_command(cmd)


def issue_has_plan_header(body: str) -> bool:
    """Check if issue body has plan-header metadata block."""
    return find_metadata_block(body, "plan-header") is not None


def migrate_issue(issue: dict) -> None:
    """Migrate a single issue to schema v2."""
    number = issue["number"]
    title = issue["title"]
    body = issue["body"]
    author = issue["author"]["login"]
    created_at = issue["createdAt"]

    # Check if already migrated
    if issue_has_plan_header(body):
        print(f"  ✓ Issue #{number} already has plan-header - skipping")
        return

    print(f"  Migrating issue #{number}: {title}")

    # Derive worktree name from title
    worktree_name = sanitize_branch_component(title)

    # Create plan-header metadata block
    header_block = create_plan_header_block(
        created_at=created_at,
        created_by=author,
        worktree_name=worktree_name,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        plan_type=None,
        source_plan_issues=None,
        extraction_session_ids=None,
        objective_issue=None,
    )

    # Render the metadata block
    header_content = render_metadata_block(header_block)

    # Prepend to existing body
    if body.strip():
        new_body = f"{header_content}\n\n{body}"
    else:
        new_body = header_content

    # Update issue body via gh CLI
    cmd = [
        "gh",
        "issue",
        "edit",
        str(number),
        "--body",
        new_body,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"  ✓ Issue #{number} migrated successfully")


def main() -> int:
    """Main migration logic."""
    print("Fetching all plan issues...")
    issues = get_plan_issues()
    print(f"Found {len(issues)} plan issues")

    migrated_count = 0
    skipped_count = 0

    for issue in issues:
        if issue_has_plan_header(issue["body"]):
            skipped_count += 1
        else:
            migrate_issue(issue)
            migrated_count += 1

    print("\nMigration complete:")
    print(f"  - Migrated: {migrated_count}")
    print(f"  - Skipped (already v2): {skipped_count}")
    print(f"  - Total: {len(issues)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
