"""
Strongly typed Python classes for Slack Block Kit API.

This module provides type-safe wrappers around Slack's Block Kit API,
using Pydantic for validation and ensuring all required fields are present.

Warning: this was entirely vibe coded and is completely untested.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class BlockType(str, Enum):
    """Enumeration of all available Slack block types."""

    ACTIONS = "actions"
    CONTEXT = "context"
    DIVIDER = "divider"
    FILE = "file"
    HEADER = "header"
    IMAGE = "image"
    INPUT = "input"
    MARKDOWN = "markdown"
    RICH_TEXT = "rich_text"
    SECTION = "section"
    VIDEO = "video"


class ElementType(str, Enum):
    """Enumeration of all available Slack element types."""

    BUTTON = "button"
    CHECKBOXES = "checkboxes"
    DATEPICKER = "datepicker"
    DATETIMEPICKER = "datetimepicker"
    EMAIL_INPUT = "email_input"
    IMAGE = "image"
    MULTI_STATIC_SELECT = "multi_static_select"
    MULTI_USERS_SELECT = "multi_users_select"
    MULTI_CONVERSATIONS_SELECT = "multi_conversations_select"
    MULTI_CHANNELS_SELECT = "multi_channels_select"
    NUMBER_INPUT = "number_input"
    OVERFLOW = "overflow"
    PLAIN_TEXT_INPUT = "plain_text_input"
    RADIO_BUTTONS = "radio_buttons"
    RICH_TEXT_LIST = "rich_text_list"
    RICH_TEXT_PREFORMATTED = "rich_text_preformatted"
    RICH_TEXT_QUOTE = "rich_text_quote"
    RICH_TEXT_SECTION = "rich_text_section"
    SELECT_MENU = "select_menu"
    SELECT_MENU_USERS = "select_menu_users"
    SELECT_MENU_CONVERSATIONS = "select_menu_conversations"
    SELECT_MENU_CHANNELS = "select_menu_channels"
    SELECT_MENU_EXTERNAL = "select_menu_external"
    TIME_PICKER = "time_picker"
    URL_INPUT = "url_input"
    WORKFLOW_BUTTON = "workflow_button"


class TextType(str, Enum):
    """Text type enumeration."""

    PLAIN_TEXT = "plain_text"
    MRKDWN = "mrkdwn"


class ConfirmStyle(str, Enum):
    """Confirmation dialog style."""

    PRIMARY = "primary"
    DANGER = "danger"


class DispatchActionConfig(BaseModel):
    """Configuration for dispatch actions on input elements."""

    trigger_actions_on: list[Literal["on_enter_pressed", "on_character_entered"]] = Field(
        default_factory=list
    )


class Option(BaseModel):
    """A selectable option for select menus, radio buttons, etc."""

    text: "TextObject"
    value: str
    description: Optional["TextObject"] = None
    url: str | None = None


class OptionGroup(BaseModel):
    """A group of options for select menus."""

    label: "TextObject"
    options: list[Option]


class TextObject(BaseModel):
    """Base class for text objects in Slack."""

    type: TextType
    text: str
    emoji: bool | None = None
    verbatim: bool | None = None

    @classmethod
    def plain_text(cls, text: str, emoji: bool = True) -> TextObject:
        """Create a plain text object."""
        return cls(type=TextType.PLAIN_TEXT, text=text, emoji=emoji)

    @classmethod
    def mrkdwn(cls, text: str, verbatim: bool = False) -> TextObject:
        """Create a markdown text object."""
        return cls(type=TextType.MRKDWN, text=text, verbatim=verbatim)


class ConfirmDialog(BaseModel):
    """Confirmation dialog for interactive elements."""

    title: TextObject
    text: TextObject
    confirm: TextObject
    deny: TextObject
    style: ConfirmStyle | None = None


class Element(ABC, BaseModel):
    """Base class for all interactive elements."""

    action_id: str | None = None

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        pass


class ButtonElement(Element):
    """Button element."""

    type: Literal[ElementType.BUTTON] = ElementType.BUTTON
    text: TextObject
    url: str | None = None
    value: str | None = None
    style: Literal["primary", "danger"] | None = None
    confirm: ConfirmDialog | None = None
    accessibility_label: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class CheckboxesElement(Element):
    """Checkboxes element."""

    type: Literal[ElementType.CHECKBOXES] = ElementType.CHECKBOXES
    options: list[Option]
    initial_options: list[Option] | None = None
    confirm: ConfirmDialog | None = None
    focus_on_load: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class DatePickerElement(Element):
    """Date picker element."""

    type: Literal[ElementType.DATEPICKER] = ElementType.DATEPICKER
    placeholder: TextObject | None = None
    initial_date: str | None = None
    confirm: ConfirmDialog | None = None
    focus_on_load: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class DateTimePickerElement(Element):
    """Date and time picker element."""

    type: Literal[ElementType.DATETIMEPICKER] = ElementType.DATETIMEPICKER
    placeholder: TextObject | None = None
    initial_date_time: int | None = None
    confirm: ConfirmDialog | None = None
    focus_on_load: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class EmailInputElement(Element):
    """Email input element."""

    type: Literal[ElementType.EMAIL_INPUT] = ElementType.EMAIL_INPUT
    placeholder: TextObject | None = None
    initial_value: str | None = None
    dispatch_action_config: DispatchActionConfig | None = None
    focus_on_load: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class ImageElement(Element):
    """Image element."""

    type: Literal[ElementType.IMAGE] = ElementType.IMAGE
    image_url: str
    alt_text: str
    fallback: str | None = None
    image_width: int | None = None
    image_height: int | None = None
    image_bytes: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class MultiStaticSelectElement(Element):
    """Multi-static select element."""

    type: Literal[ElementType.MULTI_STATIC_SELECT] = ElementType.MULTI_STATIC_SELECT
    placeholder: TextObject
    options: list[Option] | None = None
    option_groups: list[OptionGroup] | None = None
    initial_options: list[Option] | None = None
    confirm: ConfirmDialog | None = None
    max_selected_items: int | None = None
    focus_on_load: bool | None = None

    @field_validator("options", "option_groups", mode="before")
    @classmethod
    def validate_options_or_groups(cls, v, info):
        if info.field_name == "options" and "option_groups" in info.data:
            if v is not None and info.data["option_groups"] is not None:
                raise ValueError("Cannot specify both options and option_groups")
        elif info.field_name == "option_groups" and "options" in info.data:
            if v is not None and info.data["options"] is not None:
                raise ValueError("Cannot specify both options and option_groups")
        return v

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class MultiUsersSelectElement(Element):
    """Multi-users select element."""

    type: Literal[ElementType.MULTI_USERS_SELECT] = ElementType.MULTI_USERS_SELECT
    placeholder: TextObject
    initial_users: list[str] | None = None
    confirm: ConfirmDialog | None = None
    max_selected_items: int | None = None
    focus_on_load: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class MultiConversationsSelectElement(Element):
    """Multi-conversations select element."""

    type: Literal[ElementType.MULTI_CONVERSATIONS_SELECT] = ElementType.MULTI_CONVERSATIONS_SELECT
    placeholder: TextObject
    initial_conversations: list[str] | None = None
    confirm: ConfirmDialog | None = None
    max_selected_items: int | None = None
    focus_on_load: bool | None = None
    filter: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class MultiChannelsSelectElement(Element):
    """Multi-channels select element."""

    type: Literal[ElementType.MULTI_CHANNELS_SELECT] = ElementType.MULTI_CHANNELS_SELECT
    placeholder: TextObject
    initial_channels: list[str] | None = None
    confirm: ConfirmDialog | None = None
    max_selected_items: int | None = None
    focus_on_load: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class NumberInputElement(Element):
    """Number input element."""

    type: Literal[ElementType.NUMBER_INPUT] = ElementType.NUMBER_INPUT
    placeholder: TextObject | None = None
    initial_value: str | None = None
    min_value: str | None = None
    max_value: str | None = None
    decimal_allowed: bool | None = None
    dispatch_action_config: DispatchActionConfig | None = None
    focus_on_load: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class OverflowElement(Element):
    """Overflow menu element."""

    type: Literal[ElementType.OVERFLOW] = ElementType.OVERFLOW
    options: list[Option]
    confirm: ConfirmDialog | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class PlainTextInputElement(Element):
    """Plain text input element."""

    type: Literal[ElementType.PLAIN_TEXT_INPUT] = ElementType.PLAIN_TEXT_INPUT
    placeholder: TextObject | None = None
    initial_value: str | None = None
    multiline: bool | None = None
    min_length: int | None = None
    max_length: int | None = None
    dispatch_action_config: DispatchActionConfig | None = None
    focus_on_load: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class RadioButtonsElement(Element):
    """Radio buttons element."""

    type: Literal[ElementType.RADIO_BUTTONS] = ElementType.RADIO_BUTTONS
    options: list[Option]
    initial_option: Option | None = None
    confirm: ConfirmDialog | None = None
    focus_on_load: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class SelectMenuElement(Element):
    """Static select menu element."""

    type: Literal[ElementType.SELECT_MENU] = ElementType.SELECT_MENU
    placeholder: TextObject
    options: list[Option] | None = None
    option_groups: list[OptionGroup] | None = None
    initial_option: Option | None = None
    confirm: ConfirmDialog | None = None
    focus_on_load: bool | None = None

    @field_validator("options", "option_groups", mode="before")
    @classmethod
    def validate_options_or_groups(cls, v, info):
        if info.field_name == "options" and "option_groups" in info.data:
            if v is not None and info.data["option_groups"] is not None:
                raise ValueError("Cannot specify both options and option_groups")
        elif info.field_name == "option_groups" and "options" in info.data:
            if v is not None and info.data["options"] is not None:
                raise ValueError("Cannot specify both options and option_groups")
        return v

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class SelectMenuUsersElement(Element):
    """Users select menu element."""

    type: Literal[ElementType.SELECT_MENU_USERS] = ElementType.SELECT_MENU_USERS
    placeholder: TextObject
    initial_user: str | None = None
    confirm: ConfirmDialog | None = None
    focus_on_load: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class SelectMenuConversationsElement(Element):
    """Conversations select menu element."""

    type: Literal[ElementType.SELECT_MENU_CONVERSATIONS] = ElementType.SELECT_MENU_CONVERSATIONS
    placeholder: TextObject
    initial_conversation: str | None = None
    confirm: ConfirmDialog | None = None
    focus_on_load: bool | None = None
    filter: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class SelectMenuChannelsElement(Element):
    """Channels select menu element."""

    type: Literal[ElementType.SELECT_MENU_CHANNELS] = ElementType.SELECT_MENU_CHANNELS
    placeholder: TextObject
    initial_channel: str | None = None
    confirm: ConfirmDialog | None = None
    focus_on_load: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class SelectMenuExternalElement(Element):
    """External select menu element."""

    type: Literal[ElementType.SELECT_MENU_EXTERNAL] = ElementType.SELECT_MENU_EXTERNAL
    placeholder: TextObject
    initial_option: Option | None = None
    min_query_length: int | None = None
    confirm: ConfirmDialog | None = None
    focus_on_load: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class TimePickerElement(Element):
    """Time picker element."""

    type: Literal[ElementType.TIME_PICKER] = ElementType.TIME_PICKER
    placeholder: TextObject | None = None
    initial_time: str | None = None
    confirm: ConfirmDialog | None = None
    focus_on_load: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class UrlInputElement(Element):
    """URL input element."""

    type: Literal[ElementType.URL_INPUT] = ElementType.URL_INPUT
    placeholder: TextObject | None = None
    initial_value: str | None = None
    dispatch_action_config: DispatchActionConfig | None = None
    focus_on_load: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class WorkflowButtonElement(Element):
    """Workflow button element."""

    type: Literal[ElementType.WORKFLOW_BUTTON] = ElementType.WORKFLOW_BUTTON
    text: TextObject
    style: Literal["primary", "danger"] | None = None
    accessibility_label: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class RichTextElement(BaseModel):
    """Base class for rich text elements."""

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class RichTextBroadcastElement(RichTextElement):
    """Rich text broadcast element."""

    type: Literal["broadcast"] = "broadcast"
    range: str


class RichTextColorElement(RichTextElement):
    """Rich text color element."""

    type: Literal["color"] = "color"
    value: str


class RichTextChannelElement(RichTextElement):
    """Rich text channel element."""

    type: Literal["channel"] = "channel"
    channel_id: str


class RichTextDateElement(RichTextElement):
    """Rich text date element."""

    type: Literal["date"] = "date"
    timestamp: str
    format: str | None = None
    fallback: str | None = None


class RichTextEmojiElement(RichTextElement):
    """Rich text emoji element."""

    type: Literal["emoji"] = "emoji"
    name: str
    unicode: str | None = None
    skin_tone: int | None = None


class RichTextLinkElement(RichTextElement):
    """Rich text link element."""

    type: Literal["link"] = "link"
    url: str
    text: str | None = None


class RichTextTextElement(RichTextElement):
    """Rich text text element."""

    type: Literal["text"] = "text"
    text: str
    style: dict[str, Any] | None = None


class RichTextUserElement(RichTextElement):
    """Rich text user element."""

    type: Literal["user"] = "user"
    user_id: str


class RichTextUsergroupElement(RichTextElement):
    """Rich text usergroup element."""

    type: Literal["usergroup"] = "usergroup"
    usergroup_id: str


# Union type for all rich text elements
RichTextElementUnion = (
    RichTextBroadcastElement
    | RichTextColorElement
    | RichTextChannelElement
    | RichTextDateElement
    | RichTextEmojiElement
    | RichTextLinkElement
    | RichTextTextElement
    | RichTextUserElement
    | RichTextUsergroupElement
)


class RichTextSectionElement(Element):
    """Rich text section element."""

    type: Literal[ElementType.RICH_TEXT_SECTION] = ElementType.RICH_TEXT_SECTION
    elements: list["RichTextElementUnion"]

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class RichTextListElement(Element):
    """Rich text list element."""

    type: Literal[ElementType.RICH_TEXT_LIST] = ElementType.RICH_TEXT_LIST
    elements: list["RichTextElementUnion"]
    style: Literal["bullet", "ordered"] = "bullet"
    indent: int | None = None
    border: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class RichTextQuoteElement(Element):
    """Rich text quote element."""

    type: Literal[ElementType.RICH_TEXT_QUOTE] = ElementType.RICH_TEXT_QUOTE
    elements: list["RichTextElementUnion"]
    border: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class RichTextPreformattedElement(Element):
    """Rich text preformatted element."""

    type: Literal[ElementType.RICH_TEXT_PREFORMATTED] = ElementType.RICH_TEXT_PREFORMATTED
    elements: list["RichTextElementUnion"]
    border: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


# Union type for all elements
ElementUnion = (
    ButtonElement
    | CheckboxesElement
    | DatePickerElement
    | DateTimePickerElement
    | EmailInputElement
    | ImageElement
    | MultiStaticSelectElement
    | MultiUsersSelectElement
    | MultiConversationsSelectElement
    | MultiChannelsSelectElement
    | NumberInputElement
    | OverflowElement
    | PlainTextInputElement
    | RadioButtonsElement
    | RichTextListElement
    | RichTextPreformattedElement
    | RichTextQuoteElement
    | RichTextSectionElement
    | SelectMenuElement
    | SelectMenuUsersElement
    | SelectMenuConversationsElement
    | SelectMenuChannelsElement
    | SelectMenuExternalElement
    | TimePickerElement
    | UrlInputElement
    | WorkflowButtonElement
)


class Block(ABC, BaseModel):
    """Base class for all blocks."""

    block_id: str | None = None

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        pass

    @abstractmethod
    def to_markdown(self) -> str | None:
        """Convert to markdown representation."""
        pass


class ActionsBlock(Block):
    """Actions block containing interactive elements."""

    type: Literal[BlockType.ACTIONS] = BlockType.ACTIONS
    elements: list[ElementUnion]

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)

    def to_markdown(self) -> str | None:
        """Convert to markdown representation."""
        return None


class ContextBlock(Block):
    """Context block for displaying context information."""

    type: Literal[BlockType.CONTEXT] = BlockType.CONTEXT
    elements: list[TextObject | ImageElement]

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)

    def to_markdown(self) -> str | None:
        """Convert to markdown representation."""
        context_parts = []
        for element in self.elements:
            if isinstance(element, TextObject):
                context_parts.append(element.text)
            elif isinstance(element, ImageElement):
                context_parts.append(f"![{element.alt_text}]({element.image_url})")

        return " ".join(context_parts) if context_parts else ""


class DividerBlock(Block):
    """Divider block for visual separation."""

    type: Literal[BlockType.DIVIDER] = BlockType.DIVIDER

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)

    def to_markdown(self) -> str | None:
        """Convert to markdown representation."""
        return "---"


class FileBlock(Block):
    """File block for displaying files."""

    type: Literal[BlockType.FILE] = BlockType.FILE
    external_id: str
    source: Literal["remote"] = "remote"

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)

    def to_markdown(self) -> str | None:
        """Convert to markdown representation."""
        return "(file)"


class HeaderBlock(Block):
    """Header block for section headers."""

    type: Literal[BlockType.HEADER] = BlockType.HEADER
    text: TextObject

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)

    def to_markdown(self) -> str | None:
        """Convert to markdown representation."""
        return f"*{self.text.text}*\n"


class SlackFile(BaseModel):
    id: str | None = None
    url: str | None = None


class ImageBlock(Block):
    """Image block for displaying images."""

    type: Literal[BlockType.IMAGE] = BlockType.IMAGE
    image_url: str | None = None
    slack_file: SlackFile | None = None
    alt_text: str
    title: TextObject | None = None
    fallback: str | None = None
    image_width: int | None = None
    image_height: int | None = None
    image_bytes: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)

    def to_markdown(self) -> str | None:
        """Convert to markdown representation."""
        return "(image)"


class InputBlock(Block):
    """Input block for collecting user input."""

    type: Literal[BlockType.INPUT] = BlockType.INPUT
    label: TextObject
    element: ElementUnion
    hint: TextObject | None = None
    optional: bool | None = None
    dispatch_action: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)

    def to_markdown(self) -> str | None:
        """Convert to markdown representation."""
        return None


def sanitize_slack_markdown(text: str) -> str:
    """Sanitize Slack markdown to avoid API errors.

    Slack has a bug where user mentions within code blocks
    fail the API request. LLM has been known to generate these so
    we sanitize them out.
    """

    mention_pattern = r"<@[A-Z][0-9A-Z]+>"

    # Finally, handle a mention that occurs anywhere in a multi-line code block
    # by just removing the angle brackets
    def replace_mentions_in_multiline_backtick(match: re.Match[str]) -> str:
        lang = match.group(1) or ""
        content = match.group(2)
        # Remove angle brackets from mentions: <@U123> -> @U123
        sanitized = re.sub(
            mention_pattern, lambda m: m.group(0).replace("<", "").replace(">", ""), content
        )
        return f"```{lang}\n{sanitized}```"

    text = re.sub(
        r"```([^\n]*)\n(.*?)```", replace_mentions_in_multiline_backtick, text, flags=re.DOTALL
    )

    def replace_mentions_in_single_backtick(match: re.Match[str]) -> str:
        full_text = match.group(1)[1:-1]
        chunks = re.split(f"({mention_pattern})", full_text)
        transformed_chunks = []
        for i in range(len(chunks)):
            is_mention = i % 2 == 1
            chunk = chunks[i]
            if not is_mention:
                is_first = i == 0
                is_last = i == len(chunks) - 1
                if not is_first and chunk.startswith(" "):
                    chunk = chunk[1:]
                if not is_last and chunk.endswith(" "):
                    chunk = chunk[:-1]

                if len(chunk) == 0:
                    continue
                transformed_chunks.append(f"`{chunk}`")
            else:
                transformed_chunks.append(chunk)
        return " ".join(transformed_chunks)

    text = re.sub(r"(`[^`]+`)", replace_mentions_in_single_backtick, text)
    return text


class MarkdownBlock(Block):
    """Markdown block for displaying formatted text."""

    type: Literal[BlockType.MARKDOWN] = BlockType.MARKDOWN
    text: str

    def model_post_init(self, __context: Any):
        self.text = sanitize_slack_markdown(self.text)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)

    def to_markdown(self) -> str | None:
        """Convert to markdown representation."""
        return self.text


def _rich_text_element_to_markdown(element: RichTextElementUnion) -> str:
    """Convert a rich text element to markdown representation."""
    if isinstance(element, RichTextTextElement):
        text = element.text
        # Apply styling if present
        if element.style:
            if element.style.get("bold"):
                text = f"**{text}**"
            if element.style.get("italic"):
                text = f"*{text}*"
            if element.style.get("strike"):
                text = f"~~{text}~~"
            if element.style.get("code"):
                text = f"`{text}`"
        return text
    elif isinstance(element, RichTextLinkElement):
        if element.text:
            return f"[{element.text}]({element.url})"
        else:
            return element.url
    elif isinstance(element, RichTextEmojiElement):
        return f":{element.name}:"
    elif isinstance(element, RichTextUserElement):
        return f"<@{element.user_id}>"
    elif isinstance(element, RichTextChannelElement):
        return f"<#{element.channel_id}>"
    elif isinstance(element, RichTextDateElement):
        if element.fallback:
            return element.fallback
        else:
            return f"<!date^{element.timestamp}^{element.format or 'default'}|date>"
    elif isinstance(element, RichTextBroadcastElement):
        return f"<!here|{element.range}>"
    elif isinstance(element, RichTextColorElement):
        return f"`{element.value}`"
    elif isinstance(element, RichTextUsergroupElement):
        return f"<!subteam^{element.usergroup_id}|usergroup>"
    else:
        # Unknown element type, return empty string
        return ""


class RichTextBlock(Block):
    """Rich text block for displaying formatted content."""

    type: Literal[BlockType.RICH_TEXT] = BlockType.RICH_TEXT
    elements: list[
        RichTextSectionElement
        | RichTextListElement
        | RichTextQuoteElement
        | RichTextPreformattedElement
    ]

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)

    def to_markdown(self) -> str | None:
        """Convert to markdown representation."""
        markdown_parts = []
        for element in self.elements:
            if isinstance(element, RichTextSectionElement):
                # Convert rich text section elements to markdown
                section_parts = []
                for rich_element in element.elements:
                    section_parts.append(_rich_text_element_to_markdown(rich_element))
                markdown_parts.append("".join(section_parts))
            elif isinstance(element, RichTextListElement):
                # Convert list elements
                for i, rich_element in enumerate(element.elements):
                    element_text = _rich_text_element_to_markdown(rich_element)
                    if element.style == "ordered":
                        markdown_parts.append(f"{i + 1}. {element_text}")
                    else:
                        markdown_parts.append(f"• {element_text}")
            elif isinstance(element, RichTextQuoteElement):
                # Convert quote elements
                for rich_element in element.elements:
                    element_text = _rich_text_element_to_markdown(rich_element)
                    markdown_parts.append(f"> {element_text}")
            elif isinstance(element, RichTextPreformattedElement):
                # Convert preformatted elements
                preformatted_parts = []
                for rich_element in element.elements:
                    preformatted_parts.append(_rich_text_element_to_markdown(rich_element))
                preformatted_text = "".join(preformatted_parts)
                markdown_parts.append(f"```\n{preformatted_text}\n```")

        return "\n".join(markdown_parts) if markdown_parts else None


class SectionBlock(Block):
    """Section block for displaying text and optional accessory."""

    type: Literal[BlockType.SECTION] = BlockType.SECTION
    text: TextObject | None = None
    fields: list[TextObject] | None = None
    accessory: ElementUnion | None = None
    expand: bool | None = None

    @field_validator("text", "fields", mode="before")
    @classmethod
    def validate_text_or_fields(cls, v, info):
        data = info.data
        if "text" in data and "fields" in data:
            if data["text"] is None and data["fields"] is None:
                raise ValueError("Either text or fields must be specified")
        return v

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)

    def to_markdown(self) -> str | None:
        """Convert to markdown representation."""
        parts = []

        if self.text:
            parts.append(self.text.text)

        if self.fields:
            field_texts = [field.text for field in self.fields]
            parts.append(" | ".join(field_texts))

        return " ".join(parts) if parts else None


class VideoBlock(Block):
    """Video block for displaying videos."""

    type: Literal[BlockType.VIDEO] = BlockType.VIDEO
    title: TextObject
    title_url: str
    description: TextObject | None = None
    video_url: str
    thumbnail_url: str | None = None
    alt_text: str | None = None
    author_name: str | None = None
    provider_name: str | None = None
    provider_icon_url: str | None = None
    title_url_domain: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)

    def to_markdown(self) -> str | None:
        """Convert to markdown representation."""
        return "(video)"


# Union type for all blocks
BlockUnion = (
    ActionsBlock
    | ContextBlock
    | DividerBlock
    | FileBlock
    | HeaderBlock
    | ImageBlock
    | InputBlock
    | MarkdownBlock
    | RichTextBlock
    | SectionBlock
    | VideoBlock
)


class BlockKitBuilder:
    """Builder class for creating Block Kit layouts easily."""

    def __init__(self):
        self.blocks: list[BlockUnion] = []

    def add_header(self, text: str, block_id: str | None = None) -> BlockKitBuilder:
        """Add a header block."""
        self.blocks.append(HeaderBlock(text=TextObject.plain_text(text), block_id=block_id))
        return self

    def add_section(
        self,
        text: str | None = None,
        fields: list[str] | None = None,
        accessory: ElementUnion | None = None,
        block_id: str | None = None,
    ) -> BlockKitBuilder:
        """Add a section block."""
        text_obj = TextObject.mrkdwn(text) if text else None
        field_objs = [TextObject.mrkdwn(field) for field in fields] if fields else None

        self.blocks.append(
            SectionBlock(text=text_obj, fields=field_objs, accessory=accessory, block_id=block_id)
        )
        return self

    def add_divider(self, block_id: str | None = None) -> BlockKitBuilder:
        """Add a divider block."""
        self.blocks.append(DividerBlock(block_id=block_id))
        return self

    def add_context(
        self, elements: list[str | ImageElement], block_id: str | None = None
    ) -> BlockKitBuilder:
        """Add a context block."""
        context_elements = []
        for element in elements:
            if isinstance(element, str):
                context_elements.append(TextObject.mrkdwn(element))
            else:
                context_elements.append(element)

        self.blocks.append(ContextBlock(elements=context_elements, block_id=block_id))
        return self

    def add_actions(
        self, elements: list[ElementUnion], block_id: str | None = None
    ) -> BlockKitBuilder:
        """Add an actions block."""
        self.blocks.append(ActionsBlock(elements=elements, block_id=block_id))
        return self

    def add_input(
        self,
        label: str,
        element: ElementUnion,
        hint: str | None = None,
        optional: bool | None = None,
        block_id: str | None = None,
    ) -> BlockKitBuilder:
        """Add an input block."""
        hint_obj = TextObject.plain_text(hint) if hint else None

        self.blocks.append(
            InputBlock(
                label=TextObject.plain_text(label),
                element=element,
                hint=hint_obj,
                optional=optional,
                block_id=block_id,
            )
        )
        return self

    def add_image(
        self,
        image_url: str,
        alt_text: str,
        title: str | None = None,
        block_id: str | None = None,
    ) -> BlockKitBuilder:
        """Add an image block."""
        title_obj = TextObject.plain_text(title) if title else None

        self.blocks.append(
            ImageBlock(
                image_url=image_url,
                alt_text=alt_text,
                title=title_obj,
                block_id=block_id,
            )
        )
        return self

    def add_markdown(self, text: str, block_id: str | None = None) -> BlockKitBuilder:
        """Add a markdown block."""
        self.blocks.append(MarkdownBlock(text=text, block_id=block_id))
        return self

    def add_rich_text(
        self,
        elements: list[
            RichTextSectionElement
            | RichTextListElement
            | RichTextQuoteElement
            | RichTextPreformattedElement
        ],
        block_id: str | None = None,
    ) -> BlockKitBuilder:
        """Add a rich text block."""
        self.blocks.append(RichTextBlock(elements=elements, block_id=block_id))
        return self

    def build(self) -> list[dict[str, Any]]:
        """Build the final Block Kit structure."""
        return [block.to_dict() for block in self.blocks]

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.build(), indent=2)


class FormField(BaseModel):
    id: str
    label: str
    placeholder: str = ""
    hint: str = ""
    initial_value: str = ""
    multiline: bool = False
    min_length: int = 0
    max_length: int = 0


# Convenience functions for creating common elements
def create_button(
    text: str,
    action_id: str | None = None,
    url: str | None = None,
    value: str | None = None,
    style: Literal["primary", "danger"] | None = None,
    confirm: ConfirmDialog | None = None,
) -> ButtonElement:
    """Create a button element."""
    return ButtonElement(
        text=TextObject.plain_text(text),
        action_id=action_id,
        url=url,
        value=value,
        style=style,
        confirm=confirm,
    )


def create_text_input(
    action_id: str | None = None,
    placeholder: str | None = None,
    initial_value: str | None = None,
    multiline: bool = False,
    min_length: int | None = None,
    max_length: int | None = None,
) -> PlainTextInputElement:
    """Create a plain text input element."""
    placeholder_obj = TextObject.plain_text(placeholder) if placeholder else None

    return PlainTextInputElement(
        action_id=action_id,
        placeholder=placeholder_obj,
        initial_value=initial_value,
        multiline=multiline,
        min_length=min_length,
        max_length=max_length,
    )


def create_select_menu(
    placeholder: str,
    options: list[dict[str, str]],
    action_id: str | None = None,
    initial_option: dict[str, str] | None = None,
) -> SelectMenuElement:
    """Create a select menu element."""
    option_objects = [
        Option(text=TextObject.plain_text(opt["text"]), value=opt["value"]) for opt in options
    ]

    initial_option_obj = None
    if initial_option:
        initial_option_obj = Option(
            text=TextObject.plain_text(initial_option["text"]),
            value=initial_option["value"],
        )

    return SelectMenuElement(
        action_id=action_id,
        placeholder=TextObject.plain_text(placeholder),
        options=option_objects,
        initial_option=initial_option_obj,
    )


def create_confirm_dialog(
    title: str,
    text: str,
    confirm_text: str = "Yes",
    deny_text: str = "No",
    style: ConfirmStyle | None = None,
) -> ConfirmDialog:
    """Create a confirmation dialog."""
    return ConfirmDialog(
        title=TextObject.plain_text(title),
        text=TextObject.plain_text(text),
        confirm=TextObject.plain_text(confirm_text),
        deny=TextObject.plain_text(deny_text),
        style=style,
    )


def create_rich_text_element(
    text: str,
    element_type: str = "text",
    url: str | None = None,
    user_id: str | None = None,
    channel_id: str | None = None,
    timestamp: str | None = None,
    style: dict[str, Any] | None = None,
) -> RichTextElementUnion:
    """Create a rich text element."""
    if element_type == "text":
        return RichTextTextElement(text=text, style=style)
    elif element_type == "link":
        return RichTextLinkElement(url=url or "", text=text)
    elif element_type == "user":
        return RichTextUserElement(user_id=user_id or "")
    elif element_type == "channel":
        return RichTextChannelElement(channel_id=channel_id or "")
    elif element_type == "date":
        return RichTextDateElement(timestamp=timestamp or "", fallback=text)
    elif element_type == "emoji":
        return RichTextEmojiElement(name=text)
    elif element_type == "broadcast":
        return RichTextBroadcastElement(range=text)
    elif element_type == "color":
        return RichTextColorElement(value=text)
    elif element_type == "usergroup":
        return RichTextUsergroupElement(usergroup_id=user_id or "")
    else:
        # Default to text element
        return RichTextTextElement(text=text, style=style)


def create_rich_text_section(
    elements: list[RichTextElementUnion],
    action_id: str | None = None,
) -> RichTextSectionElement:
    """Create a rich text section element."""
    return RichTextSectionElement(
        type=ElementType.RICH_TEXT_SECTION,
        elements=elements,
        action_id=action_id,
    )


def create_rich_text_list(
    elements: list[RichTextElementUnion],
    style: Literal["bullet", "ordered"] = "bullet",
    indent: int | None = None,
    border: int | None = None,
    action_id: str | None = None,
) -> RichTextListElement:
    """Create a rich text list element."""
    return RichTextListElement(
        type=ElementType.RICH_TEXT_LIST,
        elements=elements,
        style=style,
        indent=indent,
        border=border,
        action_id=action_id,
    )


def create_rich_text_quote(
    elements: list[RichTextElementUnion],
    border: int | None = None,
    action_id: str | None = None,
) -> RichTextQuoteElement:
    """Create a rich text quote element."""
    return RichTextQuoteElement(
        type=ElementType.RICH_TEXT_QUOTE,
        elements=elements,
        border=border,
        action_id=action_id,
    )


def create_rich_text_preformatted(
    elements: list[RichTextElementUnion],
    border: int | None = None,
    action_id: str | None = None,
) -> RichTextPreformattedElement:
    """Create a rich text preformatted element."""
    return RichTextPreformattedElement(
        type=ElementType.RICH_TEXT_PREFORMATTED,
        elements=elements,
        border=border,
        action_id=action_id,
    )


# Example usage and utility functions
def create_simple_message(text: str) -> list[dict[str, Any]]:
    """Create a simple message with just text."""
    return BlockKitBuilder().add_section(text=text).build()


def create_markdown_message(text: str) -> list[dict[str, Any]]:
    """Create a message with markdown formatting."""
    return BlockKitBuilder().add_markdown(text=text).build()


def create_rich_text_message(
    elements: list[
        RichTextSectionElement
        | RichTextListElement
        | RichTextQuoteElement
        | RichTextPreformattedElement
    ],
) -> list[dict[str, Any]]:
    """Create a message with rich text formatting."""
    return BlockKitBuilder().add_rich_text(elements=elements).build()


def create_form(
    title: str, fields: list[FormField], submit_button_text: str = "Submit"
) -> list[dict[str, Any]]:
    """Create a form with multiple input fields."""
    builder = BlockKitBuilder().add_header(title)

    for field in fields:
        input_element = create_text_input(
            action_id=field.id,
            placeholder=field.placeholder,
            initial_value=field.initial_value if field.initial_value else None,
            multiline=field.multiline,
            min_length=field.min_length if field.min_length > 0 else None,
            max_length=field.max_length if field.max_length > 0 else None,
        )
        builder.add_input(
            label=field.label,
            element=input_element,
            hint=field.hint if field.hint else None,
        )

    submit_button = create_button(text=submit_button_text, action_id="submit", style="primary")
    builder.add_actions([submit_button])

    return builder.build()


# Type aliases for convenience
BlockKit = list[dict[str, Any]]
BlockKitMessage = dict[str, str | BlockKit]
