import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import click

from dot_agent_kit.cli.output import user_output
from dot_agent_kit.version import __version__

if TYPE_CHECKING:
    from erk_shared.context import ErkContext
    from erk_shared.github.types import RepoInfo

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


def _get_repo_info(git: "Git", repo_root: Path) -> "RepoInfo | None":
    """Detect repository info from git remote URL.

    Parses the origin remote URL to extract owner/name for GitHub API calls.
    Returns None if no origin remote is configured or URL cannot be parsed.
    """
    from erk_shared.git.abc import Git
    from erk_shared.github.parsing import parse_git_remote_url
    from erk_shared.github.types import RepoInfo

    try:
        remote_url = git.get_remote_url(repo_root)
        owner, name = parse_git_remote_url(remote_url)
        return RepoInfo(owner=owner, name=name)
    except ValueError:
        return None


def _create_context(*, debug: bool) -> "ErkContext":
    """Create production context with real implementations for dot-agent-kit.

    This is the canonical factory for creating the application context.
    Called once at CLI entry point to create the context for the entire
    command execution.

    Detects repository root using git rev-parse. Exits with error if not in a git repository.
    """
    from erk_shared.context import ErkContext, LoadedConfig, RepoContext
    from erk_shared.extraction.claude_code_session_store import RealClaudeCodeSessionStore
    from erk_shared.git.real import RealGit
    from erk_shared.github.issues import RealGitHubIssues
    from erk_shared.github.real import RealGitHub
    from erk_shared.integrations.completion import FakeCompletion
    from erk_shared.integrations.feedback import SuppressedFeedback
    from erk_shared.integrations.graphite.fake import FakeGraphite
    from erk_shared.integrations.shell import FakeShell
    from erk_shared.integrations.time.fake import FakeTime
    from erk_shared.integrations.time.real import RealTime
    from erk_shared.objectives.storage import FakeObjectiveStore
    from erk_shared.plan_store.fake import FakePlanStore
    from erk_shared.prompt_executor.real import RealPromptExecutor

    # Detect repo root using git rev-parse
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        click.echo("Error: Not in a git repository", err=True)
        raise SystemExit(1)

    repo_root = Path(result.stdout.strip())
    cwd = Path.cwd()

    # Create git instance and detect repo_info
    git = RealGit()
    repo_info = _get_repo_info(git, repo_root)

    # Create minimal repo context for dot-agent-kit
    repo = RepoContext(
        root=repo_root,
        repo_name=repo_root.name,
        repo_dir=Path.home() / ".erk" / "repos" / repo_root.name,
        worktrees_dir=Path.home() / ".erk" / "repos" / repo_root.name / "worktrees",
    )

    # Create fake implementations for erk-specific services that dot-agent-kit doesn't need
    class FakeClaudeExecutor:
        def execute_interactive(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
            raise NotImplementedError("ClaudeExecutor not available in dot-agent-kit context")

        def execute_interactive_command(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
            raise NotImplementedError("ClaudeExecutor not available in dot-agent-kit context")

    class FakeConfigStore:
        def exists(self) -> bool:
            return False

        def load(self):  # noqa: ANN201
            raise NotImplementedError("ConfigStore not available in dot-agent-kit context")

        def save(self, config) -> None:  # noqa: ANN001
            raise NotImplementedError("ConfigStore not available in dot-agent-kit context")

        def path(self) -> Path:
            return Path("/fake/config")

    class FakeScriptWriter:
        pass

    class FakePlannerRegistry:
        pass

    class FakePlanListService:
        pass

    return ErkContext(
        git=git,
        github=RealGitHub(time=RealTime(), repo_info=repo_info),
        issues=RealGitHubIssues(),
        session_store=RealClaudeCodeSessionStore(),
        prompt_executor=RealPromptExecutor(),
        graphite=FakeGraphite(),
        time=FakeTime(),
        plan_store=FakePlanStore(),
        objectives=FakeObjectiveStore(),
        shell=FakeShell(),
        completion=FakeCompletion(),
        feedback=SuppressedFeedback(),
        claude_executor=FakeClaudeExecutor(),
        config_store=FakeConfigStore(),
        script_writer=FakeScriptWriter(),
        planner_registry=FakePlannerRegistry(),
        plan_list_service=FakePlanListService(),
        cwd=cwd,
        repo=repo,
        project=None,
        repo_info=repo_info,
        global_config=None,
        local_config=LoadedConfig(env={}, post_create_commands=[], post_create_shell=None),
        dry_run=False,
        debug=debug,
    )


class LazyGroup(click.Group):
    """Click Group that lazily loads commands."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._commands_registered = False

    def list_commands(self, ctx):
        """List available commands, registering them if needed."""
        if not self._commands_registered:
            self._register_commands()
        return super().list_commands(ctx)

    def get_command(self, ctx, cmd_name):
        """Get a command by name, registering if needed."""
        if not self._commands_registered:
            self._register_commands()
        return super().get_command(ctx, cmd_name)

    def _register_commands(self) -> None:
        """Register all commands with the CLI group."""
        if self._commands_registered:
            return

        from dot_agent_kit.commands import check
        from dot_agent_kit.commands.artifact.group import artifact_group
        from dot_agent_kit.commands.command import command
        from dot_agent_kit.commands.dev.group import dev_group
        from dot_agent_kit.commands.docs.group import docs_group
        from dot_agent_kit.commands.hook.group import hook_group
        from dot_agent_kit.commands.init import init
        from dot_agent_kit.commands.kit.group import kit_group
        from dot_agent_kit.commands.kit_exec.group import kit_exec_group
        from dot_agent_kit.commands.md.group import md_group
        from dot_agent_kit.commands.status import st, status

        self.add_command(check.check)
        self.add_command(command)
        self.add_command(init)
        self.add_command(status)
        self.add_command(st)

        # Register command groups
        self.add_command(artifact_group)
        self.add_command(dev_group)
        self.add_command(docs_group)
        self.add_command(hook_group)
        self.add_command(kit_group)
        self.add_command(md_group)

        # Add 'kit-command' as backward-compatible alias for 'kit exec'
        # Users can use 'dot-agent kit-command' which wraps 'dot-agent kit exec'
        kit_command_alias = click.Group(
            name="kit-command",
            help="(Alias for 'kit exec') Execute scripts from bundled kits.",
            commands=kit_exec_group.commands,
        )
        self.add_command(kit_command_alias)

        # Add 'run' as an alias for 'kit exec' for backwards compatibility
        # Users can use either 'dot-agent run' or 'dot-agent kit exec'
        run_alias = click.Group(
            name="run",
            help="(Alias for 'kit exec') Execute scripts from bundled kits.",
            commands=kit_exec_group.commands,
        )
        self.add_command(run_alias)

        self._commands_registered = True


@click.command(cls=LazyGroup, invoke_without_command=True, context_settings=CONTEXT_SETTINGS)
@click.version_option(version=__version__)
@click.option("--debug", is_flag=True, help="Show full stack traces for errors")
@click.pass_context
def cli(ctx: click.Context, debug: bool) -> None:
    """Manage Claude Code kits."""
    # Only create context if not already provided (e.g., by tests)
    if ctx.obj is None:
        ctx.obj = _create_context(debug=debug)

    if ctx.invoked_subcommand is None:
        user_output(ctx.get_help())


def main() -> None:
    """Entry point with error boundary."""
    from dot_agent_kit.error_boundary import cli_error_boundary

    cli_error_boundary(cli)()


if __name__ == "__main__":
    main()
