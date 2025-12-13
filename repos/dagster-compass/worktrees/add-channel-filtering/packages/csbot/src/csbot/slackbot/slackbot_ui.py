import base64
import json
import re
from abc import ABC, abstractmethod
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import (
    Any,
    cast,
)

import structlog

from csbot.agents.messages import (
    AgentBlockDelta,
    AgentContentBlock,
    AgentInputJSONDelta,
    AgentMessage,
    AgentModelSpecificMessage,
    AgentTextBlock,
    AgentTextDelta,
    AgentToolUseBlock,
)
from csbot.slackbot.slackbot_blockkit import (
    ActionsBlock,
    Block,
    ButtonElement,
    ImageBlock,
    MarkdownBlock,
    SectionBlock,
    SlackFile,
    TextObject,
    TextType,
)
from csbot.slackbot.slackbot_dataviz import ChartConfig, ChartType, DataVizDSL
from csbot.slackbot.slackbot_slackstream import CsvAttachment, ImageAttachment, SlackstreamReply
from csbot.slackbot.storage.interface import SlackbotInstanceStorage
from csbot.slackbot.webapp.htmlstring import HtmlString
from csbot.utils.sync_to_async import sync_to_async

logger = structlog.get_logger(__name__)

# Context variables to access bot configuration in UI components
scaffold_branch_enabled: ContextVar[bool] = ContextVar("scaffold_branch_enabled", default=False)
data_request_ticket_url: ContextVar[str | None] = ContextVar(
    "data_request_ticket_url", default=None
)
context_update_review_url: ContextVar[str | None] = ContextVar(
    "context_update_review_url", default=None
)


# Helper functions for consistent UI components
def create_info_block_html(emoji: str, message: str, border_color: str = "blue") -> HtmlString:
    """Create a consistent info block with emoji and message."""
    return HtmlString.from_template(
        """
        <div class="flex items-start gap-2 mb-3 p-3 bg-zinc-50 border-l-4 border-{border_color}-300 rounded-r">
            <span class="text-lg -mt-1">{emoji}</span>
            <div class="text-sm text-zinc-700">{message}</div>
        </div>
        """,
        emoji=emoji,
        message=message,
        border_color=border_color,
    )


def create_markdown_block_text(emoji: str, message: str) -> str:
    """Create consistent markdown text for Slack blocks."""
    return f">{emoji}  *{message}*"


def create_aggregate_text(emoji: str, action: str, count: int) -> str:
    """Create consistent aggregate text for multiple actions."""
    if count == 1:
        return f"{emoji} *{action}*"
    else:
        return f"{emoji} *{action} {count} times*"


def create_complex_info_block_html(
    emoji: str, title: str, subtitle: str = "", border_color: str = "blue"
) -> HtmlString:
    """Create an info block with title and optional subtitle."""
    subtitle_html = f'<div class="text-xs text-zinc-600">{subtitle}</div>' if subtitle else ""
    return HtmlString.from_template(
        """
        <div class="flex items-start gap-2 mb-3 p-3 bg-zinc-50 border-l-4 border-{border_color}-300 rounded-r">
            <span class="text-lg -mt-1">{emoji}</span>
            <div class="flex-1">
                <div class="text-sm text-zinc-700 mb-1">{title}</div>
                {subtitle_html}
            </div>
        </div>
        """,
        emoji=emoji,
        title=title,
        subtitle_html=subtitle_html,
        border_color=border_color,
    )


class SlackThread:
    def __init__(
        self,
        kv_store: SlackbotInstanceStorage,
        bot_id: str,
        channel: str,
        thread_ts: str,
        timeout_seconds: int = 90 * 24 * 60 * 60,
    ):
        self.kv_store = kv_store
        self.bot_id = bot_id
        self.channel = channel
        self.thread_ts = thread_ts
        self.timeout_seconds = timeout_seconds

    async def try_lock(self, timeout_seconds: int = 5 * 60) -> bool:
        # yes i know there is a slight race condition here, but it's okay
        locked_at_iso8601 = await self.kv_store.get(
            "slack_thread_locked_at",
            self._cache_key,
        )
        is_locked = (
            locked_at_iso8601 is not None
            and datetime.fromisoformat(locked_at_iso8601) + timedelta(seconds=timeout_seconds)
            > datetime.now()
        )
        if is_locked:
            return False

        await self.kv_store.set(
            "slack_thread_locked_at",
            self._cache_key,
            datetime.now().isoformat(),
            expiry_seconds=self.timeout_seconds,
        )
        return True

    async def unlock(self):
        await self.kv_store.delete(
            "slack_thread_locked_at",
            self._cache_key,
        )

    @property
    def _cache_key(self) -> str:
        return f"{self.channel}:{self.thread_ts}"

    @property
    def _cache_family(self) -> str:
        return "slack_thread_events"

    async def get_events(self) -> list[AgentMessage]:
        # First, check if we have this thread cached
        cached_events = await self.kv_store.get(self._cache_family, self._cache_key)
        if cached_events:
            return [
                AgentModelSpecificMessage(role=event["role"], content=event["content"])
                for event in json.loads(cached_events)
            ]
        else:
            return []

    async def add_event(self, event: AgentMessage):
        prev_events = cast("list[AgentMessage]", await self.get_events())
        prev_events.append(event)
        await self._save_events(prev_events)

    async def _save_events(self, events: list[AgentMessage]):
        await self.kv_store.set(
            self._cache_family,
            self._cache_key,
            json.dumps([{"role": event.role, "content": event.content} for event in events]),
            expiry_seconds=self.timeout_seconds,
        )

    @property
    def _html_cache_family(self) -> str:
        return "slack_thread_html"

    async def get_html(self) -> str | None:
        """Get the HTML representation of the thread."""
        return await self.kv_store.get(self._html_cache_family, self._cache_key)

    async def set_html(self, html: str):
        """Set the HTML representation of the thread with the same timeout as events."""
        await self.kv_store.set(
            self._html_cache_family,
            self._cache_key,
            html,
            expiry_seconds=self.timeout_seconds,
        )


@dataclass
class BlockComponentContext[T: AgentContentBlock, D: AgentBlockDelta]:
    content_block: T
    deltas: list[D]
    completed: bool
    is_prospector_mode: bool


class BlockComponent[T: AgentContentBlock, D: AgentBlockDelta, S](ABC):
    @abstractmethod
    def render(
        self, context: BlockComponentContext[T, D], completed_state: S | None
    ) -> list[Block]:
        pass

    @abstractmethod
    def render_aggregate(self, calls: list[tuple[BlockComponentContext[T, D], S]]) -> str:
        """
        Returns markdown for a block that shows the aggregate count of tool calls. For example:
        "🔍 Searched data documentation 3 times"
        "🔍 Searched data documentation once"
        """
        pass

    @abstractmethod
    def render_to_html(
        self, context: BlockComponentContext[T, D], completed_state: S | None
    ) -> HtmlString:
        """Render the component to HTML with Tailwind v4 styling emulating Slack UI."""
        pass

    async def on_completed(
        self, context: BlockComponentContext[T, D], slackstream_reply: SlackstreamReply
    ) -> S | None:
        pass


def split_line_into_chunks(line: str, max_text_in_chunk: int) -> list[str]:
    rv = []
    while len(line) > max_text_in_chunk:
        rv.append(line[:max_text_in_chunk])
        line = line[max_text_in_chunk:]
    rv.append(line)
    return rv


def split_lines_into_chunks(
    text: str, max_text_in_chunk: int, max_newlines_in_chunk: int | None = None
) -> list[str]:
    lines = text.split("\n")
    blocks = []
    current_block = ""
    in_code_block = False

    for line in lines:
        if max_newlines_in_chunk is not None and current_block.count("\n") >= max_newlines_in_chunk:
            blocks.extend(split_line_into_chunks(current_block, max_text_in_chunk))
            current_block = ""
        if len(current_block) + len(line) > max_text_in_chunk:
            if in_code_block:
                current_block += "```"
            blocks.extend(split_line_into_chunks(current_block, max_text_in_chunk))
            current_block = "```\n" if in_code_block else ""

        if line.strip().startswith("```"):
            in_code_block = not in_code_block

        current_block += line + "\n"

    if current_block:
        blocks.extend(split_line_into_chunks(current_block[:-1], max_text_in_chunk))
    return blocks


class TextBlockComponent(BlockComponent[AgentTextBlock, AgentTextDelta, None]):
    def render(
        self,
        context: BlockComponentContext[AgentTextBlock, AgentTextDelta],
        completed_state: None,
    ) -> list[Block]:
        text = "".join(delta.text for delta in context.deltas)
        max_text_in_chunk = 2500
        blocks = split_lines_into_chunks(text, max_text_in_chunk)
        return [MarkdownBlock(text=block) for block in blocks]

    def render_aggregate(
        self,
        calls: list[tuple[BlockComponentContext[AgentTextBlock, AgentTextDelta], None]],
    ) -> str:
        raise NotImplementedError("TextBlockComponent does not support aggregate rendering")

    def render_to_html(
        self,
        context: BlockComponentContext[AgentTextBlock, AgentTextDelta],
        completed_state: None,
    ) -> HtmlString:
        text = "".join(delta.text for delta in context.deltas)
        # Convert basic markdown to HTML with Slack-like styling
        html_content = self._markdown_to_html(text)
        return HtmlString.from_template(
            '<div class="text-md text-zinc-900 leading-relaxed mb-3">{html_content}</div>',
            html_content=html_content,
        )

    def _markdown_to_html(self, text: str) -> HtmlString:
        """Convert basic markdown to HTML."""
        import html
        import re

        # Escape HTML
        text = html.escape(text)

        # Convert bold **text**
        text = re.sub(r"\*\*(.*?)\*\*", r'<strong class="font-semibold">\1</strong>', text)

        # Convert italic *text*
        text = re.sub(r"\*(.*?)\*", r'<em class="italic">\1</em>', text)

        # Convert inline code `text`
        text = re.sub(
            r"`([^`]+)`",
            r'<code class="bg-zinc-100 text-red-600 px-1 py-0.5 rounded text-xs font-mono">\1</code>',
            text,
        )

        # Convert code blocks ```text```
        text = re.sub(
            r"```([^`]+)```",
            r'<pre class="bg-zinc-100 border border-zinc-200 rounded p-3 mt-2 mb-2 text-xs sm:text-sm font-mono overflow-x-auto whitespace-pre-wrap break-words"><code>\1</code></pre>',
            text,
            flags=re.MULTILINE | re.DOTALL,
        )

        # Convert newlines to <br>
        text = text.replace("\n", "<br>")

        return HtmlString(unsafe_html=text)


class GenericToolUseBlockComponent(BlockComponent[AgentToolUseBlock, AgentInputJSONDelta, None]):
    def render(
        self,
        context: BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta],
        completed_state: None,
    ) -> list[Block]:
        partial_json = "".join(delta.partial_json for delta in context.deltas)

        if not context.completed:
            message = (
                f">🤔  *Calling tool: `{context.content_block.name}`...*\n>```\n{partial_json}\n```"
            )
        else:
            message = (
                f">✅  *Called tool `{context.content_block.name}`*\n>```\n{partial_json}\n```"
            )

        return [
            SectionBlock(
                text=TextObject(
                    type=TextType.MRKDWN,
                    text=message,
                ),
            )
        ]

    def render_aggregate(
        self,
        calls: list[tuple[BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta], None]],
    ) -> str:
        if not calls:
            return ""

        tool_name = calls[0][0].content_block.name
        count = len(calls)

        if count == 1:
            return f"⚡ *Called tool `{tool_name}` once*"
        else:
            return f"⚡ *Called tool `{tool_name}` {count} times*"

    def render_to_html(
        self,
        context: BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta],
        completed_state: None,
    ) -> HtmlString:
        partial_json = "".join(delta.partial_json for delta in context.deltas)

        if not context.completed:
            icon = "🤔"
            status_text = HtmlString.from_template(
                "Calling tool: <code class='font-mono text-sm bg-zinc-100 px-1 rounded'>{tool_name}</code>...",
                tool_name=context.content_block.name,
            )
        else:
            icon = "✅"
            status_text = HtmlString.from_template(
                "Called tool <code class='font-mono text-sm bg-zinc-100 px-1 rounded'>{tool_name}</code>",
                tool_name=context.content_block.name,
            )

        return HtmlString.from_template(
            """
        <div class="flex items-start gap-2 mb-3 p-3 bg-zinc-50 border-l-4 border-zinc-300 rounded-r">
            <span class="text-lg -mt-1">{icon}</span>
            <div class="flex-1">
                <div class="text-sm text-zinc-700 mb-2">{status_text}</div>
                <pre class="bg-zinc-100 border border-zinc-200 rounded p-2 text-xs sm:text-sm font-mono overflow-x-auto text-zinc-800 whitespace-pre-wrap break-words"><code>{partial_json}</code></pre>
            </div>
        </div>
        """,
            icon=icon,
            status_text=status_text,
            partial_json=partial_json,
        )


class SearchDatasetsToolUseBlockComponent(
    BlockComponent[AgentToolUseBlock, AgentInputJSONDelta, None]
):
    def render(
        self,
        context: BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta],
        completed_state: None,
    ) -> list[Block]:
        if not context.completed:
            return [
                SectionBlock(
                    text=TextObject(
                        type=TextType.MRKDWN,
                        text=">🤔  *Searching data documentation...*",
                    ),
                )
            ]

        partial_json = "".join(delta.partial_json for delta in context.deltas)
        query = json.loads(partial_json)["query"]
        return [
            SectionBlock(
                text=TextObject(
                    type=TextType.MRKDWN,
                    text=create_markdown_block_text(
                        "🔍", f"Searched data documentation for `{query}`"
                    ),
                ),
            )
        ]

    def render_aggregate(
        self,
        calls: list[tuple[BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta], None]],
    ) -> str:
        count = len(calls)
        return create_aggregate_text("🔍", "Searched data documentation", count)

    def render_to_html(
        self,
        context: BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta],
        completed_state: None,
    ) -> HtmlString:
        if not context.completed:
            return HtmlString.from_template("""
            <div class="flex items-start gap-2 mb-3 p-3 bg-zinc-50 border-l-4 border-zinc-300 rounded-r">
                <span class="text-lg -mt-1">🤔</span>
                <div class="text-sm text-zinc-700">Searching data documentation...</div>
            </div>
            """)

        partial_json = "".join(delta.partial_json for delta in context.deltas)
        query = json.loads(partial_json)["query"]
        return HtmlString.from_template(
            """
        <div class="flex items-start gap-2 mb-3 p-3 bg-zinc-50 border-l-4 border-blue-300 rounded-r">
            <span class="text-lg -mt-1">🔍</span>
            <div class="text-sm text-zinc-700">Searched data documentation for <code class='font-mono text-sm bg-zinc-100 px-1 rounded'>{query}</code></div>
        </div>
        """,
            query=query,
        )


class SearchContextToolUseBlockComponent(
    BlockComponent[AgentToolUseBlock, AgentInputJSONDelta, None]
):
    def render(
        self,
        context: BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta],
        completed_state: None,
    ) -> list[Block]:
        if not context.completed:
            return [
                SectionBlock(
                    text=TextObject(
                        type=TextType.MRKDWN,
                        text=">🤔  *Searching context...*",
                    ),
                )
            ]

        partial_json = "".join(delta.partial_json for delta in context.deltas)
        query = json.loads(partial_json)["query"]
        return [
            SectionBlock(
                text=TextObject(
                    type=TextType.MRKDWN,
                    text=create_markdown_block_text("🧠", f"Searched context for `{query}`"),
                ),
            )
        ]

    def render_aggregate(
        self,
        calls: list[tuple[BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta], None]],
    ) -> str:
        count = len(calls)
        return create_aggregate_text("🧠", "Searched context", count)

    def render_to_html(
        self,
        context: BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta],
        completed_state: None,
    ) -> HtmlString:
        if not context.completed:
            return HtmlString.from_template("""
            <div class="flex items-start gap-2 mb-3 p-3 bg-zinc-50 border-l-4 border-zinc-300 rounded-r">
                <span class="text-lg -mt-1">🤔</span>
                <div class="text-sm text-zinc-700">Searching context...</div>
            </div>
            """)

        partial_json = "".join(delta.partial_json for delta in context.deltas)
        query = json.loads(partial_json)["query"]
        return HtmlString.from_template(
            """
        <div class="flex items-start gap-2 mb-3 p-3 bg-zinc-50 border-l-4 border-purple-300 rounded-r">
            <span class="text-lg -mt-1">🧠</span>
            <div class="text-sm text-zinc-700">Searched context for <code class='font-mono text-sm bg-zinc-100 px-1 rounded'>{query}</code></div>
        </div>
        """,
            query=query,
        )


class RunSqlQueryToolUseBlockComponent(
    BlockComponent[AgentToolUseBlock, AgentInputJSONDelta, None]
):
    def render(
        self,
        context: BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta],
        completed_state: None,
    ) -> list[Block]:
        is_prospector_mode = context.is_prospector_mode

        partial_json = "".join(delta.partial_json for delta in context.deltas)

        try:
            args = json.loads(partial_json)
            query_text = args.get("query", "")
            description = args.get("description", "")
        except Exception:
            # regex it
            match = re.search(r'"query":\s*"(.*)', partial_json)
            if match:
                query_text = match.group(1)
            else:
                query_text = ""
            desc_match = re.search(r'"description":\s*"(.*?)"', partial_json)
            if desc_match:
                description = desc_match.group(1)
            else:
                description = ""

        if not description:
            if not context.completed:
                description = "Analyzing..."
            else:
                description = "Running query..."

        # In prospector mode, only show description in Slack (not SQL query)
        # Normal mode: show SQL query
        query_text_lines = query_text.strip().split("\n")
        if len(query_text_lines) > 10:
            trimmed_query_text_lines = query_text_lines[:5]
            lines_trimmed = len(query_text_lines) - 10
            trimmed_query_text_lines.append(f"... {lines_trimmed} lines ...")
            trimmed_query_text_lines.extend(query_text_lines[-5:])
        else:
            trimmed_query_text_lines = query_text_lines
        trimmed_query_text = "\n".join(line[:80] for line in trimmed_query_text_lines)

        if len(trimmed_query_text.strip()) == 0 or is_prospector_mode:
            query_text_code_block = ""
        elif "\n" in trimmed_query_text:
            query_text_code_block = f"\n>```\n{trimmed_query_text}\n```"
        else:
            query_text_code_block = f"\n>```{trimmed_query_text}```"

        if not context.completed:
            message = f">🤔  *{description}*{query_text_code_block}"
        else:
            message = f">💻  *{description}*{query_text_code_block}"

        return [
            SectionBlock(
                text=TextObject(
                    type=TextType.MRKDWN,
                    text=message,
                ),
                expand=True,
            )
        ]

    def render_aggregate(
        self,
        calls: list[tuple[BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta], None]],
    ) -> str:
        count = len(calls)
        if count == 1:
            return "💻 *Ran 1 query*"
        else:
            return f"💻 *Ran {count} queries*"

    def render_to_html(
        self,
        context: BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta],
        completed_state: None,
    ) -> HtmlString:
        partial_json = "".join(delta.partial_json for delta in context.deltas)

        try:
            args = json.loads(partial_json)
            query_text = args.get("query", "")
            description = args.get("description", "")
        except Exception:
            # regex it
            match = re.search(r'"query":\s*"(.*)', partial_json)
            if match:
                query_text = match.group(1)
            else:
                query_text = ""
            desc_match = re.search(r'"description":\s*"(.*?)"', partial_json)
            if desc_match:
                description = desc_match.group(1)
            else:
                description = ""

        if not context.completed:
            icon = "🤔"
            status_text = "Building query..."
        else:
            icon = "💻"
            status_text = "Running query:"

        # HTML always includes SQL query (even in prospector mode)
        query_display_parts = []
        if description:
            query_display_parts.append(
                HtmlString.from_template(
                    '<div class="text-sm text-zinc-600 italic mb-2">{description}</div>',
                    description=description,
                )
            )
        if len(query_text.strip()) > 0:
            query_display_parts.append(
                HtmlString.from_template(
                    '<pre class="w-full max-w-full bg-zinc-100 border border-zinc-200 rounded p-2 text-xs sm:text-sm font-mono overflow-x-auto text-zinc-800 mt-2 whitespace-pre-wrap break-words"><code>{query_text}</code></pre>',
                    query_text=query_text,
                )
            )

        query_display = (
            HtmlString("".join(part.unsafe_html for part in query_display_parts))
            if query_display_parts
            else HtmlString("")
        )

        return HtmlString.from_template(
            """
        <div class="flex items-start gap-2 mb-3 p-3 bg-zinc-50 border-l-4 border-green-300 rounded-r">
            <span class="text-lg -mt-1">{icon}</span>
            <div class="flex-1 min-w-0 max-w-3xl">
                <div class="text-sm text-zinc-700">{status_text}</div>
                {query_display}
            </div>
        </div>
        """,
            icon=icon,
            status_text=status_text,
            query_display=query_display,
        )


class AddContextToolUseBlockComponent(BlockComponent[AgentToolUseBlock, AgentInputJSONDelta, None]):
    def render(
        self,
        context: BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta],
        completed_state: None,
    ) -> list[Block]:
        if not context.completed:
            return [
                SectionBlock(
                    text=TextObject(
                        type=TextType.MRKDWN,
                        text=">🤔  *Remembering context...*",
                    ),
                )
            ]

        partial_json = "".join(delta.partial_json for delta in context.deltas)
        args = json.loads(partial_json)
        content = args["correct_understanding"]
        topic = args["topic"]

        if len(content) > 2500:
            content_preview = content[:2500] + "..."
        else:
            content_preview = content

        return [
            SectionBlock(
                text=TextObject(
                    type=TextType.MRKDWN,
                    text=(
                        f">📝  *Remembered context for topic `{topic}`*\n"
                        f">```\n{content_preview}\n```"
                    ),
                ),
            )
        ]

    def render_aggregate(
        self,
        calls: list[tuple[BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta], None]],
    ) -> str:
        count = len(calls)
        if count == 1:
            return "📝 *Remembered context*"
        else:
            return f"📝 *Remembered context {count} times*"

    def render_to_html(
        self,
        context: BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta],
        completed_state: None,
    ) -> HtmlString:
        if not context.completed:
            return HtmlString.from_template("""
            <div class="flex items-start gap-2 mb-3 p-3 bg-zinc-50 border-l-4 border-zinc-300 rounded-r">
                <span class="text-lg -mt-1">🤔</span>
                <div class="text-sm text-zinc-700">Remembering context...</div>
            </div>
            """)

        partial_json = "".join(delta.partial_json for delta in context.deltas)
        args = json.loads(partial_json)
        content = args["correct_understanding"]
        topic = args["topic"]

        if len(content) > 2500:
            content_preview = content[:2500] + "..."
        else:
            content_preview = content

        return HtmlString.from_template(
            """
        <div class="flex items-start gap-2 mb-3 p-3 bg-zinc-50 border-l-4 border-orange-300 rounded-r">
            <span class="text-lg -mt-1">📝</span>
            <div class="flex-1">
                <div class="text-sm text-zinc-700 mb-2">Remembered context for topic <code class='font-mono text-sm bg-zinc-100 px-1 rounded'>{topic}</code></div>
                <pre class="bg-zinc-100 border border-zinc-200 rounded p-2 text-xs sm:text-sm font-mono overflow-x-auto text-zinc-800 whitespace-pre-wrap break-words"><code>{content_preview}</code></pre>
            </div>
        </div>
        """,
            topic=topic,
            content_preview=content_preview,
        )


class OpenDataRequestTicketToolUseBlockComponent(
    BlockComponent[AgentToolUseBlock, AgentInputJSONDelta, None]
):
    def render(
        self,
        context: BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta],
        completed_state: None,
    ) -> list[Block]:
        if not context.completed:
            return [
                SectionBlock(
                    text=TextObject(
                        type=TextType.MRKDWN,
                        text=">🤔  *Opening data request ticket...*",
                    ),
                )
            ]

        partial_json = "".join(delta.partial_json for delta in context.deltas)
        try:
            args = json.loads(partial_json)
            title = args.get("title", "")
            description = args.get("body", "")
        except Exception:
            title = ""
            description = ""

        if len(title) > 2500:
            title_preview = title[:2500] + "..."
        else:
            title_preview = title

        if len(description) > 2500:
            description_preview = description[:2500] + "..."
        else:
            description_preview = description

        message = f">🎫  *Opened data request ticket*\n>*Title:* {title_preview}"
        if description_preview:
            message += f"\n>*Description:*\n>```\n{description_preview}\n```"

        blocks: list[Block] = [
            SectionBlock(
                text=TextObject(
                    type=TextType.MRKDWN,
                    text=message,
                ),
            )
        ]

        # Add scaffold button if enabled and ticket URL is available
        if scaffold_branch_enabled.get(False):
            ticket_url = data_request_ticket_url.get()
            if ticket_url:
                blocks.append(
                    ActionsBlock(
                        elements=[
                            ButtonElement(
                                text=TextObject.plain_text("🚀 Scaffold Dagster PR", emoji=True),
                                style="primary",
                                action_id="scaffold_dagster_pr",
                                value=ticket_url,
                            ),
                            ButtonElement(
                                text=TextObject.plain_text("View Ticket on GitHub"),
                                url=ticket_url,
                            ),
                        ],
                    )
                )

        return blocks

    def render_aggregate(
        self,
        calls: list[tuple[BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta], None]],
    ) -> str:
        count = len(calls)
        if count == 1:
            return "🎫 *Opened data request ticket*"
        else:
            return f"🎫 *Opened {count} data request tickets*"

    def render_to_html(
        self,
        context: BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta],
        completed_state: None,
    ) -> HtmlString:
        if not context.completed:
            return HtmlString.from_template("""
            <div class="flex items-start gap-2 mb-3 p-3 bg-zinc-50 border-l-4 border-zinc-300 rounded-r">
                <span class="text-lg -mt-1">🤔</span>
                <div class="text-sm text-zinc-700">Opening data request ticket...</div>
            </div>
            """)

        partial_json = "".join(delta.partial_json for delta in context.deltas)
        try:
            args = json.loads(partial_json)
            title = args.get("title", "")
            description = args.get("body", "")
        except Exception:
            title = ""
            description = ""

        if len(title) > 2500:
            title_preview = title[:2500] + "..."
        else:
            title_preview = title

        if len(description) > 2500:
            description_preview = description[:2500] + "..."
        else:
            description_preview = description

        title_html = (
            HtmlString.from_template(
                '<div class="font-semibold text-sm text-zinc-900 mb-1">Title: {title_preview}</div>',
                title_preview=title_preview,
            )
            if title_preview
            else ""
        )
        description_html = (
            HtmlString.from_template(
                '<div class="text-sm text-zinc-700 mb-2">Description:</div><pre class="bg-zinc-100 border border-zinc-200 rounded p-2 text-xs sm:text-sm font-mono overflow-x-auto text-zinc-800 whitespace-pre-wrap break-words"><code>{description_preview}</code></pre>',
                description_preview=description_preview,
            )
            if description_preview
            else ""
        )

        return HtmlString.from_template(
            """
        <div class="flex items-start gap-2 mb-3 p-3 bg-zinc-50 border-l-4 border-red-300 rounded-r">
            <span class="text-lg -mt-1">🎫</span>
            <div class="flex-1">
                <div class="text-sm text-zinc-700 mb-2">Opened data request ticket</div>
                {title_html}
                {description_html}
            </div>
        </div>
        """,
            title_html=title_html,
            description_html=description_html,
        )


class AddOrEditCronJobToolUseBlockComponent(
    BlockComponent[AgentToolUseBlock, AgentInputJSONDelta, None]
):
    def render(
        self,
        context: BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta],
        completed_state: None,
    ) -> list[Block]:
        if not context.completed:
            return [
                SectionBlock(
                    text=TextObject(
                        type=TextType.MRKDWN,
                        text=">🤔  *Updating recurring analyses...*",
                    ),
                )
            ]

        partial_json = "".join(delta.partial_json for delta in context.deltas)
        try:
            args = json.loads(partial_json)
            cron_job_name = args.get("cron_job_name", "")
            cron_string = args.get("cron_string", "")
            thread = args.get("thread", "")
            question = args.get("question", "")
            is_edit = args.get("is_edit", False)
        except Exception:
            cron_job_name = ""
            cron_string = ""
            thread = ""
            question = ""
            is_edit = False

        if len(question) > 2000:
            question_preview = question[:2000] + "..."
        else:
            question_preview = question

        message_parts = [
            f">⏰  *{'Updated' if is_edit else 'Created'} recurring analysis: `{cron_job_name}`* (pending approval)"
        ]

        if cron_string:
            message_parts.append(f">*Schedule:* `{cron_string}`")

        if thread:
            message_parts.append(f">*Thread title:* {thread}")

        if question_preview:
            message_parts.append(f">*Analysis:*\n>```\n{question_preview}\n```")

        return [
            SectionBlock(
                text=TextObject(
                    type=TextType.MRKDWN,
                    text="\n".join(message_parts),
                ),
            )
        ]

    def render_aggregate(
        self,
        calls: list[tuple[BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta], None]],
    ) -> str:
        count = len(calls)
        if count == 1:
            return "⏰ *Updated recurring analyses*"
        else:
            return f"⏰ *Updated {count} recurring analyses*"

    def render_to_html(
        self,
        context: BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta],
        completed_state: None,
    ) -> HtmlString:
        if not context.completed:
            return HtmlString.from_template("""
            <div class="flex items-start gap-2 mb-3 p-3 bg-zinc-50 border-l-4 border-zinc-300 rounded-r">
                <span class="text-lg -mt-1">🤔</span>
                <div class="text-sm text-zinc-700">Updating recurring analyses...</div>
            </div>
            """)

        partial_json = "".join(delta.partial_json for delta in context.deltas)
        try:
            args = json.loads(partial_json)
            cron_job_name = args.get("cron_job_name", "")
            cron_string = args.get("cron_string", "")
            thread = args.get("thread", "")
            question = args.get("question", "")
            is_edit = args.get("is_edit", False)
        except Exception:
            cron_job_name = ""
            cron_string = ""
            thread = ""
            question = ""
            is_edit = False

        if len(question) > 2000:
            question_preview = question[:2000] + "..."
        else:
            question_preview = question

        details_html = []
        if cron_string:
            details_html.append(
                HtmlString.from_template(
                    '<div class="text-sm text-zinc-700"><strong>Schedule:</strong> <code class="font-mono text-sm bg-zinc-100 px-1 rounded">{cron_string}</code></div>',
                    cron_string=cron_string,
                )
            )
        if thread:
            details_html.append(
                HtmlString.from_template(
                    '<div class="text-sm text-zinc-700"><strong>Thread title:</strong> {thread}</div>',
                    thread=thread,
                )
            )
        if question_preview:
            details_html.append(
                HtmlString.from_template(
                    '<div class="text-sm text-zinc-700 mb-2"><strong>Analysis:</strong></div><pre class="bg-zinc-100 border border-zinc-200 rounded p-2 text-xs sm:text-sm font-mono overflow-x-auto text-zinc-800 whitespace-pre-wrap break-words"><code>{question_preview}</code></pre>',
                    question_preview=question_preview,
                )
            )

        details_content: HtmlString | str = ""
        if details_html:
            details_content = HtmlString.from_template(
                '<div class="mt-2 space-y-2">{details_content}</div>',
                details_content=HtmlString.join(*details_html),
            )

        return HtmlString.from_template(
            """
        <div class="flex items-start gap-2 mb-3 p-3 bg-zinc-50 border-l-4 border-amber-300 rounded-r">
            <span class="text-lg -mt-1">⏰</span>
            <div class="flex-1">
                <div class="text-sm text-zinc-700 mb-2">{verb} recurring analysis: <code class='font-mono text-sm bg-zinc-100 px-1 rounded'>{cron_job_name}</code> <span class="text-amber-600 font-medium">(pending approval)</span></div>
                {details_content}
            </div>
        </div>
        """,
            cron_job_name=cron_job_name,
            details_content=details_content,
            verb="Updated" if is_edit else "Created",
        )


class DeleteCronJobToolUseBlockComponent(
    BlockComponent[AgentToolUseBlock, AgentInputJSONDelta, None]
):
    def render(
        self,
        context: BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta],
        completed_state: None,
    ) -> list[Block]:
        if not context.completed:
            return [
                SectionBlock(
                    text=TextObject(
                        type=TextType.MRKDWN,
                        text=">🤔  *Deleting recurring analysis...*",
                    ),
                )
            ]

        return [
            SectionBlock(
                text=TextObject(
                    type=TextType.MRKDWN,
                    text=(
                        ">🗑️  *Deleted recurring analysis*\n"
                        ">This recurring analysis will be stopped (pending approval)."
                    ),
                ),
            )
        ]

    def render_aggregate(
        self,
        calls: list[tuple[BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta], None]],
    ) -> str:
        count = len(calls)
        return create_aggregate_text("🗑️", "Deleted recurring analysis", count).replace(
            "analysis times", "analyses"
        )

    def render_to_html(
        self,
        context: BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta],
        completed_state: None,
    ) -> HtmlString:
        if not context.completed:
            return create_info_block_html("🤔", "Deleting recurring analysis...", "zinc")

        subtitle = 'All future recurring analyses will be stopped <span class="text-amber-600 font-medium">(pending approval)</span>.'
        return create_complex_info_block_html("🗑️", "Deleted recurring analysis", subtitle, "red")


class ListCronJobsToolUseBlockComponent(
    BlockComponent[AgentToolUseBlock, AgentInputJSONDelta, None]
):
    def render(
        self,
        context: BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta],
        completed_state: None,
    ) -> list[Block]:
        if not context.completed:
            return [
                SectionBlock(
                    text=TextObject(
                        type=TextType.MRKDWN,
                        text=">🤔  *Retrieving scheduled analyses...*",
                    ),
                )
            ]

        return [
            SectionBlock(
                text=TextObject(
                    type=TextType.MRKDWN,
                    text=">📋  *Retrieved scheduled analyses*",
                ),
            )
        ]

    def render_aggregate(
        self,
        calls: list[tuple[BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta], None]],
    ) -> str:
        count = len(calls)
        if count == 1:
            return "📋 *Retrieved scheduled analyses*"
        else:
            return f"📋 *Retrieved scheduled analyses {count} times*"

    def render_to_html(
        self,
        context: BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta],
        completed_state: None,
    ) -> HtmlString:
        if not context.completed:
            return create_info_block_html("🤔", "Retrieving scheduled analyses...", "zinc")

        return create_info_block_html("📋", "Retrieved scheduled analyses", "blue")


class ReadPrFileToolUseBlockComponent(BlockComponent[AgentToolUseBlock, AgentInputJSONDelta, None]):
    def render(
        self,
        context: BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta],
        completed_state: None,
    ) -> list[Block]:
        if not context.completed:
            return [
                SectionBlock(
                    text=TextObject(
                        type=TextType.MRKDWN,
                        text=">🤔  *Reading GitHub pull request file...*",
                    ),
                )
            ]

        partial_json = "".join(delta.partial_json for delta in context.deltas)
        try:
            args = json.loads(partial_json)
            filename = args.get("filename", "")
        except Exception:
            filename = ""

        if filename:
            return [
                SectionBlock(
                    text=TextObject(
                        type=TextType.MRKDWN,
                        text=f">📄  *Read GitHub pull request file: `{filename}`*",
                    ),
                )
            ]
        else:
            return [
                SectionBlock(
                    text=TextObject(
                        type=TextType.MRKDWN,
                        text=">📄  *Read GitHub pull request file*",
                    ),
                )
            ]

    def render_aggregate(
        self,
        calls: list[tuple[BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta], None]],
    ) -> str:
        count = len(calls)
        if count == 1:
            return "📄 *Read GitHub pull request file*"
        else:
            return f"📄 *Read {count} GitHub pull request files*"

    def render_to_html(
        self,
        context: BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta],
        completed_state: None,
    ) -> HtmlString:
        if not context.completed:
            return HtmlString("""
            <div class="flex items-start gap-2 mb-3 p-3 bg-zinc-50 border-l-4 border-zinc-300 rounded-r">
                <span class="text-lg -mt-1">🤔</span>
                <div class="text-sm text-zinc-700">Reading GitHub pull request file...</div>
            </div>
            """)

        partial_json = "".join(delta.partial_json for delta in context.deltas)
        try:
            args = json.loads(partial_json)
            filename = args.get("filename", "")
        except Exception:
            filename = ""

        if filename:
            return HtmlString.from_template(
                """
            <div class="flex items-start gap-2 mb-3 p-3 bg-zinc-50 border-l-4 border-indigo-300 rounded-r">
                <span class="text-lg -mt-1">📄</span>
                <div class="text-sm text-zinc-700">Read GitHub pull request file: <code class='font-mono text-sm bg-zinc-100 px-1 rounded'>{filename}</code></div>
            </div>
            """,
                filename=filename,
            )
        else:
            return HtmlString("""
            <div class="flex items-start gap-2 mb-3 p-3 bg-zinc-50 border-l-4 border-indigo-300 rounded-r">
                <span class="text-lg -mt-1">📄</span>
                <div class="text-sm text-zinc-700">Read GitHub pull request file</div>
            </div>
            """)


class ListPrFilesToolUseBlockComponent(
    BlockComponent[AgentToolUseBlock, AgentInputJSONDelta, None]
):
    def render(
        self,
        context: BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta],
        completed_state: None,
    ) -> list[Block]:
        if not context.completed:
            return [
                SectionBlock(
                    text=TextObject(
                        type=TextType.MRKDWN,
                        text=">🤔  *Listing GitHub pull request files...*",
                    ),
                )
            ]

        return [
            SectionBlock(
                text=TextObject(
                    type=TextType.MRKDWN,
                    text=">📋  *Listed GitHub pull request files*",
                ),
            )
        ]

    def render_aggregate(
        self,
        calls: list[tuple[BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta], None]],
    ) -> str:
        count = len(calls)
        if count == 1:
            return "📋 *Listed GitHub pull request files*"
        else:
            return f"📋 *Listed {count} GitHub pull request files*"

    def render_to_html(
        self,
        context: BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta],
        completed_state: None,
    ) -> HtmlString:
        if not context.completed:
            return HtmlString("""
            <div class="flex items-start gap-2 mb-3 p-3 bg-zinc-50 border-l-4 border-zinc-300 rounded-r">
                <span class="text-lg -mt-1">🤔</span>
                <div class="text-sm text-zinc-700">Listing GitHub pull request files...</div>
            </div>
            """)

        return HtmlString("""
        <div class="flex items-start gap-2 mb-3 p-3 bg-zinc-50 border-l-4 border-indigo-300 rounded-r">
            <span class="text-lg -mt-1">📋</span>
            <div class="text-sm text-zinc-700">Listed GitHub pull request files</div>
        </div>
        """)


class UpdatePrFileToolUseBlockComponent(
    BlockComponent[AgentToolUseBlock, AgentInputJSONDelta, None]
):
    def render(
        self,
        context: BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta],
        completed_state: None,
    ) -> list[Block]:
        if not context.completed:
            return [
                SectionBlock(
                    text=TextObject(
                        type=TextType.MRKDWN,
                        text=">🤔  *Updating GitHub pull request file...*",
                    ),
                )
            ]

        partial_json = "".join(delta.partial_json for delta in context.deltas)
        try:
            args = json.loads(partial_json)
            filename = args.get("filename", "")
            args.get("content", "")
            commit_message = args.get("commit_message", "")
        except Exception:
            filename = ""
            commit_message = ""

        if filename:
            message_parts = [f">💾  *Updated {filename} in GitHub pull request*"]

            if commit_message:
                if len(commit_message) > 200:
                    commit_preview = commit_message[:200] + "..."
                else:
                    commit_preview = commit_message
                message_parts.append(f">*Commit message:* {commit_preview}")

            return [
                SectionBlock(
                    text=TextObject(
                        type=TextType.MRKDWN,
                        text="\n".join(message_parts),
                    ),
                )
            ]
        else:
            return [
                SectionBlock(
                    text=TextObject(
                        type=TextType.MRKDWN,
                        text=">💾  *Updated GitHub pull request file*",
                    ),
                )
            ]

    def render_aggregate(
        self,
        calls: list[tuple[BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta], None]],
    ) -> str:
        count = len(calls)
        if count == 1:
            return "💾 *Updated GitHub pull request file*"
        else:
            return f"💾 *Updated {count} GitHub pull request files*"

    def render_to_html(
        self,
        context: BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta],
        completed_state: None,
    ) -> HtmlString:
        if not context.completed:
            return HtmlString("""
            <div class="flex items-start gap-2 mb-3 p-3 bg-zinc-50 border-l-4 border-zinc-300 rounded-r">
                <span class="text-lg -mt-1">🤔</span>
                <div class="text-sm text-zinc-700">Updating GitHub pull request file...</div>
            </div>
            """)

        partial_json = "".join(delta.partial_json for delta in context.deltas)
        try:
            args = json.loads(partial_json)
            filename = args.get("filename", "")
            args.get("content", "")
            commit_message = args.get("commit_message", "")
        except Exception:
            filename = ""
            commit_message = ""

        if filename:
            commit_html: HtmlString | str = ""
            if commit_message:
                if len(commit_message) > 200:
                    commit_preview = commit_message[:200] + "..."
                else:
                    commit_preview = commit_message
                commit_html = HtmlString.from_template(
                    '<div class="text-sm text-zinc-700 mt-2"><strong>Commit message:</strong> {commit_preview}</div>',
                    commit_preview=commit_preview,
                )

            return HtmlString.from_template(
                """
            <div class="flex items-start gap-2 mb-3 p-3 bg-zinc-50 border-l-4 border-indigo-300 rounded-r">
                <span class="text-lg -mt-1">💾</span>
                <div class="flex-1">
                    <div class="text-sm text-zinc-700">Updated <code class='font-mono text-sm bg-zinc-100 px-1 rounded'>{filename}</code> in GitHub pull request</div>
                    {commit_html}
                </div>
            </div>
            """,
                filename=filename,
                commit_html=commit_html,
            )
        else:
            return HtmlString("""
            <div class="flex items-start gap-2 mb-3 p-3 bg-zinc-50 border-l-4 border-indigo-300 rounded-r">
                <span class="text-lg -mt-1">💾</span>
                <div class="text-sm text-zinc-700">Updated GitHub pull request file</div>
            </div>
            """)


@dataclass
class RenderDataVisualizationCompletedState:
    image_attachment: ImageAttachment
    image_base64: str


@dataclass
class AttachCsvCompletedState:
    csv_attachment: CsvAttachment


class RenderDataVisualizationToolUseBlockComponent(
    BlockComponent[AgentToolUseBlock, AgentInputJSONDelta, RenderDataVisualizationCompletedState]
):
    def render(
        self,
        context: BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta],
        completed_state: RenderDataVisualizationCompletedState | None,
    ) -> list[Block]:
        if not completed_state:
            return [
                SectionBlock(
                    text=TextObject(
                        type=TextType.MRKDWN,
                        text=">🤔  *Rendering data visualization...*",
                    ),
                )
            ]

        args = json.loads("".join(delta.partial_json for delta in context.deltas))
        try:
            config = ChartConfig.model_validate_json(json.dumps(args["config"]), strict=True)
        except Exception:
            config = None

        if config is None:
            return [
                SectionBlock(
                    text=TextObject(
                        type=TextType.MRKDWN,
                        text=">❌  *Tried and failed to render a data visualization.*",
                    ),
                )
            ]

        if config.chart_specific_config.chart_type == ChartType.BAR:
            chart_type = "bar chart"
            emoji = "📊"
        elif config.chart_specific_config.chart_type == ChartType.LINE:
            chart_type = "line chart"
            emoji = "📈"
        elif config.chart_specific_config.chart_type == ChartType.DONUT:
            chart_type = "donut chart"
            emoji = "🍩"
        elif config.chart_specific_config.chart_type == ChartType.WORDCLOUD:
            chart_type = "word cloud"
            emoji = "🌥️"
        else:
            raise ValueError(f"Unknown chart type: {config.chart_specific_config.chart_type}")

        blocks: list[Block] = [
            SectionBlock(
                text=TextObject(
                    type=TextType.MRKDWN,
                    text=f">{emoji}  *Rendered {chart_type}*",
                ),
            ),
        ]

        blocks.append(
            ImageBlock(
                slack_file=SlackFile(
                    id=completed_state.image_attachment.id,
                    # url=completed_state.image_attachment.url,
                    # id="F095JDS8GLR"
                ),
                alt_text=f"Rendered {chart_type}",
            ),
        )

        return blocks

    def render_to_html(
        self,
        context: BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta],
        completed_state: RenderDataVisualizationCompletedState | None,
    ) -> HtmlString:
        if not completed_state:
            return HtmlString("""
            <div class="flex items-start gap-2 mb-3 p-3 bg-zinc-50 border-l-4 border-zinc-300 rounded-r">
                <span class="text-lg -mt-1">🤔</span>
                <div class="text-sm text-zinc-700">Rendering data visualization...</div>
            </div>
            """)

        args = json.loads("".join(delta.partial_json for delta in context.deltas))
        try:
            config = ChartConfig.model_validate_json(json.dumps(args["config"]), strict=True)
        except Exception:
            config = None

        if config is None:
            return HtmlString("""
            <div class="flex items-start gap-2 mb-3 p-3 bg-zinc-50 border-l-4 border-red-300 rounded-r">
                <span class="text-lg -mt-1">❌</span>
                <div class="text-sm text-zinc-700">Tried and failed to render a data visualization.</div>
            </div>
            """)

        if config.chart_specific_config.chart_type == ChartType.BAR:
            chart_type = "bar chart"
            emoji = "📊"
        elif config.chart_specific_config.chart_type == ChartType.LINE:
            chart_type = "line chart"
            emoji = "📈"
        elif config.chart_specific_config.chart_type == ChartType.DONUT:
            chart_type = "donut chart"
            emoji = "🍩"
        elif config.chart_specific_config.chart_type == ChartType.WORDCLOUD:
            chart_type = "word cloud"
            emoji = "🌥️"
        else:
            raise ValueError(f"Unknown chart type: {config.chart_specific_config.chart_type}")

        # Encode image bytes as base64 for HTML display
        image_base64 = completed_state.image_base64
        image_html = HtmlString.from_template(
            '<div class="mt-2"><img src="data:image/png;base64,{image_base64}" alt="Rendered {chart_type}" class="max-w-full h-auto rounded border border-zinc-200 shadow-sm" /></div>',
            image_base64=image_base64,
            chart_type=chart_type,
        )

        return HtmlString.from_template(
            """
        <div class="flex items-start gap-2 mb-3 p-3 bg-zinc-50 border-l-4 border-cyan-300 rounded-r">
            <span class="text-lg -mt-1">{emoji}</span>
            <div class="flex-1">
                <div class="text-sm text-zinc-700">Rendered {chart_type}</div>
                {image_html}
            </div>
        </div>
        """,
            emoji=emoji,
            chart_type=chart_type,
            image_html=image_html,
        )

    def render_aggregate(
        self,
        calls: list[
            tuple[
                BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta],
                RenderDataVisualizationCompletedState,
            ]
        ],
    ) -> str:
        count = len(calls)
        if count == 1:
            return "📊 *Rendered data visualization*"
        else:
            return f"📊 *Rendered {count} data visualizations*"

    async def on_completed(
        self,
        context: BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta],
        slackstream_reply: SlackstreamReply,
    ) -> RenderDataVisualizationCompletedState | None:
        args = json.loads("".join(delta.partial_json for delta in context.deltas))
        try:
            config = ChartConfig.model_validate_json(json.dumps(args["config"]), strict=True)
        except Exception:
            return

        @sync_to_async
        def create_image_data():
            dsl = DataVizDSL()
            viz = dsl.create_chart(config)
            return dsl.get_chart_as_bytes(viz)

        image_data = await create_image_data()
        attachment = await slackstream_reply.attach_image(image_data)
        image_base64 = base64.b64encode(image_data).decode("utf-8")
        return RenderDataVisualizationCompletedState(
            image_attachment=attachment,
            image_base64=image_base64,
        )


class AttachCsvToolUseBlockComponent(BlockComponent[AgentToolUseBlock, AgentInputJSONDelta, None]):
    def render(
        self,
        context: BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta],
        completed_state: None,
    ) -> list[Block]:
        is_prospector_mode = context.is_prospector_mode
        partial_json = "".join(delta.partial_json for delta in context.deltas)

        try:
            args = json.loads(partial_json)
            query_text = args.get("query", "")
        except Exception:
            query_match = re.search(r'"query":\s*"(.*?)"', partial_json)
            query_text = query_match.group(1).replace("\\n", "\n") if query_match else ""

        query_text_lines = query_text.strip().split("\n")
        if len(query_text_lines) > 10:
            trimmed_query_text_lines = query_text_lines[:5]
            lines_trimmed = len(query_text_lines) - 10
            trimmed_query_text_lines.append(f"... {lines_trimmed} lines ...")
            trimmed_query_text_lines.extend(query_text_lines[-5:])
        else:
            trimmed_query_text_lines = query_text_lines
        trimmed_query_text = "\n".join(line[:80] for line in trimmed_query_text_lines)

        if len(trimmed_query_text.strip()) == 0 or is_prospector_mode:
            query_text_code_block = ""
        elif "\n" in trimmed_query_text:
            query_text_code_block = f"\n>```\n{trimmed_query_text}\n```"
        else:
            query_text_code_block = f"\n>```{trimmed_query_text}```"

        if not context.completed:
            message = f">🤔  *Generating CSV file...*{query_text_code_block}"
        else:
            message = f">📄  *Generated CSV file:*{query_text_code_block}"

        return [
            SectionBlock(
                text=TextObject(
                    type=TextType.MRKDWN,
                    text=message,
                ),
                expand=True,
            )
        ]

    def render_to_html(
        self,
        context: BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta],
        completed_state: None,
    ) -> HtmlString:
        partial_json = "".join(delta.partial_json for delta in context.deltas)

        try:
            args = json.loads(partial_json)
            query_text = args.get("query", "")
        except Exception:
            query_match = re.search(r'"query":\s*"(.*?)"', partial_json)
            query_text = query_match.group(1).replace("\\n", "\n") if query_match else ""

        if not context.completed:
            return HtmlString("""
            <div class="flex items-start gap-2 mb-3 p-3 bg-zinc-50 border-l-4 border-zinc-300 rounded-r">
                <span class="text-lg -mt-1">🤔</span>
                <div class="text-sm text-zinc-700">Generating CSV file...</div>
            </div>
            """)

        if len(query_text.strip()) == 0:
            query_display = ""
        else:
            query_display = HtmlString.from_template(
                '<pre class="w-full max-w-full bg-zinc-100 border border-zinc-200 rounded p-2 text-xs sm:text-sm font-mono overflow-x-auto text-zinc-800 mt-2 whitespace-pre-wrap break-words"><code>{query_text}</code></pre>',
                query_text=query_text,
            )

        return HtmlString.from_template(
            """
        <div class="flex items-start gap-2 mb-3 p-3 bg-zinc-50 border-l-4 border-green-300 rounded-r">
            <span class="text-lg -mt-1">📄</span>
            <div class="flex-1 min-w-0 max-w-3xl">
                <div class="text-sm text-zinc-700">Generated CSV file</div>
                {query_display}
            </div>
        </div>
        """,
            query_display=query_display,
        )

    def render_aggregate(
        self,
        calls: list[
            tuple[
                BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta],
                None,
            ]
        ],
    ) -> str:
        count = len(calls)
        if count == 1:
            return "📄 *Generated CSV file*"
        else:
            return f"📄 *Generated {count} CSV files*"


class SearchWebToolUseBlockComponent(BlockComponent[AgentToolUseBlock, AgentInputJSONDelta, None]):
    def render(
        self,
        context: BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta],
        completed_state: None,
    ) -> list[Block]:
        if not context.completed:
            return [
                SectionBlock(
                    text=TextObject(
                        type=TextType.MRKDWN,
                        text=">🌐  *Searching the web...*",
                    ),
                )
            ]

        partial_json = "".join(delta.partial_json for delta in context.deltas)
        query = json.loads(partial_json)["query"]
        return [
            SectionBlock(
                text=TextObject(
                    type=TextType.MRKDWN,
                    text=create_markdown_block_text("🌐", f"Searched the web for `{query}`"),
                ),
            )
        ]

    def render_aggregate(
        self,
        calls: list[tuple[BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta], None]],
    ) -> str:
        count = len(calls)
        return create_aggregate_text("🌐", "Searched the web", count)

    def render_to_html(
        self,
        context: BlockComponentContext[AgentToolUseBlock, AgentInputJSONDelta],
        completed_state: None,
    ) -> HtmlString:
        if not context.completed:
            return HtmlString.from_template("""
            <div class="flex items-start gap-2 mb-3 p-3 bg-zinc-50 border-l-4 border-zinc-300 rounded-r">
                <span class="text-lg -mt-1">🌐</span>
                <div class="text-sm text-zinc-700">Searching the web...</div>
            </div>
            """)

        partial_json = "".join(delta.partial_json for delta in context.deltas)
        query = json.loads(partial_json)["query"]
        return HtmlString.from_template(
            """
        <div class="flex items-start gap-2 mb-3 p-3 bg-zinc-50 border-l-4 border-blue-300 rounded-r">
            <span class="text-lg -mt-1">🌐</span>
            <div class="text-sm text-zinc-700">Searched the web for <code class='font-mono text-sm bg-zinc-100 px-1 rounded'>{query}</code></div>
        </div>
        """,
            query=query,
        )


def _get_block_component(
    content_block: AgentContentBlock,
) -> BlockComponent[Any, Any, Any]:
    if content_block.type == "output_text":
        return TextBlockComponent()
    elif content_block.type == "call_tool":
        if content_block.name == "search_datasets":
            return SearchDatasetsToolUseBlockComponent()
        elif content_block.name == "run_sql_query":
            return RunSqlQueryToolUseBlockComponent()
        elif content_block.name == "search_context":
            return SearchContextToolUseBlockComponent()
        elif content_block.name == "search_web":
            return SearchWebToolUseBlockComponent()
        elif content_block.name == "add_context":
            return AddContextToolUseBlockComponent()
        elif content_block.name == "open_data_request_ticket":
            return OpenDataRequestTicketToolUseBlockComponent()
        elif content_block.name == "render_data_visualization":
            return RenderDataVisualizationToolUseBlockComponent()
        elif content_block.name == "attach_csv":
            return AttachCsvToolUseBlockComponent()
        elif content_block.name == "add_or_edit_cron_job":
            return AddOrEditCronJobToolUseBlockComponent()
        elif content_block.name == "delete_cron_job":
            return DeleteCronJobToolUseBlockComponent()
        elif content_block.name == "list_cron_jobs":
            return ListCronJobsToolUseBlockComponent()
        elif content_block.name == "read_pr_file":
            return ReadPrFileToolUseBlockComponent()
        elif content_block.name == "list_pr_files":
            return ListPrFilesToolUseBlockComponent()
        elif content_block.name == "update_pr_file":
            return UpdatePrFileToolUseBlockComponent()
        else:
            return GenericToolUseBlockComponent()
    else:
        raise ValueError(f"Unknown content block type: {content_block.type}")


def render_block_component(
    content_block: AgentContentBlock,
    deltas: list[AgentBlockDelta],
    completed: bool,
    completed_state: Any | None,
    is_prospector_mode: bool,
) -> list[Block]:
    context = BlockComponentContext(
        content_block=content_block,
        deltas=deltas,
        completed=completed,
        is_prospector_mode=is_prospector_mode,
    )
    return _get_block_component(content_block).render(context, completed_state)


def render_block_component_to_html(
    content_block: AgentContentBlock,
    deltas: list[AgentBlockDelta],
    completed: bool,
    completed_state: Any | None,
    is_prospector_mode: bool,
) -> str:
    """Render a block component to HTML with Tailwind v4 styling emulating Slack UI."""
    context = BlockComponentContext(
        content_block=content_block,
        deltas=deltas,
        completed=completed,
        is_prospector_mode=is_prospector_mode,
    )
    return _get_block_component(content_block).render_to_html(context, completed_state).unsafe_html


async def run_block_component_side_effects(
    content_block: AgentContentBlock,
    deltas: list[AgentBlockDelta],
    slackstream_reply: SlackstreamReply,
    is_prospector_mode: bool,
) -> Any | None:
    context = BlockComponentContext(
        content_block=content_block,
        deltas=deltas,
        completed=True,
        is_prospector_mode=is_prospector_mode,
    )
    return await _get_block_component(content_block).on_completed(context, slackstream_reply)
