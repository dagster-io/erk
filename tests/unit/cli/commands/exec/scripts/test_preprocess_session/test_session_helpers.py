"""Session analysis and helper function tests for session log preprocessing."""

from erk.cli.commands.exec.scripts.preprocess_session import (
    deduplicate_documentation_blocks,
    is_empty_session,
    is_log_discovery_operation,
    is_warmup_session,
    prune_tool_result_content,
    truncate_parameter_value,
    truncate_tool_parameters,
)


def test_is_empty_session_with_few_entries() -> None:
    """Test that sessions with <3 entries are considered empty."""
    entries = [{"type": "user", "message": {"content": "Hi"}}]
    assert is_empty_session(entries) is True


def test_is_empty_session_with_no_meaningful_content() -> None:
    """Test that sessions without meaningful interaction are empty."""
    entries = [
        {"type": "user", "message": {"content": ""}},
        {"type": "assistant", "message": {"content": []}},
        {"type": "user", "message": {"content": "   "}},
    ]
    assert is_empty_session(entries) is True


def test_is_empty_session_with_meaningful_content() -> None:
    """Test that sessions with meaningful content are not empty."""
    entries = [
        {"type": "user", "message": {"content": "Hello"}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "Hi there"}]}},
        {"type": "user", "message": {"content": "How are you?"}},
    ]
    assert is_empty_session(entries) is False


def test_is_warmup_session_detects_warmup() -> None:
    """Test that warmup sessions are detected."""
    entries = [{"type": "user", "message": {"content": "warmup"}}]
    assert is_warmup_session(entries) is True


def test_is_warmup_session_with_normal_content() -> None:
    """Test that normal sessions are not detected as warmup."""
    entries = [{"type": "user", "message": {"content": "Please help me with this task"}}]
    assert is_warmup_session(entries) is False


def test_deduplicate_documentation_blocks_keeps_first() -> None:
    """Test that first documentation block is kept."""
    long_doc = "command-message>" + ("x" * 600)
    entries = [{"type": "user", "message": {"content": long_doc}}]
    result = deduplicate_documentation_blocks(entries)
    assert len(result) == 1
    assert long_doc in str(result[0])


def test_deduplicate_documentation_blocks_replaces_duplicate() -> None:
    """Test that duplicate documentation blocks are replaced with markers."""
    long_doc = "/erk:plan-save-issue" + ("x" * 600)
    entries = [
        {"type": "user", "message": {"content": long_doc}},
        {"type": "user", "message": {"content": long_doc}},
    ]
    result = deduplicate_documentation_blocks(entries)
    assert len(result) == 2
    # Second entry should have marker
    assert "[Duplicate command documentation block omitted" in str(result[1])


def test_truncate_parameter_value_preserves_short() -> None:
    """Test that short values are not truncated."""
    value = "short text"
    assert truncate_parameter_value(value) == value


def test_truncate_parameter_value_truncates_long() -> None:
    """Test that long values are truncated."""
    value = "x" * 300
    result = truncate_parameter_value(value)
    assert len(result) < len(value)
    assert "truncated" in result


def test_truncate_parameter_value_preserves_file_paths() -> None:
    """Test that file paths preserve structure."""
    value = "/very/long/path/to/some/file/deep/in/directory/structure/file.py"
    result = truncate_parameter_value(value, max_length=30)
    assert result.startswith("/very")
    assert result.endswith("file.py")
    assert "..." in result


def test_truncate_tool_parameters_modifies_long_params() -> None:
    """Test that tool parameters are truncated."""
    entries = [
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Read",
                        "input": {"file_path": "/short", "prompt": "x" * 300},
                    }
                ]
            },
        }
    ]
    result = truncate_tool_parameters(entries)
    # Long prompt should be truncated
    prompt = result[0]["message"]["content"][0]["input"]["prompt"]
    assert len(prompt) < 300


def test_prune_tool_result_content_preserves_short() -> None:
    """Test that short results are not pruned."""
    result = "Line 1\nLine 2\nLine 3"
    assert prune_tool_result_content(result) == result


def test_prune_tool_result_content_prunes_long() -> None:
    """Test that long results are pruned to 30 lines."""
    lines = [f"Line {i}" for i in range(100)]
    result_text = "\n".join(lines)
    pruned = prune_tool_result_content(result_text)
    assert "omitted" in pruned
    assert len(pruned.split("\n")) < 100


def test_prune_tool_result_content_preserves_errors() -> None:
    """Test that error lines are preserved even after 30 lines."""
    lines = [f"Line {i}" for i in range(100)]
    lines[50] = "ERROR: Something went wrong"
    result_text = "\n".join(lines)
    pruned = prune_tool_result_content(result_text)
    assert "ERROR: Something went wrong" in pruned


def test_is_log_discovery_operation_detects_pwd() -> None:
    """Test that pwd commands are detected as log discovery."""
    entry = {
        "type": "assistant",
        "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "pwd"}}]},
    }
    assert is_log_discovery_operation(entry) is True


def test_is_log_discovery_operation_detects_ls_claude() -> None:
    """Test that ls ~/.claude commands are detected."""
    entry = {
        "type": "assistant",
        "message": {
            "content": [
                {"type": "tool_use", "name": "Bash", "input": {"command": "ls ~/.claude/projects/"}}
            ]
        },
    }
    assert is_log_discovery_operation(entry) is True


def test_is_log_discovery_operation_ignores_normal_commands() -> None:
    """Test that normal commands are not detected as log discovery."""
    entry = {
        "type": "assistant",
        "message": {
            "content": [{"type": "tool_use", "name": "Bash", "input": {"command": "git status"}}]
        },
    }
    assert is_log_discovery_operation(entry) is False
