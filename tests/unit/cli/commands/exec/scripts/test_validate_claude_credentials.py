"""Unit tests for validate_claude_credentials exec script.

Tests validation of Claude API credentials for CI workflows.
Uses monkeypatch for environment variable isolation and subprocess mocking.
"""

import json
import subprocess
from unittest.mock import MagicMock

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.validate_claude_credentials import (
    ValidationError,
    ValidationSuccess,
    _check_env_vars,
    _validate_credentials_impl,
)
from erk.cli.commands.exec.scripts.validate_claude_credentials import (
    validate_claude_credentials as validate_claude_credentials_command,
)

# ============================================================================
# 1. Helper Function Tests (3 tests)
# ============================================================================


def test_check_env_vars_oauth_token_set(monkeypatch: MagicMock) -> None:
    """Test env var check when CLAUDE_CODE_OAUTH_TOKEN is set."""
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "test-token")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    result = _check_env_vars()

    assert result is True


def test_check_env_vars_api_key_set(monkeypatch: MagicMock) -> None:
    """Test env var check when ANTHROPIC_API_KEY is set."""
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")

    result = _check_env_vars()

    assert result is True


def test_check_env_vars_neither_set(monkeypatch: MagicMock) -> None:
    """Test env var check when neither credential is set."""
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    result = _check_env_vars()

    assert result is False


# ============================================================================
# 2. Implementation Logic Tests (3 tests)
# ============================================================================


def test_validate_impl_missing_credentials(monkeypatch: MagicMock) -> None:
    """Test validation returns error when credentials are missing."""
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    result = _validate_credentials_impl()

    assert isinstance(result, ValidationError)
    assert result.success is False
    assert result.error == "credentials-missing"
    assert "CLAUDE_CODE_OAUTH_TOKEN" in result.message
    assert "ANTHROPIC_API_KEY" in result.message


def test_validate_impl_auth_failed(monkeypatch: MagicMock) -> None:
    """Test validation returns error when API call fails."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-invalid-key")

    # Mock subprocess.run to simulate failed API call
    def mock_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["claude", "--print", "--max-turns", "1", "respond with ok"],
            returncode=1,
            stdout="",
            stderr="Authentication failed",
        )

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = _validate_credentials_impl()

    assert isinstance(result, ValidationError)
    assert result.success is False
    assert result.error == "authentication-failed"
    assert "expired or invalid" in result.message


def test_validate_impl_success(monkeypatch: MagicMock) -> None:
    """Test validation returns success when API call succeeds."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-valid-key")

    # Mock subprocess.run to simulate successful API call
    def mock_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["claude", "--print", "--max-turns", "1", "respond with ok"],
            returncode=0,
            stdout="ok",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = _validate_credentials_impl()

    assert isinstance(result, ValidationSuccess)
    assert result.success is True
    assert "validated successfully" in result.message


# ============================================================================
# 3. CLI Command Tests (3 tests)
# ============================================================================


def test_cli_missing_credentials(monkeypatch: MagicMock) -> None:
    """Test CLI command returns error JSON when credentials missing."""
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    runner = CliRunner()
    result = runner.invoke(validate_claude_credentials_command, [])

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "credentials-missing"


def test_cli_auth_failed(monkeypatch: MagicMock) -> None:
    """Test CLI command returns error JSON when auth fails."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-invalid-key")

    def mock_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["claude"],
            returncode=1,
            stdout="",
            stderr="Auth failed",
        )

    monkeypatch.setattr(subprocess, "run", mock_run)

    runner = CliRunner()
    result = runner.invoke(validate_claude_credentials_command, [])

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "authentication-failed"


def test_cli_success(monkeypatch: MagicMock) -> None:
    """Test CLI command returns success JSON when validation passes."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-valid-key")

    def mock_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["claude"],
            returncode=0,
            stdout="ok",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", mock_run)

    runner = CliRunner()
    result = runner.invoke(validate_claude_credentials_command, [])

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert "validated successfully" in output["message"]
