"""Tests for GitHub dispatch_workflow() fire-and-forget method."""

from pathlib import Path

from erk_shared.gateway.github.fake import FakeGitHub


def test_dispatch_workflow_returns_none() -> None:
    """Verify dispatch_workflow() returns None (not a run ID)."""
    github = FakeGitHub()
    repo_root = Path("/repo")

    result = github.dispatch_workflow(
        repo_root=repo_root,
        workflow="implement-plan.yml",
        inputs={"branch_name": "feature"},
    )

    assert result is None


def test_dispatch_workflow_tracks_call() -> None:
    """Verify FakeGitHub records dispatch_workflow calls."""
    github = FakeGitHub()
    repo_root = Path("/repo")

    github.dispatch_workflow(
        repo_root=repo_root,
        workflow="implement-plan.yml",
        inputs={"branch_name": "feature"},
    )

    assert len(github.dispatched_workflows) == 1
    workflow, inputs = github.dispatched_workflows[0]
    assert workflow == "implement-plan.yml"
    assert inputs == {"branch_name": "feature"}


def test_dispatch_workflow_does_not_create_workflow_run() -> None:
    """Verify dispatch_workflow() does NOT create a WorkflowRun entry.

    Fire-and-forget dispatches have no run ID, so no run should be trackable.
    """
    github = FakeGitHub()
    repo_root = Path("/repo")

    github.dispatch_workflow(
        repo_root=repo_root,
        workflow="implement-plan.yml",
        inputs={"branch_name": "feature"},
    )

    # No run should be created (list_workflow_runs returns empty)
    runs = github.list_workflow_runs(repo_root, "implement-plan.yml")
    assert len(runs) == 0


def test_dispatch_workflow_independent_from_trigger_workflow() -> None:
    """Verify dispatch_workflow and trigger_workflow tracking lists are separate."""
    github = FakeGitHub()
    repo_root = Path("/repo")

    github.dispatch_workflow(
        repo_root=repo_root,
        workflow="workflow-a.yml",
        inputs={"key": "dispatch"},
    )
    github.trigger_workflow(
        repo_root=repo_root,
        workflow="workflow-b.yml",
        inputs={"key": "trigger"},
    )

    assert len(github.dispatched_workflows) == 1
    assert github.dispatched_workflows[0][0] == "workflow-a.yml"

    assert len(github.triggered_workflows) == 1
    assert github.triggered_workflows[0][0] == "workflow-b.yml"


def test_dispatch_workflow_tracks_multiple_calls() -> None:
    """Verify multiple dispatch_workflow calls are all tracked."""
    github = FakeGitHub()
    repo_root = Path("/repo")

    github.dispatch_workflow(
        repo_root=repo_root,
        workflow="workflow1.yml",
        inputs={"key": "value1"},
    )
    github.dispatch_workflow(
        repo_root=repo_root,
        workflow="workflow2.yml",
        inputs={"key": "value2"},
    )

    assert len(github.dispatched_workflows) == 2
    assert github.dispatched_workflows[0][0] == "workflow1.yml"
    assert github.dispatched_workflows[1][0] == "workflow2.yml"
