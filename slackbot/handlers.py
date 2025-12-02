"""Slack command handlers for Erk integration."""

import re

from slack_bolt.async_app import AsyncApp

from slackbot.erk_service import ErkService


def register_handlers(app: AsyncApp, erk: ErkService) -> None:
    """Register slash command and event handlers with the Slack app.

    Args:
        app: Slack Bolt AsyncApp instance
        erk: ErkService instance for Erk operations
    """

    # =========================================================================
    # Slash Commands
    # =========================================================================

    @app.command("/erk-plan")
    async def handle_plan(ack, command, respond) -> None:  # type: ignore[no-untyped-def]
        """Handle /erk-plan command to create a plan from the message text.

        Usage: /erk-plan <plan content>
        """
        await ack()

        text = command.get("text", "").strip()
        if not text:
            await respond(
                "Please provide plan content.\n\n"
                "Usage: `/erk-plan <plan content>`\n\n"
                "Example:\n```\n/erk-plan # My Feature\n\n"
                "## Goal\nImplement a new feature\n\n"
                "## Steps\n1. Do this\n2. Do that\n```"
            )
            return

        try:
            result = erk.create_plan(text)
            await respond(
                f"Plan created successfully!\n\n"
                f"*Issue:* <{result.url}|#{result.issue_number}>\n"
                f"*Title:* {result.title}\n\n"
                f"Next steps:\n"
                f"- View: `erk get {result.issue_number}`\n"
                f"- Implement: `erk implement {result.issue_number}`\n"
                f"- Submit: `/erk-submit {result.issue_number}`"
            )
        except ValueError as e:
            await respond(f"Failed to create plan: {e}")
        except RuntimeError as e:
            await respond(f"Error communicating with GitHub: {e}")

    @app.command("/erk-submit")
    async def handle_submit(ack, command, respond) -> None:  # type: ignore[no-untyped-def]
        """Handle /erk-submit command to submit a plan to the queue.

        Usage: /erk-submit <issue_number>
        """
        await ack()

        text = command.get("text", "").strip()
        if not text:
            await respond(
                "Please provide an issue number.\n\n"
                "Usage: `/erk-submit <issue_number>`\n\n"
                "Example: `/erk-submit 123`"
            )
            return

        # Parse issue number
        if not text.isdigit():
            await respond(f"Invalid issue number: `{text}`\n\nPlease provide a valid number.")
            return

        issue_number = int(text)

        # Get submitter from Slack user info
        user_id = command.get("user_id", "unknown")
        user_name = command.get("user_name", user_id)

        try:
            result = erk.submit_to_queue(issue_number, submitted_by=user_name)
            await respond(
                f"Plan #{issue_number} submitted to queue!\n\n"
                f"*Workflow run:* <{result.workflow_url}|View run>\n\n"
                f"The implementation will start shortly."
            )
        except ValueError as e:
            await respond(f"Failed to submit plan: {e}")
        except RuntimeError as e:
            await respond(f"Error communicating with GitHub: {e}")

    @app.command("/erk-plans")
    async def handle_plans(ack, respond) -> None:  # type: ignore[no-untyped-def]
        """Handle /erk-plans command to list open plans.

        Usage: /erk-plans
        """
        await ack()

        try:
            plans = erk.list_plans(limit=20)

            if not plans:
                await respond("No open plans found.")
                return

            lines = ["*Open Plans:*\n"]
            for plan in plans:
                # Format created_at as relative time
                lines.append(f"- <{plan.url}|#{plan.number}>: {plan.title}")

            await respond("\n".join(lines))
        except RuntimeError as e:
            await respond(f"Error fetching plans: {e}")

    # =========================================================================
    # Event Handlers (DMs and @mentions)
    # =========================================================================

    async def process_message(text: str, user_name: str, say) -> None:  # type: ignore[no-untyped-def]
        """Process a message and execute the appropriate command.

        Supports:
        - plan: <content> or plan <content> - Create a plan
        - submit: <number> or submit <number> - Submit a plan
        - list, plans, or help - List plans or show help

        Args:
            text: Message text (with bot mention stripped if applicable)
            user_name: Slack username for attribution
            say: Function to send response
        """
        text = text.strip()
        text_lower = text.lower()

        # Help command
        if text_lower in ("help", "hi", "hello"):
            await say(
                "*Erk Bot Commands*\n\n"
                "You can use these commands in DMs or by @mentioning me:\n\n"
                "• `plan: <content>` - Create a new plan\n"
                "• `submit: <issue_number>` - Submit a plan to the queue\n"
                "• `list` or `plans` - List open plans\n"
                "• `help` - Show this message\n\n"
                "Or use slash commands:\n"
                "• `/erk-plan <content>`\n"
                "• `/erk-submit <number>`\n"
                "• `/erk-plans`"
            )
            return

        # List plans command
        if text_lower in ("list", "plans", "list plans"):
            try:
                plans = erk.list_plans(limit=20)
                if not plans:
                    await say("No open plans found.")
                    return

                lines = ["*Open Plans:*\n"]
                for plan in plans:
                    lines.append(f"• <{plan.url}|#{plan.number}>: {plan.title}")
                await say("\n".join(lines))
            except RuntimeError as e:
                await say(f"Error fetching plans: {e}")
            return

        # Submit command: "submit: 123" or "submit 123"
        submit_match = re.match(r"^submit[:\s]+(\d+)\s*$", text_lower)
        if submit_match:
            issue_number = int(submit_match.group(1))
            try:
                result = erk.submit_to_queue(issue_number, submitted_by=user_name)
                await say(
                    f"Plan #{issue_number} submitted to queue!\n\n"
                    f"*Workflow run:* <{result.workflow_url}|View run>\n\n"
                    f"The implementation will start shortly."
                )
            except ValueError as e:
                await say(f"Failed to submit plan: {e}")
            except RuntimeError as e:
                await say(f"Error communicating with GitHub: {e}")
            return

        # Plan command: "plan: <content>" or "plan <content>"
        plan_match = re.match(r"^plan[:\s]+(.+)$", text, re.DOTALL | re.IGNORECASE)
        if plan_match:
            plan_content = plan_match.group(1).strip()
            if not plan_content:
                await say("Please provide plan content after `plan:`")
                return

            try:
                result = erk.create_plan(plan_content)
                await say(
                    f"Plan created successfully!\n\n"
                    f"*Issue:* <{result.url}|#{result.issue_number}>\n"
                    f"*Title:* {result.title}\n\n"
                    f"Next steps:\n"
                    f"• `submit: {result.issue_number}` - Submit to queue\n"
                    f"• View: {result.url}"
                )
            except ValueError as e:
                await say(f"Failed to create plan: {e}")
            except RuntimeError as e:
                await say(f"Error communicating with GitHub: {e}")
            return

        # Unrecognized command
        await say(
            "I didn't understand that. Try `help` to see available commands.\n\n"
            "Quick examples:\n"
            "• `plan: # My Feature\\n\\n## Goal\\nDo something`\n"
            "• `submit: 123`\n"
            "• `list`"
        )

    @app.event("message")
    async def handle_dm(event, say) -> None:  # type: ignore[no-untyped-def]
        """Handle direct messages to the bot.

        Triggered when someone sends a DM to the bot.
        """
        # Ignore bot messages to prevent loops
        if event.get("bot_id"):
            return

        # Only handle DMs (channel type "im")
        if event.get("channel_type") != "im":
            return

        text = event.get("text", "")
        user_name = event.get("user", "unknown")

        await process_message(text, user_name, say)

    @app.event("app_mention")
    async def handle_mention(event, say) -> None:  # type: ignore[no-untyped-def]
        """Handle @mentions of the bot in channels.

        Triggered when someone @mentions the bot in a channel.
        """
        text = event.get("text", "")
        user_name = event.get("user", "unknown")

        # Strip the bot mention from the beginning of the message
        # Format: <@U12345678> rest of message
        text = re.sub(r"^<@[A-Z0-9]+>\s*", "", text)

        await process_message(text, user_name, say)
