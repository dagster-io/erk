"""PR landing command using Graphite workflow."""

import click

from csbot.compass_dev.land_pr_logic import execute_pr_landing


@click.command()
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what operations would be performed without executing them",
)
def land_pr(dry_run: bool):
    """Land a pull request using Graphite workflow automation.

    Automates the complete PR landing workflow using Graphite (gt) and GitHub CLI (gh).
    Handles both single PR and multi-PR stack scenarios with robust conflict resolution.

    **Workflow Steps:**

    1. **Pre-flight Checks**
       - Verify current branch has an open PR
       - Ensure branch is tracked by Graphite
       - Confirm not already on trunk/main

    2. **Pre-merge Restack**
       - Execute `gt restack` to update stack before merge
       - Handle merge conflicts with user guidance
       - Provide clear resolution instructions

    3. **Merge PR**
       - Execute `gh pr merge -s` (squash merge)
       - Use enhanced commit message with PR title and description

    4. **Sync with Graphite**
       - Execute `gt sync` to detect merged PRs
       - Automatically delete merged branches
       - Eliminate race conditions between GitHub and Graphite

    5. **Handle Stack Continuation**
       - Single PR: lands on main/master (workflow complete)
       - Multi-PR stack: lands on next PR branch, performs final restack

    **Prerequisites:**
    - Graphite CLI (`gt`) installed and configured
    - GitHub CLI (`gh`) installed and authenticated
    - Current branch has an associated open PR
    - Branch is tracked by Graphite (`gt branch track`)

    **Conflict Resolution:**
    When merge conflicts occur during restack:
    1. Script pauses with clear instructions
    2. Resolve conflicts manually in your editor
    3. Run: `git add . && git rebase --continue`
    4. Re-run this command to continue landing

    **Error Scenarios Handled:**
    - No PR on current branch
    - PR already merged/closed
    - Merge conflicts during pre-merge restack
    - Branch not tracked by Graphite
    - Network/API failures

    **GitHub Alias Setup:**
    Create a GitHub alias for convenience:
    `gh alias set land '!compass-dev land-pr'`

    Then use: `gh land` from any branch with a PR.
    """
    if dry_run:
        click.echo(
            "Dry run mode would perform the following operations:\n\n"
            "🔍 Pre-flight checks:\n"
            "  - Verify current branch has an open PR (gh pr view)\n"
            "  - Check branch is tracked by Graphite (gt branch info)\n"
            "  - Ensure not on trunk branch (main/master)\n\n"
            "🔄 Pre-merge restack:\n"
            "  - Run `gt restack` to update stack\n"
            "  - Handle potential merge conflicts\n\n"
            "🚀 Merge PR:\n"
            "  - Execute `gh pr merge -s` with enhanced commit message\n"
            "  - Include PR title and description in squash commit\n\n"
            "🔄 Sync with Graphite:\n"
            "  - Run `gt sync -f --no-restack --no-interactive`\n"
            "  - Auto-delete merged branch\n\n"
            "🎯 Finalize:\n"
            "  - If single PR: complete on main/master\n"
            "  - If multi-PR stack: restack remaining PRs\n\n"
            "No actual changes would be made to branches or PRs."
        )
        return

    success = execute_pr_landing(dry_run=dry_run)

    if success:
        if not dry_run:
            click.echo("✅ PR landing completed successfully!")
    else:
        click.echo("❌ PR landing failed. Check the output above for details.")
        click.echo("\n💡 Common solutions:")
        click.echo("  - Ensure you have an open PR on the current branch")
        click.echo("  - Run `gt branch track` if branch is not tracked by Graphite")
        click.echo("  - Resolve any merge conflicts and re-run the command")
        click.echo("  - Check that `gh` and `gt` CLIs are installed and authenticated")
        raise click.ClickException("PR landing failed")
