from dataclasses import dataclass


@dataclass(frozen=True)
class TextDelta:
    text: str


@dataclass(frozen=True)
class ToolStart:
    tool_name: str
    tool_use_id: str


@dataclass(frozen=True)
class ToolEnd:
    tool_name: str
    tool_use_id: str


@dataclass(frozen=True)
class TurnStart:
    turn_index: int


@dataclass(frozen=True)
class TurnEnd:
    turn_index: int


@dataclass(frozen=True)
class AgentResult:
    session_id: str | None
    num_turns: int
    input_tokens: int
    output_tokens: int


AgentEvent = TextDelta | ToolStart | ToolEnd | TurnStart | TurnEnd | AgentResult
