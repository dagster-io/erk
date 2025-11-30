"""Create .impl/ folder from GitHub issue with plan content.

This kit CLI command fetches a plan from a GitHub issue and creates the .impl/
folder structure, providing a testable alternative to inline workflow scripts.

Usage:
    dot-agent run erk create-impl-from-issue <issue-number>

Output:
    Structured JSON output with success status and folder details

Exit Codes:
    0: Success (.impl/ folder created)
    1: Error (issue not found, plan fetch failed, folder creation failed)

Examples:
    $ dot-agent run erk create-impl-from-issue 1028
    {"success": true, "impl_path": "/path/to/.impl", "issue_number": 1028}

    $ dot-agent run erk create-impl-from-issue 999
    {"success": false, "error": "issue_not_found", "message": "..."}
"""

import json
from pathlib import Path

import click
from erk_shared.github.issues import RealGitHubIssues
from erk_shared.impl_folder import create_impl_folder, save_issue_reference
from erk_shared.plan_store.github import GitHubPlanStore


@click.command(name="create-impl-from-issue")
@click.argument("issue_number", type=int)
@click.option(
    "--repo-root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=None,
    help="Repository root directory (defaults to current directory)",
)
def create_impl_from_issue(
    issue_number: int,
    repo_root: Path | None,
) -> None:
    """Create .impl/ folder from GitHub issue with plan content.

    Fetches plan content from GitHub issue and creates .impl/ folder structure
    with plan.md, progress.md, and issue.json.

    ISSUE_NUMBER: GitHub issue number containing the plan
    """
    # Default to current directory if not specified
    if repo_root is None:
        repo_root = Path.cwd()

    # Direct instantiation of required dependencies (avoids erk import)
    # This allows the command to work when run via dot-agent without uv
    github_issues = RealGitHubIssues()
    plan_store = GitHubPlanStore(github_issues)

    # Fetch plan from GitHub (raises RuntimeError if not found)
    try:
        plan = plan_store.get_plan(repo_root, str(issue_number))
    except RuntimeError as e:
        error_output = {
            "success": False,
            "error": "plan_not_found",
            "message": f"Could not fetch plan for issue #{issue_number}: {e}. "
            f"Ensure issue has erk-plan label and plan content.",
        }
        click.echo(json.dumps(error_output), err=True)
        raise SystemExit(1) from e

    # Remove stale .impl/ if exists (for reruns)
    impl_path = repo_root / ".impl"
    if impl_path.exists():
        import shutil

        shutil.rmtree(impl_path)

    # Create .impl/ folder using existing function
    impl_path = create_impl_folder(repo_root, plan.body)

    # Add issue.json reference
    save_issue_reference(impl_path, issue_number, plan.url)

    # Output structured success result
    output = {
        "success": True,
        "impl_path": str(impl_path),
        "issue_number": issue_number,
        "issue_url": plan.url,
    }
    click.echo(json.dumps(output))
