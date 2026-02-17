"""Tests for resolve_backend utility."""

from click.testing import CliRunner

from erk.cli.commands.init.capability.backend_utils import resolve_backend
from erk_shared.context.types import GlobalConfig, InteractiveAgentConfig
from erk_shared.gateway.erk_installation.fake import FakeErkInstallation
from erk_shared.gateway.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_resolve_backend_returns_claude_when_no_global_config() -> None:
    """When global_config is None, resolve_backend defaults to 'claude'."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        ctx = env.build_context(
            git=FakeGit(git_common_dirs={}),
            erk_installation=FakeErkInstallation(config=None),
            global_config=None,
        )
        assert resolve_backend(ctx) == "claude"


def test_resolve_backend_returns_claude_from_config() -> None:
    """When global_config has backend='claude', resolve_backend returns 'claude'."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )
        ctx = env.build_context(
            git=FakeGit(git_common_dirs={}),
            erk_installation=FakeErkInstallation(config=global_config),
            global_config=global_config,
        )
        assert resolve_backend(ctx) == "claude"


def test_resolve_backend_returns_codex_from_config() -> None:
    """When global_config has backend='codex', resolve_backend returns 'codex'."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        agent_config = InteractiveAgentConfig(
            backend="codex",
            model=None,
            verbose=False,
            permission_mode="edits",
            dangerous=False,
            allow_dangerous=False,
        )
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks",
            use_graphite=False,
            shell_setup_complete=False,
            interactive_agent=agent_config,
        )
        ctx = env.build_context(
            git=FakeGit(git_common_dirs={}),
            erk_installation=FakeErkInstallation(config=global_config),
            global_config=global_config,
        )
        assert resolve_backend(ctx) == "codex"
