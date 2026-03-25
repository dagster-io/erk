"""Tests for dispatch ref resolution logic."""

from pathlib import Path

import click
import pytest

from erk.cli.commands.ref_resolution import resolve_dispatch_ref
from erk_shared.context.types import LoadedConfig
from tests.fakes.gateway.git import FakeGit
from tests.fakes.tests.context import create_test_context


def test_mutual_exclusion_error() -> None:
    """Both --ref and --ref-current raises UsageError."""
    ctx = create_test_context()

    with pytest.raises(click.UsageError, match="mutually exclusive"):
        resolve_dispatch_ref(ctx, dispatch_ref="some-branch", ref_current=True)


def test_ref_current_returns_branch() -> None:
    """--ref-current calls get_current_branch and returns it."""
    cwd = Path("/fake/repo")
    git = FakeGit(current_branches={cwd: "feature/my-branch"})
    ctx = create_test_context(git=git, cwd=cwd)

    result = resolve_dispatch_ref(ctx, dispatch_ref=None, ref_current=True)

    assert result == "feature/my-branch"


def test_ref_current_detached_head_error() -> None:
    """--ref-current with detached HEAD raises UsageError."""
    cwd = Path("/fake/repo")
    git = FakeGit()  # No current branch configured → returns None
    ctx = create_test_context(git=git, cwd=cwd)

    with pytest.raises(click.UsageError, match="not detached HEAD"):
        resolve_dispatch_ref(ctx, dispatch_ref=None, ref_current=True)


def test_explicit_ref_returned() -> None:
    """--ref value is returned directly."""
    ctx = create_test_context()

    result = resolve_dispatch_ref(ctx, dispatch_ref="my-custom-ref", ref_current=False)

    assert result == "my-custom-ref"


def test_falls_back_to_config() -> None:
    """Neither flag returns ctx.local_config.dispatch_ref."""
    local_config = LoadedConfig.test(dispatch_ref="config-default-ref")
    ctx = create_test_context(local_config=local_config)

    result = resolve_dispatch_ref(ctx, dispatch_ref=None, ref_current=False)

    assert result == "config-default-ref"


def test_falls_back_to_none_when_no_config() -> None:
    """Neither flag with no config dispatch_ref returns None."""
    ctx = create_test_context()

    result = resolve_dispatch_ref(ctx, dispatch_ref=None, ref_current=False)

    assert result is None
