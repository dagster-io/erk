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


def save_run_info(impl_dir: Path, run_id: str, run_url: str) -> None:
    """Save GitHub Actions run information to .impl/run-info.json.

    Args:
        impl_dir: Path to .impl/ directory
        run_id: GitHub Actions run ID
        run_url: Full URL to the GitHub Actions run
    """
    run_info_file = impl_dir / "run-info.json"
    data = {
        "run_id": run_id,
        "run_url": run_url,
    }
    run_info_file.write_text(json.dumps(data, indent=2), encoding="utf-8")


@click.command(name="create-impl-from-issue")
@click.argument("issue_number", type=int)
@click.option(
    "--repo-root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=None,
    help="Repository root directory (defaults to current directory)",
)
@click.option(
    "--run-id",
    type=str,
    default=None,
    help="GitHub Actions run ID (optional, for workflow context)",
)
@click.option(
    "--run-url",
    type=str,
    default=None,
    help="GitHub Actions run URL (optional, for workflow context)",
)
def create_impl_from_issue(
    issue_number: int,
    repo_root: Path | None,
    run_id: str | None,
    run_url: str | None,
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

    # Create .impl/ folder with plan content
    impl_path = repo_root / ".impl"

    # Check if .impl/ already exists (LBYL)
    if impl_path.exists():
        error_output = {
            "success": False,
            "error": "impl_exists",
            "message": f".impl/ folder already exists at {impl_path}",
        }
        click.echo(json.dumps(error_output), err=True)
        raise SystemExit(1)

    # Create .impl/ with plan.md and progress.md
    create_impl_folder(repo_root, plan.body)

    # Save issue.json using canonical function
    save_issue_reference(impl_path, issue_number, plan.url)

    # Optionally save run-info.json if workflow context is provided
    if run_id is not None and run_url is not None:
        save_run_info(impl_path, run_id, run_url)

    # Output structured success result
    output = {
        "success": True,
        "impl_path": str(impl_path),
        "issue_number": issue_number,
        "issue_url": plan.url,
    }

    if run_id is not None:
        output["run_id"] = run_id

    click.echo(json.dumps(output))
