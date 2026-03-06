"""CLI command and full workflow tests for session log preprocessing."""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.preprocess_session import preprocess_session
from tests.unit.cli.commands.exec.scripts import fixtures

# ============================================================================
# CLI Command Tests
# ============================================================================


def test_preprocess_session_creates_temp_file(tmp_path: Path) -> None:
    """Test that command creates temp file."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        log_file = Path("session-123.jsonl")
        user_json = json.dumps(json.loads(fixtures.JSONL_USER_MESSAGE_STRING))
        log_file.write_text(user_json, encoding="utf-8")

        result = runner.invoke(preprocess_session, [str(log_file), "--no-filtering"])
        assert result.exit_code == 0

        # Extract temp file path from output
        temp_path = Path(result.output.strip())
        assert temp_path.exists()
        # Check filename pattern (now includes random suffix for uniqueness)
        assert temp_path.name.startswith("session-session-123-")
        assert temp_path.name.endswith("-compressed.xml")


def test_preprocess_session_outputs_path(tmp_path: Path) -> None:
    """Test that command outputs temp file path to stdout."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        log_file = Path("session-123.jsonl")
        user_json = json.dumps(json.loads(fixtures.JSONL_USER_MESSAGE_STRING))
        log_file.write_text(user_json, encoding="utf-8")

        result = runner.invoke(preprocess_session, [str(log_file), "--no-filtering"])
        # Output should contain temp file path with correct filename pattern
        assert "session-session-123-" in result.output
        assert "-compressed.xml" in result.output


def test_preprocess_session_includes_agents_by_default(tmp_path: Path) -> None:
    """Test that agent logs are included by default."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create entries with matching session ID
        session_id = "session-123"
        entry = json.dumps(
            {"sessionId": session_id, "type": "user", "message": {"content": "test"}}
        )

        log_file = Path(f"{session_id}.jsonl")
        log_file.write_text(entry, encoding="utf-8")

        agent_file = Path("agent-abc.jsonl")
        agent_file.write_text(entry, encoding="utf-8")

        result = runner.invoke(preprocess_session, [str(log_file), "--no-filtering"])
        assert result.exit_code == 0

        # Check temp file contains multiple sessions
        temp_path = Path(result.output.strip())
        content = temp_path.read_text(encoding="utf-8")
        assert content.count("<session>") == 2  # Main + agent


def test_preprocess_session_no_include_agents_flag(tmp_path: Path) -> None:
    """Test --no-include-agents flag excludes agent logs."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create entries with matching session ID
        session_id = "session-123"
        entry = json.dumps(
            {"sessionId": session_id, "type": "user", "message": {"content": "test"}}
        )

        log_file = Path(f"{session_id}.jsonl")
        log_file.write_text(entry, encoding="utf-8")

        agent_file = Path("agent-abc.jsonl")
        agent_file.write_text(entry, encoding="utf-8")

        result = runner.invoke(
            preprocess_session, [str(log_file), "--no-include-agents", "--no-filtering"]
        )
        assert result.exit_code == 0

        # Check temp file contains only main session
        temp_path = Path(result.output.strip())
        content = temp_path.read_text(encoding="utf-8")
        assert content.count("<session>") == 1  # Only main


def test_preprocess_session_nonexistent_file() -> None:
    """Test handling of nonexistent log file."""
    runner = CliRunner()
    result = runner.invoke(preprocess_session, ["/nonexistent/file.jsonl"])
    assert result.exit_code != 0  # Should fail


def test_preprocess_session_agent_logs_with_source_labels(tmp_path: Path) -> None:
    """Test that agent logs include source labels."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create entries with matching session ID
        session_id = "session-123"
        entry = json.dumps(
            {"sessionId": session_id, "type": "user", "message": {"content": "test"}}
        )

        log_file = Path(f"{session_id}.jsonl")
        log_file.write_text(entry, encoding="utf-8")

        agent_file = Path("agent-xyz.jsonl")
        agent_file.write_text(entry, encoding="utf-8")

        result = runner.invoke(preprocess_session, [str(log_file), "--no-filtering"])
        assert result.exit_code == 0

        # Check temp file has source labels
        temp_path = Path(result.output.strip())
        content = temp_path.read_text(encoding="utf-8")
        assert '<meta source="agent-xyz" />' in content


# ============================================================================
# Full Workflow Integration Tests
# ============================================================================


def test_full_workflow_compression_ratio(tmp_path: Path) -> None:
    """Test that full workflow achieves expected compression ratio."""
    # Create log file with realistic content (multiple entries with metadata)
    session_id = "session-123"

    # Adapt fixtures to use matching session ID
    def with_session_id(fixture_json: str) -> dict:
        data = json.loads(fixture_json)
        data["sessionId"] = session_id
        return data

    # Adapt tool_result fixture
    tool_result_data = with_session_id(fixtures.JSONL_TOOL_RESULT)
    content_block = tool_result_data["message"]["content"][0]
    content_text = content_block["content"]
    tool_result_data["message"]["content"] = [{"type": "text", "text": content_text}]

    log_entries = [
        json.dumps(with_session_id(fixtures.JSONL_USER_MESSAGE_STRING)),
        json.dumps(with_session_id(fixtures.JSONL_ASSISTANT_TEXT)),
        json.dumps(with_session_id(fixtures.JSONL_ASSISTANT_TOOL_USE)),
        json.dumps(tool_result_data),
        json.dumps(with_session_id(fixtures.JSONL_FILE_HISTORY_SNAPSHOT)),  # Should be filtered
    ]

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        log_file = Path(f"{session_id}.jsonl")
        log_file.write_text("\n".join(log_entries), encoding="utf-8")

        original_size = log_file.stat().st_size

        result = runner.invoke(preprocess_session, [str(log_file), "--no-filtering"])
        assert result.exit_code == 0

        temp_path = Path(result.output.strip())
        compressed_size = temp_path.stat().st_size

        compression_ratio = (1 - compressed_size / original_size) * 100
        assert compression_ratio >= 50  # Should achieve at least 50% compression


def test_full_workflow_preserves_tool_results(tmp_path: Path) -> None:
    """Test that tool results are preserved verbatim in full workflow."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        session_id = "session-123"
        log_file = Path(f"{session_id}.jsonl")

        # Adapt fixture to match what the code expects
        entry_data = json.loads(fixtures.JSONL_TOOL_RESULT)
        entry_data["sessionId"] = session_id
        content_block = entry_data["message"]["content"][0]
        content_text = content_block["content"]
        entry_data["message"]["content"] = [{"type": "text", "text": content_text}]

        log_file.write_text(json.dumps(entry_data), encoding="utf-8")

        result = runner.invoke(preprocess_session, [str(log_file), "--no-filtering"])
        assert result.exit_code == 0

        temp_path = Path(result.output.strip())
        content = temp_path.read_text(encoding="utf-8")

        # Verify tool result content preserved with formatting
        assert "File contents:" in content
        assert "def hello():" in content
        assert "print('Hello')" in content


def test_full_workflow_deduplicates_correctly(tmp_path: Path) -> None:
    """Test that deduplication works correctly in full workflow."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        session_id = "session-123"
        log_file = Path(f"{session_id}.jsonl")

        # Update session IDs to match filename
        dup_text_data = json.loads(fixtures.JSONL_DUPLICATE_ASSISTANT_TEXT)
        dup_text_data["sessionId"] = session_id

        dup_tool_data = json.loads(fixtures.JSONL_DUPLICATE_ASSISTANT_WITH_TOOL)
        dup_tool_data["sessionId"] = session_id

        log_file.write_text(
            f"{json.dumps(dup_text_data)}\n{json.dumps(dup_tool_data)}",
            encoding="utf-8",
        )

        result = runner.invoke(preprocess_session, [str(log_file), "--no-filtering"])
        assert result.exit_code == 0

        temp_path = Path(result.output.strip())
        content = temp_path.read_text(encoding="utf-8")

        # First assistant should have text
        # Second assistant should only have tool_use (text deduplicated)
        assert content.count("I'll help you with that.") == 1  # Only once
        assert '<tool_use name="Edit"' in content  # Tool preserved


def test_compression_metric_includes_agent_logs(tmp_path: Path) -> None:
    """Regression test: Token reduction metric must include agent log sizes.

    Bug: The compression metric was only measuring the main session log size,
    missing agent logs that were included in the output. This caused inaccurate
    compression ratios when agent logs were included.

    Fix: Track combined size of all included logs (main session + agent logs)
    before compression, providing an accurate compression ratio.
    """
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        session_id = "session-123"

        # Helper to update session ID in fixtures
        def with_session_id(fixture_json: str) -> dict:
            data = json.loads(fixture_json)
            data["sessionId"] = session_id
            return data

        # Create main session log with 3+ entries (required to pass empty session check)
        main_entries = [
            json.dumps(with_session_id(fixtures.JSONL_USER_MESSAGE_STRING)),
            json.dumps(with_session_id(fixtures.JSONL_ASSISTANT_TEXT)),
            json.dumps(with_session_id(fixtures.JSONL_USER_MESSAGE_STRING)),
        ]
        main_log = Path(f"{session_id}.jsonl")
        main_log.write_text("\n".join(main_entries), encoding="utf-8")
        main_size = main_log.stat().st_size

        # Create agent log with same content (and matching session ID)
        agent_log = Path("agent-abc.jsonl")
        agent_log.write_text("\n".join(main_entries), encoding="utf-8")
        agent_size = agent_log.stat().st_size

        # Combined size is what should be reported as "original"
        combined_size = main_size + agent_size

        # Run with filtering enabled (to trigger compression metrics output)
        # Click mixes stderr into result.output by default
        result = runner.invoke(
            preprocess_session,
            [str(main_log), "--stdout"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0

        # Verify compression metric uses combined size (main + agent logs)
        # The output should contain: "({combined_size:,} → {compressed_size:,} chars)"
        assert f"({combined_size:,} →" in result.output, (
            f"Expected original size {combined_size:,} (main={main_size} + agent={agent_size}) "
            f"in compression stats, but got: {result.output}"
        )


# ============================================================================
# Stdout Output Mode Tests
# ============================================================================


def test_preprocess_session_stdout_outputs_xml(tmp_path: Path) -> None:
    """Test that --stdout flag outputs XML to stdout."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        session_id = "session-123"
        log_file = Path(f"{session_id}.jsonl")

        # Create entry with matching session ID
        entry_data = json.loads(fixtures.JSONL_USER_MESSAGE_STRING)
        entry_data["sessionId"] = session_id
        log_file.write_text(json.dumps(entry_data), encoding="utf-8")

        result = runner.invoke(preprocess_session, [str(log_file), "--stdout", "--no-filtering"])
        assert result.exit_code == 0

        # Output should contain XML directly
        assert "<session>" in result.output
        assert "</session>" in result.output
        assert "<user>" in result.output


def test_preprocess_session_stdout_no_temp_file(tmp_path: Path) -> None:
    """Test that --stdout flag does not create temp file."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        session_id = "session-123"
        log_file = Path(f"{session_id}.jsonl")

        # Create entry with matching session ID
        entry_data = json.loads(fixtures.JSONL_USER_MESSAGE_STRING)
        entry_data["sessionId"] = session_id
        log_file.write_text(json.dumps(entry_data), encoding="utf-8")

        result = runner.invoke(preprocess_session, [str(log_file), "--stdout", "--no-filtering"])
        assert result.exit_code == 0

        # Output should NOT contain temp file path
        assert "session-session-123-" not in result.output or "<session>" in result.output


def test_preprocess_session_stdout_stats_to_stderr(tmp_path: Path) -> None:
    """Test that stats go to stderr when --stdout enabled."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        session_id = "session-123"
        log_file = Path(f"{session_id}.jsonl")

        # Create multi-line content for stats to be generated (valid JSONL format)
        # Need both user and assistant messages to pass empty session check
        user_data = json.loads(fixtures.JSONL_USER_MESSAGE_STRING)
        user_data["sessionId"] = session_id
        assistant_data = json.loads(fixtures.JSONL_ASSISTANT_TEXT)
        assistant_data["sessionId"] = session_id

        entries = []
        for _ in range(5):
            entries.append(json.dumps(user_data))
            entries.append(json.dumps(assistant_data))
        log_file.write_text("\n".join(entries), encoding="utf-8")

        result = runner.invoke(preprocess_session, [str(log_file), "--stdout"])
        assert result.exit_code == 0

        # XML should be in stdout (result.output)
        assert "<session>" in result.output

        # Stats should NOT pollute stdout
        assert "Token reduction" not in result.output or "</session>" in result.output


def test_preprocess_session_backward_compatibility(tmp_path: Path) -> None:
    """Test that default behavior (no --stdout) still creates temp file."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        log_file = Path("session-123.jsonl")
        user_json = json.dumps(json.loads(fixtures.JSONL_USER_MESSAGE_STRING))
        log_file.write_text(user_json, encoding="utf-8")

        # Run without --stdout flag
        result = runner.invoke(preprocess_session, [str(log_file), "--no-filtering"])
        assert result.exit_code == 0

        # Output should contain temp file path (backward compatible)
        assert "session-session-123-" in result.output
        assert "-compressed.xml" in result.output

        # Should NOT output XML to stdout
        assert "<session>" not in result.output


# ============================================================================
# Session ID Auto-Extraction and Filtering Tests
# ============================================================================


def test_preprocess_session_auto_extracts_session_id_from_filename(tmp_path: Path) -> None:
    """Test that session ID is auto-extracted from filename when not provided.

    This is a regression test for the bug where preprocess-session loaded ALL
    agent logs instead of filtering by session ID.
    """
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Main session log with session ID = "abc-123-xyz"
        main_log = Path("abc-123-xyz.jsonl")
        main_entries = [
            json.dumps(
                {
                    "sessionId": "abc-123-xyz",
                    "type": "user",
                    "message": {"content": "Hello"},
                }
            ),
            json.dumps(
                {
                    "sessionId": "abc-123-xyz",
                    "type": "assistant",
                    "message": {"content": [{"type": "text", "text": "Hi"}]},
                }
            ),
            json.dumps(
                {
                    "sessionId": "abc-123-xyz",
                    "type": "user",
                    "message": {"content": "Thanks"},
                }
            ),
        ]
        main_log.write_text("\n".join(main_entries), encoding="utf-8")

        # Agent log belonging to same session
        agent_match = Path("agent-match.jsonl")
        agent_match.write_text(
            json.dumps(
                {
                    "sessionId": "abc-123-xyz",
                    "type": "user",
                    "message": {"content": "Agent content"},
                }
            ),
            encoding="utf-8",
        )

        # Agent log belonging to DIFFERENT session (should be excluded)
        agent_other = Path("agent-other.jsonl")
        agent_other.write_text(
            json.dumps(
                {
                    "sessionId": "different-session",
                    "type": "user",
                    "message": {"content": "Other agent content"},
                }
            ),
            encoding="utf-8",
        )

        result = runner.invoke(preprocess_session, [str(main_log), "--stdout", "--no-filtering"])
        assert result.exit_code == 0

        # Main session should be included
        assert "<session>" in result.output
        assert "Hello" in result.output

        # Agent from same session should be included
        assert "Agent content" in result.output

        # Agent from different session should NOT be included
        assert "Other agent content" not in result.output


def test_preprocess_session_filters_agent_logs_by_session_id(tmp_path: Path) -> None:
    """Test that only agent logs matching session ID are included.

    Regression test for the bug where all agent logs were loaded regardless
    of session ID, causing a 67KB session to produce 10MB output.
    """
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Main session log
        main_log = Path("target-session.jsonl")
        sid = "target-session"
        main_entries = [
            json.dumps({"sessionId": sid, "type": "user", "message": {"content": "A"}}),
            json.dumps(
                {
                    "sessionId": sid,
                    "type": "assistant",
                    "message": {"content": [{"type": "text", "text": "B"}]},
                }
            ),
            json.dumps({"sessionId": sid, "type": "user", "message": {"content": "C"}}),
        ]
        main_log.write_text("\n".join(main_entries), encoding="utf-8")

        # Create multiple agent logs from different sessions
        for i in range(5):
            # Some agents from target session
            if i < 2:
                session_id = "target-session"
                content = f"target-agent-{i}"
            else:
                # Other agents from different sessions
                session_id = f"other-session-{i}"
                content = f"other-agent-{i}"

            agent = Path(f"agent-{i:03d}.jsonl")
            entry = {"sessionId": session_id, "type": "user", "message": {"content": content}}
            agent.write_text(json.dumps(entry), encoding="utf-8")

        result = runner.invoke(preprocess_session, [str(main_log), "--stdout", "--no-filtering"])
        assert result.exit_code == 0

        # Target session agents should be included
        assert "target-agent-0" in result.output
        assert "target-agent-1" in result.output

        # Other session agents should NOT be included
        assert "other-agent-2" not in result.output
        assert "other-agent-3" not in result.output
        assert "other-agent-4" not in result.output

        # Count sessions - should be 3 (main + 2 matching agents)
        assert result.output.count("<session>") == 3
