"""Helper functions for rendering Slack threads as HTML.

This module provides reusable utilities for generating HTML representations of Slack
conversations, used by both the production webapp and test utilities.
"""

import html


def render_user_message_html(
    message: str,
    user_name: str = "User",
    user_icon_html: str | None = None,
) -> str:
    """Render a user message as HTML.

    Args:
        message: The message text
        user_name: Display name of the user
        user_icon_html: Optional custom HTML for user icon. Defaults to user-circle icon.

    Returns:
        HTML string for the user message card
    """
    if user_icon_html is None:
        user_icon_html = """
            <div class="user-avatar flex items-center justify-center text-white text-xl">
                <i class="ph ph-user-circle"></i>
            </div>
        """

    return f"""
<div class="bg-white rounded-lg border border-gray-200 shadow-sm mb-4">
    <div class="flex gap-3 p-4">
        {user_icon_html}
        <div class="flex-1 min-w-0">
            <div class="flex items-baseline gap-2">
                <span class="font-semibold text-gray-900 text-md">{html.escape(user_name)}</span>
            </div>
            <div class="text-gray-900 text-md leading-relaxed -mt-1">{html.escape(message)}</div>
        </div>
    </div>
</div>
"""


def render_bot_message_html(
    content_html: str,
    bot_name: str = "Compass",
    bot_icon_url: str = "/static/logo-square.svg",
) -> str:
    """Render a bot message as HTML.

    Args:
        content_html: The HTML content to display (already escaped/rendered)
        bot_name: Display name of the bot
        bot_icon_url: URL to bot icon image

    Returns:
        HTML string for the bot message card
    """
    return f"""
<div class="bg-white rounded-lg border border-gray-200 shadow-sm mb-4">
    <div class="flex gap-3 p-4">
        <img src="{html.escape(bot_icon_url)}" class="h-9 w-9 flex-shrink-0 rounded-md" alt="{html.escape(bot_name)}">
        <div class="flex-1 min-w-0">
            <div class="flex items-baseline gap-2">
                <span class="font-semibold text-gray-900 text-md">{html.escape(bot_name)}</span>
            </div>
            <div class="text-gray-900 text-md leading-relaxed -mt-1">{content_html}</div>
        </div>
    </div>
</div>
"""


async def render_slack_messages_to_html(
    slack_client,  # AsyncWebClient or compatible client (like FakeSlackClient)
    channel_id: str,
    thread_ts: str,
    *,
    bot_user_id: str | None = None,
) -> str:
    """Render Slack messages from a thread as HTML.

    Args:
        slack_client: Slack API client (AsyncWebClient or compatible)
        channel_id: Channel ID containing the thread
        thread_ts: Thread timestamp (parent message timestamp)
        bot_user_id: Bot user ID to identify bot messages

    Returns:
        HTML string with all messages rendered
    """
    # Get messages in the thread
    response = await slack_client.conversations_replies(
        channel=channel_id,
        ts=thread_ts,
    )

    if not response.get("ok"):
        return "<div class='text-zinc-500 p-4'>Thread not found</div>"

    messages = response.get("messages", [])
    if not messages:
        return "<div class='text-zinc-500 p-4'>No messages found</div>"

    html_parts = []

    for msg in messages:
        user_id = msg.get("user")
        text_content = msg.get("text", "")
        blocks = msg.get("blocks", [])

        # Determine if this is from the bot
        is_bot = user_id == bot_user_id

        # Render blocks if present
        blocks_html = ""
        if blocks:
            blocks_html = '<div class="mt-2 space-y-1">'
            for block in blocks:
                if block.get("type") == "section":
                    block_text = block.get("text", {}).get("text", "")
                    blocks_html += (
                        f'<div class="text-sm text-zinc-800">{html.escape(block_text)}</div>'
                    )
            blocks_html += "</div>"

        # Build message content - combine escaped text with blocks HTML
        escaped_text = html.escape(text_content)
        message_content_html = f"{escaped_text}{blocks_html}"

        # Render as user or bot message
        if is_bot:
            html_parts.append(render_bot_message_html(message_content_html))
        else:
            # For user messages, we need to render with HTML content instead of plain text
            # Create simple user icon
            user_icon_html = f"""
                <div class="w-8 h-8 rounded bg-blue-500 flex items-center justify-center text-white text-xs font-semibold">
                    {html.escape((user_id or "U")[:2].upper())}
                </div>
            """
            # Render directly instead of using render_user_message_html to avoid double-escaping
            html_parts.append(
                f"""
<div class="bg-white rounded-lg border border-gray-200 shadow-sm mb-4">
    <div class="flex gap-3 p-4">
        {user_icon_html}
        <div class="flex-1 min-w-0">
            <div class="flex items-baseline gap-2">
                <span class="font-semibold text-gray-900 text-md">{html.escape(user_id or "Unknown")}</span>
            </div>
            <div class="text-gray-900 text-md leading-relaxed -mt-1">{message_content_html}</div>
        </div>
    </div>
</div>
"""
            )

    return "".join(html_parts)
