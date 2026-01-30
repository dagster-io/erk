"""Unit tests for finalize_pr pipeline step."""

import json
from pathlib import Path

from erk.cli.commands.pr.submit_pipeline import (
    SubmitError,
    SubmitState,
    finalize_pr,
)
from erk.core.context import context_for_test
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.types import PRDetails


def _make_state(
    *,
    cwd: Path,
    repo_root: Path | None = None,
    branch_name: str = "feature",
    parent_branch: str = "main",
    trunk_branch: str = "main",
    use_graphite: bool = False,
    force: bool = False,
    debug: bool = False,
    session_id: str = "test-session",
    issue_number: int | None = None,
    pr_number: int | None = 42,
    pr_url: str | None = "https://github.com/owner/repo/pull/42",
    was_created: bool = True,
    base_branch: str | None = "main",
    graphite_url: str | None = None,
    diff_file: Path | None = None,
    plan_context: None = None,
    title: str | None = "My PR Title",
    body: str | None = "My PR body",
) -> SubmitState:
    return SubmitState(
        cwd=cwd,
        repo_root=repo_root if repo_root is not None else cwd,
        branch_name=branch_name,
        parent_branch=parent_branch,
        trunk_branch=trunk_branch,
        use_graphite=use_graphite,
        force=force,
        debug=debug,
        session_id=session_id,
        issue_number=issue_number,
        pr_number=pr_number,
        pr_url=pr_url,
        was_created=was_created,
        base_branch=base_branch,
        graphite_url=graphite_url,
        diff_file=diff_file,
        plan_context=plan_context,
        title=title,
        body=body,
    )


def _pr_details(
    *,
    number: int = 42,
    branch: str = "feature",
    body: str = "",
) -> PRDetails:
    return PRDetails(
        number=number,
        url=f"https://github.com/owner/repo/pull/{number}",
        title="Test PR",
        body=body,
        state="OPEN",
        base_ref_name="main",
        head_ref_name=branch,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        is_draft=False,
        is_cross_repository=False,
        owner="owner",
        repo="repo",
    )


def test_no_pr_number_returns_error(tmp_path: Path) -> None:
    """SubmitError(error_type='no_pr_number') when pr_number is None."""
    ctx = context_for_test(cwd=tmp_path)
    state = _make_state(cwd=tmp_path, pr_number=None)

    result = finalize_pr(ctx, state)

    assert isinstance(result, SubmitError)
    assert result.error_type == "no_pr_number"


def test_updates_pr_title_and_body(tmp_path: Path) -> None:
    """update_pr_title_and_body called with correct args."""
    pr = _pr_details(number=42)
    fake_git = FakeGit(
        repository_roots={tmp_path: tmp_path},
        remote_urls={(tmp_path, "origin"): "git@github.com:owner/repo.git"},
    )
    fake_github = FakeGitHub(
        prs_by_branch={"feature": pr},
        pr_details={42: pr},
    )
    ctx = context_for_test(git=fake_git, github=fake_github, cwd=tmp_path)
    state = _make_state(cwd=tmp_path, title="New Title", body="New body")

    result = finalize_pr(ctx, state)

    assert isinstance(result, SubmitState)
    assert len(fake_github.updated_pr_titles) == 1
    assert fake_github.updated_pr_titles[0] == (42, "New Title")
    # Body should contain the body text plus footer
    updated_body = fake_github.updated_pr_bodies[0][1]
    assert "New body" in updated_body


def test_closing_ref_from_existing_pr_body(tmp_path: Path) -> None:
    """Extracts 'Closes #55' from existing footer when no issue_number set."""
    # PR body with existing footer containing closing reference
    existing_body = "PR body\n\n---\n\nCloses owner/plans-repo#55\n\n```\nerk pr checkout 42\n```"
    pr = _pr_details(number=42, body=existing_body)
    fake_git = FakeGit(
        repository_roots={tmp_path: tmp_path},
        remote_urls={(tmp_path, "origin"): "git@github.com:owner/repo.git"},
    )
    fake_github = FakeGitHub(
        prs_by_branch={"feature": pr},
        pr_details={42: pr},
    )
    ctx = context_for_test(git=fake_git, github=fake_github, cwd=tmp_path)
    state = _make_state(cwd=tmp_path, issue_number=None)

    result = finalize_pr(ctx, state)

    assert isinstance(result, SubmitState)
    # The issue_number should be extracted from the existing PR body footer
    assert result.issue_number == 55


def test_issue_number_takes_precedence(tmp_path: Path) -> None:
    """state.issue_number overrides PR body reference."""
    existing_body = "PR body\n\n---\n\nCloses owner/plans-repo#55\n\n```\nerk pr checkout 42\n```"
    pr = _pr_details(number=42, body=existing_body)
    fake_git = FakeGit(
        repository_roots={tmp_path: tmp_path},
        remote_urls={(tmp_path, "origin"): "git@github.com:owner/repo.git"},
    )
    fake_github = FakeGitHub(
        prs_by_branch={"feature": pr},
        pr_details={42: pr},
    )
    ctx = context_for_test(git=fake_git, github=fake_github, cwd=tmp_path)
    state = _make_state(cwd=tmp_path, issue_number=99)

    result = finalize_pr(ctx, state)

    assert isinstance(result, SubmitState)
    assert result.issue_number == 99


def test_adds_learn_plan_label(tmp_path: Path) -> None:
    """.impl/ learn plan => adds ERK_SKIP_LEARN_LABEL."""
    # Create .impl/issue.json with erk-learn label
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    issue_json = impl_dir / "issue.json"
    issue_json.write_text(
        json.dumps(
            {
                "issue_number": 42,
                "issue_url": "https://github.com/owner/repo/issues/42",
                "created_at": "2025-01-01T00:00:00+00:00",
                "synced_at": "2025-01-01T00:00:00+00:00",
                "labels": ["erk-learn"],
            }
        )
    )

    pr = _pr_details(number=42)
    fake_git = FakeGit(
        repository_roots={tmp_path: tmp_path},
        remote_urls={(tmp_path, "origin"): "git@github.com:owner/repo.git"},
    )
    fake_github = FakeGitHub(
        prs_by_branch={"feature": pr},
        pr_details={42: pr},
    )
    ctx = context_for_test(git=fake_git, github=fake_github, cwd=tmp_path)
    state = _make_state(cwd=tmp_path)

    result = finalize_pr(ctx, state)

    assert isinstance(result, SubmitState)
    assert len(fake_github.added_labels) == 1
    assert fake_github.added_labels[0][0] == 42


def test_amends_commit_with_title_and_body(tmp_path: Path) -> None:
    """amend_commit called with 'Title\\n\\nBody'."""
    pr = _pr_details(number=42)
    fake_git = FakeGit(
        repository_roots={tmp_path: tmp_path},
        remote_urls={(tmp_path, "origin"): "git@github.com:owner/repo.git"},
    )
    fake_github = FakeGitHub(
        prs_by_branch={"feature": pr},
        pr_details={42: pr},
    )
    ctx = context_for_test(git=fake_git, github=fake_github, cwd=tmp_path)
    state = _make_state(cwd=tmp_path, title="Title", body="Body text")

    result = finalize_pr(ctx, state)

    assert isinstance(result, SubmitState)
    # amend_commit should have been called
    assert len(fake_git.commit.commits) == 1
    commit_msg = fake_git.commit.commits[0].message
    assert commit_msg == "Title\n\nBody text"


def test_cleans_up_diff_file(tmp_path: Path) -> None:
    """Temp diff file deleted after finalize."""
    diff_file = tmp_path / "test.diff"
    diff_file.write_text("some diff content")
    assert diff_file.exists()

    pr = _pr_details(number=42)
    fake_git = FakeGit(
        repository_roots={tmp_path: tmp_path},
        remote_urls={(tmp_path, "origin"): "git@github.com:owner/repo.git"},
    )
    fake_github = FakeGitHub(
        prs_by_branch={"feature": pr},
        pr_details={42: pr},
    )
    ctx = context_for_test(git=fake_git, github=fake_github, cwd=tmp_path)
    state = _make_state(cwd=tmp_path, diff_file=diff_file)

    result = finalize_pr(ctx, state)

    assert isinstance(result, SubmitState)
    assert not diff_file.exists()
