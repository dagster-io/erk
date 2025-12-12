"""Layer 2 tests: Adapter implementation tests with mocking."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from erk_kits.data.kits.command.scripts.command.ops import (
    FakeClaudeCliOps,
    RealClaudeCliOps,
)


class TestRealClaudeCliOps:
    """Layer 2: Test real implementation with mocked subprocess."""

    def _create_mock_process(self, stdout_lines: list[str], returncode: int = 0) -> MagicMock:
        """Create a mock subprocess.Popen process with configured output."""
        mock_process = MagicMock()
        mock_process.stdout = iter(stdout_lines)
        mock_process.wait.return_value = returncode
        return mock_process

    @contextmanager
    def _mock_claude_execution(
        self, stdout_lines: list[str], returncode: int = 0
    ) -> Iterator[tuple[MagicMock, MagicMock]]:
        """Context manager that mocks subprocess.Popen and print for testing.

        Yields tuple of (mock_popen, mock_print) for assertions.
        """
        mock_process = self._create_mock_process(stdout_lines, returncode)

        with patch("subprocess.Popen", return_value=mock_process) as mock_popen:
            with patch("builtins.print") as mock_print:
                # Mock the command_status context manager to avoid Rich Console interactions
                with patch(
                    "erk_kits.data.kits.command.scripts.command.ops.command_status"
                ) as mock_status:
                    # Make the context manager return a mock Status object
                    mock_status.return_value.__enter__ = MagicMock()
                    mock_status.return_value.__exit__ = MagicMock()
                    yield mock_popen, mock_print

    def test_successful_execution_with_subprocess(self) -> None:
        """Test that RealClaudeCliOps correctly invokes subprocess with streaming."""
        ops = RealClaudeCliOps()

        with self._mock_claude_execution([]) as (mock_popen, mock_print):
            result = ops.execute_command(
                command_name="test",
                cwd=Path("/fake/path"),
                json_output=False,
            )

            # Verify result
            assert result.returncode == 0

            # Status message is now handled by command_status context manager (Rich)
            # No direct print calls expected when there's no output
            assert mock_print.call_count == 0

            # Verify subprocess.Popen was called correctly
            mock_popen.assert_called_once()
            call_args = mock_popen.call_args

            # Check command arguments include stream-json and verbose
            cmd = call_args[0][0]
            assert cmd[0] == "claude"
            assert "--print" in cmd
            assert "--verbose" in cmd
            assert "--permission-mode" in cmd
            assert "bypassPermissions" in cmd
            assert "--setting-sources" in cmd
            assert "project" in cmd
            assert "--output-format" in cmd
            assert "stream-json" in cmd
            assert "/test" in cmd

            # Check keyword arguments
            assert call_args[1]["cwd"] == Path("/fake/path")
            assert call_args[1]["stdout"] is not None
            assert call_args[1]["stderr"] is not None
            assert call_args[1]["text"] is True
            assert call_args[1]["bufsize"] == 1

    def test_failed_execution_with_subprocess(self) -> None:
        """Test that RealClaudeCliOps propagates non-zero exit codes."""
        ops = RealClaudeCliOps()

        with self._mock_claude_execution([], returncode=1) as (mock_popen, mock_print):
            result = ops.execute_command(
                command_name="test",
                cwd=Path("/fake/path"),
                json_output=False,
            )

            # Verify exit code propagated
            assert result.returncode == 1

    def test_always_uses_stream_json_format(self) -> None:
        """Test that stream-json is always used regardless of json_output parameter."""
        ops = RealClaudeCliOps()

        with self._mock_claude_execution([]) as (mock_popen, mock_print):
            # Test with json_output=True
            ops.execute_command(
                command_name="test",
                cwd=Path("/fake/path"),
                json_output=True,
            )

            # Verify --output-format stream-json in command
            call_args = mock_popen.call_args
            cmd = call_args[0][0]
            assert "--output-format" in cmd
            assert "stream-json" in cmd

            # Reset mock
            mock_popen.reset_mock()

            # Test with json_output=False - should still use stream-json
            ops.execute_command(
                command_name="test2",
                cwd=Path("/fake/path"),
                json_output=False,
            )

            # Verify stream-json still used
            call_args = mock_popen.call_args
            cmd = call_args[0][0]
            assert "--output-format" in cmd
            assert "stream-json" in cmd

    def test_namespaced_command_passed_to_subprocess(self) -> None:
        """Test that namespaced commands are passed correctly."""
        ops = RealClaudeCliOps()

        with self._mock_claude_execution([]) as (mock_popen, mock_print):
            ops.execute_command(
                command_name="gt:submit-branch",
                cwd=Path("/fake/path"),
                json_output=False,
            )

            # Verify namespace in command
            call_args = mock_popen.call_args
            cmd = call_args[0][0]
            assert "/gt:submit-branch" in cmd

    def test_file_not_found_error_propagates(self) -> None:
        """Test that FileNotFoundError is propagated when claude binary not found."""
        ops = RealClaudeCliOps()

        with patch("subprocess.Popen", side_effect=FileNotFoundError):
            with patch("builtins.print"):
                with pytest.raises(FileNotFoundError):
                    ops.execute_command(
                        command_name="test",
                        cwd=Path("/fake/path"),
                        json_output=False,
                    )

    def test_parses_jsonl_and_extracts_text(self) -> None:
        """Test that JSONL output is parsed and text is extracted from assistant messages."""
        import json

        ops = RealClaudeCliOps()

        # Create JSONL output with assistant messages (stream-json format)
        jsonl_output = [
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "Hello "}],
                    },
                }
            ),
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "World!"}],
                    },
                }
            ),
        ]

        with self._mock_claude_execution(jsonl_output) as (mock_popen, mock_print):
            result = ops.execute_command(
                command_name="test",
                cwd=Path("/fake/path"),
                json_output=False,
            )

            # Verify result
            assert result.returncode == 0

            # Verify print was called for text chunks (status handled by command_status)
            assert mock_print.call_count == 2
            # First call: "Hello "
            assert mock_print.call_args_list[0] == (("Hello ",), {"end": "", "flush": True})
            # Second call: "World!"
            assert mock_print.call_args_list[1] == (("World!",), {"end": "", "flush": True})

    def test_hides_system_messages_but_shows_tool_results(self) -> None:
        """Test that system messages are hidden but tool results from user messages are shown."""
        import json

        ops = RealClaudeCliOps()

        # Create JSONL output with system and user messages
        jsonl_output = [
            json.dumps({"type": "system", "subtype": "init", "data": "metadata"}),
            json.dumps(
                {
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": "toolu_123",
                                "content": "Test result output",
                            }
                        ],
                    },
                }
            ),
        ]

        with self._mock_claude_execution(jsonl_output) as (mock_popen, mock_print):
            result = ops.execute_command(
                command_name="test",
                cwd=Path("/fake/path"),
                json_output=False,
            )

            # Verify result
            assert result.returncode == 0

            # System message hidden, but tool result should be displayed
            # Status handled by command_status, so only result header + content expected
            all_print_calls = [str(call) for call in mock_print.call_args_list]
            assert mock_print.call_count >= 2
            assert any("Result:" in str(call) for call in all_print_calls)
            assert any("Test result output" in str(call) for call in all_print_calls)

    def test_displays_tool_use_from_assistant_messages(self) -> None:
        """Test that tool_use blocks in assistant messages are displayed."""
        import json

        ops = RealClaudeCliOps()

        # Create JSONL output with assistant message containing tool use
        jsonl_output = [
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "tool_use",
                                "id": "toolu_123",
                                "name": "Bash",
                                "input": {"command": "pytest tests/"},
                            }
                        ],
                    },
                }
            ),
        ]

        with self._mock_claude_execution(jsonl_output) as (mock_popen, mock_print):
            result = ops.execute_command(
                command_name="test",
                cwd=Path("/fake/path"),
                json_output=False,
            )

            # Verify result
            assert result.returncode == 0

            # Verify tool use was displayed
            all_print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("Using Bash" in str(call) for call in all_print_calls)
            assert any("pytest tests/" in str(call) for call in all_print_calls)

    def test_displays_all_tool_parameters(self) -> None:
        """Test that all parameters for all tools are displayed, not just Bash/Edit."""
        import json

        ops = RealClaudeCliOps()

        # Create JSONL output with various tool invocations
        jsonl_output = [
            # TodoWrite with complex parameters
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "tool_use",
                                "id": "toolu_1",
                                "name": "TodoWrite",
                                "input": {
                                    "todos": [
                                        {"content": "Task 1", "status": "pending"},
                                        {"content": "Task 2", "status": "completed"},
                                    ]
                                },
                            }
                        ],
                    },
                }
            ),
            # Task with string parameters
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "tool_use",
                                "id": "toolu_2",
                                "name": "Task",
                                "input": {
                                    "subagent_type": "devrun",
                                    "description": "Run tests",
                                    "prompt": "Run pytest tests/",
                                },
                            }
                        ],
                    },
                }
            ),
        ]

        with self._mock_claude_execution(jsonl_output) as (mock_popen, mock_print):
            result = ops.execute_command(
                command_name="test",
                cwd=Path("/fake/path"),
                json_output=False,
            )

            # Verify result
            assert result.returncode == 0

            # Verify TodoWrite parameters displayed
            all_print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("Using TodoWrite" in str(call) for call in all_print_calls)
            assert any("todos:" in str(call) for call in all_print_calls)
            assert any("Task 1" in str(call) for call in all_print_calls)

            # Verify Task parameters displayed
            assert any("Using Task" in str(call) for call in all_print_calls)
            assert any("subagent_type: devrun" in str(call) for call in all_print_calls)
            assert any("description: Run tests" in str(call) for call in all_print_calls)
            assert any("prompt: Run pytest tests/" in str(call) for call in all_print_calls)

    def test_displays_tool_result_with_multiline_content(self) -> None:
        """Test that multiline tool results are displayed with proper indentation."""
        import json

        ops = RealClaudeCliOps()

        # Create JSONL output with multiline tool result
        jsonl_output = [
            json.dumps(
                {
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": "toolu_123",
                                "content": "Line 1\nLine 2\nLine 3",
                            }
                        ],
                    },
                }
            ),
        ]

        with self._mock_claude_execution(jsonl_output) as (mock_popen, mock_print):
            result = ops.execute_command(
                command_name="test",
                cwd=Path("/fake/path"),
                json_output=False,
            )

            # Verify result
            assert result.returncode == 0

            # Verify all lines displayed
            all_print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("Result:" in str(call) for call in all_print_calls)
            assert any("Line 1" in str(call) for call in all_print_calls)
            assert any("Line 2" in str(call) for call in all_print_calls)
            assert any("Line 3" in str(call) for call in all_print_calls)

    def test_displays_tool_result_with_structured_content(self) -> None:
        """Test that structured list content in tool results is displayed."""
        import json

        ops = RealClaudeCliOps()

        # Create JSONL output with structured tool result
        jsonl_output = [
            json.dumps(
                {
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": "toolu_123",
                                "content": [
                                    {"type": "text", "text": "Structured output line 1"},
                                    {"type": "text", "text": "Structured output line 2"},
                                ],
                            }
                        ],
                    },
                }
            ),
        ]

        with self._mock_claude_execution(jsonl_output) as (mock_popen, mock_print):
            result = ops.execute_command(
                command_name="test",
                cwd=Path("/fake/path"),
                json_output=False,
            )

            # Verify result
            assert result.returncode == 0

            # Verify structured content displayed
            all_print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("Result:" in str(call) for call in all_print_calls)
            assert any("Structured output line 1" in str(call) for call in all_print_calls)
            assert any("Structured output line 2" in str(call) for call in all_print_calls)

    def test_displays_tool_result_error_flag(self) -> None:
        """Test that error results are marked with [Error result]."""
        import json

        ops = RealClaudeCliOps()

        # Create JSONL output with error tool result
        jsonl_output = [
            json.dumps(
                {
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": "toolu_123",
                                "content": "Error: Command failed",
                                "is_error": True,
                            }
                        ],
                    },
                }
            ),
        ]

        with self._mock_claude_execution(jsonl_output) as (mock_popen, mock_print):
            result = ops.execute_command(
                command_name="test",
                cwd=Path("/fake/path"),
                json_output=False,
            )

            # Verify result
            assert result.returncode == 0

            # Verify error flag displayed
            all_print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("Error result" in str(call) for call in all_print_calls)
            assert any("Error: Command failed" in str(call) for call in all_print_calls)

    def test_displays_result_message(self) -> None:
        """Test that result messages display completion summary."""
        import json

        ops = RealClaudeCliOps()

        # Create JSONL output with result message
        jsonl_output = [
            json.dumps(
                {
                    "type": "result",
                    "is_error": False,
                    "total_cost_usd": 0.0234,
                    "duration_ms": 5432,
                    "num_turns": 3,
                }
            ),
        ]

        with self._mock_claude_execution(jsonl_output) as (mock_popen, mock_print):
            result = ops.execute_command(
                command_name="test",
                cwd=Path("/fake/path"),
                json_output=False,
            )

            # Verify result
            assert result.returncode == 0

            # Verify completion summary was displayed
            all_print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("Success" in str(call) for call in all_print_calls)
            assert any("$0.0234" in str(call) for call in all_print_calls)
            assert any("5432ms" in str(call) for call in all_print_calls)

    def test_displays_error_result_message(self) -> None:
        """Test that error result messages display error status."""
        import json

        ops = RealClaudeCliOps()

        # Create JSONL output with error result
        jsonl_output = [
            json.dumps(
                {
                    "type": "result",
                    "is_error": True,
                    "total_cost_usd": 0.0123,
                    "duration_ms": 2000,
                }
            ),
        ]

        with self._mock_claude_execution(jsonl_output) as (mock_popen, mock_print):
            result = ops.execute_command(
                command_name="test",
                cwd=Path("/fake/path"),
                json_output=False,
            )

            # Verify result
            assert result.returncode == 0

            # Verify error status was displayed
            all_print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("Error" in str(call) for call in all_print_calls)

    def test_handles_malformed_json_gracefully(self) -> None:
        """Test that malformed JSON lines are printed with warning without crashing."""
        ops = RealClaudeCliOps()

        # Create output with malformed JSON
        output = [
            "This is not JSON\n",
            '{"incomplete": ',
        ]

        with self._mock_claude_execution(output) as (mock_popen, mock_print):
            result = ops.execute_command(
                command_name="test",
                cwd=Path("/fake/path"),
                json_output=False,
            )

            # Verify result
            assert result.returncode == 0

            # Verify print was called for warning messages (status handled by command_status)
            assert mock_print.call_count >= 2

            # Verify warning messages for malformed JSON
            all_print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("Warning: Invalid JSON" in str(call) for call in all_print_calls)
            assert any("This is not JSON" in str(call) for call in all_print_calls)
            assert any("incomplete" in str(call) for call in all_print_calls)


class TestFakeClaudeCliOps:
    """Layer 1: Test fake implementation itself."""

    def test_records_executions(self) -> None:
        """Test that fake records all executions."""
        fake = FakeClaudeCliOps()

        # Execute multiple times
        fake.execute_command("test1", Path("/path1"), False)
        fake.execute_command("test2", Path("/path2"), True)

        # Verify executions recorded
        assert fake.get_execution_count() == 2
        assert len(fake.executions) == 2

        # Verify details
        assert fake.executions[0] == ("test1", Path("/path1"), False)
        assert fake.executions[1] == ("test2", Path("/path2"), True)

    def test_get_last_execution(self) -> None:
        """Test get_last_execution returns most recent execution."""
        fake = FakeClaudeCliOps()

        # Initially no executions
        assert fake.get_last_execution() is None

        # Execute
        fake.execute_command("test", Path("/path"), False)

        # Verify last execution
        last = fake.get_last_execution()
        assert last == ("test", Path("/path"), False)

    def test_configured_returncode(self) -> None:
        """Test that configured return code is returned."""
        fake = FakeClaudeCliOps()

        # Default is 0
        result = fake.execute_command("test", Path("/path"), False)
        assert result.returncode == 0

        # Configure to return 1
        fake.set_next_returncode(1)
        result = fake.execute_command("test", Path("/path"), False)
        assert result.returncode == 1

    def test_file_not_found_error(self) -> None:
        """Test that fake can be configured to raise FileNotFoundError."""
        fake = FakeClaudeCliOps()

        # Default does not raise
        fake.execute_command("test", Path("/path"), False)

        # Configure to raise
        fake.set_file_not_found_error(True)
        with pytest.raises(FileNotFoundError):
            fake.execute_command("test", Path("/path"), False)

    def test_executions_property_returns_copy(self) -> None:
        """Test that executions property returns a copy, not original list."""
        fake = FakeClaudeCliOps()

        fake.execute_command("test", Path("/path"), False)

        # Get executions
        executions1 = fake.executions
        executions2 = fake.executions

        # Should be equal but not same object
        assert executions1 == executions2
        assert executions1 is not executions2

        # Modifying returned list should not affect internal state
        executions1.clear()
        assert fake.get_execution_count() == 1
