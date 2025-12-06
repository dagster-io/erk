"""Unit tests for select_sessions kit CLI command.

Tests auto-selection logic based on branch context:
- On trunk: current session only
- Current trivial + substantial exists: auto-select substantial
- Current substantial: use current only
"""

import json

from click.testing import CliRunner

from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.select_sessions import (
    TRIVIAL_SIZE_THRESHOLD,
    auto_select_sessions,
    select_sessions,
)

# ============================================================================
# 1. Selection Logic Tests - Trunk Branch (4 tests)
# ============================================================================


def test_select_on_trunk_uses_current_only() -> None:
    """Test that on trunk branch, only current session is selected."""
    list_sessions_output = {
        "success": True,
        "branch_context": {
            "current_branch": "main",
            "trunk_branch": "main",
            "is_on_trunk": True,
        },
        "current_session_id": "abc123",
        "sessions": [
            {"session_id": "abc123", "size_bytes": 5000, "summary": "Current"},
            {"session_id": "def456", "size_bytes": 10000, "summary": "Other"},
        ],
        "project_dir": "/path/to/project",
    }

    result = auto_select_sessions(list_sessions_output)

    assert result["selection_mode"] == "trunk_current_only"
    assert len(result["selected_sessions"]) == 1
    assert result["selected_sessions"][0]["session_id"] == "abc123"


def test_select_on_trunk_no_current_session() -> None:
    """Test trunk selection when current session not in list."""
    list_sessions_output = {
        "success": True,
        "branch_context": {
            "current_branch": "main",
            "trunk_branch": "main",
            "is_on_trunk": True,
        },
        "current_session_id": "not_found",
        "sessions": [
            {"session_id": "abc123", "size_bytes": 5000, "summary": "Other"},
        ],
        "project_dir": "/path/to/project",
    }

    result = auto_select_sessions(list_sessions_output)

    assert result["selection_mode"] == "trunk_no_current"
    assert len(result["selected_sessions"]) == 0


def test_select_on_master_trunk() -> None:
    """Test that master branch is detected as trunk."""
    list_sessions_output = {
        "success": True,
        "branch_context": {
            "current_branch": "master",
            "trunk_branch": "master",
            "is_on_trunk": True,
        },
        "current_session_id": "abc123",
        "sessions": [
            {"session_id": "abc123", "size_bytes": 5000, "summary": "Current"},
        ],
        "project_dir": "/path/to/project",
    }

    result = auto_select_sessions(list_sessions_output)

    assert result["selection_mode"] == "trunk_current_only"


def test_select_trunk_includes_path_in_output() -> None:
    """Test that path is correctly included in selected sessions."""
    list_sessions_output = {
        "success": True,
        "branch_context": {
            "current_branch": "main",
            "trunk_branch": "main",
            "is_on_trunk": True,
        },
        "current_session_id": "abc123",
        "sessions": [
            {"session_id": "abc123", "size_bytes": 5000, "summary": "Test"},
        ],
        "project_dir": "/path/to/project",
    }

    result = auto_select_sessions(list_sessions_output)

    assert result["selected_sessions"][0]["path"] == "/path/to/project/abc123.jsonl"


# ============================================================================
# 2. Selection Logic Tests - Feature Branch Trivial Current (5 tests)
# ============================================================================


def test_select_trivial_current_selects_substantial() -> None:
    """Test that trivial current session causes selection of substantial sessions."""
    list_sessions_output = {
        "success": True,
        "branch_context": {
            "current_branch": "feature-xyz",
            "trunk_branch": "main",
            "is_on_trunk": False,
        },
        "current_session_id": "trivial123",
        "sessions": [
            {"session_id": "trivial123", "size_bytes": 100, "summary": "Trivial"},
            {"session_id": "substantial1", "size_bytes": 5000, "summary": "Big"},
            {"session_id": "substantial2", "size_bytes": 3000, "summary": "Medium"},
        ],
        "project_dir": "/path/to/project",
    }

    result = auto_select_sessions(list_sessions_output)

    assert result["selection_mode"] == "auto_substantial"
    assert len(result["selected_sessions"]) == 2
    session_ids = [s["session_id"] for s in result["selected_sessions"]]
    assert "substantial1" in session_ids
    assert "substantial2" in session_ids
    assert "trivial123" not in session_ids


def test_select_trivial_threshold() -> None:
    """Test that trivial threshold is correctly applied."""
    list_sessions_output = {
        "success": True,
        "branch_context": {
            "current_branch": "feature",
            "trunk_branch": "main",
            "is_on_trunk": False,
        },
        "current_session_id": "current",
        "sessions": [
            {
                "session_id": "current",
                "size_bytes": TRIVIAL_SIZE_THRESHOLD - 1,
                "summary": "Just under",
            },
            {
                "session_id": "substantial",
                "size_bytes": TRIVIAL_SIZE_THRESHOLD,
                "summary": "At threshold",
            },
        ],
        "project_dir": "/path",
    }

    result = auto_select_sessions(list_sessions_output)

    assert result["selection_mode"] == "auto_substantial"
    assert len(result["selected_sessions"]) == 1
    assert result["selected_sessions"][0]["session_id"] == "substantial"


def test_select_trivial_no_substantial_available() -> None:
    """Test fallback when current is trivial but no substantial sessions exist."""
    list_sessions_output = {
        "success": True,
        "branch_context": {
            "current_branch": "feature",
            "trunk_branch": "main",
            "is_on_trunk": False,
        },
        "current_session_id": "trivial",
        "sessions": [
            {"session_id": "trivial", "size_bytes": 100, "summary": "Small"},
            {"session_id": "also_trivial", "size_bytes": 200, "summary": "Also small"},
        ],
        "project_dir": "/path",
    }

    result = auto_select_sessions(list_sessions_output)

    # Should fall back to current
    assert result["selection_mode"] == "fallback_current"
    assert result["selected_sessions"][0]["session_id"] == "trivial"


def test_select_trivial_current_message() -> None:
    """Test that message correctly describes auto-selection."""
    list_sessions_output = {
        "success": True,
        "branch_context": {
            "current_branch": "feature",
            "trunk_branch": "main",
            "is_on_trunk": False,
        },
        "current_session_id": "trivial",
        "sessions": [
            {"session_id": "trivial", "size_bytes": 100, "summary": ""},
            {"session_id": "big1", "size_bytes": 2000, "summary": ""},
            {"session_id": "big2", "size_bytes": 3000, "summary": ""},
        ],
        "project_dir": "/path",
    }

    result = auto_select_sessions(list_sessions_output)

    assert "2 substantial" in result["message"]
    assert "trivial" in result["message"]


def test_select_trivial_preserves_metadata() -> None:
    """Test that selected sessions include size and summary metadata."""
    list_sessions_output = {
        "success": True,
        "branch_context": {
            "current_branch": "feature",
            "trunk_branch": "main",
            "is_on_trunk": False,
        },
        "current_session_id": "trivial",
        "sessions": [
            {"session_id": "trivial", "size_bytes": 100, "summary": "Tiny"},
            {"session_id": "big", "size_bytes": 5000, "summary": "Big session"},
        ],
        "project_dir": "/path",
    }

    result = auto_select_sessions(list_sessions_output)

    assert result["selected_sessions"][0]["size_bytes"] == 5000
    assert result["selected_sessions"][0]["summary"] == "Big session"


# ============================================================================
# 3. Selection Logic Tests - Feature Branch Substantial Current (3 tests)
# ============================================================================


def test_select_substantial_current_uses_current() -> None:
    """Test that substantial current session is used alone."""
    list_sessions_output = {
        "success": True,
        "branch_context": {
            "current_branch": "feature",
            "trunk_branch": "main",
            "is_on_trunk": False,
        },
        "current_session_id": "substantial",
        "sessions": [
            {"session_id": "substantial", "size_bytes": 5000, "summary": "Current"},
            {"session_id": "other", "size_bytes": 10000, "summary": "Other"},
        ],
        "project_dir": "/path",
    }

    result = auto_select_sessions(list_sessions_output)

    assert result["selection_mode"] == "current_substantial"
    assert len(result["selected_sessions"]) == 1
    assert result["selected_sessions"][0]["session_id"] == "substantial"


def test_select_substantial_current_ignores_other_substantial() -> None:
    """Test that other substantial sessions are ignored when current is substantial."""
    list_sessions_output = {
        "success": True,
        "branch_context": {
            "current_branch": "feature",
            "trunk_branch": "main",
            "is_on_trunk": False,
        },
        "current_session_id": "current",
        "sessions": [
            {"session_id": "current", "size_bytes": 2000, "summary": "Current"},
            {"session_id": "bigger", "size_bytes": 50000, "summary": "Much bigger"},
        ],
        "project_dir": "/path",
    }

    result = auto_select_sessions(list_sessions_output)

    assert result["selection_mode"] == "current_substantial"
    assert len(result["selected_sessions"]) == 1
    assert result["selected_sessions"][0]["session_id"] == "current"


def test_select_substantial_at_threshold() -> None:
    """Test selection when current is exactly at threshold."""
    list_sessions_output = {
        "success": True,
        "branch_context": {
            "current_branch": "feature",
            "trunk_branch": "main",
            "is_on_trunk": False,
        },
        "current_session_id": "current",
        "sessions": [
            {
                "session_id": "current",
                "size_bytes": TRIVIAL_SIZE_THRESHOLD,
                "summary": "At threshold",
            },
        ],
        "project_dir": "/path",
    }

    result = auto_select_sessions(list_sessions_output)

    # At threshold should count as substantial
    assert result["selection_mode"] == "current_substantial"


# ============================================================================
# 4. Edge Cases (4 tests)
# ============================================================================


def test_select_no_sessions() -> None:
    """Test handling of empty sessions list."""
    list_sessions_output = {
        "success": True,
        "branch_context": {
            "current_branch": "feature",
            "trunk_branch": "main",
            "is_on_trunk": False,
        },
        "current_session_id": None,
        "sessions": [],
        "project_dir": "/path",
    }

    result = auto_select_sessions(list_sessions_output)

    assert result["selection_mode"] == "no_sessions"
    assert len(result["selected_sessions"]) == 0


def test_select_missing_branch_context() -> None:
    """Test handling of missing branch context."""
    list_sessions_output = {
        "success": True,
        "branch_context": {},
        "current_session_id": "abc",
        "sessions": [
            {"session_id": "abc", "size_bytes": 5000, "summary": "Test"},
        ],
        "project_dir": "/path",
    }

    result = auto_select_sessions(list_sessions_output)

    # With missing is_on_trunk (defaults to False), should use substantial logic
    assert result["selection_mode"] == "current_substantial"


def test_select_missing_size_bytes() -> None:
    """Test handling of sessions without size_bytes."""
    list_sessions_output = {
        "success": True,
        "branch_context": {
            "current_branch": "feature",
            "trunk_branch": "main",
            "is_on_trunk": False,
        },
        "current_session_id": "current",
        "sessions": [
            {"session_id": "current", "summary": "No size"},  # Missing size_bytes
        ],
        "project_dir": "/path",
    }

    result = auto_select_sessions(list_sessions_output)

    # Missing size defaults to 0, which is trivial
    # But since no substantial exists, fallback to current
    assert result["selection_mode"] == "fallback_current"


def test_select_current_not_in_list() -> None:
    """Test when current_session_id doesn't match any session."""
    list_sessions_output = {
        "success": True,
        "branch_context": {
            "current_branch": "feature",
            "trunk_branch": "main",
            "is_on_trunk": False,
        },
        "current_session_id": "missing",
        "sessions": [
            {"session_id": "other", "size_bytes": 5000, "summary": "Other"},
        ],
        "project_dir": "/path",
    }

    result = auto_select_sessions(list_sessions_output)

    # Current is missing (None), so trivial check fails, falls through to auto_substantial
    assert result["selection_mode"] == "auto_substantial"


# ============================================================================
# 5. CLI Command Tests (6 tests)
# ============================================================================


def test_cli_success() -> None:
    """Test CLI with valid input."""
    list_sessions_input = {
        "success": True,
        "branch_context": {
            "current_branch": "feature",
            "trunk_branch": "main",
            "is_on_trunk": False,
        },
        "current_session_id": "abc123",
        "sessions": [
            {"session_id": "abc123", "size_bytes": 5000, "summary": "Test"},
        ],
        "project_dir": "/path/to/project",
    }

    runner = CliRunner()
    result = runner.invoke(
        select_sessions,
        [],
        input=json.dumps(list_sessions_input),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert "selected_sessions" in output
    assert "selection_mode" in output


def test_cli_invalid_json_error() -> None:
    """Test CLI error with invalid JSON input."""
    runner = CliRunner()
    result = runner.invoke(
        select_sessions,
        [],
        input="not valid json",
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "Invalid JSON" in output["error"]


def test_cli_failed_input_error() -> None:
    """Test CLI error when input indicates failure."""
    failed_input = {
        "success": False,
        "error": "Something went wrong",
    }

    runner = CliRunner()
    result = runner.invoke(
        select_sessions,
        [],
        input=json.dumps(failed_input),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False


def test_cli_output_structure() -> None:
    """Test that CLI output has expected structure."""
    list_sessions_input = {
        "success": True,
        "branch_context": {"is_on_trunk": False},
        "current_session_id": "abc",
        "sessions": [
            {"session_id": "abc", "size_bytes": 5000, "summary": ""},
        ],
        "project_dir": "/path",
    }

    runner = CliRunner()
    result = runner.invoke(
        select_sessions,
        [],
        input=json.dumps(list_sessions_input),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    assert "success" in output
    assert "selected_sessions" in output
    assert "selection_mode" in output
    assert "message" in output


def test_cli_trunk_selection() -> None:
    """Test CLI correctly applies trunk selection."""
    list_sessions_input = {
        "success": True,
        "branch_context": {
            "current_branch": "main",
            "trunk_branch": "main",
            "is_on_trunk": True,
        },
        "current_session_id": "current",
        "sessions": [
            {"session_id": "current", "size_bytes": 100, "summary": ""},
            {"session_id": "other", "size_bytes": 10000, "summary": ""},
        ],
        "project_dir": "/path",
    }

    runner = CliRunner()
    result = runner.invoke(
        select_sessions,
        [],
        input=json.dumps(list_sessions_input),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["selection_mode"] == "trunk_current_only"
    assert len(output["selected_sessions"]) == 1


def test_cli_auto_substantial_selection() -> None:
    """Test CLI correctly applies auto-substantial selection."""
    list_sessions_input = {
        "success": True,
        "branch_context": {
            "current_branch": "feature",
            "trunk_branch": "main",
            "is_on_trunk": False,
        },
        "current_session_id": "trivial",
        "sessions": [
            {"session_id": "trivial", "size_bytes": 100, "summary": ""},
            {"session_id": "big", "size_bytes": 5000, "summary": ""},
        ],
        "project_dir": "/path",
    }

    runner = CliRunner()
    result = runner.invoke(
        select_sessions,
        [],
        input=json.dumps(list_sessions_input),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["selection_mode"] == "auto_substantial"
    assert output["selected_sessions"][0]["session_id"] == "big"
