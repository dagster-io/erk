"""Format error messages with consistent structure.

This kit CLI command generates standardized error messages with brief description,
details, and suggested actions.

Usage:
    dot-agent kit-command erk format-error \\
        --brief "Brief error description" \\
        --details "Detailed error message" \\
        --action "First action" \\
        --action "Second action"

Output:
    Formatted error message with consistent structure

Exit Codes:
    0: Success

Examples:
    $ dot-agent kit-command erk format-error \\
        --brief "No plan found" \\
        --details "Could not find a valid implementation plan in conversation" \\
        --action "Ensure plan is in conversation" \\
        --action "Plan should have headers and structure"
    ❌ Error: No plan found

    Details: Could not find a valid implementation plan in conversation

    Suggested action:
      1. Ensure plan is in conversation
      2. Plan should have headers and structure
"""

import click


def format_error_message(brief: str, details: str, actions: list[str]) -> str:
    """Generate consistent error message format.

    Args:
        brief: Brief description in 5-10 words
        details: Specific error message or context
        actions: List of 1-3 concrete steps to resolve

    Returns:
        Formatted error message following template

    Raises:
        ValueError: If actions list is empty
    """
    if not actions:
        raise ValueError("At least one action must be provided")

    # Use singular "action" for single action, plural "actions" for multiple
    action_header = "Suggested action:" if len(actions) == 1 else "Suggested actions:"
    error_msg = f"❌ Error: {brief}\n\nDetails: {details}\n\n{action_header}"

    for i, action in enumerate(actions, start=1):
        error_msg += f"\n  {i}. {action}"

    return error_msg


@click.command(name="format-error")
@click.option("--brief", type=str, required=True, help="Brief error description (5-10 words)")
@click.option("--details", type=str, required=True, help="Detailed error message or context")
@click.option(
    "--action",
    "actions",
    type=str,
    multiple=True,
    required=True,
    help="Suggested action (can be repeated)",
)
def format_error(brief: str, details: str, actions: tuple[str, ...]) -> None:
    """Format standardized error message.

    Args:
        brief: Brief error description
        details: Detailed error message
        actions: Tuple of suggested actions (1-3 items)

    Outputs:
        Formatted error message with:
        - Error header with brief description
        - Details section with context
        - Numbered list of suggested actions
    """
    actions_list = list(actions)
    error_message = format_error_message(brief, details, actions_list)
    click.echo(error_message)
