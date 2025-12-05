"""Generate PR body footer for remote implementation PRs.

This kit CLI command generates a footer section for PR descriptions that includes
the `erk pr checkout` command. This is used by the GitHub Actions workflow when
creating PRs from remote implementations.

Usage:
    dot-agent run erk get-pr-body-footer --pr-number 123
    dot-agent run erk get-pr-body-footer --pr-number 123 --issue-number 456

Output:
    Markdown footer with checkout command and optional issue closing reference

Exit Codes:
    0: Success
    1: Error (missing pr-number)

Examples:
    $ dot-agent run erk get-pr-body-footer --pr-number 1895

    ---

    To checkout this PR in a fresh worktree and environment locally, run:

    ```
    erk pr checkout 1895 && erk pr sync
    ```

    $ dot-agent run erk get-pr-body-footer --pr-number 1895 --issue-number 123

    ---

    Closes #123

    To checkout this PR in a fresh worktree and environment locally, run:

    ```
    erk pr checkout 1895 && erk pr sync
    ```
"""

import click


@click.command(name="get-pr-body-footer")
@click.option("--pr-number", type=int, required=True, help="PR number for checkout command")
@click.option("--issue-number", type=int, required=False, help="Issue number to close")
def get_pr_body_footer(pr_number: int, issue_number: int | None) -> None:
    """Generate PR body footer with checkout command.

    Outputs a markdown footer section that includes the `erk pr checkout` command,
    allowing users to easily checkout the PR in a fresh worktree locally.

    When issue_number is provided, includes "Closes #N" to auto-close the issue
    when the PR is merged.

    Args:
        pr_number: The PR number to include in the checkout command
        issue_number: Optional issue number to close when PR is merged
    """
    parts: list[str] = []
    parts.append("\n---\n")

    if issue_number is not None:
        parts.append(f"\nCloses #{issue_number}\n")

    parts.append(
        f"\nTo checkout this PR in a fresh worktree and environment locally, run:\n\n"
        f"```\n"
        f"erk pr checkout {pr_number} && erk pr sync\n"
        f"```\n"
    )

    output = "\n".join(parts)
    click.echo(output, nl=False)
