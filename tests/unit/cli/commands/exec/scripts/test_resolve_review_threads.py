"""Unit tests for resolve-review-threads batch command.

Tests the batch resolution command that processes multiple threads from JSON stdin.
Uses FakeGitHub for fast, reliable testing.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.resolve_review_threads import resolve_review_threads
from erk_shared.context.context import ErkContext
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub

# ============================================================================
# Success Cases
# ============================================================================


def test_batch_resolve_empty_array(tmp_path: Path) -> None:
    """Test batch resolve with empty array returns success."""
    fake_github = FakeGitHub()
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            resolve_review_threads,
            input="[]",
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["results"] == []


def test_batch_resolve_single_thread(tmp_path: Path) -> None:
    """Test batch resolve with a single thread."""
    fake_github = FakeGitHub()
    fake_git = FakeGit()
    runner = CliRunner()

    input_data = json.dumps([{"thread_id": "PRRT_1"}])

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            resolve_review_threads,
            input=input_data,
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert len(output["results"]) == 1
    assert output["results"][0]["success"] is True
    assert output["results"][0]["thread_id"] == "PRRT_1"
    assert output["results"][0]["comment_added"] is False

    # Verify resolution was tracked
    assert "PRRT_1" in fake_github.resolved_thread_ids


def test_batch_resolve_multiple_threads(tmp_path: Path) -> None:
    """Test batch resolve with multiple threads."""
    fake_github = FakeGitHub()
    fake_git = FakeGit()
    runner = CliRunner()

    input_data = json.dumps([{"thread_id": "PRRT_1"}, {"thread_id": "PRRT_2"}])

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            resolve_review_threads,
            input=input_data,
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert len(output["results"]) == 2

    # Verify both threads resolved
    assert output["results"][0]["success"] is True
    assert output["results"][0]["thread_id"] == "PRRT_1"
    assert output["results"][1]["success"] is True
    assert output["results"][1]["thread_id"] == "PRRT_2"

    # Verify both resolutions were tracked
    assert "PRRT_1" in fake_github.resolved_thread_ids
    assert "PRRT_2" in fake_github.resolved_thread_ids


def test_batch_resolve_with_comments(tmp_path: Path) -> None:
    """Test batch resolve with comments on some threads."""
    fake_github = FakeGitHub()
    fake_git = FakeGit()
    runner = CliRunner()

    input_data = json.dumps(
        [{"thread_id": "PRRT_1", "comment": "Fixed typo"}, {"thread_id": "PRRT_2"}]
    )

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            resolve_review_threads,
            input=input_data,
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert len(output["results"]) == 2

    # First thread should have comment added
    assert output["results"][0]["success"] is True
    assert output["results"][0]["thread_id"] == "PRRT_1"
    assert output["results"][0]["comment_added"] is True

    # Second thread should not have comment added
    assert output["results"][1]["success"] is True
    assert output["results"][1]["thread_id"] == "PRRT_2"
    assert output["results"][1]["comment_added"] is False

    # Verify comment was tracked
    assert len(fake_github.thread_replies) == 1
    thread_id, comment_body = fake_github.thread_replies[0]
    assert thread_id == "PRRT_1"
    assert comment_body.startswith("Fixed typo\n\n")
    assert "_Addressed via `/erk:pr-address` at" in comment_body


def test_batch_resolve_with_null_comment(tmp_path: Path) -> None:
    """Test batch resolve with explicit null comment."""
    fake_github = FakeGitHub()
    fake_git = FakeGit()
    runner = CliRunner()

    input_data = json.dumps([{"thread_id": "PRRT_1", "comment": None}])

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            resolve_review_threads,
            input=input_data,
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["results"][0]["comment_added"] is False
    assert len(fake_github.thread_replies) == 0


# ============================================================================
# Partial Failure Cases
# ============================================================================


def test_batch_resolve_partial_failure(tmp_path: Path) -> None:
    """Test batch resolve with one thread failing."""
    # Configure fake to fail on specific thread
    fake_github = FakeGitHub(resolve_thread_failures={"PRRT_2"})
    fake_git = FakeGit()
    runner = CliRunner()

    input_data = json.dumps([{"thread_id": "PRRT_1"}, {"thread_id": "PRRT_2"}])

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            resolve_review_threads,
            input=input_data,
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)

    # Top-level success should be false because one failed
    assert output["success"] is False
    assert len(output["results"]) == 2

    # First thread succeeded
    assert output["results"][0]["success"] is True
    assert output["results"][0]["thread_id"] == "PRRT_1"

    # Second thread failed
    assert output["results"][1]["success"] is False
    assert output["results"][1]["error_type"] == "resolution-failed"


def test_batch_resolve_all_failures(tmp_path: Path) -> None:
    """Test batch resolve when all threads fail."""
    # Configure fake to fail on all threads
    fake_github = FakeGitHub(resolve_thread_failures={"PRRT_1", "PRRT_2"})
    fake_git = FakeGit()
    runner = CliRunner()

    input_data = json.dumps([{"thread_id": "PRRT_1"}, {"thread_id": "PRRT_2"}])

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            resolve_review_threads,
            input=input_data,
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is False
    assert len(output["results"]) == 2
    assert output["results"][0]["success"] is False
    assert output["results"][1]["success"] is False


# ============================================================================
# Input Validation Error Cases
# ============================================================================


def test_batch_resolve_invalid_json(tmp_path: Path) -> None:
    """Test batch resolve with invalid JSON."""
    fake_github = FakeGitHub()
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            resolve_review_threads,
            input="{not valid json}",
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "invalid-json"
    assert "Failed to parse JSON" in output["message"]


def test_batch_resolve_not_array(tmp_path: Path) -> None:
    """Test batch resolve with non-array JSON."""
    fake_github = FakeGitHub()
    fake_git = FakeGit()
    runner = CliRunner()

    input_data = json.dumps({"thread_id": "PRRT_1"})

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            resolve_review_threads,
            input=input_data,
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "invalid-input"
    assert "must be a JSON array" in output["message"]


def test_batch_resolve_item_not_object(tmp_path: Path) -> None:
    """Test batch resolve with non-object item in array."""
    fake_github = FakeGitHub()
    fake_git = FakeGit()
    runner = CliRunner()

    input_data = json.dumps(["PRRT_1"])

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            resolve_review_threads,
            input=input_data,
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "invalid-input"
    assert "not an object" in output["message"]


def test_batch_resolve_missing_thread_id(tmp_path: Path) -> None:
    """Test batch resolve with missing thread_id field."""
    fake_github = FakeGitHub()
    fake_git = FakeGit()
    runner = CliRunner()

    input_data = json.dumps([{"comment": "No thread ID"}])

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            resolve_review_threads,
            input=input_data,
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "invalid-input"
    assert "missing required 'thread_id' field" in output["message"]


def test_batch_resolve_non_string_thread_id(tmp_path: Path) -> None:
    """Test batch resolve with non-string thread_id."""
    fake_github = FakeGitHub()
    fake_git = FakeGit()
    runner = CliRunner()

    input_data = json.dumps([{"thread_id": 123}])

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            resolve_review_threads,
            input=input_data,
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "invalid-input"
    assert "non-string 'thread_id'" in output["message"]


def test_batch_resolve_non_string_comment(tmp_path: Path) -> None:
    """Test batch resolve with non-string comment."""
    fake_github = FakeGitHub()
    fake_git = FakeGit()
    runner = CliRunner()

    input_data = json.dumps([{"thread_id": "PRRT_1", "comment": 123}])

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            resolve_review_threads,
            input=input_data,
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "invalid-input"
    assert "non-string 'comment'" in output["message"]


# ============================================================================
# JSON Output Structure Tests
# ============================================================================


def test_batch_resolve_json_structure_success(tmp_path: Path) -> None:
    """Test JSON output structure for successful batch resolution."""
    fake_github = FakeGitHub()
    fake_git = FakeGit()
    runner = CliRunner()

    input_data = json.dumps([{"thread_id": "PRRT_1", "comment": "Fixed"}])

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            resolve_review_threads,
            input=input_data,
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify top-level structure
    assert "success" in output
    assert "results" in output
    assert isinstance(output["results"], list)

    # Verify result item structure
    result_item = output["results"][0]
    assert "success" in result_item
    assert "thread_id" in result_item
    assert "comment_added" in result_item


def test_batch_resolve_json_structure_error(tmp_path: Path) -> None:
    """Test JSON output structure for validation error."""
    fake_github = FakeGitHub()
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            resolve_review_threads,
            input="invalid",
            obj=ErkContext.for_test(github=fake_github, git=fake_git, repo_root=cwd, cwd=cwd),
        )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify error structure
    assert "success" in output
    assert output["success"] is False
    assert "error_type" in output
    assert "message" in output
