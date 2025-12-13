"""Unit tests for Agent message types."""

from csbot.agents.messages import (
    AgentBlockDeltaEvent,
    AgentInputJSONDelta,
    AgentModelSpecificMessage,
    AgentStartBlockEvent,
    AgentStopBlockEvent,
    AgentTextBlock,
    AgentTextDelta,
    AgentTextMessage,
    AgentToolUseBlock,
)


class TestAgentMessages:
    """Test suite for Agent message types."""

    def test_agent_text_message(self):
        """Test AgentTextMessage creation and attributes."""
        message = AgentTextMessage(role="user", content="Hello, world!")

        assert message.role == "user"
        assert message.content == "Hello, world!"

    def test_agent_model_specific_message(self):
        """Test AgentModelSpecificMessage with various content types."""
        # Test with string content
        message = AgentModelSpecificMessage(role="assistant", content="Hello!")
        assert message.role == "assistant"
        assert message.content == "Hello!"

        # Test with structured content
        structured_content = [
            {"type": "text", "text": "Here's the result:"},
            {"type": "tool_use", "id": "tool_123", "name": "search", "input": {"query": "test"}},
        ]
        message = AgentModelSpecificMessage(role="assistant", content=structured_content)
        assert message.role == "assistant"
        assert message.content == structured_content
        assert len(message.content) == 2
        assert message.content[0]["type"] == "text"
        assert message.content[1]["type"] == "tool_use"

    def test_agent_text_delta(self):
        """Test AgentTextDelta creation and attributes."""
        delta = AgentTextDelta(type="text_delta", text="Hello")

        assert delta.type == "text_delta"
        assert delta.text == "Hello"

    def test_agent_input_json_delta(self):
        """Test AgentInputJSONDelta creation and attributes."""
        delta = AgentInputJSONDelta(type="input_json_delta", partial_json='{"key": "val')

        assert delta.type == "input_json_delta"
        assert delta.partial_json == '{"key": "val'

    def test_agent_text_block(self):
        """Test AgentTextBlock creation and attributes."""
        block = AgentTextBlock(type="output_text")

        assert block.type == "output_text"

    def test_agent_tool_use_block(self):
        """Test AgentToolUseBlock creation and attributes."""
        block = AgentToolUseBlock(type="call_tool", id="tool_123", name="search_tool")

        assert block.type == "call_tool"
        assert block.id == "tool_123"
        assert block.name == "search_tool"

    def test_agent_start_block_event(self):
        """Test AgentStartBlockEvent creation and attributes."""
        text_block = AgentTextBlock(type="output_text")
        event = AgentStartBlockEvent(type="start", index=0, content_block=text_block)

        assert event.type == "start"
        assert event.content_block == text_block
        assert isinstance(event.content_block, AgentTextBlock)

    def test_agent_stop_block_event(self):
        """Test AgentStopBlockEvent creation and attributes."""
        event = AgentStopBlockEvent(type="stop", index=0)

        assert event.type == "stop"

    def test_agent_block_delta_event(self):
        """Test AgentBlockDeltaEvent creation and attributes."""
        text_delta = AgentTextDelta(type="text_delta", text="Hello")
        event = AgentBlockDeltaEvent(type="delta", index=0, delta=text_delta)

        assert event.type == "delta"
        assert event.delta == text_delta
        assert isinstance(event.delta, AgentTextDelta)
        assert event.delta.text == "Hello"

    def test_agent_block_delta_event_with_json_delta(self):
        """Test AgentBlockDeltaEvent with JSON delta."""
        json_delta = AgentInputJSONDelta(type="input_json_delta", partial_json='{"query": "')
        event = AgentBlockDeltaEvent(type="delta", index=0, delta=json_delta)

        assert event.type == "delta"
        assert event.delta == json_delta
        assert isinstance(event.delta, AgentInputJSONDelta)
        assert event.delta.partial_json == '{"query": "'

    def test_message_role_validation(self):
        """Test that message roles accept valid values."""
        # Test valid roles
        user_msg = AgentTextMessage(role="user", content="Hello")
        assert user_msg.role == "user"

        assistant_msg = AgentTextMessage(role="assistant", content="Hi there")
        assert assistant_msg.role == "assistant"

        # Test with model specific messages
        model_msg = AgentModelSpecificMessage(
            role="user", content={"type": "text", "text": "Hello"}
        )
        assert model_msg.role == "user"

    def test_content_block_types(self):
        """Test that content blocks have correct type literals."""
        text_block = AgentTextBlock(type="output_text")
        assert text_block.type == "output_text"

        tool_block = AgentToolUseBlock(type="call_tool", id="123", name="test")
        assert tool_block.type == "call_tool"

    def test_delta_types(self):
        """Test that delta objects have correct type literals."""
        text_delta = AgentTextDelta(type="text_delta", text="content")
        assert text_delta.type == "text_delta"

        json_delta = AgentInputJSONDelta(type="input_json_delta", partial_json="{}")
        assert json_delta.type == "input_json_delta"

    def test_event_types(self):
        """Test that event objects have correct type literals."""
        start_event = AgentStartBlockEvent(
            type="start", index=0, content_block=AgentTextBlock(type="output_text")
        )
        assert start_event.type == "start"

        stop_event = AgentStopBlockEvent(type="stop", index=0)
        assert stop_event.type == "stop"

        delta_event = AgentBlockDeltaEvent(
            type="delta", index=0, delta=AgentTextDelta(type="text_delta", text="test")
        )
        assert delta_event.type == "delta"

    def test_dataclass_equality(self):
        """Test that dataclass instances compare correctly."""
        msg1 = AgentTextMessage(role="user", content="Hello")
        msg2 = AgentTextMessage(role="user", content="Hello")
        msg3 = AgentTextMessage(role="user", content="Hi")

        assert msg1 == msg2
        assert msg1 != msg3

        delta1 = AgentTextDelta(type="text_delta", text="test")
        delta2 = AgentTextDelta(type="text_delta", text="test")
        delta3 = AgentTextDelta(type="text_delta", text="other")

        assert delta1 == delta2
        assert delta1 != delta3

    def test_dataclass_repr(self):
        """Test that dataclass representations are meaningful."""
        msg = AgentTextMessage(role="user", content="Hello")
        repr_str = repr(msg)

        assert "AgentTextMessage" in repr_str
        assert "role='user'" in repr_str
        assert "content='Hello'" in repr_str

        block = AgentToolUseBlock(type="call_tool", id="123", name="search")
        repr_str = repr(block)

        assert "AgentToolUseBlock" in repr_str
        assert "type='call_tool'" in repr_str
        assert "id='123'" in repr_str
        assert "name='search'" in repr_str

    def test_complex_message_structure(self):
        """Test complex message structures with nested content."""
        # Simulate a message with tool use and tool result
        tool_use_content = [
            {"type": "text", "text": "I'll search for that information."},
            {
                "type": "tool_use",
                "id": "toolu_123",
                "name": "web_search",
                "input": {"query": "Python best practices", "limit": 10},
            },
        ]

        assistant_msg = AgentModelSpecificMessage(role="assistant", content=tool_use_content)

        assert assistant_msg.role == "assistant"
        assert len(assistant_msg.content) == 2
        assert assistant_msg.content[0]["type"] == "text"
        assert assistant_msg.content[1]["type"] == "tool_use"
        assert assistant_msg.content[1]["name"] == "web_search"
        assert assistant_msg.content[1]["input"]["query"] == "Python best practices"

        # Tool result message
        tool_result_content = [
            {
                "type": "tool_result",
                "tool_use_id": "toolu_123",
                "content": "Found 10 results about Python best practices...",
            }
        ]

        user_msg = AgentModelSpecificMessage(role="user", content=tool_result_content)

        assert user_msg.role == "user"
        assert user_msg.content[0]["type"] == "tool_result"
        assert user_msg.content[0]["tool_use_id"] == "toolu_123"

    def test_event_sequence_simulation(self):
        """Test a typical sequence of events during streaming."""
        # Start block event
        text_block = AgentTextBlock(type="output_text")
        start_event = AgentStartBlockEvent(type="start", index=0, content_block=text_block)

        # Multiple delta events
        delta1 = AgentTextDelta(type="text_delta", text="Hello")
        event1 = AgentBlockDeltaEvent(type="delta", index=0, delta=delta1)

        delta2 = AgentTextDelta(type="text_delta", text=" world")
        event2 = AgentBlockDeltaEvent(type="delta", index=0, delta=delta2)

        delta3 = AgentTextDelta(type="text_delta", text="!")
        event3 = AgentBlockDeltaEvent(type="delta", index=0, delta=delta3)

        # Stop event
        stop_event = AgentStopBlockEvent(type="stop", index=0)

        # Simulate processing the events
        events = [start_event, event1, event2, event3, stop_event]

        assert events[0].type == "start"
        assert isinstance(events[0].content_block, AgentTextBlock)

        text_parts = []
        for event in events[1:4]:  # The delta events
            assert event.type == "delta"
            assert isinstance(event.delta, AgentTextDelta)
            text_parts.append(event.delta.text)

        assert "".join(text_parts) == "Hello world!"
        assert events[-1].type == "stop"
