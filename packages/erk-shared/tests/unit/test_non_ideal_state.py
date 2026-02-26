"""Unit tests for NonIdealStateError and NonIdealState protocol."""

from dataclasses import dataclass

import pytest

from erk_shared.non_ideal_state import (
    BranchDetectionFailed,
    EnsurableResult,
    GitHubAPIFailed,
    NonIdealState,
    NonIdealStateError,
    NoPRForBranch,
    PRNotFoundError,
    SessionNotFound,
)

# ============================================================================
# NonIdealStateError
# ============================================================================


def test_non_ideal_state_error_stores_error_type() -> None:
    """NonIdealStateError.error_type matches the state's error_type."""
    state = BranchDetectionFailed()
    with pytest.raises(NonIdealStateError) as exc_info:
        raise NonIdealStateError(state)
    assert exc_info.value.error_type == "branch-detection-failed"


def test_non_ideal_state_error_message_is_state_message() -> None:
    """NonIdealStateError message matches the state's message."""
    state = NoPRForBranch(branch="my-feature")
    with pytest.raises(NonIdealStateError) as exc_info:
        raise NonIdealStateError(state)
    assert str(exc_info.value) == "No PR found for branch 'my-feature'"


def test_non_ideal_state_error_is_exception() -> None:
    """NonIdealStateError is an Exception subclass."""
    state = BranchDetectionFailed()
    error = NonIdealStateError(state)
    assert isinstance(error, Exception)


# ============================================================================
# NonIdealState.ensure()
# ============================================================================


def test_ensure_raises_non_ideal_state_error() -> None:
    """NonIdealState.ensure() raises NonIdealStateError."""
    state = BranchDetectionFailed()
    with pytest.raises(NonIdealStateError) as exc_info:
        state.ensure()
    assert exc_info.value.error_type == "branch-detection-failed"


def test_ensure_propagates_message() -> None:
    """NonIdealState.ensure() sets the correct error message."""
    state = NoPRForBranch(branch="feature-branch")
    with pytest.raises(NonIdealStateError) as exc_info:
        state.ensure()
    assert "feature-branch" in str(exc_info.value)


# ============================================================================
# Concrete NonIdealState implementations
# ============================================================================


def test_branch_detection_failed_satisfies_protocol() -> None:
    """BranchDetectionFailed satisfies the NonIdealState protocol."""
    state = BranchDetectionFailed()
    assert isinstance(state, NonIdealState)
    assert state.error_type == "branch-detection-failed"
    assert state.message == "Could not determine current branch"


def test_no_pr_for_branch_satisfies_protocol() -> None:
    """NoPRForBranch satisfies the NonIdealState protocol."""
    state = NoPRForBranch(branch="my-branch")
    assert isinstance(state, NonIdealState)
    assert state.error_type == "no-pr-for-branch"
    assert "my-branch" in state.message


def test_pr_not_found_error_satisfies_protocol() -> None:
    """PRNotFoundError satisfies the NonIdealState protocol."""
    state = PRNotFoundError(pr_number=42)
    assert isinstance(state, NonIdealState)
    assert state.error_type == "pr-not-found"
    assert "42" in state.message


def test_github_api_failed_satisfies_protocol() -> None:
    """GitHubAPIFailed satisfies the NonIdealState protocol."""
    state = GitHubAPIFailed(message="API rate limit exceeded")
    assert isinstance(state, NonIdealState)
    assert state.error_type == "github-api-failed"
    assert state.message == "API rate limit exceeded"


def test_session_not_found_satisfies_protocol() -> None:
    """SessionNotFound satisfies the NonIdealState protocol."""
    state = SessionNotFound(session_id="abc-123")
    assert isinstance(state, NonIdealState)
    assert state.error_type == "session-not-found"
    assert "abc-123" in state.message


def test_concrete_ensure_raises_non_ideal_state_error() -> None:
    """Concrete NonIdealState.ensure() raises NonIdealStateError with correct type."""
    state = PRNotFoundError(pr_number=99)
    with pytest.raises(NonIdealStateError) as exc_info:
        state.ensure()
    assert exc_info.value.error_type == "pr-not-found"


# ============================================================================
# EnsurableResult
# ============================================================================


@dataclass(frozen=True)
class _SampleResult(EnsurableResult):
    value: str


def test_ensurable_result_ensure_returns_self() -> None:
    """EnsurableResult.ensure() returns self for one-liner unwrapping."""
    result = _SampleResult(value="ok")
    assert result.ensure() is result
