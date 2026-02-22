"""Tests for --backend CLI flag and _apply_backend_override helper."""

import dataclasses
from pathlib import Path

from erk.cli.cli import _apply_backend_override, _resolve_backend_flag
from erk.core.context import context_for_test
from erk_shared.context.types import GlobalConfig, InteractiveAgentConfig


def test_apply_backend_override_with_existing_config() -> None:
    """Override works when global_config exists — backend changed, other fields preserved."""
    original_agent = InteractiveAgentConfig(
        backend="claude",
        model="opus",
        verbose=True,
        permission_mode="plan",
        dangerous=False,
        allow_dangerous=True,
    )
    original_config = GlobalConfig.test(
        erk_root=Path("/test/erks"),
        interactive_agent=original_agent,
    )
    ctx = context_for_test(global_config=original_config)

    result = _apply_backend_override(ctx, "codex", erk_root=Path("/test/erks"))

    assert result.global_config is not None
    agent = result.global_config.interactive_agent
    assert agent.backend == "codex"
    # Other fields preserved
    assert agent.model == "opus"
    assert agent.verbose is True
    assert agent.permission_mode == "plan"
    assert agent.dangerous is False
    assert agent.allow_dangerous is True
    # Non-agent config fields preserved
    assert result.global_config.erk_root == Path("/test/erks")


def test_apply_backend_override_with_none_config() -> None:
    """Override works when global_config is None (pre-init case)."""
    ctx = context_for_test(global_config=None)
    # context_for_test sets a default GlobalConfig when None is passed,
    # so we need to create context manually with None
    ctx = dataclasses.replace(ctx, global_config=None)

    result = _apply_backend_override(ctx, "codex", erk_root=Path("/test/erks"))

    assert result.global_config is not None
    assert result.global_config.interactive_agent.backend == "codex"


def test_resolve_backend_flag_cli_takes_precedence() -> None:
    """CLI flag takes precedence over env var."""
    result = _resolve_backend_flag(cli_flag="codex", env_var="claude")
    assert result == "codex"


def test_resolve_backend_flag_env_var_fallback() -> None:
    """Env var is used when CLI flag is None."""
    result = _resolve_backend_flag(cli_flag=None, env_var="codex")
    assert result == "codex"


def test_resolve_backend_flag_env_var_case_insensitive() -> None:
    """Env var is case-insensitive."""
    result = _resolve_backend_flag(cli_flag=None, env_var="CODEX")
    assert result == "codex"


def test_resolve_backend_flag_neither_set() -> None:
    """Returns None when neither CLI flag nor env var is set."""
    result = _resolve_backend_flag(cli_flag=None, env_var=None)
    assert result is None


def test_resolve_backend_flag_invalid_env_var(capsys: object) -> None:
    """Invalid env var is ignored with a warning."""
    result = _resolve_backend_flag(cli_flag=None, env_var="invalid")
    assert result is None
