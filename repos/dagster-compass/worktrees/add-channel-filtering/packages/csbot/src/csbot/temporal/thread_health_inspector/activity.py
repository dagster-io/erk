"""Temporal activity for inspecting thread health."""

import json
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel
from temporalio import activity, workflow

from csbot.agents.messages import AgentTextMessage
from csbot.temporal import constants

if TYPE_CHECKING:
    from csbot.agents.protocol import AsyncAgent
    from csbot.slackbot.storage.interface import SlackbotStorage

with workflow.unsafe.imports_passed_through():
    from libhoney import Client as HoneycombClient

    from csbot.slackbot.slackbot_core import ThreadHealthHoneycombLogging
    from csbot.slackbot.slackbot_ui import SlackThread


class ThreadHealthInspectorInput(BaseModel):
    """Input for thread health inspector activity."""

    governance_bot_id: str
    channel_id: str
    thread_ts: str


class ThreadHealthScore(BaseModel):
    """AI-generated health score for a thread conversation."""

    accuracy: int  # 1-10 scale
    responsiveness: int  # 1-10 scale
    helpfulness: int  # 1-10 scale
    reasoning: str  # Explanation of the scores
    failure_occurred: bool


class ThreadHealthInspectorSuccess(BaseModel):
    """Success result from thread health inspector."""

    type: Literal["success"] = "success"

    score: ThreadHealthScore
    event_count: int
    tokens_consumed: int


class ThreadHealthEmptyThread(BaseModel):
    type: Literal["empty_thread"] = "empty_thread"


ThreadHealthInspectorResult = ThreadHealthInspectorSuccess | ThreadHealthEmptyThread


def _create_honeycomb_client(config: ThreadHealthHoneycombLogging):
    return HoneycombClient(
        writekey=config.api_key,
        dataset=config.dataset,
    )


def _build_transcript_from_events(events: list) -> str:
    """Build a transcript string from thread events.

    Args:
        events: List of AgentMessage events from the thread

    Returns:
        Formatted transcript string
    """
    transcript_lines = []
    for i, event in enumerate(events, 1):
        role = event.role
        transcript_lines.append(f"[Event {i} - Role: {role}]")

        # Extract text content from content blocks
        if isinstance(event.content, list):
            for block in event.content:
                if isinstance(block, dict):
                    block_type = block.get("type")
                    if block_type == "text":
                        text = block.get("text", "")
                        transcript_lines.append(f"  Text: {text}")
                    elif block_type == "tool_use":
                        tool_name = block.get("name", "unknown")
                        tool_input = block.get("input", {})
                        transcript_lines.append(
                            f"  Tool Use: {tool_name} - {json.dumps(tool_input)}"
                        )
                    elif block_type == "tool_result":
                        tool_use_id = block.get("tool_use_id", "unknown")
                        content = block.get("content", "")
                        transcript_lines.append(f"  Tool Result [{tool_use_id}]: {content}")
                else:
                    transcript_lines.append(f"  {block}")
        else:
            transcript_lines.append(f"  Content: {event.content}")

        transcript_lines.append("")  # Blank line between events

    return "\n".join(transcript_lines)


def _get_evaluation_system_prompt() -> str:
    """Get the system prompt for AI evaluation.

    Returns:
        System prompt string
    """
    return """You are evaluating a conversation between a Slack bot and users. The bot is designed to help answer data-related questions.

You will receive a transcript of the conversation. Please rate the bot's performance on the following criteria (1-10 scale), but do not include any information whatsoever about the content of the message, just the performance:

1. **Accuracy**: How accurate and correct were the bot's responses?
2. **Responsiveness**: How well did the bot maintain conversation flow? Low scores if bot stopped responding, needed prompting to continue, or had long gaps.
3. **Helpfulness**: How helpful was the bot in addressing the user's needs?
4. **Failure Occurred**: Whether or not an explicit failure occurred during processing. Either the bot stopped reacting or some other system failure. 

Return your evaluation as JSON in this exact format:
{
  "accuracy": <number 1-10>,
  "responsiveness": <number 1-10>,
  "helpfulness": <number 1-10>,
  "reasoning": "<explanation of your scores>",
  "failure_occurred": <bool>
}"""


def _parse_evaluation_response(response_text: str) -> ThreadHealthScore:
    """Parse AI evaluation response into ThreadHealthScore.

    Args:
        response_text: Raw text response from AI

    Returns:
        Parsed ThreadHealthScore

    Raises:
        json.JSONDecodeError: If response cannot be parsed
        KeyError: If required fields are missing
    """
    # Try to extract JSON from markdown code blocks if present
    if "```json" in response_text:
        json_start = response_text.find("```json") + 7
        json_end = response_text.find("```", json_start)
        json_text = response_text[json_start:json_end].strip()
    elif "```" in response_text:
        json_start = response_text.find("```") + 3
        json_end = response_text.find("```", json_start)
        json_text = response_text[json_start:json_end].strip()
    else:
        json_text = response_text.strip()

    score_data = json.loads(json_text)
    return ThreadHealthScore(
        accuracy=score_data["accuracy"],
        responsiveness=score_data["responsiveness"],
        helpfulness=score_data["helpfulness"],
        reasoning=score_data["reasoning"],
        failure_occurred=score_data["failure_occurred"],
    )


class ThreadHealthInspectorActivity:
    """Activity that inspects thread health using AI evaluation."""

    def __init__(
        self,
        slackbot_storage: "SlackbotStorage",
        agent: "AsyncAgent",
        honeycomb_config: ThreadHealthHoneycombLogging | None,
    ):
        """Initialize with SlackbotStorage and AsyncAgent.

        Args:
            slackbot_storage: Storage instance for accessing bot data
            agent: AsyncAgent for AI evaluation
        """
        self.slackbot_storage = slackbot_storage
        self.agent = agent
        self.honeycomb_client = (
            None if not honeycomb_config else _create_honeycomb_client(honeycomb_config)
        )

    @activity.defn(name=constants.Activity.INSPECT_THREAD_HEALTH_ACTIVITY_NAME.value)
    async def inspect_thread_health(
        self, args: ThreadHealthInspectorInput
    ) -> ThreadHealthInspectorResult:
        """Inspect thread health and rate the conversation quality.

        Args:
            args: Input containing governance_bot_id, channel_id, thread_ts

        Returns:
            ThreadHealthInspectorResult with AI-generated scores
        """
        governance_bot_id = args.governance_bot_id
        channel_id = args.channel_id
        thread_ts = args.thread_ts

        activity.logger.info(
            f"Inspecting thread health for bot={governance_bot_id}, "
            f"channel={channel_id}, thread={thread_ts}"
        )

        # Get instance storage for this bot
        instance_storage = self.slackbot_storage.for_instance(governance_bot_id)

        # Create SlackThread to load events
        # Note: slack_client is not needed for just reading events
        slack_thread = SlackThread(
            kv_store=instance_storage,
            bot_id=governance_bot_id,
            channel=channel_id,
            thread_ts=thread_ts,
        )

        # Get all events from the thread
        events = await slack_thread.get_events()

        if not events:
            activity.logger.warning(f"No events found for thread {thread_ts}")
            # Return default scores for empty thread
            return ThreadHealthEmptyThread()

        activity.logger.info(f"Found {len(events)} events in thread")

        # Build transcript from events
        transcript = _build_transcript_from_events(events)

        # Use AsyncAgent to evaluate thread
        activity.logger.info("Submitting transcript to AI for evaluation")

        system_prompt = _get_evaluation_system_prompt()
        user_message = f"TRANSCRIPT:\n{transcript}"

        # Use create_completion_with_tokens to track token usage
        response_text, tokens_consumed = await self.agent.create_completion_with_tokens(  # type: ignore
            model=self.agent.model,
            system=system_prompt,
            messages=[AgentTextMessage(role="user", content=user_message)],
            max_tokens=1024,
        )

        activity.logger.info(
            f"AI evaluation response: {response_text}, tokens_consumed={tokens_consumed}"
        )

        # Parse response into score
        try:
            score = _parse_evaluation_response(response_text)
        except:
            activity.logger.exception(
                f"Parsing evaluation response failed. Got text: {response_text}"
            )
            raise

        activity.logger.info(
            f"Thread health scores: accuracy={score.accuracy}, "
            f"responsiveness={score.responsiveness}, helpfulness={score.helpfulness}, "
            f"tokens_consumed={tokens_consumed}"
        )

        if self.honeycomb_client is not None:
            try:
                self._log_result_to_honeycomb(self.honeycomb_client, args, score)
            except Exception:
                activity.logger.exception("Failed sending thread score to honeycomb. Continuing")

        return ThreadHealthInspectorSuccess(
            score=score, event_count=len(events), tokens_consumed=tokens_consumed
        )

    def _log_result_to_honeycomb(
        self, client: HoneycombClient, input: ThreadHealthInspectorInput, score: ThreadHealthScore
    ):
        ev = client.new_event()
        ev.add(
            {
                **input.model_dump(),
                **score.model_dump(),
            }
        )
        ev.send()
