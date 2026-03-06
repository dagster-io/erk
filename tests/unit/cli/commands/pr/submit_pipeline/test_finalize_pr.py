"""Unit tests for finalize_pr pipeline step."""

import dataclasses
from datetime import UTC, datetime
from pathlib import Path

from erk.cli.commands.pr.submit_pipeline import (
    SubmitError,
    SubmitState,
    finalize_pr,
)
from erk.core.context import context_for_test
from erk.core.plan_context_provider import PlanContext
from erk_shared.context.types import GlobalConfig
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.types import PRDetails
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.impl_folder import get_impl_dir
from erk_shared.plan_store.planned_pr import PlannedPRBackend
from erk_shared.plan_store.planned_pr_lifecycle import build_plan_stage_body
from tests.test_utils.plan_helpers import (
    create_backend_from_issues,
    format_plan_header_body_for_test,
)

BRANCH = "test/branch"
"""Test branch name used across tests."""


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
    skip_description: bool = False,
    plan_id: str | None = None,
    pr_number: int | None = 42,
    pr_url: str | None = "https://github.com/owner/repo/pull/42",
    was_created: bool = True,
    base_branch: str | None = "main",
    graphite_url: str | None = None,
    diff_file: Path | None = None,
    plan_context: PlanContext | None = None,
    title: str | None = "My PR Title",
    body: str | None = "My PR body",
    existing_pr_body: str = "",
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
        skip_description=skip_description,
        quiet=False,
        plan_id=plan_id,
        pr_number=pr_number,
        pr_url=pr_url,
        was_created=was_created,
        base_branch=base_branch,
        graphite_url=graphite_url,
        diff_file=diff_file,
        plan_context=plan_context,
        title=title,
        body=body,
        existing_pr_body=existing_pr_body,
        graphite_is_authed=None,
        graphite_branch_tracked=None,
    )


def _pr_details(
    *,
    number: int = 42,
    branch: str = "feature",
    body: str = "",
    is_draft: bool = False,
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
        is_draft=is_draft,
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


def test_adds_learn_plan_label(tmp_path: Path) -> None:
    """Branch-scoped impl dir with erk-learn label => adds ERK_SKIP_LEARN_LABEL."""
    # Create branch-scoped impl dir with plan-ref.json with erk-learn label
    impl_dir = get_impl_dir(tmp_path, branch_name=BRANCH)
    impl_dir.mkdir(parents=True)
    from erk_shared.impl_folder import build_plan_ref_json

    plan_ref_content = build_plan_ref_json(
        provider="github",
        plan_id="42",
        url="https://github.com/owner/repo/issues/42",
        labels=("erk-learn",),
        objective_id=None,
        node_ids=None,
    )
    (impl_dir / "plan-ref.json").write_text(plan_ref_content, encoding="utf-8")

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
    state = _make_state(cwd=tmp_path, branch_name=BRANCH)

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


def test_embeds_plan_in_pr_body(tmp_path: Path) -> None:
    """Plan context embedded in PR body but NOT in commit message."""
    plan_content = "# My Plan\n\nSome implementation details"
    plan_ctx = PlanContext(
        plan_id="1234",
        plan_content=plan_content,
        objective_summary=None,
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
    state = _make_state(
        cwd=tmp_path,
        title="Add feature",
        body="Summary of changes",
        plan_context=plan_ctx,
    )

    result = finalize_pr(ctx, state)

    assert isinstance(result, SubmitState)

    # Verify PR body contains the plan details block
    assert len(fake_github.updated_pr_bodies) == 1
    updated_body = fake_github.updated_pr_bodies[0][1]
    assert "Summary of changes" in updated_body
    assert "## Implementation Plan" in updated_body
    assert "<details>" in updated_body
    assert "<summary><strong>Implementation Plan</strong> (Plan #1234)</summary>" in updated_body
    assert plan_content in updated_body
    assert "</details>" in updated_body

    # Verify commit message does NOT contain plan details block
    assert len(fake_git.commit.commits) == 1
    commit_msg = fake_git.commit.commits[0].message
    assert commit_msg == "Add feature\n\nSummary of changes"
    assert "<details>" not in commit_msg
    assert plan_content not in commit_msg


def test_retracks_graphite_after_amend(tmp_path: Path) -> None:
    """retrack_branch called after amend to fix Graphite tracking divergence."""
    pr = _pr_details(number=42)
    fake_git = FakeGit(
        repository_roots={tmp_path: tmp_path},
        remote_urls={(tmp_path, "origin"): "git@github.com:owner/repo.git"},
    )
    fake_github = FakeGitHub(
        prs_by_branch={"feature": pr},
        pr_details={42: pr},
    )
    # Enable Graphite so context_for_test creates graphite_branch_ops
    global_config = GlobalConfig(
        erk_root=Path("/test/erks"),
        use_graphite=True,
        shell_setup_complete=False,
        github_planning=True,
    )
    ctx = context_for_test(
        git=fake_git, github=fake_github, global_config=global_config, cwd=tmp_path
    )
    state = _make_state(cwd=tmp_path, title="Title", body="Body text")

    result = finalize_pr(ctx, state)

    assert isinstance(result, SubmitState)
    # Verify retrack_branch was called after the amend
    assert ctx.graphite_branch_ops is not None
    assert len(ctx.graphite_branch_ops.retrack_branch_calls) == 1
    assert ctx.graphite_branch_ops.retrack_branch_calls[0] == (tmp_path, "feature")


def test_finalize_pr_planned_pr_backend_extracts_metadata(tmp_path: Path) -> None:
    """Planned PR backend: metadata prefix extracted, no self-close."""
    metadata_body = format_plan_header_body_for_test()
    plan_content = "# My Plan\n\nImplement the thing."
    pr_body = build_plan_stage_body(metadata_body, plan_content, summary=None)

    pr = _pr_details(number=42, body=pr_body)
    fake_git = FakeGit(
        repository_roots={tmp_path: tmp_path},
        remote_urls={(tmp_path, "origin"): "git@github.com:owner/repo.git"},
    )
    fake_github = FakeGitHub(
        prs_by_branch={"feature": pr},
        pr_details={42: pr},
    )
    ctx = context_for_test(
        git=fake_git,
        github=fake_github,
        plan_store=PlannedPRBackend(fake_github, fake_github.issues, time=FakeTime()),
        cwd=tmp_path,
    )
    state = _make_state(
        cwd=tmp_path,
        title="Implement feature",
        body="Summary of work",
        existing_pr_body=pr_body,
    )

    result = finalize_pr(ctx, state)

    assert isinstance(result, SubmitState)
    # Planned PR backend sets plan_id to None (no self-close)
    assert result.plan_id is None
    # PR body should contain metadata prefix
    updated_body = fake_github.updated_pr_bodies[0][1]
    assert "plan-header" in updated_body
    assert "Closes #" not in updated_body


def test_marks_planned_pr_as_ready(tmp_path: Path) -> None:
    """Draft PR is marked ready for review during finalize."""
    pr = _pr_details(number=42)
    pr = dataclasses.replace(pr, is_draft=True)
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
    assert fake_github.marked_ready_prs == [42]


def test_does_not_mark_non_planned_pr_as_ready(tmp_path: Path) -> None:
    """Non-draft PR is not marked ready (mark_pr_ready not called)."""
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
    assert fake_github.marked_ready_prs == []


def test_publishes_planned_pr(tmp_path: Path) -> None:
    """Draft PR is published (marked ready) during finalize."""
    pr = _pr_details(number=42, is_draft=True)
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
    assert 42 in fake_github.marked_pr_ready


def test_does_not_publish_non_planned_pr(tmp_path: Path) -> None:
    """Non-draft PR is NOT marked ready during finalize."""
    pr = _pr_details(number=42, is_draft=False)
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
    assert fake_github.marked_pr_ready == []


def test_skip_description_returns_state_unchanged(tmp_path: Path) -> None:
    """skip_description=True causes early return with state unchanged."""
    ctx = context_for_test(cwd=tmp_path)
    state = _make_state(cwd=tmp_path, skip_description=True)

    result = finalize_pr(ctx, state)

    assert result is state


def test_updates_lifecycle_stage_for_linked_plan(tmp_path: Path) -> None:
    """finalize_pr with a PlanContext triggers lifecycle update to 'impl'."""
    plan_body = format_plan_header_body_for_test(lifecycle_stage="planned")
    plan_issue = IssueInfo(
        number=321,
        title="Plan #321",
        body=plan_body,
        state="OPEN",
        url="https://github.com/owner/repo/issues/321",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 15, 10, 30, tzinfo=UTC),
        updated_at=datetime(2024, 1, 15, 10, 30, tzinfo=UTC),
        author="test-user",
    )
    backend, fake_github, fake_issues = create_backend_from_issues({321: plan_issue})

    fake_git = FakeGit(
        repository_roots={tmp_path: tmp_path},
        remote_urls={(tmp_path, "origin"): "git@github.com:owner/repo.git"},
    )
    ctx = context_for_test(
        git=fake_git,
        github=fake_github,
        issues=fake_issues,
        plan_store=backend,
        cwd=tmp_path,
    )

    plan_ctx = PlanContext(
        plan_id="321",
        plan_content="# Plan\n\nImplement the thing.",
        objective_summary=None,
    )
    state = _make_state(cwd=tmp_path, plan_context=plan_ctx)

    result = finalize_pr(ctx, state)

    assert isinstance(result, SubmitState)
    # Verify lifecycle_stage was updated in the plan PR (#321)
    # Note: finalize_pr also updates the feature PR (#42) body, so there may be multiple entries
    lifecycle_bodies = [b for n, b in fake_github.updated_pr_bodies if n == 321]
    assert len(lifecycle_bodies) == 1
    assert "lifecycle_stage: impl" in lifecycle_bodies[0]


def test_no_lifecycle_update_with_only_plan_id(tmp_path: Path) -> None:
    """finalize_pr does NOT update lifecycle when only plan_id is set (no plan_context)."""
    plan_body = format_plan_header_body_for_test(lifecycle_stage="planned")
    plan_issue = IssueInfo(
        number=321,
        title="Plan #321",
        body=plan_body,
        state="OPEN",
        url="https://github.com/owner/repo/issues/321",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 15, 10, 30, tzinfo=UTC),
        updated_at=datetime(2024, 1, 15, 10, 30, tzinfo=UTC),
        author="test-user",
    )
    fake_issues = FakeGitHubIssues(issues={321: plan_issue})

    pr = _pr_details(number=42)
    fake_git = FakeGit(
        repository_roots={tmp_path: tmp_path},
        remote_urls={(tmp_path, "origin"): "git@github.com:owner/repo.git"},
    )
    fake_github = FakeGitHub(
        prs_by_branch={"feature": pr},
        pr_details={42: pr},
        issues_gateway=fake_issues,
    )
    ctx = context_for_test(git=fake_git, github=fake_github, issues=fake_issues, cwd=tmp_path)

    state = _make_state(cwd=tmp_path, plan_id="321", plan_context=None)

    result = finalize_pr(ctx, state)

    assert isinstance(result, SubmitState)
    # plan_id alone should NOT trigger lifecycle update
    assert len(fake_issues.updated_bodies) == 0


def test_updates_lifecycle_stage_for_draft_pr_backend(tmp_path: Path) -> None:
    """finalize_pr updates lifecycle for draft-PR backend where plan IS the PR."""
    metadata_body = format_plan_header_body_for_test(lifecycle_stage="planned")
    plan_content = "# My Plan\n\nImplement the thing."
    pr_body = build_plan_stage_body(metadata_body, plan_content, summary=None)

    pr = _pr_details(number=42, body=pr_body)
    fake_git = FakeGit(
        repository_roots={tmp_path: tmp_path},
        remote_urls={(tmp_path, "origin"): "git@github.com:owner/repo.git"},
    )
    fake_github = FakeGitHub(
        prs_by_branch={"feature": pr},
        pr_details={42: pr},
    )
    ctx = context_for_test(
        git=fake_git,
        github=fake_github,
        plan_store=PlannedPRBackend(fake_github, fake_github.issues, time=FakeTime()),
        cwd=tmp_path,
    )
    state = _make_state(
        cwd=tmp_path,
        title="Implement feature",
        body="Summary of work",
        plan_context=None,
        plan_id=None,
        existing_pr_body=pr_body,
    )

    result = finalize_pr(ctx, state)

    assert isinstance(result, SubmitState)
    # First update is the PR body (title/body), second is lifecycle metadata update
    assert len(fake_github.updated_pr_bodies) >= 2
    # The lifecycle update is the last PR body update
    lifecycle_body = fake_github.updated_pr_bodies[-1][1]
    assert "lifecycle_stage: impl" in lifecycle_body
