"""Token estimation, splitting, max-tokens CLI, and output dir tests."""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.preprocess_session import (
    estimate_tokens,
    preprocess_session,
    split_entries_to_chunks,
)

# ============================================================================
# Token Estimation Tests
# ============================================================================


def test_estimate_tokens_empty_string() -> None:
    """Test token estimation for empty string."""
    assert estimate_tokens("") == 0


def test_estimate_tokens_short_string() -> None:
    """Test token estimation for short string."""
    # 4 chars = 1 token
    assert estimate_tokens("abcd") == 1
    # 8 chars = 2 tokens
    assert estimate_tokens("abcdefgh") == 2


def test_estimate_tokens_long_string() -> None:
    """Test token estimation for longer strings."""
    # 100 chars = 25 tokens
    assert estimate_tokens("x" * 100) == 25
    # 1000 chars = 250 tokens
    assert estimate_tokens("y" * 1000) == 250


# ============================================================================
# Split Entries to Chunks Tests
# ============================================================================


def test_split_entries_empty() -> None:
    """Test splitting empty entries list returns single empty session."""
    chunks = split_entries_to_chunks([], max_tokens=1000, source_label=None, enable_pruning=True)
    assert len(chunks) == 1
    assert "<session>" in chunks[0]
    assert "</session>" in chunks[0]


def test_split_entries_single_small_entry() -> None:
    """Test that single small entry returns single chunk."""
    entries = [{"type": "user", "message": {"content": "Hello"}}]
    chunks = split_entries_to_chunks(
        entries, max_tokens=1000, source_label=None, enable_pruning=True
    )
    assert len(chunks) == 1
    assert "Hello" in chunks[0]


def test_split_entries_splits_on_budget() -> None:
    """Test that entries are split when exceeding token budget."""
    # Create entries that together exceed budget but individually fit
    entries = [
        {"type": "user", "message": {"content": "A" * 100}},  # ~25 tokens
        {"type": "user", "message": {"content": "B" * 100}},  # ~25 tokens
        {"type": "user", "message": {"content": "C" * 100}},  # ~25 tokens
    ]
    # With max_tokens=40, should split into multiple chunks
    chunks = split_entries_to_chunks(entries, max_tokens=40, source_label=None, enable_pruning=True)
    # Should be more than 1 chunk
    assert len(chunks) > 1
    # Each chunk should be valid XML
    for chunk in chunks:
        assert "<session>" in chunk
        assert "</session>" in chunk


def test_split_entries_preserves_all_content() -> None:
    """Test that splitting preserves all original content."""
    entries = [
        {"type": "user", "message": {"content": "First message"}},
        {"type": "user", "message": {"content": "Second message"}},
        {"type": "user", "message": {"content": "Third message"}},
    ]
    # Use small budget to force splitting
    chunks = split_entries_to_chunks(entries, max_tokens=50, source_label=None, enable_pruning=True)

    # Concatenate all chunks and verify all content is present
    combined = "\n".join(chunks)
    assert "First message" in combined
    assert "Second message" in combined
    assert "Third message" in combined


def test_split_entries_includes_source_label() -> None:
    """Test that source label is included in all chunks."""
    entries = [
        {"type": "user", "message": {"content": "A" * 100}},
        {"type": "user", "message": {"content": "B" * 100}},
    ]
    chunks = split_entries_to_chunks(
        entries, max_tokens=40, source_label="agent-123", enable_pruning=True
    )

    # Source label should be in each chunk
    for chunk in chunks:
        assert '<meta source="agent-123" />' in chunk


def test_split_entries_each_chunk_is_valid_xml() -> None:
    """Test that each chunk is a valid XML document."""
    entries = [{"type": "user", "message": {"content": "Entry " + str(i)}} for i in range(10)]
    chunks = split_entries_to_chunks(entries, max_tokens=50, source_label=None, enable_pruning=True)

    for chunk in chunks:
        # Each chunk should have proper XML structure
        assert chunk.startswith("<session>")
        assert chunk.endswith("</session>")
        # Check for balanced tags
        assert chunk.count("<session>") == 1
        assert chunk.count("</session>") == 1


def test_split_entries_respects_token_limit() -> None:
    """Test that each chunk respects the token limit."""
    entries = [{"type": "user", "message": {"content": "Message " + "x" * 50}} for i in range(5)]
    max_tokens = 100
    chunks = split_entries_to_chunks(
        entries, max_tokens=max_tokens, source_label=None, enable_pruning=True
    )

    # Each chunk should be under the token limit (approximately)
    for chunk in chunks:
        chunk_tokens = estimate_tokens(chunk)
        # Allow some overhead for XML wrapper
        assert chunk_tokens <= max_tokens + 20


# ============================================================================
# Max Tokens CLI Tests
# ============================================================================


def test_preprocess_session_max_tokens_creates_multiple_files(tmp_path: Path) -> None:
    """Test that --max-tokens creates multiple output files."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        session_id = "session-123"
        log_file = Path(f"{session_id}.jsonl")

        # Create entries that will exceed a small token budget
        entries = []
        for i in range(10):
            entry = {
                "sessionId": session_id,
                "type": "user",
                "message": {"content": f"Message {i} " + "x" * 200},
            }
            entries.append(json.dumps(entry))

        # Add assistant messages to pass empty session check
        for i in range(10):
            entry = {
                "sessionId": session_id,
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": f"Response {i}"}]},
            }
            entries.append(json.dumps(entry))

        log_file.write_text("\n".join(entries), encoding="utf-8")

        result = runner.invoke(
            preprocess_session, [str(log_file), "--max-tokens", "100", "--no-filtering"]
        )
        assert result.exit_code == 0

        # Should output multiple file paths
        output_lines = result.output.strip().split("\n")
        assert len(output_lines) > 1

        # Each path should exist and contain valid XML
        for line in output_lines:
            path = Path(line.strip())
            assert path.exists()
            content = path.read_text(encoding="utf-8")
            assert "<session>" in content
            assert "</session>" in content


def test_preprocess_session_max_tokens_stdout_uses_delimiter(tmp_path: Path) -> None:
    """Test that --max-tokens with --stdout uses chunk delimiter."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        session_id = "session-123"
        log_file = Path(f"{session_id}.jsonl")

        # Create entries that will exceed a small token budget
        entries = []
        for i in range(10):
            entry = {
                "sessionId": session_id,
                "type": "user",
                "message": {"content": f"Message {i} " + "x" * 200},
            }
            entries.append(json.dumps(entry))

        # Add assistant messages
        for i in range(10):
            entry = {
                "sessionId": session_id,
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": f"Response {i}"}]},
            }
            entries.append(json.dumps(entry))

        log_file.write_text("\n".join(entries), encoding="utf-8")

        result = runner.invoke(
            preprocess_session,
            [str(log_file), "--max-tokens", "100", "--stdout", "--no-filtering"],
        )
        assert result.exit_code == 0

        # Output should contain chunk delimiter
        assert "---CHUNK---" in result.output

        # Each chunk should be valid XML
        chunks = result.output.split("---CHUNK---")
        assert len(chunks) > 1
        for chunk in chunks:
            chunk = chunk.strip()
            if chunk:
                assert "<session>" in chunk
                assert "</session>" in chunk


def test_preprocess_session_max_tokens_no_split_if_under_budget(tmp_path: Path) -> None:
    """Test that --max-tokens doesn't split if content is under budget."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        session_id = "session-123"
        log_file = Path(f"{session_id}.jsonl")

        # Create small entries that won't exceed budget
        entries = [
            json.dumps({"sessionId": session_id, "type": "user", "message": {"content": "Hello"}}),
            json.dumps(
                {
                    "sessionId": session_id,
                    "type": "assistant",
                    "message": {"content": [{"type": "text", "text": "Hi"}]},
                }
            ),
            json.dumps({"sessionId": session_id, "type": "user", "message": {"content": "Thanks"}}),
        ]
        log_file.write_text("\n".join(entries), encoding="utf-8")

        result = runner.invoke(
            preprocess_session, [str(log_file), "--max-tokens", "10000", "--no-filtering"]
        )
        assert result.exit_code == 0

        # Should output single file path (no splitting)
        output_lines = result.output.strip().split("\n")
        assert len(output_lines) == 1
        assert "part" not in output_lines[0]


def test_preprocess_session_max_tokens_preserves_content(tmp_path: Path) -> None:
    """Test that --max-tokens preserves all content across chunks."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        session_id = "session-123"
        log_file = Path(f"{session_id}.jsonl")

        # Create entries with unique identifiable content
        messages = ["UNIQUE_MSG_AAA", "UNIQUE_MSG_BBB", "UNIQUE_MSG_CCC"]
        entries = []
        for msg in messages:
            content = msg + " " + "x" * 100
            entry = {"sessionId": session_id, "type": "user", "message": {"content": content}}
            entries.append(json.dumps(entry))
        # Add assistant response
        entries.append(
            json.dumps(
                {
                    "sessionId": session_id,
                    "type": "assistant",
                    "message": {"content": [{"type": "text", "text": "Response"}]},
                }
            )
        )

        log_file.write_text("\n".join(entries), encoding="utf-8")

        result = runner.invoke(
            preprocess_session,
            [str(log_file), "--max-tokens", "100", "--stdout", "--no-filtering"],
        )
        assert result.exit_code == 0

        # All unique messages should be present in output
        for msg in messages:
            assert msg in result.output


def test_preprocess_session_max_tokens_file_naming(tmp_path: Path) -> None:
    """Test that split files have correct naming pattern."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        session_id = "test-session-abc"
        log_file = Path(f"{session_id}.jsonl")

        # Create enough content to force splitting
        entries = []
        for i in range(20):
            entries.append(
                json.dumps(
                    {
                        "sessionId": session_id,
                        "type": "user",
                        "message": {"content": f"Msg{i} " + "x" * 200},
                    }
                )
            )
            entries.append(
                json.dumps(
                    {
                        "sessionId": session_id,
                        "type": "assistant",
                        "message": {"content": [{"type": "text", "text": f"R{i}"}]},
                    }
                )
            )

        log_file.write_text("\n".join(entries), encoding="utf-8")

        result = runner.invoke(
            preprocess_session, [str(log_file), "--max-tokens", "50", "--no-filtering"]
        )
        assert result.exit_code == 0

        # Check file naming pattern
        output_lines = result.output.strip().split("\n")
        for i, line in enumerate(output_lines, start=1):
            path = Path(line.strip())
            # Should contain part number
            assert f"part{i}" in path.name
            # Should contain session ID
            assert session_id in path.name


# ============================================================================
# Output Dir and Prefix Tests
# ============================================================================


def test_preprocess_session_output_dir_and_prefix_single_file(tmp_path: Path) -> None:
    """Test that --output-dir and --prefix create named file with session ID."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        session_id = "abc-123-xyz"
        log_file = Path(f"{session_id}.jsonl")

        # Create entries with matching session ID
        entries = [
            json.dumps({"sessionId": session_id, "type": "user", "message": {"content": "Hello"}}),
            json.dumps(
                {
                    "sessionId": session_id,
                    "type": "assistant",
                    "message": {"content": [{"type": "text", "text": "Hi"}]},
                }
            ),
            json.dumps({"sessionId": session_id, "type": "user", "message": {"content": "Thanks"}}),
        ]
        log_file.write_text("\n".join(entries), encoding="utf-8")

        output_dir = tmp_path / "output"

        result = runner.invoke(
            preprocess_session,
            [
                str(log_file),
                "--output-dir",
                str(output_dir),
                "--prefix",
                "planning",
                "--no-filtering",
            ],
        )
        assert result.exit_code == 0

        # Check output file path
        output_lines = result.output.strip().split("\n")
        assert len(output_lines) == 1

        # File should be named: {prefix}-{session_id}.xml
        expected_file = output_dir / f"planning-{session_id}.xml"
        assert expected_file.exists()
        assert str(expected_file) == output_lines[0]

        # Verify content is valid XML
        content = expected_file.read_text(encoding="utf-8")
        assert "<session>" in content
        assert "</session>" in content


def test_preprocess_session_output_dir_creates_directory(tmp_path: Path) -> None:
    """Test that --output-dir creates the directory if it doesn't exist."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        session_id = "test-session"
        log_file = Path(f"{session_id}.jsonl")

        entries = [
            json.dumps({"sessionId": session_id, "type": "user", "message": {"content": "A"}}),
            json.dumps(
                {
                    "sessionId": session_id,
                    "type": "assistant",
                    "message": {"content": [{"type": "text", "text": "B"}]},
                }
            ),
            json.dumps({"sessionId": session_id, "type": "user", "message": {"content": "C"}}),
        ]
        log_file.write_text("\n".join(entries), encoding="utf-8")

        # Use nested directory that doesn't exist
        output_dir = tmp_path / "deep" / "nested" / "dir"
        assert not output_dir.exists()

        result = runner.invoke(
            preprocess_session,
            [
                str(log_file),
                "--output-dir",
                str(output_dir),
                "--prefix",
                "impl",
                "--no-filtering",
            ],
        )
        assert result.exit_code == 0

        # Directory should be created
        assert output_dir.exists()
        # File should exist
        expected_file = output_dir / f"impl-{session_id}.xml"
        assert expected_file.exists()


def test_preprocess_session_output_dir_with_max_tokens_creates_chunks(tmp_path: Path) -> None:
    """Test that --output-dir with --max-tokens creates numbered chunk files."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        session_id = "chunk-test"
        log_file = Path(f"{session_id}.jsonl")

        # Create enough content to force splitting
        entries = []
        for i in range(20):
            entries.append(
                json.dumps(
                    {
                        "sessionId": session_id,
                        "type": "user",
                        "message": {"content": f"Msg{i} " + "x" * 200},
                    }
                )
            )
            entries.append(
                json.dumps(
                    {
                        "sessionId": session_id,
                        "type": "assistant",
                        "message": {"content": [{"type": "text", "text": f"R{i}"}]},
                    }
                )
            )
        log_file.write_text("\n".join(entries), encoding="utf-8")

        output_dir = tmp_path / "chunks"

        result = runner.invoke(
            preprocess_session,
            [
                str(log_file),
                "--output-dir",
                str(output_dir),
                "--prefix",
                "impl",
                "--max-tokens",
                "100",
                "--no-filtering",
            ],
        )
        assert result.exit_code == 0

        # Should have multiple output files
        output_lines = result.output.strip().split("\n")
        assert len(output_lines) > 1

        # Each file should follow naming pattern: {prefix}-{session_id}-part{N}.xml
        for i, line in enumerate(output_lines, start=1):
            path = Path(line.strip())
            assert path.exists()
            assert path.name == f"impl-{session_id}-part{i}.xml"
            # Verify valid XML
            content = path.read_text(encoding="utf-8")
            assert "<session>" in content
            assert "</session>" in content


def test_preprocess_session_output_dir_requires_prefix(tmp_path: Path) -> None:
    """Test that --output-dir without --prefix raises error."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create a dummy log file so the path validation passes
        log_file = Path("test.jsonl")
        log_file.write_text("{}", encoding="utf-8")

        result = runner.invoke(
            preprocess_session,
            [str(log_file), "--output-dir", "/some/dir"],
        )
        assert result.exit_code != 0
        assert "--output-dir and --prefix must be used together" in result.output


def test_preprocess_session_prefix_requires_output_dir(tmp_path: Path) -> None:
    """Test that --prefix without --output-dir raises error."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create a dummy log file so the path validation passes
        log_file = Path("test.jsonl")
        log_file.write_text("{}", encoding="utf-8")

        result = runner.invoke(
            preprocess_session,
            [str(log_file), "--prefix", "planning"],
        )
        assert result.exit_code != 0
        assert "--output-dir and --prefix must be used together" in result.output


def test_preprocess_session_output_dir_and_stdout_mutually_exclusive(tmp_path: Path) -> None:
    """Test that --output-dir/--prefix and --stdout are mutually exclusive."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        log_file = Path("test.jsonl")
        log_file.write_text("{}", encoding="utf-8")

        result = runner.invoke(
            preprocess_session,
            [str(log_file), "--output-dir", str(tmp_path), "--prefix", "test", "--stdout"],
        )
        assert result.exit_code != 0
        assert "--output-dir/--prefix cannot be used with --stdout" in result.output


def test_preprocess_session_output_dir_preserves_all_content(tmp_path: Path) -> None:
    """Test that --output-dir preserves all content across chunks."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        session_id = "preserve-test"
        log_file = Path(f"{session_id}.jsonl")

        # Create entries with unique identifiable content
        messages = ["UNIQUE_AAA", "UNIQUE_BBB", "UNIQUE_CCC"]
        entries = []
        for msg in messages:
            content = msg + " " + "x" * 100
            entry = {"sessionId": session_id, "type": "user", "message": {"content": content}}
            entries.append(json.dumps(entry))
        # Add assistant response
        entries.append(
            json.dumps(
                {
                    "sessionId": session_id,
                    "type": "assistant",
                    "message": {"content": [{"type": "text", "text": "Response"}]},
                }
            )
        )
        log_file.write_text("\n".join(entries), encoding="utf-8")

        output_dir = tmp_path / "preserve"

        result = runner.invoke(
            preprocess_session,
            [
                str(log_file),
                "--output-dir",
                str(output_dir),
                "--prefix",
                "test",
                "--max-tokens",
                "100",
                "--no-filtering",
            ],
        )
        assert result.exit_code == 0

        # Read all output files and combine content
        combined_content = ""
        for line in result.output.strip().split("\n"):
            path = Path(line.strip())
            combined_content += path.read_text(encoding="utf-8")

        # All unique messages should be present
        for msg in messages:
            assert msg in combined_content
