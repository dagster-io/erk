"""Admin commands for repository configuration."""

import json
import subprocess
from typing import Literal

import click

from erk.cli.core import discover_repo_context
from erk.cli.subprocess_utils import run_with_error_reporting
from erk.core.context import ErkContext
from erk.core.implementation_queue.github.real import RealGitHubAdmin
from erk_shared.github.types import GitHubRepoLocation
from erk_shared.output.output import user_output


@click.group("admin")
def admin_group() -> None:
    """Administrative commands for repository configuration."""
    pass


@admin_group.command("github-pr-setting")
@click.option(
    "--enable",
    "action",
    flag_value="enable",
    help="Enable PR creation for GitHub Actions workflows",
)
@click.option(
    "--disable",
    "action",
    flag_value="disable",
    help="Disable PR creation for GitHub Actions workflows",
)
@click.pass_obj
def github_pr_setting(ctx: ErkContext, action: Literal["enable", "disable"] | None) -> None:
    """Manage GitHub Actions workflow permission for PR creation.

    Without flags: Display current setting
    With --enable: Enable PR creation for workflows
    With --disable: Disable PR creation for workflows

    This setting controls whether GitHub Actions workflows can create
    and approve pull requests in your repository.

    GitHub UI location: Settings > Actions > General > Workflow permissions
    """
    # Discover repository context
    repo = discover_repo_context(ctx, ctx.cwd)

    # Check for GitHub identity
    if repo.github is None:
        user_output(click.style("Error: ", fg="red") + "Not a GitHub repository")
        user_output("This command requires the repository to have a GitHub remote configured.")
        raise SystemExit(1)

    # Create admin interface
    # TODO: Use injected admin from context when dry-run support is added
    admin = RealGitHubAdmin()
    location = GitHubRepoLocation(root=repo.root, repo_id=repo.github)

    if action is None:
        # Display current setting
        try:
            perms = admin.get_workflow_permissions(location)
            enabled = perms.get("can_approve_pull_request_reviews", False)

            user_output(click.style("GitHub Actions PR Creation Setting", bold=True))
            user_output("")

            status_text = "Enabled" if enabled else "Disabled"
            status_color = "green" if enabled else "red"
            user_output(f"Current status: {click.style(status_text, fg=status_color)}")
            user_output("")

            if enabled:
                user_output("Workflows can create and approve pull requests in this repository.")
            else:
                user_output("Workflows cannot create pull requests in this repository.")

            user_output("")
            user_output(click.style("GitHub UI location:", fg="white", dim=True))
            user_output(
                click.style(
                    "  Settings > Actions > General > Workflow permissions",
                    fg="white",
                    dim=True,
                )
            )

        except RuntimeError as e:
            user_output(click.style("Error: ", fg="red") + str(e))
            raise SystemExit(1) from e

    elif action == "enable":
        # Enable PR creation
        try:
            admin.set_workflow_pr_permissions(location, enabled=True)

            user_output(
                click.style("✓", fg="green") + " Enabled PR creation for GitHub Actions workflows"
            )
            user_output("")
            user_output("Workflows can now create and approve pull requests.")

        except RuntimeError as e:
            user_output(click.style("Error: ", fg="red") + str(e))
            raise SystemExit(1) from e

    elif action == "disable":
        # Disable PR creation
        try:
            admin.set_workflow_pr_permissions(location, enabled=False)

            user_output(
                click.style("✓", fg="green") + " Disabled PR creation for GitHub Actions workflows"
            )
            user_output("")
            user_output("Workflows can no longer create pull requests.")

        except RuntimeError as e:
            user_output(click.style("Error: ", fg="red") + str(e))
            raise SystemExit(1) from e


@admin_group.command("upgrade-repo")
@click.pass_obj
def upgrade_repo(ctx: ErkContext) -> None:
    """Upgrade repo to match installed erk version.

    Updates .erk/required-erk-uv-tool-version and prints next steps.
    """
    from erk.core.release_notes import get_current_version

    repo = discover_repo_context(ctx, ctx.cwd)
    current_version = get_current_version()

    # Check if this is an erk-managed repository
    erk_dir = repo.root / ".erk"
    if not erk_dir.exists():
        user_output(click.style("Error: ", fg="red") + "Not an erk-managed repository")
        user_output(f"The directory {repo.root} does not contain a .erk directory.")
        user_output("This command only works in repositories initialized with erk.")
        raise SystemExit(1)

    # Update version file
    version_file = erk_dir / "required-erk-uv-tool-version"
    version_file.write_text(f"{current_version}\n", encoding="utf-8")
    user_output(f"Updated required version to {current_version}")

    # Print next steps
    user_output("")
    user_output("Next steps:")
    user_output("  erk artifact sync   # Sync skills, commands, hooks")
    user_output("  erk doctor          # Verify the upgrade")


@admin_group.command("test-erk-impl-gh-workflow")
@click.option("--issue", "-i", type=int, help="Existing issue number to use")
@click.option("--watch", "-w", is_flag=True, help="Watch the workflow run after triggering")
@click.pass_obj
def test_erk_impl_gh_workflow(ctx: ErkContext, issue: int | None, watch: bool) -> None:
    """Test the erk-impl.yml GitHub Actions workflow.

    This command automates testing of erk-impl workflow changes by:

    \b
    1. Ensuring the current branch exists on remote
    2. Finding or creating a test issue
    3. Creating a test branch and draft PR
    4. Triggering the workflow with --ref set to your branch
    5. Outputting the run URL

    Use this when modifying .github/workflows/erk-impl.yml to test changes.
    """
    repo = discover_repo_context(ctx, ctx.cwd)

    if repo.github is None:
        user_output(click.style("Error: ", fg="red") + "Not a GitHub repository")
        raise SystemExit(1)

    # Convert GitHubRepoId to string format for gh CLI
    repo_slug = f"{repo.github.owner}/{repo.github.repo}"

    current_branch = ctx.git.get_current_branch(repo.root)
    if current_branch is None:
        user_output(click.style("Error: ", fg="red") + "Not on a branch (detached HEAD)")
        raise SystemExit(1)

    # Step 1: Ensure current branch exists on remote
    user_output(f"Ensuring branch '{current_branch}' exists on remote...")
    ctx.git.push_to_remote(repo.root, "origin", current_branch, set_upstream=True)
    user_output(click.style("✓", fg="green") + f" Branch '{current_branch}' pushed to origin")

    # Step 2: Find or create test issue
    if issue is not None:
        issue_number = issue
        user_output(f"Using existing issue #{issue_number}")
    else:
        issue_number = _create_test_issue(repo_slug)
        user_output(click.style("✓", fg="green") + f" Created test issue #{issue_number}")

    # Step 3: Create test branch for implementation
    timestamp = int(ctx.time.now().timestamp())
    distinct_id = _base36_encode(timestamp)
    test_branch = f"test-workflow-{distinct_id}"

    user_output(f"Creating test branch '{test_branch}'...")
    # Push master to the test branch using refspec syntax
    ctx.git.push_to_remote(repo.root, "origin", f"master:{test_branch}")
    user_output(click.style("✓", fg="green") + f" Test branch '{test_branch}' created")

    # Step 4: Create draft PR
    pr_number = _create_draft_pr(repo_slug, test_branch)
    user_output(click.style("✓", fg="green") + f" Draft PR #{pr_number} created")

    # Step 5: Trigger workflow
    username = ctx.issues.get_current_username()
    if username is None:
        user_output(click.style("Error: ", fg="red") + "Not authenticated with GitHub")
        raise SystemExit(1)

    user_output(f"Triggering erk-impl workflow from '{current_branch}'...")
    _trigger_workflow(
        repo_slug=repo_slug,
        ref=current_branch,
        issue_number=issue_number,
        submitted_by=username,
        distinct_id=distinct_id,
        issue_title="Test workflow run",
        branch_name=test_branch,
        pr_number=pr_number,
        base_branch="master",
    )

    # Step 6: Get run URL
    ctx.time.sleep(2)  # Give GitHub a moment to create the run
    run_url = _get_latest_run_url(repo_slug)

    user_output("")
    user_output(click.style("Workflow triggered successfully!", fg="green", bold=True))
    user_output("")
    user_output(f"Run URL: {run_url}")
    user_output(f"Test branch: {test_branch}")
    user_output(f"Draft PR: https://github.com/{repo_slug}/pull/{pr_number}")

    if watch:
        user_output("")
        user_output("Watching run... (Ctrl+C to stop)")
        subprocess.run(["gh", "run", "watch", "--repo", repo_slug], check=False)


def _base36_encode(num: int) -> str:
    """Encode a number to base36 string."""
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    if num == 0:
        return "0"
    result = []
    while num:
        result.append(chars[num % 36])
        num //= 36
    return "".join(reversed(result))


def _create_test_issue(repo_slug: str) -> int:
    """Create a minimal test issue for workflow testing."""
    # GH-API-AUDIT: REST - POST repos/{owner}/{repo}/issues
    result = run_with_error_reporting(
        [
            "gh",
            "api",
            f"repos/{repo_slug}/issues",
            "-X",
            "POST",
            "-f",
            "title=Test workflow run",
            "-f",
            "body=This issue was created to test the erk-impl workflow. Safe to close.",
            "-f",
            "labels[]=test",
            "--jq",
            ".number",
        ],
        error_prefix="Failed to create test issue",
    )
    return int(result.stdout.strip())


def _create_draft_pr(repo_slug: str, branch: str) -> int:
    """Create a draft PR for the test branch."""
    # GH-API-AUDIT: REST - POST repos/{owner}/{repo}/pulls
    result = run_with_error_reporting(
        [
            "gh",
            "api",
            f"repos/{repo_slug}/pulls",
            "-X",
            "POST",
            "-f",
            "title=Test workflow run",
            "-f",
            "body=This PR was created to test the erk-impl workflow. Safe to close.",
            "-f",
            f"head={branch}",
            "-f",
            "base=master",
            "-F",
            "draft=true",
            "--jq",
            ".number",
        ],
        error_prefix="Failed to create draft PR",
    )
    return int(result.stdout.strip())


def _trigger_workflow(
    *,
    repo_slug: str,
    ref: str,
    issue_number: int,
    submitted_by: str,
    distinct_id: str,
    issue_title: str,
    branch_name: str,
    pr_number: int,
    base_branch: str,
) -> None:
    """Trigger the erk-impl workflow with the given parameters."""
    # GH-API-AUDIT: REST - POST actions/workflows/{workflow_id}/dispatches
    run_with_error_reporting(
        [
            "gh",
            "workflow",
            "run",
            "erk-impl.yml",
            "--repo",
            repo_slug,
            "--ref",
            ref,
            "-f",
            f"issue_number={issue_number}",
            "-f",
            f"submitted_by={submitted_by}",
            "-f",
            f"distinct_id={distinct_id}",
            "-f",
            f"issue_title={issue_title}",
            "-f",
            f"branch_name={branch_name}",
            "-f",
            f"pr_number={pr_number}",
            "-f",
            f"base_branch={base_branch}",
        ],
        error_prefix="Failed to trigger erk-impl workflow",
    )


def _get_latest_run_url(repo_slug: str) -> str:
    """Get the URL of the latest erk-impl workflow run."""
    # GH-API-AUDIT: REST - GET actions/runs
    result = run_with_error_reporting(
        [
            "gh",
            "run",
            "list",
            "--repo",
            repo_slug,
            "--workflow",
            "erk-impl.yml",
            "--limit",
            "1",
            "--json",
            "url",
        ],
        error_prefix="Failed to get workflow run URL",
    )
    runs = json.loads(result.stdout)
    if runs:
        return runs[0]["url"]
    return f"https://github.com/{repo_slug}/actions/workflows/erk-impl.yml"
