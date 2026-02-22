"""Tests for impl-verify kit CLI command.

Tests the guardrail that ensures .impl/ folder is preserved after implementation.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.impl_verify import impl_verify
from erk_shared.context.context import ErkContext


def test_impl_verify_succeeds_when_impl_exists(tmp_path: Path) -> None:
    """Test impl-verify returns success JSON when .impl/ exists."""
    # Create .impl/ folder
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    runner = CliRunner()
    result = runner.invoke(
        impl_verify,
        obj=ErkContext.for_test(cwd=tmp_path),
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["valid"] is True
    assert "impl_dir" in data
    assert data["impl_dir"].endswith(".impl")


def test_impl_verify_fails_when_impl_missing(tmp_path: Path) -> None:
    """Test impl-verify returns error JSON when .impl/ is missing."""
    # No .impl/ folder created - simulates deletion during implementation
    runner = CliRunner()
    result = runner.invoke(
        impl_verify,
        obj=ErkContext.for_test(cwd=tmp_path),
    )

    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["valid"] is False
    assert "error" in data
    assert ".impl/ folder was deleted" in data["error"]
    assert "action" in data


def test_impl_verify_ignores_impl_context(tmp_path: Path) -> None:
    """Test impl-verify only checks for .impl/, not .erk/impl-context/."""
    # Create .erk/impl-context/ but not .impl/ - should fail
    impl_context_dir = tmp_path / ".erk" / "impl-context"
    impl_context_dir.mkdir(parents=True)

    runner = CliRunner()
    result = runner.invoke(
        impl_verify,
        obj=ErkContext.for_test(cwd=tmp_path),
    )

    # Should fail because we only check for .impl/
    # (.erk/impl-context/ is for remote implementations which get deleted)
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["valid"] is False
