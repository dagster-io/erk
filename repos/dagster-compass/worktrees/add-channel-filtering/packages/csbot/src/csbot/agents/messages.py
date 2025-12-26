# Wrapper dataclasses for anthropic types with minimal interfaces
from dataclasses import dataclass
from typing import Any, Literal


@dataclass
class AgentModelSpecificMessage:
    role: Literal["user", "assistant"]
    content: Any


@dataclass
class AgentTextMessage:
    role: Literal["user", "assistant"]
    content: str


AgentMessage = AgentModelSpecificMessage | AgentTextMessage


@dataclass
class AgentTextDelta:
    type: Literal["text_delta"]
    text: str


@dataclass
class AgentInputJSONDelta:
    type: Literal["input_json_delta"]
    partial_json: str


AgentBlockDelta = AgentTextDelta | AgentInputJSONDelta


@dataclass
class AgentToolUseBlock:
    type: Literal["call_tool"]
    id: str
    name: str


@dataclass
class AgentTextBlock:
    type: Literal["output_text"]


AgentContentBlock = AgentToolUseBlock | AgentTextBlock


@dataclass
class AgentStartBlockEvent:
    type: Literal["start"]
    index: int
    content_block: AgentContentBlock


@dataclass
class AgentStopBlockEvent:
    type: Literal["stop"]
    index: int
    # Include the completed block's type to avoid brittle external coupling
    # Values: "text" for AgentTextBlock, "tool" for AgentToolUseBlock
    block_type: Literal["text", "tool"] | None = None


@dataclass
class AgentBlockDeltaEvent:
    type: Literal["delta"]
    index: int
    delta: AgentBlockDelta


AgentBlockEvent = AgentStartBlockEvent | AgentStopBlockEvent | AgentBlockDeltaEvent
