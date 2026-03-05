"""Generate PR body footer for remote implementation PRs.

This exec command generates a footer section for PR descriptions that includes
the `erk pr teleport` command. This is used by the GitHub Actions workflow when
creating PRs from remote implementations.

Usage:
    erk exec get-pr-body-footer --pr-number 123

Output:
    Markdown footer with teleport command

Exit Codes:
    0: Success
    1: Error (missing pr-number)

Examples:
    $ erk exec get-pr-body-footer --pr-number 1895

    ---

    To replicate this PR locally, run:

    ```
    erk pr teleport 1895
    ```
"""

import click

from erk_shared.gateway.github.pr_footer import build_pr_body_footer


@click.command(name="get-pr-body-footer")
@click.option("--pr-number", type=int, required=True, help="PR number for checkout command")
def get_pr_body_footer(pr_number: int) -> None:
    """Generate PR body footer with teleport command.

    Outputs a markdown footer section that includes the `erk pr teleport` command,
    allowing users to easily replicate the PR locally.

    Args:
        pr_number: The PR number to include in the checkout command
    """
    output = build_pr_body_footer(pr_number)
    click.echo(output, nl=False)
