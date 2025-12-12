"""Format success output for GitHub issue creation.

This kit CLI command generates standardized markdown output for successful
issue creation with next steps and JSON metadata.

Usage:
    erk kit exec erk format-success-output --issue-number N --issue-url URL

Output:
    Formatted markdown with success message, commands, and JSON metadata

Exit Codes:
    0: Success

Examples:
    $ erk kit exec erk format-success-output \\
        --issue-number 123 \\
        --issue-url https://github.com/org/repo/issues/123
    ✅ GitHub issue created: #123
    https://github.com/org/repo/issues/123

    Next steps:

    View Issue: gh issue view 123 --web
    Interactive: erk implement 123
    Dangerous Interactive: erk implement 123 --dangerous
    Dangerous, Non-Interactive, Auto-Submit: erk implement 123 --yolo
    Submit to Queue: erk submit 123
      # Or use: /erk:submit-plan

    ---

    {"issue_number": 123, "issue_url": "https://github.com/org/repo/issues/123",
     "status": "created"}
"""

import json

import click

from erk_shared.output.next_steps import format_next_steps_plain


@click.command(name="format-success-output")
@click.option("--issue-number", type=int, required=True, help="GitHub issue number")
@click.option("--issue-url", type=str, required=True, help="Full GitHub issue URL")
def format_success_output(issue_number: int, issue_url: str) -> None:
    """Format standardized success output for issue creation.

    Args:
        issue_number: The GitHub issue number
        issue_url: The full URL to the GitHub issue

    Outputs:
        Formatted markdown with:
        - Success header with issue number and URL
        - Next steps section with commands
        - JSON metadata footer
    """
    # Generate formatted output
    output = f"""✅ GitHub issue created: #{issue_number}
{issue_url}

{format_next_steps_plain(issue_number)}

---

{json.dumps({"issue_number": issue_number, "issue_url": issue_url, "status": "created"})}"""

    click.echo(output)
