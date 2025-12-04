"""Tests for the ErkContext."""

from pathlib import Path

import pytest
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.integrations.graphite.fake import FakeGraphite

from erk.core.config_store import GlobalConfig
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext
from tests.fakes.shell import FakeShell
from tests.test_utils.paths import sentinel_path


def test_context_initialization_and_attributes() -> None:
    """Initialization wires through every dependency and exposes them as attributes."""
    git_ops = FakeGit()
    github_ops = FakeGitHub()
    graphite_ops = FakeGraphite()
    shell_ops = FakeShell()
    global_config = GlobalConfig(
        erk_root=Path("/tmp"),
        use_graphite=False,
        shell_setup_complete=False,
        show_pr_info=True,
        github_planning=True,
    )

    ctx = ErkContext.for_test(
        git=git_ops,
        github=github_ops,
        graphite=graphite_ops,
        shell=shell_ops,
        cwd=sentinel_path(),
        global_config=global_config,
        dry_run=False,
    )

    assert ctx.git is git_ops
    assert ctx.global_config == global_config
    assert ctx.github is github_ops
    assert ctx.graphite is graphite_ops
    assert ctx.shell is shell_ops
    assert ctx.dry_run is False


def test_context_is_frozen() -> None:
    """ErkContext is a frozen dataclass."""
    global_config = GlobalConfig(
        erk_root=Path("/tmp"),
        use_graphite=False,
        shell_setup_complete=False,
        show_pr_info=True,
        github_planning=True,
    )
    ctx = ErkContext.for_test(
        git=FakeGit(),
        global_config=global_config,
        github=FakeGitHub(),
        graphite=FakeGraphite(),
        shell=FakeShell(),
        cwd=sentinel_path(),
        dry_run=True,
    )

    with pytest.raises(AttributeError):
        ctx.dry_run = False  # type: ignore[misc]


def test_minimal_factory_creates_context_with_git_ops() -> None:
    """ErkContext.minimal() creates context with only git_ops configured."""
    git_ops = FakeGit(
        current_branches={Path("/repo"): "main"},
        default_branches={Path("/repo"): "main"},
    )
    cwd = sentinel_path()

    ctx = ErkContext.minimal(git_ops, cwd)

    assert ctx.git is git_ops
    assert ctx.cwd == cwd
    assert ctx.dry_run is False
    assert ctx.trunk_branch is None
    assert ctx.global_config is None


def test_minimal_factory_with_dry_run() -> None:
    """ErkContext.minimal() respects dry_run parameter."""
    git_ops = FakeGit()
    cwd = sentinel_path()

    ctx = ErkContext.minimal(git_ops, cwd, dry_run=True)

    assert ctx.dry_run is True


def test_minimal_factory_creates_fake_ops() -> None:
    """ErkContext.minimal() initializes other ops with fakes."""
    git_ops = FakeGit()
    cwd = sentinel_path()

    ctx = ErkContext.minimal(git_ops, cwd)

    # All other ops should be fake implementations
    assert isinstance(ctx.github, FakeGitHub)
    assert isinstance(ctx.graphite, FakeGraphite)
    assert isinstance(ctx.shell, FakeShell)


def test_for_test_factory_creates_context_with_defaults() -> None:
    """ErkContext.for_test() creates context with all defaults when no args provided."""
    ctx = ErkContext.for_test()

    assert isinstance(ctx.git, FakeGit)
    assert isinstance(ctx.github, FakeGitHub)
    assert isinstance(ctx.graphite, FakeGraphite)
    assert isinstance(ctx.shell, FakeShell)
    assert ctx.cwd == sentinel_path()
    assert ctx.dry_run is False
    assert ctx.trunk_branch is None


def test_for_test_factory_accepts_custom_ops() -> None:
    """ErkContext.for_test() uses provided ops instead of defaults."""
    git_ops = FakeGit(
        current_branches={Path("/repo"): "main"},
        default_branches={Path("/repo"): "main"},
    )
    github_ops = FakeGitHub()
    cwd = Path("/custom/cwd")

    ctx = ErkContext.for_test(
        git=git_ops,
        github=github_ops,
        cwd=cwd,
    )

    assert ctx.git is git_ops
    assert ctx.github is github_ops
    assert ctx.cwd == cwd


def test_for_test_factory_accepts_trunk_branch() -> None:
    """ErkContext.for_test() computes trunk_branch from git_ops."""
    git_ops = FakeGit(trunk_branches={Path("/repo"): "develop"})
    ctx = ErkContext.for_test(
        git=git_ops,
        repo=RepoContext(
            root=Path("/repo"),
            repo_name="repo",
            repo_dir=Path("/repo/.erks"),
            worktrees_dir=Path("/repo/.erks") / "worktrees",
        ),
    )

    assert ctx.trunk_branch == "develop"
