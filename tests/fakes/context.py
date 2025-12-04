"""Factory functions for creating test contexts."""

from pathlib import Path

from erk_shared.git.fake import FakeGit
from erk_shared.github.gateway import GitHubGateway, create_fake_github_gateway
from erk_shared.integrations.graphite.fake import FakeGraphite

from erk.cli.config import LoadedConfig
from erk.core.claude_executor import ClaudeExecutor
from erk.core.config_store import GlobalConfig
from erk.core.context import ErkContext
from erk.core.repo_discovery import NoRepoSentinel, RepoContext
from erk.core.script_writer import ScriptWriter
from tests.fakes.completion import FakeCompletion
from tests.fakes.shell import FakeShell


def create_test_context(
    git: FakeGit | None = None,
    github: GitHubGateway | None = None,
    graphite: FakeGraphite | None = None,
    shell: FakeShell | None = None,
    claude_executor: ClaudeExecutor | None = None,
    completion: FakeCompletion | None = None,
    script_writer: ScriptWriter | None = None,
    cwd: Path | None = None,
    global_config: GlobalConfig | None = None,
    local_config: LoadedConfig | None = None,
    repo: RepoContext | NoRepoSentinel | None = None,
    dry_run: bool = False,
) -> ErkContext:
    """Create test context with optional pre-configured ops.

    This is a convenience wrapper around ErkContext.for_test() for backward
    compatibility. New code should use ErkContext.for_test() directly.

    Args:
        git: Optional FakeGit with test configuration.
                If None, creates empty FakeGit.
        github: Optional GitHubGateway with test configuration.
                   If None, creates default fake gateway via create_fake_github_gateway().
        graphite: Optional FakeGraphite with test configuration.
                     If None, creates empty FakeGraphite.
        shell: Optional FakeShell with test configuration.
                  If None, creates empty FakeShell (no shell detected).
        completion: Optional FakeCompletion with test configuration.
                       If None, creates empty FakeCompletion.
        script_writer: Optional ScriptWriter (Real or Fake) for test context.
                      If None, defaults to FakeScriptWriter in ErkContext.for_test.
                      Pass RealScriptWriter() for integration tests that need real scripts.
        cwd: Optional current working directory path for test context.
            If None, defaults to Path("/test/default/cwd") to prevent accidental use
            of real Path.cwd() in tests.
        global_config: Optional GlobalConfig for test context.
                      If None, uses test defaults.
        local_config: Optional LoadedConfig for test context.
                     If None, uses empty defaults.
        repo: Optional RepoContext or NoRepoSentinel for test context.
             If None, uses NoRepoSentinel().
        dry_run: Whether to set dry_run mode

    Returns:
        Frozen ErkContext for use in tests

    Example:
        # With pre-configured git ops
        >>> git = FakeGit(default_branches={Path("/repo"): "main"})
        >>> ctx = create_test_context(git=git)

        # With custom PR gateway
        >>> from erk_shared.github.pr.fake import FakeGitHubPrGateway
        >>> from erk_shared.github.gateway import create_fake_github_gateway
        >>> pr = FakeGitHubPrGateway(pr_issue_linkages={42: [pr1, pr2]})
        >>> github = create_fake_github_gateway(pr=pr)
        >>> ctx = create_test_context(github=github)

        # Without any ops (empty fakes)
        >>> ctx = create_test_context()
    """
    return ErkContext.for_test(
        git=git,
        github=github or create_fake_github_gateway(),
        graphite=graphite,
        shell=shell,
        claude_executor=claude_executor,
        completion=completion,
        script_writer=script_writer,
        cwd=cwd,
        global_config=global_config,
        local_config=local_config,
        repo=repo,
        dry_run=dry_run,
    )
