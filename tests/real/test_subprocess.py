"""Tests for subprocess wrapper with rich error context."""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from erk_shared.subprocess_utils import run_subprocess_with_context


def test_success_case_returns_completed_process() -> None:
    """Test that successful subprocess execution returns CompletedProcess."""
    with patch("erk_shared.subprocess_utils.subprocess.run") as mock_run:
        # Setup successful execution
        mock_result = Mock(spec=subprocess.CompletedProcess)
        mock_result.returncode = 0
        mock_result.stdout = "success output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # Execute
        result = run_subprocess_with_context(
            cmd=["git", "status"],
            operation_context="check git status",
            cwd=Path("/repo"),
        )

        # Verify
        assert result == mock_result
        assert result.returncode == 0
        assert result.stdout == "success output"

        # Verify subprocess.run was called with correct parameters
        mock_run.assert_called_once_with(
            ["git", "status"],
            cwd=Path("/repo"),
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
            stdout=None,
            stderr=None,
        )


def test_failure_with_stderr_includes_stderr_in_error() -> None:
    """Test that subprocess failure with stderr includes stderr in error message."""
    with patch("erk_shared.subprocess_utils.subprocess.run") as mock_run:
        # Setup failed execution with stderr
        error = subprocess.CalledProcessError(
            returncode=1,
            cmd=["git", "checkout", "nonexistent"],
            stderr="error: pathspec 'nonexistent' did not match any file(s) known to git",
        )
        mock_run.side_effect = error

        # Execute and verify exception
        with pytest.raises(RuntimeError) as exc_info:
            run_subprocess_with_context(
                cmd=["git", "checkout", "nonexistent"],
                operation_context="checkout branch 'nonexistent'",
                cwd=Path("/repo"),
            )

        # Verify error message contains all expected parts
        error_message = str(exc_info.value)
        assert "Failed to checkout branch 'nonexistent'" in error_message
        assert "Command: git checkout nonexistent" in error_message
        assert "Exit code: 1" in error_message
        assert (
            "stderr: error: pathspec 'nonexistent' did not match any file(s) known to git"
            in error_message
        )


def test_failure_without_stderr_handles_gracefully() -> None:
    """Test that subprocess failure without stderr still produces useful error."""
    with patch("erk_shared.subprocess_utils.subprocess.run") as mock_run:
        # Setup failed execution without stderr
        error = subprocess.CalledProcessError(
            returncode=127,
            cmd=["nonexistent-command"],
            stderr=None,
        )
        mock_run.side_effect = error

        # Execute and verify exception
        with pytest.raises(RuntimeError) as exc_info:
            run_subprocess_with_context(
                cmd=["nonexistent-command"],
                operation_context="run nonexistent command",
            )

        # Verify error message contains command and exit code but not stderr
        error_message = str(exc_info.value)
        assert "Failed to run nonexistent command" in error_message
        assert "Command: nonexistent-command" in error_message
        assert "Exit code: 127" in error_message
        # Should not have stderr line when stderr is None
        assert "stderr:" not in error_message


def test_failure_with_empty_stderr_omits_stderr_line() -> None:
    """Test that subprocess failure with empty stderr omits the stderr line."""
    with patch("erk_shared.subprocess_utils.subprocess.run") as mock_run:
        # Setup failed execution with empty stderr
        error = subprocess.CalledProcessError(
            returncode=1,
            cmd=["command"],
            stderr="   \n  ",  # Whitespace only
        )
        mock_run.side_effect = error

        # Execute and verify exception
        with pytest.raises(RuntimeError) as exc_info:
            run_subprocess_with_context(
                cmd=["command"],
                operation_context="run command",
            )

        # Verify error message omits stderr when it's only whitespace
        error_message = str(exc_info.value)
        assert "Failed to run command" in error_message
        assert "Command: command" in error_message
        assert "Exit code: 1" in error_message
        assert "stderr:" not in error_message


def test_exception_chaining_preserved() -> None:
    """Test that original CalledProcessError is preserved via exception chaining."""
    with patch("erk_shared.subprocess_utils.subprocess.run") as mock_run:
        # Setup failed execution
        original_error = subprocess.CalledProcessError(
            returncode=1,
            cmd=["git", "status"],
            stderr="fatal: not a git repository",
        )
        mock_run.side_effect = original_error

        # Execute and verify exception chaining
        with pytest.raises(RuntimeError) as exc_info:
            run_subprocess_with_context(
                cmd=["git", "status"],
                operation_context="check git status",
            )

        # Verify original exception is preserved as __cause__
        assert exc_info.value.__cause__ is original_error
        assert isinstance(exc_info.value.__cause__, subprocess.CalledProcessError)


def test_parameter_pass_through() -> None:
    """Test that all kwargs are correctly passed through to subprocess.run."""
    with patch("erk_shared.subprocess_utils.subprocess.run") as mock_run:
        # Setup successful execution
        mock_result = Mock(spec=subprocess.CompletedProcess)
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Execute with custom kwargs
        run_subprocess_with_context(
            cmd=["echo", "test"],
            operation_context="echo test",
            cwd=Path("/tmp"),
            timeout=30,
            env={"VAR": "value"},
        )

        # Verify all parameters including custom kwargs were passed
        mock_run.assert_called_once_with(
            ["echo", "test"],
            cwd=Path("/tmp"),
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
            stdout=None,
            stderr=None,
            timeout=30,
            env={"VAR": "value"},
        )


def test_check_false_behavior_no_exception() -> None:
    """Test that check=False prevents exception on non-zero exit."""
    with patch("erk_shared.subprocess_utils.subprocess.run") as mock_run:
        # Setup failed execution but with check=False
        mock_result = Mock(spec=subprocess.CompletedProcess)
        mock_result.returncode = 1
        mock_result.stderr = "some error"
        mock_run.return_value = mock_result

        # Execute with check=False - should NOT raise
        result = run_subprocess_with_context(
            cmd=["command"],
            operation_context="run command",
            check=False,
        )

        # Verify result returned without exception
        assert result == mock_result
        assert result.returncode == 1


def test_custom_encoding_parameter() -> None:
    """Test that custom encoding parameter is passed through."""
    with patch("erk_shared.subprocess_utils.subprocess.run") as mock_run:
        # Setup successful execution
        mock_result = Mock(spec=subprocess.CompletedProcess)
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Execute with custom encoding
        run_subprocess_with_context(
            cmd=["cat", "file.txt"],
            operation_context="read file",
            encoding="latin-1",
        )

        # Verify custom encoding was used
        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["encoding"] == "latin-1"


def test_capture_output_false_parameter() -> None:
    """Test that capture_output=False is passed through correctly."""
    with patch("erk_shared.subprocess_utils.subprocess.run") as mock_run:
        # Setup successful execution
        mock_result = Mock(spec=subprocess.CompletedProcess)
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Execute with capture_output=False
        run_subprocess_with_context(
            cmd=["echo", "test"],
            operation_context="echo test",
            capture_output=False,
        )

        # Verify capture_output=False was used
        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["capture_output"] is False


def test_text_false_parameter() -> None:
    """Test that text=False is passed through correctly."""
    with patch("erk_shared.subprocess_utils.subprocess.run") as mock_run:
        # Setup successful execution
        mock_result = Mock(spec=subprocess.CompletedProcess)
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Execute with text=False
        run_subprocess_with_context(
            cmd=["command"],
            operation_context="run command",
            text=False,
        )

        # Verify text=False was used
        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["text"] is False


def test_explicit_stderr_with_default_capture_output() -> None:
    """Test that explicit stderr parameter works with default capture_output=True.

    Regression test: When capture_output=True (the default), passing explicit
    stdout/stderr parameters should disable capture_output to avoid ValueError.
    """
    with patch("erk_shared.subprocess_utils.subprocess.run") as mock_run:
        # Setup successful execution
        mock_result = Mock(spec=subprocess.CompletedProcess)
        mock_result.returncode = 0
        mock_result.stderr = "some output"
        mock_run.return_value = mock_result

        # Execute with explicit stderr parameter - should NOT raise ValueError
        result = run_subprocess_with_context(
            cmd=["gt", "sync"],
            operation_context="sync with Graphite",
            stderr=subprocess.PIPE,
        )

        # Verify it succeeded
        assert result == mock_result

        # Verify subprocess.run was called with explicit stderr and capture_output=False
        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["stderr"] == subprocess.PIPE
        # capture_output should be disabled when explicit stdout/stderr is passed
        assert call_kwargs["capture_output"] is False


def test_explicit_stdout_and_stderr_both_disable_capture_output() -> None:
    """Test that both stdout and stderr parameters disable capture_output."""
    with patch("erk_shared.subprocess_utils.subprocess.run") as mock_run:
        # Setup successful execution
        mock_result = Mock(spec=subprocess.CompletedProcess)
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Execute with both stdout and stderr explicit
        result = run_subprocess_with_context(
            cmd=["gt", "sync"],
            operation_context="sync with Graphite",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

        # Verify it succeeded
        assert result == mock_result

        # Verify subprocess.run was called with both explicit and capture_output=False
        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["stdout"] == subprocess.DEVNULL
        assert call_kwargs["stderr"] == subprocess.PIPE
        assert call_kwargs["capture_output"] is False


def test_failure_with_stdout_includes_stdout_in_error() -> None:
    """Test that subprocess failure with stdout includes stdout in error message."""
    with patch("erk_shared.subprocess_utils.subprocess.run") as mock_run:
        # Setup failed execution with stdout
        error = subprocess.CalledProcessError(
            returncode=1,
            cmd=["gt", "delete", "branch"],
        )
        error.stdout = "ERROR: Could not find branch 'branch'"
        mock_run.side_effect = error

        # Execute and verify exception
        with pytest.raises(RuntimeError) as exc_info:
            run_subprocess_with_context(
                cmd=["gt", "delete", "branch"],
                operation_context="delete branch 'branch' with Graphite",
                cwd=Path("/repo"),
            )

        # Verify error message contains all expected parts including stdout
        error_message = str(exc_info.value)
        assert "Failed to delete branch 'branch' with Graphite" in error_message
        assert "Command: gt delete branch" in error_message
        assert "Exit code: 1" in error_message
        assert "stdout: ERROR: Could not find branch 'branch'" in error_message


def test_failure_with_both_stdout_and_stderr_includes_both() -> None:
    """Test that subprocess failure with both outputs includes both in error."""
    with patch("erk_shared.subprocess_utils.subprocess.run") as mock_run:
        # Setup failed execution with both stdout and stderr
        error = subprocess.CalledProcessError(
            returncode=1,
            cmd=["command", "arg"],
        )
        error.stdout = "Output message"
        error.stderr = "Error message"
        mock_run.side_effect = error

        # Execute and verify exception
        with pytest.raises(RuntimeError) as exc_info:
            run_subprocess_with_context(
                cmd=["command", "arg"],
                operation_context="run command",
                cwd=Path("/repo"),
            )

        # Verify error message contains both stdout and stderr
        error_message = str(exc_info.value)
        assert "Failed to run command" in error_message
        assert "Command: command arg" in error_message
        assert "Exit code: 1" in error_message
        assert "stdout: Output message" in error_message
        assert "stderr: Error message" in error_message
