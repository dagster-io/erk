"""
Utility functions for Slack bot operations.
"""

import json
from typing import NamedTuple

import aiohttp


class ParsedIssueOrPRBody(NamedTuple):
    """Parsed GitHub issue or PR body with extracted attribution information."""

    cleaned_body: str
    opened_by: str | None
    slack_message_url: str | None
    created_date: str | None


def parse_issue_or_pr_body(raw_body: str) -> ParsedIssueOrPRBody:
    """
    Parse GitHub issue or PR body to extract metadata from HTML comment and clean the body.

    Returns ParsedIssueOrPRBody with:
    - cleaned_body: body starting from first header after attribution
    - opened_by: name extracted from JSON metadata (or None)
    - slack_message_url: URL extracted from JSON metadata (or None)
    - created_date: date extracted from JSON metadata (or None)
    """
    if not raw_body:
        return ParsedIssueOrPRBody(
            cleaned_body="",
            opened_by=None,
            slack_message_url=None,
            created_date=None,
        )

    lines = raw_body.split("\n")
    opened_by = None
    slack_message_url = None
    created_date = None
    found_attribution = False

    # First pass: extract metadata from the first HTML comment
    for line in lines:
        if line.strip().startswith("<!--") and line.strip().endswith("-->"):
            try:
                # Extract JSON from comment
                comment_content = line.strip()[4:-3].strip()  # Remove <!-- and -->
                metadata = json.loads(comment_content)

                # Extract attribution data from JSON (only from the first attribution found)
                if metadata.get("action") == "Created" and not found_attribution:
                    display_name = metadata.get("display_name")
                    # Strip markdown formatting from display names (for backwards compatibility)
                    opened_by = display_name.strip("*").strip() if display_name else None
                    created_date = metadata.get("timestamp")
                    slack_message_url = metadata.get("slack_link")
                    found_attribution = True
                    break
            except (json.JSONDecodeError, KeyError):
                # If JSON parsing fails, continue looking
                continue

    # Second pass: find the first header after attribution and include everything from there
    if found_attribution:
        header_index = next(
            (
                i + 1
                for i, line in enumerate(lines)
                if line.strip().startswith("#") or line.strip().startswith("---")
            ),
            0,
        )
        cleaned_body = "\n".join(lines[header_index:]).strip()

    else:
        # No attribution found, return the original body
        cleaned_body = raw_body.strip()

    return ParsedIssueOrPRBody(
        cleaned_body=cleaned_body,
        opened_by=opened_by,
        slack_message_url=slack_message_url,
        created_date=created_date,
    )


def format_attribution(
    action: str, display_name: str, timestamp: str, permalink: str | None = None
) -> str:
    """
    Format attribution string for GitHub issues/PRs.

    This is the core formatting logic extracted from CompassChannelBotInstance._create_attribution()
    to be reusable in tests and other contexts.

    Args:
        action: The action being performed (e.g., "Created", "Updated", "Deleted")
        display_name: User display name
        timestamp: Formatted timestamp string
        permalink: Optional Slack message permalink URL

    Returns:
        Formatted attribution string with HTML commented metadata
    """
    # Create metadata object
    metadata = {
        "action": action,
        "display_name": display_name,
        "timestamp": timestamp,
        "slack_link": permalink,
    }

    # Create HTML commented JSON blob
    json_metadata = json.dumps(metadata, separators=(",", ":"))
    html_comment = f"<!-- {json_metadata} -->"

    # Create the visible attribution text
    if permalink:
        attribution_text = (
            f"**{action} by:** {display_name} on {timestamp} ([Slack message]({permalink}))"
        )
    else:
        attribution_text = f"**{action} by:** {display_name} on {timestamp}"

    # Combine HTML comment with attribution text
    return f"{html_comment}\n\n{attribution_text}"


async def send_ephemeral_message(response_url: str, message: str) -> None:
    """
    Send an ephemeral message using a Slack response URL.

    Args:
        response_url: The Slack response URL from the payload
        message: The message text to send
    """
    async with aiohttp.ClientSession() as session:
        await session.post(response_url, json={"response_type": "ephemeral", "text": message})
