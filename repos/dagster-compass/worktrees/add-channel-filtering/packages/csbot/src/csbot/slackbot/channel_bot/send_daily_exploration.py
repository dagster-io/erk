"""Generic analysis suggestion functionality for CompassChannelBotInstance."""

import json
import random
import time
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, cast

from ddtrace.trace import tracer
from pydantic import BaseModel

from csbot.slackbot.flags import is_dagsterlabs_internal
from csbot.slackbot.memes import (
    get_meme_template_by_filename,
    render_meme,
    select_meme_for_daily_insight,
)
from csbot.slackbot.slackbot_blockkit import MarkdownBlock
from csbot.slackbot.slackbot_slackstream import wait_for_file_ready

if TYPE_CHECKING:
    import structlog

    from csbot.slackbot.channel_bot.bot import CompassChannelBaseBotInstance

TOTAL_IDEAS = 50
IDEAS_TO_ANALYZE = 3


class DailyExplorationIdeas(BaseModel):
    ideas: list[str]


class AnalysisResult(BaseModel):
    selected_idea: str
    summary_of_findings_formatted_as_slack_message: str


@tracer.wrap()
async def send_daily_exploration(bot: "CompassChannelBaseBotInstance", channel: str):
    """Send a daily exploration to the channel.

    Args:
        bot: The bot instance
        channel: Channel to send to
    """

    logger = cast("structlog.BoundLogger", bot.logger).bind(
        channel=channel, task="daily_exploration"
    )
    start_time = time.time()

    logger.info(f"Starting daily exploration for {channel}")
    daily_exploration_ideas = await bot.answer_question_for_background_task(
        dedent(f"""
        given the datasets and context you have available, suggest {TOTAL_IDEAS} analysis ideas
        that would be:
        1. interesting to our key personas (data people, gtm leaders, support leaders, startup
           founders, etc)
        2. show off some data visualization capabilities
        3. timely and actionable
        
        the strings should be phrased as questions that a user might realistically ask
        (as this is for the purposes of learning how the bot works), and should be
        concise and to the point.
    """).strip(),
        4096,
        DailyExplorationIdeas,
    )
    logger.debug(f"Got {len(daily_exploration_ideas.ideas)} daily exploration ideas")

    ideas_to_analyze = random.sample(daily_exploration_ideas.ideas, IDEAS_TO_ANALYZE)

    logger.debug(f"Picked ideas: {repr(ideas_to_analyze)}")

    analysis_result = await bot.answer_question_for_background_task(
        dedent(f"""
i want you to conduct three analyses. based on your results, pick the one that is
1) the most timely and actionable and 2) most interesting for our personas of
data people, startup founders, gtm leaders, support leaders, and sales reps.
Keep in mind that KPIs may have a recency effect (i.e. close rates may vary significantly with age),
and keep in mind that metrics may drop for partial time periods, so don't flag major drops for
days, weeks, or months that have not been fully observed.

for the one that you pick, include a summary of your findings formatted as a slack message we can
share with a group. I also want you to hedge a little bit, like "X may be true", not "X is true" etc.
Your message should follow this format:


:bulb: **compass insight:**
[single sentence headline]
* [detail or follow up action 1]
* [detail or follow up action 2]
* [... etc ...]
details in thread :thread:


the ideas are:
{json.dumps(ideas_to_analyze)}
        """),
        32000,
        AnalysisResult,
    )
    logger.debug(f"Got analysis result. Picked idea: {analysis_result.selected_idea}")

    # Select meme using AI agent
    meme_selection = None
    if is_dagsterlabs_internal(bot):
        meme_selection = await select_meme_for_daily_insight(
            bot.agent, analysis_result.summary_of_findings_formatted_as_slack_message
        )
        logger.debug(f"Meme selection result: meme_id={meme_selection.meme_id}")

    # Generate meme if provided
    meme_file_id = None
    if meme_selection and meme_selection.meme_id and meme_selection.meme_box_name_to_text:
        try:
            meme_template = get_meme_template_by_filename(meme_selection.meme_id)
            if meme_template:
                # Render the meme
                meme_bytes = await render_meme(
                    meme_template,
                    meme_selection.meme_box_name_to_text,
                )

                # Upload to Slack
                meme_filename = Path(meme_selection.meme_id).stem + ".png"
                upload_response = await bot.client.files_upload_v2(
                    filename=f"meme_{meme_filename}",
                    file=meme_bytes,
                )

                if upload_response.get("ok") and upload_response.get("files"):
                    meme_file_id = upload_response["files"][0]["id"]  # type: ignore
                    await wait_for_file_ready(
                        bot.client,
                        meme_file_id,
                        lambda file_info: bool(file_info.get("thumb_64")),
                    )
                    logger.debug(f"Uploaded meme: {meme_selection.meme_id}")
                else:
                    logger.warning(f"Failed to upload meme: {upload_response}")
            else:
                logger.warning(f"Meme template not found: {meme_selection.meme_id}")
        except Exception as e:
            logger.warning(f"Error generating meme: {e}", exc_info=True)

    # Get bot user ID
    bot_user_id = await bot.get_bot_user_id()
    if not bot_user_id:
        raise ValueError("Could not get bot user ID for daily exploration")

    # Build blocks
    blocks = []

    # Add meme image block if we have one
    if meme_file_id and meme_selection:
        from csbot.slackbot.slackbot_blockkit import ImageBlock, SlackFile

        blocks.append(
            ImageBlock(
                slack_file=SlackFile(id=meme_file_id),
                alt_text=f"Meme: {meme_selection.meme_id or 'daily insight meme'}",
            ).to_dict()
        )

    blocks.append(
        MarkdownBlock(
            text=analysis_result.summary_of_findings_formatted_as_slack_message.strip()
        ).to_dict(),
    )

    response = await bot.client.chat_postMessage(
        channel=channel,
        text=analysis_result.summary_of_findings_formatted_as_slack_message.strip(),
        blocks=blocks,
    )

    logger.debug(f"Sent daily exploration to {channel}")

    ts = response.get("ts")
    if not response.get("ok") or not ts:
        raise ValueError(f"Error sending daily insight: {response}")

    # Mark this thread as a daily insight
    await bot.mark_thread_as_daily_insight(channel, ts)

    await bot._handle_new_thread(
        bot_user_id=bot_user_id,
        channel=channel,
        thread_ts=ts,
        user=bot_user_id,
        message_ts=ts,
        message_content=dedent(f"""
        While researching the following question:
        
        {analysis_result.selected_idea}

        Our automated data analysis found the following:
        {analysis_result.summary_of_findings_formatted_as_slack_message}
        
        Please perform the analysis to confirm, and share any additional insights or
context.
        """).strip(),
        collapse_thinking_steps=True,
        is_automated_message=True,
    )

    logger.info(
        f"Completed daily exploration for {channel} in {time.time() - start_time:.2f} seconds"
    )
