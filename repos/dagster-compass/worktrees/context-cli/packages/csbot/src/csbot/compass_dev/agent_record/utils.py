"""Utility functions for agent-record functionality."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

# from csbot.agents.stream_event_agent import SeaEvent, SeaMessage, SeaToolSpec


def create_mock_object(data):
    """Recursively create mock objects from dictionary data."""
    if isinstance(data, dict):
        mock_obj = AsyncMock()
        for key, value in data.items():
            setattr(mock_obj, key, create_mock_object(value))
        return mock_obj
    elif isinstance(data, list):
        return [create_mock_object(item) for item in data]
    else:
        return data


class RecordingMockClient:
    """Mock Anthropic client that replays recorded events."""

    def __init__(self, recording_data: dict[str, Any]):
        self.recording_data = recording_data
        self.messages = MockMessages(recording_data)

    async def close(self):
        """Mock close method."""
        pass


class MockMessages:
    """Mock messages interface that replays recorded events."""

    def __init__(self, recording_data: dict[str, Any]):
        self.recording_data = recording_data

    async def create(self, **kwargs):
        """Mock create method that returns an async generator."""

        async def mock_stream():
            events = self.recording_data["raw_anthropic_events"]

            for event_data in events:
                # Remove our added timestamp and recreate the event
                event_dict = event_data.copy()
                event_dict.pop("timestamp", None)

                # Create a mock event object that has the right structure
                mock_event = create_mock_object(event_dict)

                yield mock_event

        return mock_stream()


async def load_recording(recording_path: Path) -> dict[str, Any]:
    """Load a recording from a JSON file."""
    with open(recording_path, encoding="utf-8") as f:
        return json.load(f)


def discover_recordings(recordings_dir: Path) -> list[Path]:
    """Discover all recording files in the recordings directory."""
    if not recordings_dir.exists():
        return []

    recordings = []
    for json_file in recordings_dir.rglob("*.json"):
        if not json_file.name.startswith("_"):  # Skip private files
            recordings.append(json_file)

    return sorted(recordings)


# async def replay_recording_through_agent(
#     agent, recording_data: dict[str, Any], tools: list[SeaToolSpec] | None = None
# ) -> list[SeaEvent]:
#     """Replay a recording through AnthropicSea and collect events."""
#     # Import here to avoid circular imports

#     # Create mock client
#     mock_client = RecordingMockClient(recording_data)

#     # Parse messages
#     messages = [SeaMessage(**msg) for msg in recording_data["request_params"]["messages"]]

#     events = []
#     with patch.object(agent, "client", mock_client):
#         async for event in agent.stream(
#             messages=messages,
#             model=recording_data["request_params"]["model"],
#             tools=tools,
#             max_tokens=recording_data["request_params"]["max_tokens"],
#             temperature=recording_data["request_params"]["temperature"],
#         ):
#             events.append(event)

#     return events
