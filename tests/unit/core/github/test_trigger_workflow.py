"""Tests for GitHub trigger_workflow() and dispatch_workflow() methods."""

from pathlib import Path

from erk_shared.gateway.github.fake import FakeGitHub


def test_trigger_workflow_tracks_call() -> None:
    """Verify FakeGitHub records workflow triggers and returns run ID."""
    github = FakeGitHub()
    repo_root = Path("/repo")

    run_id = github.trigger_workflow(
        repo_root=repo_root,
        workflow="implement-plan.yml",
        inputs={"branch-name": "feature"},
        ref=None,
    )

    assert run_id == "1234567890"
    assert len(github.triggered_workflows) == 1
    workflow, inputs = github.triggered_workflows[0]
    assert workflow == "implement-plan.yml"
    assert inputs == {"branch-name": "feature"}


def test_trigger_workflow_tracks_multiple_calls() -> None:
    """Verify multiple workflow triggers are tracked and return run IDs."""
    github = FakeGitHub()
    repo_root = Path("/repo")

    run_id1 = github.trigger_workflow(
        repo_root=repo_root, workflow="workflow1.yml", inputs={"key": "value1"}, ref=None
    )
    run_id2 = github.trigger_workflow(
        repo_root=repo_root, workflow="workflow2.yml", inputs={"key": "value2"}, ref=None
    )

    assert run_id1 == "1234567890"
    assert run_id2 == "1234567890"
    assert len(github.triggered_workflows) == 2
    assert github.triggered_workflows[0][0] == "workflow1.yml"
    assert github.triggered_workflows[1][0] == "workflow2.yml"


def test_dispatch_workflow_tracks_call_returns_none() -> None:
    """Verify FakeGitHub records dispatch_workflow and returns None."""
    github = FakeGitHub()
    repo_root = Path("/repo")

    result = github.dispatch_workflow(
        repo_root=repo_root,
        workflow="implement-plan.yml",
        inputs={"branch-name": "feature"},
        ref=None,
    )

    assert result is None
    assert len(github.triggered_workflows) == 1
    workflow, inputs = github.triggered_workflows[0]
    assert workflow == "implement-plan.yml"
    assert inputs == {"branch-name": "feature"}


def test_dispatch_workflow_shares_tracking_with_trigger() -> None:
    """Verify dispatch_workflow and trigger_workflow share triggered_workflows list."""
    github = FakeGitHub()
    repo_root = Path("/repo")

    github.dispatch_workflow(
        repo_root=repo_root, workflow="dispatch.yml", inputs={"key": "dispatch"}, ref=None
    )
    github.trigger_workflow(
        repo_root=repo_root, workflow="trigger.yml", inputs={"key": "trigger"}, ref=None
    )

    assert len(github.triggered_workflows) == 2
    assert github.triggered_workflows[0][0] == "dispatch.yml"
    assert github.triggered_workflows[1][0] == "trigger.yml"
