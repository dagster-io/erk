"""Unit tests for user-prompt-hook command.

This test file uses the pure logic extraction pattern. Most tests call the
pure functions directly with no mocking required. The hook code is structured
with data class inputs (HookInput) and outputs (VenvCheckResult), making
tests clean and focused.
"""

from pathlib import Path

from erk.cli.commands.exec.scripts.user_prompt_hook import (
    HookAction,
    HookInput,
    VenvCheckResult,
    build_coding_standards_reminder,
    build_session_context,
    build_tripwires_reminder,
    check_venv,
)

# ============================================================================
# Pure Logic Tests for check_venv() - NO MOCKING REQUIRED
# ============================================================================


def test_check_venv_allows_when_bypass_signal_exists() -> None:
    """Bypass signal present - always allows, regardless of venv state."""
    result = check_venv(
        HookInput(
            session_id="test-session",
            repo_root=Path("/repo"),
            expected_venv=Path("/repo/.venv"),  # Venv expected
            actual_venv=None,  # But not activated
            bypass_signal_exists=True,  # Bypass present
        )
    )
    assert result.action == HookAction.ALLOW
    assert result.error_message == ""


def test_check_venv_allows_when_no_venv_expected() -> None:
    """No .venv directory exists - always allows."""
    result = check_venv(
        HookInput(
            session_id="test-session",
            repo_root=Path("/repo"),
            expected_venv=None,  # No .venv exists
            actual_venv=None,
            bypass_signal_exists=False,
        )
    )
    assert result.action == HookAction.ALLOW
    assert result.error_message == ""


def test_check_venv_allows_when_correct_venv_activated() -> None:
    """Correct venv activated - allows."""
    venv_path = Path("/repo/.venv")
    result = check_venv(
        HookInput(
            session_id="test-session",
            repo_root=Path("/repo"),
            expected_venv=venv_path,
            actual_venv=venv_path,  # Matches expected
            bypass_signal_exists=False,
        )
    )
    assert result.action == HookAction.ALLOW
    assert result.error_message == ""


def test_check_venv_blocks_when_no_venv_activated_but_expected() -> None:
    """No venv activated but .venv exists - blocks."""
    expected = Path("/repo/.venv")
    result = check_venv(
        HookInput(
            session_id="test-session",
            repo_root=Path("/repo"),
            expected_venv=expected,
            actual_venv=None,  # Not activated
            bypass_signal_exists=False,
        )
    )
    assert result.action == HookAction.BLOCK
    assert "No virtual environment activated" in result.error_message
    assert str(expected) in result.error_message
    assert "source" in result.error_message  # Activation hint


def test_check_venv_blocks_when_wrong_venv_activated() -> None:
    """Wrong venv activated - blocks with helpful message."""
    expected = Path("/repo/.venv")
    actual = Path("/other/project/.venv")
    result = check_venv(
        HookInput(
            session_id="test-session",
            repo_root=Path("/repo"),
            expected_venv=expected,
            actual_venv=actual,
            bypass_signal_exists=False,
        )
    )
    assert result.action == HookAction.BLOCK
    assert "Wrong virtual environment activated" in result.error_message
    assert str(expected) in result.error_message
    assert str(actual) in result.error_message


def test_check_venv_result_is_correct_type() -> None:
    """Verify check_venv returns VenvCheckResult with correct fields."""
    result = check_venv(
        HookInput(
            session_id="test-session",
            repo_root=Path("/repo"),
            expected_venv=None,
            actual_venv=None,
            bypass_signal_exists=False,
        )
    )
    assert isinstance(result, VenvCheckResult)
    assert isinstance(result.action, HookAction)
    assert isinstance(result.error_message, str)


# ============================================================================
# Pure Logic Tests for build_session_context() - NO MOCKING REQUIRED
# ============================================================================


def test_build_session_context_returns_session_prefix() -> None:
    """Session context includes session ID."""
    result = build_session_context("abc123")
    assert "session: abc123" in result


def test_build_session_context_returns_empty_for_unknown() -> None:
    """Unknown session returns empty string."""
    result = build_session_context("unknown")
    assert result == ""


def test_build_session_context_with_uuid_format() -> None:
    """Session context works with UUID-style session IDs."""
    session_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    result = build_session_context(session_id)
    assert session_id in result


# ============================================================================
# Pure Logic Tests for build_coding_standards_reminder() - NO MOCKING REQUIRED
# ============================================================================


def test_build_coding_standards_reminder_mentions_dignified_python() -> None:
    """Reminder mentions dignified-python skill."""
    result = build_coding_standards_reminder()
    assert "dignified-python" in result


def test_build_coding_standards_reminder_mentions_devrun() -> None:
    """Reminder mentions devrun agent for CI commands."""
    result = build_coding_standards_reminder()
    assert "devrun" in result


def test_build_coding_standards_reminder_mentions_no_try_except() -> None:
    """Reminder mentions LBYL rule (no try/except for control flow)."""
    result = build_coding_standards_reminder()
    assert "NO try/except" in result


def test_build_coding_standards_reminder_mentions_forbidden_tools() -> None:
    """Reminder lists tools that require devrun agent."""
    result = build_coding_standards_reminder()
    assert "pytest" in result
    assert "pyright" in result
    assert "ruff" in result


# ============================================================================
# Pure Logic Tests for build_tripwires_reminder() - NO MOCKING REQUIRED
# ============================================================================


def test_build_tripwires_reminder_mentions_tripwires_file() -> None:
    """Reminder mentions tripwires.md file."""
    result = build_tripwires_reminder()
    assert "tripwires.md" in result


def test_build_tripwires_reminder_mentions_docs_path() -> None:
    """Reminder includes full docs path."""
    result = build_tripwires_reminder()
    assert "docs/learned/tripwires.md" in result


# ============================================================================
# Tests for HookInput data class
# ============================================================================


def test_hook_input_is_frozen() -> None:
    """HookInput is immutable (frozen dataclass)."""
    hook_input = HookInput(
        session_id="test",
        repo_root=Path("/repo"),
        expected_venv=None,
        actual_venv=None,
        bypass_signal_exists=False,
    )
    # Attempting to modify should raise FrozenInstanceError
    try:
        hook_input.session_id = "changed"  # type: ignore[misc]
        raise AssertionError("Should have raised FrozenInstanceError")
    except AttributeError:
        pass  # Expected behavior for frozen dataclass


def test_hook_input_stores_all_fields() -> None:
    """HookInput correctly stores all provided fields."""
    repo_root = Path("/test/repo")
    expected = Path("/test/repo/.venv")
    actual = Path("/other/.venv")

    hook_input = HookInput(
        session_id="my-session",
        repo_root=repo_root,
        expected_venv=expected,
        actual_venv=actual,
        bypass_signal_exists=True,
    )

    assert hook_input.session_id == "my-session"
    assert hook_input.repo_root == repo_root
    assert hook_input.expected_venv == expected
    assert hook_input.actual_venv == actual
    assert hook_input.bypass_signal_exists is True


# ============================================================================
# Tests for VenvCheckResult data class
# ============================================================================


def test_venv_check_result_is_frozen() -> None:
    """VenvCheckResult is immutable (frozen dataclass)."""
    result = VenvCheckResult(HookAction.ALLOW, "")
    try:
        result.action = HookAction.BLOCK  # type: ignore[misc]
        raise AssertionError("Should have raised FrozenInstanceError")
    except AttributeError:
        pass  # Expected behavior for frozen dataclass


# ============================================================================
# Tests for HookAction enum
# ============================================================================


def test_hook_action_allow_has_exit_code_zero() -> None:
    """ALLOW action corresponds to exit code 0."""
    assert HookAction.ALLOW.value == 0


def test_hook_action_block_has_exit_code_two() -> None:
    """BLOCK action corresponds to exit code 2."""
    assert HookAction.BLOCK.value == 2
