"""Admin commands for repository configuration."""

import os
import subprocess
from typing import Literal

import click

from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure, UserFacingCliError
from erk.core.context import ErkContext
from erk_shared.gateway.git.remote_ops.types import PushError
from erk_shared.gateway.github.types import GitHubRepoLocation
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
    github_id = Ensure.not_none(
        repo.github,
        "Not a GitHub repository\n"
        "This command requires the repository to have a GitHub remote configured.",
    )

    admin = ctx.github_admin
    location = GitHubRepoLocation(root=repo.root, repo_id=github_id)

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
            raise UserFacingCliError(str(e)) from e

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
            raise UserFacingCliError(str(e)) from e

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
            raise UserFacingCliError(str(e)) from e


@admin_group.command("gh-actions-api-key")
@click.option(
    "--enable",
    "action",
    flag_value="enable",
    help="Set ANTHROPIC_API_KEY secret from GH_ACTIONS_ANTHROPIC_API_KEY env var or interactive prompt",
)
@click.option(
    "--disable",
    "action",
    flag_value="disable",
    help="Delete ANTHROPIC_API_KEY secret from GitHub Actions",
)
@click.pass_obj
def gh_actions_api_key(
    ctx: ErkContext,
    action: Literal["enable", "disable"] | None,
) -> None:
    """Manage ANTHROPIC_API_KEY secret in GitHub Actions.

    Without flags: Check if ANTHROPIC_API_KEY secret exists
    With --enable: Set ANTHROPIC_API_KEY secret from GH_ACTIONS_ANTHROPIC_API_KEY env var
                   (prompts interactively if env var is not set)
    With --disable: Delete ANTHROPIC_API_KEY secret
    """
    repo = discover_repo_context(ctx, ctx.cwd)

    github_id = Ensure.not_none(
        repo.github,
        "Not a GitHub repository\n"
        "This command requires the repository to have a GitHub remote configured.",
    )

    admin = ctx.github_admin
    location = GitHubRepoLocation(root=repo.root, repo_id=github_id)
    github_secret_name = "ANTHROPIC_API_KEY"
    local_env_var = "GH_ACTIONS_ANTHROPIC_API_KEY"

    if action is None:
        exists = admin.secret_exists(location, github_secret_name)
        user_output(click.style("GitHub Actions API Key", bold=True))
        user_output("")
        if exists is True:
            user_output(f"Status: {click.style('Enabled', fg='green')}")
        elif exists is False:
            user_output(f"Status: {click.style('Not found', fg='yellow')}")
        else:
            user_output(f"Status: {click.style('Error checking secret', fg='red')}")

    elif action == "enable":
        secret_value = os.environ.get(local_env_var)
        if secret_value is None:
            secret_value = click.prompt(
                f"{local_env_var} not set. Enter the API key", hide_input=True
            )
        try:
            admin.set_secret(location, github_secret_name, secret_value)
            user_output(
                click.style("✓", fg="green")
                + f" Set {github_secret_name} secret in GitHub Actions"
            )
        except RuntimeError as e:
            raise UserFacingCliError(str(e)) from e

    elif action == "disable":
        try:
            admin.delete_secret(location, github_secret_name)
            user_output(
                click.style("✓", fg="green")
                + f" Deleted {github_secret_name} secret from GitHub Actions"
            )
        except RuntimeError as e:
            raise UserFacingCliError(str(e)) from e


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
    Ensure.invariant(
        erk_dir.exists(),
        f"Not an erk-managed repository\n"
        f"The directory {repo.root} does not contain a .erk directory.\n"
        f"This command only works in repositories initialized with erk.",
    )

    # Update version file
    version_file = erk_dir / "required-erk-uv-tool-version"
    version_file.write_text(f"{current_version}\n", encoding="utf-8")
    user_output(f"Updated required version to {current_version}")

    # Print next steps
    user_output("")
    user_output("Next steps:")
    user_output("  erk artifact sync   # Sync skills, commands, hooks")
    user_output("  erk doctor          # Verify the upgrade")


@admin_group.command("test-plan-implement-gh-workflow")
@click.option("--issue", "-i", type=int, help="Existing issue number to use")
@click.option("--watch", "-w", is_flag=True, help="Watch the workflow run after triggering")
@click.pass_obj
def test_plan_implement_gh_workflow(ctx: ErkContext, issue: int | None, watch: bool) -> None:
    """Test the plan-implement.yml GitHub Actions workflow.

    This command automates testing of plan-implement workflow changes by:

    \b
    1. Ensuring the current branch exists on remote
    2. Finding or creating a test issue
    3. Creating a test branch from master
    4. Adding an empty commit (required for PR creation)
    5. Creating a draft PR
    6. Triggering the workflow with --ref set to your branch
    7. Outputting the run URL

    Use this when modifying .github/workflows/plan-implement.yml to test changes.
    """
    repo = discover_repo_context(ctx, ctx.cwd)

    github_id = Ensure.not_none(repo.github, "Not a GitHub repository")

    # Convert GitHubRepoId to string format for gh CLI
    repo_slug = f"{github_id.owner}/{github_id.repo}"

    current_branch = Ensure.not_none(
        ctx.git.branch.get_current_branch(repo.root),
        "Not on a branch (detached HEAD)",
    )

    # Step 1: Ensure current branch exists on remote
    user_output(f"Ensuring branch '{current_branch}' exists on remote...")
    push_result = ctx.git.remote.push_to_remote(
        repo.root, "origin", current_branch, set_upstream=True, force=False
    )
    if isinstance(push_result, PushError):
        raise UserFacingCliError(push_result.message)
    user_output(click.style("✓", fg="green") + f" Branch '{current_branch}' pushed to origin")

    # Step 2: Find or create test issue
    if issue is not None:
        issue_number = issue
        user_output(f"Using existing issue #{issue_number}")
    else:
        result = ctx.issues.create_issue(
            repo_root=repo.root,
            title="Test workflow run",
            body="This issue was created to test the plan-implement workflow. Safe to close.",
            labels=["test"],
        )
        issue_number = result.number
        user_output(click.style("✓", fg="green") + f" Created test issue #{issue_number}")

    # Step 3: Create test branch for implementation
    timestamp = int(ctx.time.now().timestamp())
    distinct_id = _base36_encode(timestamp)
    test_branch = f"test-workflow-{distinct_id}"

    user_output(f"Creating test branch '{test_branch}'...")
    # Push master to the test branch using refspec syntax
    push_result = ctx.git.remote.push_to_remote(
        repo.root, "origin", f"master:{test_branch}", set_upstream=False, force=False
    )
    if isinstance(push_result, PushError):
        raise UserFacingCliError(push_result.message)
    user_output(click.style("✓", fg="green") + f" Test branch '{test_branch}' created")

    # Step 4: Add an empty commit to the test branch
    # GitHub rejects PRs with no commits between base and head
    user_output(f"Adding initial commit to '{test_branch}'...")
    ctx.git.remote.fetch_branch(repo.root, "origin", test_branch)
    ctx.branch_manager.checkout_branch(repo.root, test_branch)
    ctx.git.commit.commit(repo.root, "Test workflow run")
    push_result = ctx.git.remote.push_to_remote(
        repo.root, "origin", test_branch, set_upstream=False, force=False
    )
    if isinstance(push_result, PushError):
        raise UserFacingCliError(push_result.message)
    ctx.branch_manager.checkout_branch(repo.root, current_branch)
    user_output(click.style("✓", fg="green") + f" Initial commit added to '{test_branch}'")

    # Step 5: Create draft PR
    pr_number = ctx.github.create_pr(
        repo.root,
        branch=test_branch,
        title="Test workflow run",
        body="This PR was created to test the plan-implement workflow. Safe to close.",
        base="master",
        draft=True,
    )
    user_output(click.style("✓", fg="green") + f" Draft PR #{pr_number} created")

    # Step 6: Trigger workflow
    username = Ensure.not_none(
        ctx.issues.get_current_username(),
        "Not authenticated with GitHub",
    )

    user_output(f"Triggering plan-implement workflow from '{current_branch}'...")
    ctx.github.trigger_workflow(
        repo_root=repo.root,
        workflow="plan-implement.yml",
        ref=current_branch,
        inputs={
            "issue_number": str(issue_number),
            "submitted_by": username,
            "distinct_id": distinct_id,
            "issue_title": "Test workflow run",
            "branch_name": test_branch,
            "pr_number": str(pr_number),
            "base_branch": "master",
        },
    )

    # Step 7: Get run URL
    ctx.time.sleep(2)  # Give GitHub a moment to create the run
    runs = ctx.github.list_workflow_runs(repo.root, "plan-implement.yml", limit=1)
    if runs:
        run_url = f"https://github.com/{repo_slug}/actions/runs/{runs[0].run_id}"
    else:
        run_url = f"https://github.com/{repo_slug}/actions/workflows/plan-implement.yml"

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
