"""Generate PR body footer for remote implementation PRs.

This kit CLI command generates a footer section for PR descriptions that includes
the `erk pr checkout` command. This is used by the GitHub Actions workflow when
creating PRs from remote implementations.

Usage:
    dot-agent run erk get-pr-body-footer --pr-number 123

Output:
    Markdown footer with checkout command

Exit Codes:
    0: Success
    1: Error (missing pr-number)

Examples:
    $ dot-agent run erk get-pr-body-footer --pr-number 1895

    ---

    To checkout this PR in a fresh worktree and environment locally, run:

    ```
    erk pr checkout 1895
    ```

    If using Graphite, the following steps are recommended to track and link the
    branch to Graphite. The `erk` queue uses vanilla git in the remote worker.

    ```
    gt track
    gt squash && gt submit -f
    ```
"""

import click


@click.command(name="get-pr-body-footer")
@click.option("--pr-number", type=int, required=True, help="PR number for checkout command")
def get_pr_body_footer(pr_number: int) -> None:
    """Generate PR body footer with checkout command.

    Outputs a markdown footer section that includes the `erk pr checkout` command,
    allowing users to easily checkout the PR in a fresh worktree locally.

    Includes both Graphite and non-Graphite variants so users can pick the
    appropriate one for their setup.

    Args:
        pr_number: The PR number to include in the checkout command
    """
    output = f"""
---

To checkout this PR in a fresh worktree and environment locally, run:

```
erk pr checkout {pr_number}
```

If using Graphite, the following steps are recommended to track and link the
branch to Graphite. The `erk` queue uses vanilla git in the remote worker.

```
gt track
gt squash && gt submit -f
```
"""
    click.echo(output, nl=False)
