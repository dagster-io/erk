"""Integration tests for preprocess-session with real session log fixtures.

Tests processing of actual session log formats, including edge cases like
list-based tool_result content from Task agent responses.
"""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.preprocess_session import preprocess_session

# Path to fixtures relative to tests directory
FIXTURES_DIR = Path(__file__).parent.parent.parent.parent.parent / "fixtures" / "session_logs"

# Session fixture with list-based tool_result content (from Task agent responses)
ZETA_SESSION = FIXTURES_DIR / "project_zeta" / "session-zzz11111-2222-3333-4444-555555555555.jsonl"


def test_preprocess_session_handles_list_based_tool_result_content() -> None:
    """Integration test: process session with list-based tool_result content.

    Real Claude Code sessions can have tool_result entries where content is
    a list of {"type": "text", "text": "..."} blocks (from Task agent responses).
    This test verifies the preprocessor correctly extracts this format.
    """
    fixture_path = ZETA_SESSION

    # Verify fixture exists
    assert fixture_path.exists(), f"Fixture not found: {fixture_path}"

    runner = CliRunner()
    result = runner.invoke(preprocess_session, [str(fixture_path), "--stdout", "--no-filtering"])

    assert result.exit_code == 0, f"Command failed: {result.output}"

    # Verify the list-based content was extracted correctly
    output = result.output

    # Tool result should be present with tool_use_id
    assert '<tool_result tool="toolu_task_001">' in output

    # Both text blocks from the list should be in output
    assert "All tests passed successfully" in output
    assert "50 tests passed" in output
    assert "agentId: abc1234" in output

    # Verify basic session structure
    assert "<session>" in output
    assert "</session>" in output


def test_preprocess_session_preserves_conversation_flow_with_tool_results() -> None:
    """Test that conversation flow is preserved when tool_results have list content."""
    fixture_path = ZETA_SESSION

    runner = CliRunner()
    result = runner.invoke(preprocess_session, [str(fixture_path), "--stdout", "--no-filtering"])

    assert result.exit_code == 0
    output = result.output

    # Verify conversation elements are present in order
    assert "<user>Run the tests</user>" in output
    assert '<tool_use name="Task"' in output
    assert '<tool_result tool="toolu_task_001">' in output
    assert "<assistant>The tests passed successfully.</assistant>" in output
    assert "<user>Thanks!</user>" in output


def test_preprocess_session_extracts_branch_metadata_from_fixture() -> None:
    """Test that git branch metadata is extracted from fixture."""
    fixture_path = ZETA_SESSION

    runner = CliRunner()
    result = runner.invoke(preprocess_session, [str(fixture_path), "--stdout", "--no-filtering"])

    assert result.exit_code == 0

    # Branch metadata should be extracted
    assert 'branch="feature-branch"' in result.output
