from csbot.slackbot.webapp.htmlstring import HtmlString


async def get_unauthorized_message() -> HtmlString:
    return HtmlString.from_template(
        """
        Your session has expired. Please return to your Slack governance channel and run <tt>@Compass!admin</tt> to start over.
        """
    )
