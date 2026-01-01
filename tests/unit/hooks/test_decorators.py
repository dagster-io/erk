"""Unit tests for hook decorators.

Tests the HookContext injection functionality of the @logged_hook decorator.
"""

import dataclasses
import json
from pathlib import Path

import click
from click.testing import CliRunner

from erk.hooks.decorators import HookContext, hook_command, logged_hook
from erk_shared.context.context import ErkContext


def test_hook_context_injection_with_erk_project(tmp_path: Path) -> None:
    """Test that HookContext is injected when function signature accepts it."""
    # Track what was received
    received_ctx: HookContext | None = None

    @click.command()
    @click.pass_context
    @logged_hook
    def sample_hook(ctx: click.Context, *, hook_ctx: HookContext) -> None:
        nonlocal received_ctx
        received_ctx = hook_ctx
        click.echo("Hook executed")

    # Create .erk/ to mark as managed project
    (tmp_path / ".erk").mkdir()

    runner = CliRunner()
    ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)
    result = runner.invoke(sample_hook, obj=ctx)

    assert result.exit_code == 0
    assert received_ctx is not None
    assert received_ctx.repo_root == tmp_path
    assert received_ctx.is_erk_project is True
    assert received_ctx.session_id is None  # No stdin provided
    assert received_ctx.scratch_dir is None  # No session_id, no scratch_dir


def test_hook_context_injection_with_session_id(tmp_path: Path) -> None:
    """Test that session_id is extracted from stdin and scratch_dir is computed."""
    received_ctx: HookContext | None = None

    @click.command()
    @click.pass_context
    @logged_hook
    def sample_hook(ctx: click.Context, *, hook_ctx: HookContext) -> None:
        nonlocal received_ctx
        received_ctx = hook_ctx

    # Create .erk/ to mark as managed project
    (tmp_path / ".erk").mkdir()

    runner = CliRunner()
    ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)
    stdin_data = json.dumps({"session_id": "test-session-123"})
    result = runner.invoke(sample_hook, obj=ctx, input=stdin_data)

    assert result.exit_code == 0
    assert received_ctx is not None
    assert received_ctx.session_id == "test-session-123"
    assert received_ctx.scratch_dir is not None
    expected_scratch = tmp_path / ".erk" / "scratch" / "sessions" / "test-session-123"
    assert received_ctx.scratch_dir == expected_scratch


def test_hook_context_not_erk_project(tmp_path: Path) -> None:
    """Test that is_erk_project is False when .erk/ directory doesn't exist."""
    received_ctx: HookContext | None = None

    @click.command()
    @click.pass_context
    @logged_hook
    def sample_hook(ctx: click.Context, *, hook_ctx: HookContext) -> None:
        nonlocal received_ctx
        received_ctx = hook_ctx

    # No .erk/ directory - NOT a managed project
    runner = CliRunner()
    ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)
    result = runner.invoke(sample_hook, obj=ctx)

    assert result.exit_code == 0
    assert received_ctx is not None
    assert received_ctx.is_erk_project is False


def test_hook_without_hook_ctx_parameter_backward_compatible(tmp_path: Path) -> None:
    """Test that hooks without hook_ctx parameter still work (backward compatibility)."""
    executed = False

    @click.command()
    @click.pass_context
    @logged_hook
    def sample_hook(ctx: click.Context) -> None:
        nonlocal executed
        executed = True
        click.echo("Old-style hook")

    (tmp_path / ".erk").mkdir()

    runner = CliRunner()
    ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)
    result = runner.invoke(sample_hook, obj=ctx)

    assert result.exit_code == 0
    assert executed is True
    assert "Old-style hook" in result.output


def test_hook_context_frozen() -> None:
    """Test that HookContext is immutable (frozen dataclass)."""
    hook_ctx = HookContext(
        session_id="test",
        repo_root=Path("/tmp"),
        scratch_dir=Path("/tmp/scratch"),
        is_erk_project=True,
    )

    # Attempting to modify should raise FrozenInstanceError
    try:
        hook_ctx.session_id = "modified"  # type: ignore[misc]
        raise AssertionError("Expected FrozenInstanceError")
    except dataclasses.FrozenInstanceError:
        pass  # Expected


def test_hook_command_combines_decorators(tmp_path: Path) -> None:
    """Test that @hook_command combines @click.command, @click.pass_context, @logged_hook."""
    received_ctx: HookContext | None = None

    @hook_command(name="test-combined-hook")
    def combined_hook(ctx: click.Context, *, hook_ctx: HookContext) -> None:
        nonlocal received_ctx
        received_ctx = hook_ctx
        click.echo("Combined hook executed")

    # Create .erk/ to mark as managed project
    (tmp_path / ".erk").mkdir()

    runner = CliRunner()
    ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)
    result = runner.invoke(combined_hook, obj=ctx)

    assert result.exit_code == 0
    assert "Combined hook executed" in result.output
    assert received_ctx is not None
    assert received_ctx.repo_root == tmp_path
    assert received_ctx.is_erk_project is True


def test_hook_command_without_name(tmp_path: Path) -> None:
    """Test that @hook_command() works without explicit name (uses function name)."""
    executed = False

    @hook_command()
    def my_auto_named_hook(ctx: click.Context, *, hook_ctx: HookContext) -> None:
        nonlocal executed
        executed = True

    (tmp_path / ".erk").mkdir()

    runner = CliRunner()
    ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)
    result = runner.invoke(my_auto_named_hook, obj=ctx)

    assert result.exit_code == 0
    assert executed is True
