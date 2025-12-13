"""Anthropic-specific agent recorder implementation."""

import json
import time
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from anthropic import AsyncAnthropic
from pydantic import BaseModel

from csbot.agents.anthropic.anthropic_agent import DEFAULT_ANTHROPIC_RETRIES, AnthropicAgent
from csbot.agents.anthropic.intercepting_client import InterceptingClient
from csbot.agents.anthropic.recording_agent import RecordedEventDict, RecordingAnthropicAgent
from csbot.agents.messages import AgentMessage
from csbot.compass_dev.agent_record.recorder import AsyncAgentRecorder


class AgentMessageData(BaseModel):
    """Structured representation of an agent message."""

    role: str
    content: str


class RecordingMetadata(BaseModel):
    """Metadata for a recording session."""

    agent_type: str
    recorded_at: str
    scenario: str
    model: str
    raw_event_count: int
    agent_block_event_count: int
    agent_message_count: int
    duration_seconds: float | None
    output_path: str | None


class RequestParams(BaseModel):
    """Parameters used in the request."""

    system: str
    messages: list[AgentMessageData]
    tools: list[str]
    model: str
    max_tokens: int


class AnthropicSpecific(BaseModel):
    """Anthropic-specific metadata."""

    anthropic_client_version: str


class RecordingData(BaseModel):
    """Complete recording data structure."""

    metadata: RecordingMetadata
    request_params: RequestParams
    raw_anthropic_events: list[dict[str, Any]]
    agent_block_events: list[RecordedEventDict]
    agent_messages: list[AgentMessageData]
    anthropic_specific: AnthropicSpecific


class AnthropicRecorder(AsyncAgentRecorder):
    """Records real Anthropic API responses for validation testing."""

    def __init__(self, api_key: str, output_dir: Path | None = None):
        super().__init__(output_dir)
        self.api_key = api_key

    async def record_scenario(
        self,
        scenario_name: str,
        system: str,
        messages: list[AgentMessage],
        model: str = "claude-sonnet-4-20250514",
        tools: Mapping[str, Callable[..., Awaitable[Any]]] | None = None,
        max_tokens: int = 1000,
        save_as: str | None = None,
    ) -> RecordingData:
        """Record a specific scenario with both raw and Agent events.

        Args:
            scenario_name: Name of the scenario being recorded
            system: System prompt for the scenario
            messages: Input messages for the scenario
            model: Model to use for generation
            tools: Optional tools available to the model
            max_tokens: Maximum tokens to generate
            save_as: Optional custom filename
        """
        print(f"🎬 Recording Anthropic scenario: {scenario_name}")
        print("  🤖 Capturing both raw Anthropic and Agent events...")

        start_time = time.time()

        # Always use the unified recording method
        recording = await self._record_with_agent_events(
            scenario_name, system, messages, model, tools, max_tokens
        )

        end_time = time.time()

        # Update duration in the structured metadata
        recording.metadata.duration_seconds = end_time - start_time

        # Save to file
        filename = save_as or f"{scenario_name}.json"
        if not filename.endswith(".json"):
            filename += ".json"

        # Get output path using centralized logic
        output_path = self.get_output_path(scenario_name, filename)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(recording.model_dump(), f, indent=2, ensure_ascii=False)

        print(f"💾 Saved to: {output_path}")

        # Add output path to metadata
        recording.metadata.output_path = str(output_path)

        return recording

    def get_agent_type(self) -> str:
        """Get the agent type identifier."""
        return "anthropic"

    async def close(self) -> None:
        """Clean up resources."""
        # No persistent resources to clean up for Anthropic recorder
        pass

    async def _record_with_agent_events(
        self,
        scenario_name: str,
        system: str,
        messages: list[AgentMessage],
        model: str,
        tools: Mapping[str, Callable[..., Awaitable[Any]]] | None,
        max_tokens: int,
    ) -> RecordingData:
        """Record both raw Anthropic events and Agent events with tool execution."""
        # Create real Anthropic client
        real_client = AsyncAnthropic(api_key=self.api_key, max_retries=DEFAULT_ANTHROPIC_RETRIES)

        # Wrap it with our intercepting client
        intercepting_client = InterceptingClient(real_client)

        # Create base AnthropicAgent with intercepting client
        base_agent = AnthropicAgent(intercepting_client)

        # Wrap it with recording functionality using composition
        agent = RecordingAnthropicAgent(base_agent)

        # Capture agent messages
        agent_messages = []

        async def on_history_added(message: AgentMessage) -> None:
            agent_messages.append(self._agent_message_to_dict(message))

        try:
            async for event in agent.stream_messages_with_tools(
                model=model,
                system=system,
                messages=messages,
                tools=dict(tools) if tools else {},
                max_tokens=max_tokens,
                on_history_added=on_history_added,
            ):
                # Print Agent block event with relevant metadata
                if event.type == "delta":
                    if event.delta.type == "text_delta":
                        text = event.delta.text
                        display_text = text[:47] + "..." if len(text) > 50 else text
                        print(
                            f'  🤖 Captured Agent event: delta - text: "{display_text.replace(chr(10), "\\\\n")}"'
                        )
                    elif event.delta.type == "input_json_delta":
                        print(
                            f"  🤖 Captured Agent event: delta - tool input: {event.delta.partial_json}"
                        )
                elif event.type == "start":
                    if event.content_block.type == "call_tool":
                        print(
                            f"  🤖 Captured Agent event: start - tool: {event.content_block.name} (id: {event.content_block.id})"
                        )
                    else:
                        print(
                            f"  🤖 Captured Agent event: start - type: {event.content_block.type}"
                        )
                elif event.type == "stop":
                    print("  🤖 Captured Agent event: stop")
                else:
                    print(f"  🤖 Captured Agent event: {event.type}")

            # Get the captured events
            raw_events = intercepting_client.get_raw_events()
            agent_block_events = agent.get_recorded_events()

            print(
                f"✅ Captured {len(raw_events)} raw events, {len(agent_block_events)} block events, and {len(agent_messages)} messages"
            )

        except Exception as e:
            print(f"❌ Recording failed: {e}")
            # Print additional context for debugging
            print("  📊 Error context:")
            print(f"    - Model: {model}")
            print(f"    - Max tokens requested: {max_tokens}")
            print(f"    - Input messages: {len(messages)}")
            if messages:
                # Estimate input tokens roughly (4 chars per token)
                total_input_chars = sum(len(str(msg.content)) for msg in messages) + len(system)
                estimated_input_tokens = total_input_chars // 4
                print(f"    - Estimated input tokens: {estimated_input_tokens}")
                print(
                    f"    - Total estimated tokens (input + max output): {estimated_input_tokens + max_tokens}"
                )

            # Check if we captured any raw events before the error
            raw_events = intercepting_client.get_raw_events()
            if raw_events:
                print(f"    - Raw events captured before error: {len(raw_events)}")
                # Look for message_start event which contains actual input token count
                for event in raw_events:
                    if event["type"] == "message_start" and "message" in event:
                        if "usage" in event["message"]:
                            actual_input_tokens = event["message"]["usage"]["input_tokens"]
                            print(f"    - Actual input tokens from API: {actual_input_tokens}")
                            print(
                                f"    - Total tokens if completed (input + max output): {actual_input_tokens + max_tokens}"
                            )
                            break
            else:
                print(
                    "    - No raw events captured before error (API call may have failed immediately)"
                )

            # Show the first part of the input for debugging
            if messages and len(str(messages[0].content)) > 100:
                preview = str(messages[0].content)[:200] + "..."
                print(f"    - Input preview: {preview}")

            raise
        finally:
            await agent.close()
            await real_client.close()

        # Create recording data with structured schema
        recording_data = RecordingData(
            metadata=RecordingMetadata(
                agent_type="anthropic",
                recorded_at=datetime.now(UTC).isoformat(),
                scenario=scenario_name,
                model=model,
                raw_event_count=len(raw_events),
                agent_block_event_count=len(agent_block_events),
                agent_message_count=len(agent_messages),
                duration_seconds=None,
                output_path=None,
            ),
            request_params=RequestParams(
                system=system,
                messages=[self._agent_message_to_dict(msg) for msg in messages],
                tools=list(tools.keys()) if tools else [],
                model=model,
                max_tokens=max_tokens,
            ),
            raw_anthropic_events=raw_events,
            agent_block_events=agent_block_events,
            agent_messages=agent_messages,
            anthropic_specific=AnthropicSpecific(
                anthropic_client_version="0.25.1",
            ),
        )

        return recording_data

    def _agent_message_to_dict(self, message: AgentMessage) -> AgentMessageData:
        """Convert AgentMessage to structured representation."""
        return AgentMessageData(
            role=message.role,
            content=message.content,
        )
