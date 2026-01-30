"""Unit tests for run_submit_pipeline and make_initial_state."""

from pathlib import Path

from erk.cli.commands.pr.submit_pipeline import (
    SubmitError,
    make_initial_state,
    run_submit_pipeline,
)
from erk.core.context import context_for_test
from erk_shared.gateway.git.fake import FakeGit


def test_stops_at_first_error(tmp_path: Path) -> None:
    """Early error prevents later steps from running."""
    # prepare_state will fail because detached HEAD
    fake_git = FakeGit(
        repository_roots={tmp_path: tmp_path},
        current_branches={tmp_path: None},
    )
    ctx = context_for_test(git=fake_git, cwd=tmp_path)
    state = make_initial_state(
        cwd=tmp_path,
        use_graphite=False,
        force=False,
        debug=False,
        session_id="test",
    )

    result = run_submit_pipeline(ctx, state)

    assert isinstance(result, SubmitError)
    assert result.error_type == "no_branch"
    assert result.phase == "prepare"


def test_threads_state_through_steps(tmp_path: Path) -> None:
    """State is threaded: prepare_state populates fields, commit_wip sees them."""
    fake_git = FakeGit(
        repository_roots={tmp_path: tmp_path},
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
        # commit_wip checks has_uncommitted_changes => False (clean)
        # push_and_create_pr will fail at auth check (no auth configured),
        # but that proves state was threaded through prepare_state and commit_wip
    )
    ctx = context_for_test(git=fake_git, cwd=tmp_path)
    state = make_initial_state(
        cwd=tmp_path,
        use_graphite=False,
        force=False,
        debug=False,
        session_id="test",
    )

    result = run_submit_pipeline(ctx, state)

    # Pipeline should get past prepare_state (populated branch_name)
    # and commit_wip (no-op, clean), then fail at push_and_create_pr
    # which checks GitHub auth.
    # FakeGitHub defaults to authenticated=True, so it should fail at
    # no_commits (0 commits ahead) since we didn't configure commits_ahead.
    assert isinstance(result, SubmitError)
    assert result.error_type == "no_commits"
    assert result.phase == "push_and_create_pr"


def test_make_initial_state_sets_placeholders(tmp_path: Path) -> None:
    """Factory defaults are correct."""
    state = make_initial_state(
        cwd=tmp_path,
        use_graphite=True,
        force=True,
        debug=True,
        session_id="my-session",
    )

    assert state.cwd == tmp_path
    assert state.repo_root == tmp_path
    assert state.branch_name == ""
    assert state.parent_branch == ""
    assert state.trunk_branch == ""
    assert state.use_graphite is True
    assert state.force is True
    assert state.debug is True
    assert state.session_id == "my-session"
    assert state.issue_number is None
    assert state.pr_number is None
    assert state.pr_url is None
    assert state.was_created is False
    assert state.base_branch is None
    assert state.graphite_url is None
    assert state.diff_file is None
    assert state.plan_context is None
    assert state.title is None
    assert state.body is None
