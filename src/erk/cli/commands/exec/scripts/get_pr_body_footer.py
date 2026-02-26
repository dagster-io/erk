"""Generate PR body footer for remote implementation PRs.

This exec command generates a footer section for PR descriptions that includes
the `erk pr checkout` command. This is used by the GitHub Actions workflow when
creating PRs from remote implementations.

Usage:
    erk exec get-pr-body-footer --pr-number 123

Output:
    Markdown footer with checkout command

Exit Codes:
    0: Success
    1: Error (missing pr-number)

Examples:
    $ erk exec get-pr-body-footer --pr-number 1895

    ---

    To checkout this PR in a fresh worktree and environment locally, run:

    ```
    source "$(erk pr checkout 1895 --script)" && erk pr sync --dangerous
    ```
"""

import click

from erk_shared.gateway.github.pr_footer import build_pr_body_footer


@click.command(name="get-pr-body-footer")
@click.option("--pr-number", type=int, required=True, help="PR number for checkout command")
def get_pr_body_footer(pr_number: int) -> None:
    """Generate PR body footer with checkout command.

    Outputs a markdown footer section that includes the `erk pr checkout` command,
    allowing users to easily checkout the PR in a fresh worktree locally.

    Args:
        pr_number: The PR number to include in the checkout command
    """
    output = build_pr_body_footer(pr_number)
    click.echo(output, nl=False)
