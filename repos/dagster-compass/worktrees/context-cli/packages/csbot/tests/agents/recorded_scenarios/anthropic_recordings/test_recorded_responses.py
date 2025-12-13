"""Tests for recorded scenarios to verify response format consistency and data integrity."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
import yaml


class TestRecordedResponses:
    """Test suite for recorded scenario responses."""

    @pytest.fixture
    def scenarios_config(self):
        """Load scenarios configuration from YAML file."""
        config_path = Path(__file__).parent / "scenarios.yaml"
        with open(config_path) as f:
            return yaml.safe_load(f)

    @pytest.fixture
    def recordings_dir(self):
        """Get the recordings directory path."""
        return Path(__file__).parent / "recordings"

    def get_recording_files(self, recordings_dir: Path) -> list[Path]:
        """Get all JSON recording files."""
        return list(recordings_dir.rglob("*.json"))

    @pytest.fixture
    def recording_files(self, recordings_dir):
        """Get all recording JSON files."""
        return self.get_recording_files(recordings_dir)

    def load_recording(self, file_path: Path) -> dict[str, Any]:
        """Load a recording JSON file."""
        with open(file_path) as f:
            return json.load(f)

    def test_recording_directory_structure(self, recordings_dir):
        """Test that recordings are organized in expected directory structure."""
        expected_subdirs = ["text-responses", "tool-calling", "edge-cases", "error-cases"]

        for subdir in expected_subdirs:
            subdir_path = recordings_dir / subdir
            assert subdir_path.exists() and subdir_path.is_dir(), (
                f"Expected recording subdirectory missing: {subdir}"
            )

        # Each subdirectory should contain at least one recording
        for subdir in expected_subdirs:
            subdir_path = recordings_dir / subdir
            json_files = list(subdir_path.glob("*.json"))
            assert len(json_files) > 0, f"Recording subdirectory {subdir} contains no JSON files"

    def test_all_scenarios_have_recordings(self, scenarios_config, recordings_dir):
        """Test that all scenarios defined in scenarios.yaml have corresponding recordings."""
        scenario_names = set(scenarios_config["scenarios"].keys())

        # Get all recording files and extract scenario names
        recording_files = self.get_recording_files(recordings_dir)
        recorded_scenarios = set()

        for file_path in recording_files:
            recording = self.load_recording(file_path)
            recorded_scenarios.add(recording["metadata"]["scenario"])

        # Check that all scenarios have recordings
        missing_recordings = scenario_names - recorded_scenarios
        assert not missing_recordings, f"Scenarios missing recordings: {missing_recordings}"

    def test_no_extra_recordings(self, scenarios_config, recordings_dir):
        """Test that there are no recordings for undefined scenarios."""
        scenario_names = set(scenarios_config["scenarios"].keys())

        # Get all recording files and extract scenario names
        recording_files = self.get_recording_files(recordings_dir)
        recorded_scenarios = set()

        for file_path in recording_files:
            recording = self.load_recording(file_path)
            recorded_scenarios.add(recording["metadata"]["scenario"])

        # Check that all recordings have corresponding scenarios
        extra_recordings = recorded_scenarios - scenario_names
        assert not extra_recordings, f"Recordings for undefined scenarios: {extra_recordings}"

    def test_recording_has_required_metadata(self, recording_files):
        """Test that all recordings have required metadata fields."""
        for recording_file in recording_files:
            recording = self.load_recording(recording_file)

            assert "metadata" in recording, f"Recording {recording_file.name} missing metadata"
            metadata = recording["metadata"]

            required_fields = [
                "recorded_at",
                "scenario",
                "model",
                "agent_type",
                "anthropic_client_version",
                "recorder_version",
                "raw_event_count",
                "agent_block_event_count",
                "agent_message_count",
                "duration_seconds",
            ]

            for field in required_fields:
                assert field in metadata, (
                    f"Recording {recording_file.name} missing metadata field: {field}"
                )

            # Validate types
            assert isinstance(metadata["recorded_at"], str)
            assert isinstance(metadata["scenario"], str)
            assert isinstance(metadata["model"], str)
            assert isinstance(metadata["agent_type"], str)
            assert isinstance(metadata["anthropic_client_version"], str)
            assert isinstance(metadata["recorder_version"], str)
            assert isinstance(metadata["raw_event_count"], int)
            assert isinstance(metadata["agent_block_event_count"], int)
            assert isinstance(metadata["agent_message_count"], int)
            assert isinstance(metadata["duration_seconds"], int | float)

            # Validate values
            assert metadata["raw_event_count"] > 0
            assert metadata["agent_block_event_count"] >= 0
            assert metadata["agent_message_count"] > 0
            assert metadata["duration_seconds"] > 0

    def test_recording_has_required_structure(self, recording_files):
        """Test that all recordings have the expected top-level structure."""
        for recording_file in recording_files:
            recording = self.load_recording(recording_file)

            required_sections = [
                "metadata",
                "request_params",
                "raw_anthropic_events",
                "agent_block_events",
                "agent_messages",
            ]

            for section in required_sections:
                assert section in recording, (
                    f"Recording {recording_file.name} missing section: {section}"
                )

    def test_request_params_structure(self, recording_files):
        """Test that request_params has the expected structure."""
        for recording_file in recording_files:
            recording = self.load_recording(recording_file)
            request_params = recording["request_params"]

            required_fields = ["system", "messages", "tools", "model", "max_tokens"]

            for field in required_fields:
                assert field in request_params, (
                    f"Recording {recording_file.name} missing request_params field: {field}"
                )

            # Validate types
            assert isinstance(request_params["system"], str)
            assert isinstance(request_params["messages"], list)
            assert isinstance(request_params["tools"], list)
            assert isinstance(request_params["model"], str)
            assert isinstance(request_params["max_tokens"], int)

            # Messages should have role and content
            for msg in request_params["messages"]:
                assert "role" in msg
                assert "content" in msg
                assert msg["role"] in ["user", "assistant"]

    def test_raw_anthropic_events_structure(self, recording_files):
        """Test that raw_anthropic_events has valid event structure."""
        for recording_file in recording_files:
            recording = self.load_recording(recording_file)
            events = recording["raw_anthropic_events"]

            assert isinstance(events, list)
            assert len(events) > 0, f"Recording {recording_file.name} has no raw events"

            # All events should have type and timestamp
            for event in events:
                assert "type" in event, f"Event missing type: {event}"
                assert "timestamp" in event, f"Event missing timestamp: {event}"
                assert isinstance(event["type"], str)
                assert isinstance(event["timestamp"], str)

            # First event should be message_start
            assert events[0]["type"] == "message_start"

            # Last event should be message_stop
            assert events[-1]["type"] == "message_stop"

    def test_agent_block_events_structure(self, recording_files):
        """Test that agent_block_events has valid structure."""
        for recording_file in recording_files:
            recording = self.load_recording(recording_file)
            events = recording["agent_block_events"]

            assert isinstance(events, list)

            # All events should have required fields
            for event in events:
                assert "type" in event
                assert "event" in event
                assert "timestamp" in event
                assert event["type"] == "agent_block_event"

                inner_event = event["event"]
                assert "type" in inner_event
                assert "index" in inner_event
                assert inner_event["type"] in ["start", "delta", "stop"]

    def test_agent_messages_structure(self, recording_files):
        """Test that agent_messages has valid structure."""
        for recording_file in recording_files:
            recording = self.load_recording(recording_file)
            messages = recording["agent_messages"]

            assert isinstance(messages, list)
            assert len(messages) > 0, f"Recording {recording_file.name} has no agent messages"

            for msg in messages:
                assert "role" in msg
                assert "content" in msg
                # Role should be user or assistant
                assert msg["role"] in ["user", "assistant"]

    def test_event_counts_match_metadata(self, recording_files):
        """Test that event counts in metadata match actual event counts."""
        for recording_file in recording_files:
            recording = self.load_recording(recording_file)
            metadata = recording["metadata"]

            # Check raw event count
            raw_events = recording["raw_anthropic_events"]
            assert len(raw_events) == metadata["raw_event_count"], (
                f"Recording {recording_file.name}: raw event count mismatch"
            )

            # Check agent block event count
            agent_events = recording["agent_block_events"]
            assert len(agent_events) == metadata["agent_block_event_count"], (
                f"Recording {recording_file.name}: agent block event count mismatch"
            )

            # Check agent message count
            agent_messages = recording["agent_messages"]
            assert len(agent_messages) == metadata["agent_message_count"], (
                f"Recording {recording_file.name}: agent message count mismatch"
            )

    def test_scenario_consistency(self, recording_files, scenarios_config):
        """Test that recording files match their scenario definitions."""
        for recording_file in recording_files:
            recording = self.load_recording(recording_file)
            scenario_name = recording["metadata"]["scenario"]

            if scenario_name not in scenarios_config["scenarios"]:
                continue  # Skip scenarios not in config

            scenario_def = scenarios_config["scenarios"][scenario_name]
            request_params = recording["request_params"]

            # Check message content matches
            assert len(request_params["messages"]) == len(scenario_def["messages"])
            for req_msg, def_msg in zip(request_params["messages"], scenario_def["messages"]):
                assert req_msg["role"] == def_msg["role"]
                assert req_msg["content"] == def_msg["content"]

            # Check tools if specified in scenario
            if "tools" in scenario_def:
                expected_tools = set(scenario_def["tools"])
                actual_tools = set(request_params["tools"])
                # For now, just check that if scenario expects tools, recording has tools
                # TODO: Make tool matching more flexible to handle different tool implementations
                if expected_tools and not actual_tools:
                    assert False, (
                        f"Scenario {scenario_name} expects tools {expected_tools} but recording has none"
                    )
                if not expected_tools and actual_tools:
                    assert False, (
                        f"Scenario {scenario_name} expects no tools but recording has {actual_tools}"
                    )

    def test_tool_use_recordings_have_tool_events(self, recording_files, scenarios_config):
        """Test that recordings for tool scenarios contain tool use events."""
        for recording_file in recording_files:
            recording = self.load_recording(recording_file)
            scenario_name = recording["metadata"]["scenario"]

            if scenario_name not in scenarios_config["scenarios"]:
                continue  # Skip scenarios not in config

            # Get scenario config
            scenario_config = scenarios_config["scenarios"][scenario_name]

            # If scenario has tools, recording should contain tool use events
            if "tools" in scenario_config and scenario_config["tools"]:
                agent_events = recording["agent_block_events"]

                # Should have at least one tool use start event
                tool_events = [
                    event
                    for event in agent_events
                    if event["event"]["type"] == "start"
                    and "content_block" in event["event"]
                    and event["event"]["content_block"].get("type") == "call_tool"
                ]

                assert len(tool_events) > 0, (
                    f"Recording {recording_file.name} for tool scenario {scenario_name} has no tool events"
                )

    def test_text_only_recordings_have_no_tool_events(self, recording_files, scenarios_config):
        """Test that recordings for text-only scenarios contain no tool use events."""
        for recording_file in recording_files:
            recording = self.load_recording(recording_file)
            scenario_name = recording["metadata"]["scenario"]

            if scenario_name not in scenarios_config["scenarios"]:
                continue  # Skip scenarios not in config

            # Get scenario config
            scenario_config = scenarios_config["scenarios"][scenario_name]

            # If scenario has no tools, recording should not contain tool use events
            if "tools" not in scenario_config or not scenario_config["tools"]:
                agent_events = recording["agent_block_events"]

                # Should have no tool use start events
                tool_events = [
                    event
                    for event in agent_events
                    if event["event"]["type"] == "start"
                    and "content_block" in event["event"]
                    and event["event"]["content_block"].get("type") == "call_tool"
                ]

                assert len(tool_events) == 0, (
                    f"Recording {recording_file.name} for text scenario {scenario_name} has unexpected tool events"
                )

    def test_recording_timestamps_are_chronological(self, recording_files):
        """Test that timestamps in recordings are in chronological order."""
        for recording_file in recording_files:
            recording = self.load_recording(recording_file)

            # Check raw anthropic events
            raw_events = recording["raw_anthropic_events"]
            for i in range(1, len(raw_events)):
                prev_time = raw_events[i - 1]["timestamp"]
                curr_time = raw_events[i]["timestamp"]
                assert prev_time <= curr_time, (
                    f"Recording {recording_file.name}: timestamps out of order at raw event {i}"
                )

            # Check agent block events
            agent_events = recording["agent_block_events"]
            for i in range(1, len(agent_events)):
                prev_time = agent_events[i - 1]["timestamp"]
                curr_time = agent_events[i]["timestamp"]
                assert prev_time <= curr_time, (
                    f"Recording {recording_file.name}: timestamps out of order at agent event {i}"
                )

    def test_recording_has_consistent_agent_type(self, recording_files):
        """Test that all recordings use consistent agent type."""
        for recording_file in recording_files:
            recording = self.load_recording(recording_file)
            metadata = recording["metadata"]

            # For now, all recordings should use AnthropicAgent
            assert metadata["agent_type"] == "AnthropicAgent", (
                f"Recording {recording_file.name} uses unexpected agent type: {metadata['agent_type']}"
            )

    def test_recording_has_consistent_model(self, recording_files):
        """Test that recordings use expected Claude models."""
        for recording_file in recording_files:
            recording = self.load_recording(recording_file)
            metadata = recording["metadata"]

            # Should use a Claude model
            assert "claude-" in metadata["model"].lower(), (
                f"Recording {recording_file.name} uses unexpected model: {metadata['model']}"
            )

    def test_timestamps_are_valid_iso_format(self, recording_files):
        """Test that all timestamps are valid ISO format."""
        for recording_file in recording_files:
            recording = self.load_recording(recording_file)

            # Test metadata timestamp
            metadata = recording["metadata"]
            datetime.fromisoformat(metadata["recorded_at"].replace("Z", "+00:00"))

            # Test raw event timestamps
            for event in recording["raw_anthropic_events"]:
                if "timestamp" in event:
                    datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))

            # Test agent event timestamps
            for event in recording["agent_block_events"]:
                if "timestamp" in event:
                    datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))

    def test_text_scenarios_have_text_responses(self, recording_files, scenarios_config):
        """Test that text-only scenarios produce text responses."""
        for recording_file in recording_files:
            recording = self.load_recording(recording_file)
            scenario_name = recording["metadata"]["scenario"]

            if scenario_name not in scenarios_config["scenarios"]:
                continue  # Skip scenarios not in config

            scenario_def = scenarios_config["scenarios"][scenario_name]

            # If scenario has no tools, should have text response
            if "tools" not in scenario_def or not scenario_def.get("tools"):
                agent_messages = recording["agent_messages"]
                has_text_response = any(
                    isinstance(msg["content"], str) and msg["content"].strip()
                    for msg in agent_messages
                    if msg["role"] == "assistant"
                )
                assert has_text_response, f"Text scenario {scenario_name} has no text response"

    def test_recording_file_sizes_reasonable(self, recording_files):
        """Test that recording files are not excessively large."""
        for file_path in recording_files:
            file_size = file_path.stat().st_size
            # Recordings should not exceed 1MB (adjust if needed)
            assert file_size < 1024 * 1024, (
                f"Recording {file_path.name} is too large: {file_size} bytes"
            )

    def test_recording_json_validity(self, recording_files):
        """Test that each recording file contains valid JSON."""
        for recording_file in recording_files:
            try:
                with open(recording_file) as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                pytest.fail(f"Recording {recording_file.name} contains invalid JSON: {e}")

    def test_recording_count_reasonable(self, recording_files):
        """Test that we have a reasonable number of recordings."""
        assert len(recording_files) > 0, "No recording files found"
        assert len(recording_files) < 100, f"Too many recording files: {len(recording_files)}"

    def test_agent_messages_not_empty(self, recording_files):
        """Test that agent messages contain actual content."""
        for recording_file in recording_files:
            recording = self.load_recording(recording_file)
            agent_messages = recording["agent_messages"]

            # Should have at least one assistant message with content
            assistant_messages = [msg for msg in agent_messages if msg["role"] == "assistant"]
            assert len(assistant_messages) > 0, (
                f"Recording {recording_file.name} has no assistant messages"
            )

            # At least one assistant message should have non-empty content
            has_content = any(
                (isinstance(msg["content"], str) and msg["content"].strip())
                or (isinstance(msg["content"], list) and len(msg["content"]) > 0)
                for msg in assistant_messages
            )
            assert has_content, (
                f"Recording {recording_file.name} has no assistant messages with content"
            )
