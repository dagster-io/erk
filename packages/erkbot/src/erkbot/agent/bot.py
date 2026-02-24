from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, query

from erkbot.agent.events import AgentEvent
from erkbot.agent.stream import stream_agent_events


@dataclass(frozen=True)
class ErkBot:
    model: str
    max_turns: int
    cwd: Path
    system_prompt: str
    permission_mode: str

    async def chat_stream(self, *, prompt: str) -> AsyncIterator[AgentEvent]:
        options = ClaudeAgentOptions(
            model=self.model,
            max_turns=self.max_turns,
            cwd=str(self.cwd),
            system_prompt=self.system_prompt,
            permission_mode=self.permission_mode,  # type: ignore[arg-type]
        )
        messages = query(prompt=prompt, options=options)
        async for event in stream_agent_events(messages=messages):
            yield event
