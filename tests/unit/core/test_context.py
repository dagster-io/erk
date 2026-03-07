"""Tests for context creation and regeneration."""

from pathlib import Path
from unittest.mock import patch

from erk.core.codex_prompt_executor import CodexCliPromptExecutor
from erk.core.context import (
    context_for_test,
    create_prompt_executor,
    regenerate_context,
)
from erk.core.prompt_executor import ClaudeCliPromptExecutor
from erk_shared.context.types import GlobalConfig, InteractiveAgentConfig
from erk_shared.gateway.console.fake import FakeConsole
from erk_shared.gateway.git.fake import FakeGit


def test_regenerate_context_preserves_dry_run(tmp_path: Path) -> None:
    """Test that regenerate_context preserves dry_run flag."""
    # Use context_for_test to create a fast test context with dry_run=True
    ctx1 = context_for_test(git=FakeGit(), cwd=tmp_path, dry_run=True)
    assert ctx1.dry_run is True

    # Mock create_context to return another test context instead of real one
    ctx2_mock = context_for_test(git=FakeGit(), cwd=tmp_path, dry_run=True)
    with patch("erk.core.context.create_context", return_value=ctx2_mock):
        ctx2 = regenerate_context(ctx1)

    assert ctx2.dry_run is True  # Preserved


def _test_console() -> FakeConsole:
    return FakeConsole(
        is_interactive=True,
        is_stdout_tty=None,
        is_stderr_tty=None,
        confirm_responses=None,
    )


def test_create_prompt_executor_selects_codex_when_backend_is_codex() -> None:
    """Backend selection returns CodexCliPromptExecutor when config says codex."""
    config = GlobalConfig.test(
        Path("/test/erks"),
        interactive_agent=InteractiveAgentConfig(
            backend="codex",
            model=None,
            verbose=False,
            permission_mode="edits",
            dangerous=False,
            allow_dangerous=False,
        ),
    )

    executor = create_prompt_executor(global_config=config, console=_test_console())

    assert isinstance(executor, CodexCliPromptExecutor)


def test_create_prompt_executor_selects_claude_when_backend_is_claude() -> None:
    """Backend selection returns ClaudeCliPromptExecutor when config says claude."""
    config = GlobalConfig.test(
        Path("/test/erks"),
        interactive_agent=InteractiveAgentConfig(
            backend="claude",
            model=None,
            verbose=False,
            permission_mode="edits",
            dangerous=False,
            allow_dangerous=False,
        ),
    )

    executor = create_prompt_executor(global_config=config, console=_test_console())

    assert isinstance(executor, ClaudeCliPromptExecutor)


def test_create_prompt_executor_defaults_to_claude_when_config_is_none() -> None:
    """Backend selection defaults to ClaudeCliPromptExecutor when global_config is None."""
    executor = create_prompt_executor(global_config=None, console=_test_console())

    assert isinstance(executor, ClaudeCliPromptExecutor)
