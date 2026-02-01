"""Unit tests for trigger_async_learn exec script.

Tests triggering the learn.yml workflow for async learn.
Uses FakeGitHub for dependency injection.

NOTE: Full orchestration testing (session preprocessing, gist upload, etc.)
requires mocking subprocess.run calls since the script orchestrates multiple
erk exec commands via subprocess.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.trigger_async_learn import (
    trigger_async_learn as trigger_async_learn_command,
)
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.types import RepoInfo


def _parse_json_output(output: str) -> dict[str, object]:
    """Parse JSON from CliRunner output, skipping stderr progress lines.

    Click 8.x mixes stderr into result.output. The trigger-async-learn script
    writes progress messages to stderr and JSON to stdout. This helper extracts
    the JSON line from the mixed output.
    """
    for line in reversed(output.strip().splitlines()):
        if line.startswith("{"):
            return json.loads(line)  # type: ignore[no-any-return]
    raise ValueError(f"No JSON found in output: {output!r}")


def _get_stderr_lines(output: str) -> list[str]:
    """Extract stderr diagnostic lines from CliRunner output.

    Returns all lines starting with '[trigger-async-learn]'.
    """
    return [
        line for line in output.strip().splitlines() if line.startswith("[trigger-async-learn]")
    ]


def test_trigger_async_learn_success(tmp_path: Path) -> None:
    """Test successful workflow trigger with full orchestration pipeline."""
    runner = CliRunner()
    repo_info = RepoInfo(owner="test-owner", name="test-repo")
    github = FakeGitHub(repo_info=repo_info)
    ctx = ErkContext.for_test(repo_root=tmp_path, github=github, repo_info=repo_info)

    # Create the .erk/scratch directory that the script expects
    learn_dir = tmp_path / ".erk" / "scratch" / "learn-123"
    learn_dir.mkdir(parents=True)

    # Mock subprocess calls to simulate the orchestration pipeline
    mock_subprocess_results = [
        # get-learn-sessions
        MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
                    "success": True,
                    "planning_session_id": "planning-session-1",
                    "session_sources": [
                        {
                            "source_type": "local",
                            "session_id": "planning-session-1",
                            "path": "/fake/path.jsonl",
                            "run_id": None,
                            "gist_url": None,
                        }
                    ],
                }
            ),
            stderr="",
        ),
        # preprocess-session (planning) - outputs file paths, not JSON
        MagicMock(returncode=0, stdout="/tmp/learn/planning-summary.md\n", stderr=""),
        # get-pr-for-plan
        MagicMock(
            returncode=0,
            stdout=json.dumps({"success": True, "pr_number": 456}),
            stderr="",
        ),
        # get-pr-review-comments
        MagicMock(returncode=0, stdout=json.dumps({"success": True, "threads": []}), stderr=""),
        # get-pr-discussion-comments
        MagicMock(returncode=0, stdout=json.dumps({"success": True, "comments": []}), stderr=""),
        # upload-learn-materials
        MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
                    "success": True,
                    "gist_url": "https://gist.github.com/user/abc123",
                    "file_count": 1,
                    "total_size": 5432,
                }
            ),
            stderr="",
        ),
    ]

    with patch("subprocess.run", side_effect=mock_subprocess_results):
        result = runner.invoke(trigger_async_learn_command, ["123"], obj=ctx)

    assert result.exit_code == 0
    output = _parse_json_output(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 123
    assert output["workflow_triggered"] is True
    assert output["run_id"] == "1234567890"
    assert (
        output["workflow_url"] == "https://github.com/test-owner/test-repo/actions/runs/1234567890"
    )
    assert output["gist_url"] == "https://gist.github.com/user/abc123"


def test_trigger_async_learn_verifies_workflow_call(tmp_path: Path) -> None:
    """Test that workflow trigger is called with correct parameters including gist_url."""
    runner = CliRunner()
    repo_info = RepoInfo(owner="test-owner", name="test-repo")
    github = FakeGitHub(repo_info=repo_info)
    ctx = ErkContext.for_test(repo_root=tmp_path, github=github, repo_info=repo_info)

    learn_dir = tmp_path / ".erk" / "scratch" / "learn-456"
    learn_dir.mkdir(parents=True)

    # Mock the subprocess pipeline
    mock_subprocess_results = [
        MagicMock(
            returncode=0,
            stdout=json.dumps({"success": True, "session_sources": []}),
            stderr="",
        ),
        MagicMock(
            returncode=0,
            stdout=json.dumps({"success": False}),
            stderr="",
        ),  # get-pr-for-plan (no PR)
        MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
                    "success": True,
                    "gist_url": "https://gist.github.com/user/xyz789",
                    "file_count": 0,
                    "total_size": 0,
                }
            ),
            stderr="",
        ),
    ]

    with patch("subprocess.run", side_effect=mock_subprocess_results):
        runner.invoke(trigger_async_learn_command, ["456"], obj=ctx)

    assert len(github.triggered_workflows) == 1
    workflow, inputs = github.triggered_workflows[0]
    assert workflow == "learn.yml"
    assert inputs["issue_number"] == "456"
    assert inputs["gist_url"] == "https://gist.github.com/user/xyz789"


def test_trigger_async_learn_no_repo_info(tmp_path: Path) -> None:
    """Test error when not in a GitHub repository."""
    runner = CliRunner()
    github = FakeGitHub()
    # Not passing repo_info leaves it as None, simulating not being in a GitHub repo
    ctx = ErkContext.for_test(repo_root=tmp_path, github=github)

    result = runner.invoke(trigger_async_learn_command, ["123"], obj=ctx)

    assert result.exit_code == 1
    output = _parse_json_output(result.output)
    assert output["success"] is False
    assert "GitHub repository" in output["error"]


def test_trigger_async_learn_no_context(tmp_path: Path) -> None:
    """Test error when context is not initialized."""
    runner = CliRunner()

    result = runner.invoke(trigger_async_learn_command, ["123"], obj=None)

    assert result.exit_code == 1
    output = _parse_json_output(result.output)
    assert output["success"] is False
    assert "Context not initialized" in output["error"]


def test_trigger_async_learn_json_output_structure(tmp_path: Path) -> None:
    """Test that JSON output has expected structure on success including gist_url."""
    runner = CliRunner()
    repo_info = RepoInfo(owner="dagster-io", name="erk")
    github = FakeGitHub(repo_info=repo_info)
    ctx = ErkContext.for_test(repo_root=tmp_path, github=github, repo_info=repo_info)

    learn_dir = tmp_path / ".erk" / "scratch" / "learn-789"
    learn_dir.mkdir(parents=True)

    # Mock the subprocess pipeline
    mock_subprocess_results = [
        MagicMock(
            returncode=0,
            stdout=json.dumps({"success": True, "session_sources": []}),
            stderr="",
        ),
        MagicMock(
            returncode=0,
            stdout=json.dumps({"success": False}),
            stderr="",
        ),  # get-pr-for-plan (no PR)
        MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
                    "success": True,
                    "gist_url": "https://gist.github.com/user/test123",
                    "file_count": 0,
                    "total_size": 0,
                }
            ),
            stderr="",
        ),
    ]

    with patch("subprocess.run", side_effect=mock_subprocess_results):
        result = runner.invoke(trigger_async_learn_command, ["789"], obj=ctx)

    assert result.exit_code == 0
    output = _parse_json_output(result.output)

    # Verify expected keys
    assert "success" in output
    assert "issue_number" in output
    assert "workflow_triggered" in output
    assert "run_id" in output
    assert "workflow_url" in output
    assert "gist_url" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["issue_number"], int)
    assert isinstance(output["workflow_triggered"], bool)
    assert isinstance(output["run_id"], str)
    assert isinstance(output["workflow_url"], str)
    assert isinstance(output["gist_url"], str)


def test_trigger_async_learn_filtered_session_skipped(tmp_path: Path) -> None:
    """Test that a filtered session (empty stdout from preprocess) is skipped gracefully."""
    runner = CliRunner()
    repo_info = RepoInfo(owner="test-owner", name="test-repo")
    github = FakeGitHub(repo_info=repo_info)
    ctx = ErkContext.for_test(repo_root=tmp_path, github=github, repo_info=repo_info)

    learn_dir = tmp_path / ".erk" / "scratch" / "learn-123"
    learn_dir.mkdir(parents=True)

    mock_subprocess_results = [
        # get-learn-sessions - returns one local session
        MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
                    "success": True,
                    "planning_session_id": "planning-session-1",
                    "session_sources": [
                        {
                            "source_type": "local",
                            "session_id": "planning-session-1",
                            "path": "/fake/path.jsonl",
                            "run_id": None,
                            "gist_url": None,
                        }
                    ],
                }
            ),
            stderr="",
        ),
        # preprocess-session returns empty stdout (session filtered as empty/warmup)
        MagicMock(returncode=0, stdout="", stderr=""),
        # get-pr-for-plan (no PR)
        MagicMock(
            returncode=0,
            stdout=json.dumps({"success": False}),
            stderr="",
        ),
        # upload-learn-materials
        MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
                    "success": True,
                    "gist_url": "https://gist.github.com/user/abc123",
                    "file_count": 0,
                    "total_size": 0,
                }
            ),
            stderr="",
        ),
    ]

    with patch("subprocess.run", side_effect=mock_subprocess_results):
        result = runner.invoke(trigger_async_learn_command, ["123"], obj=ctx)

    assert result.exit_code == 0
    output = _parse_json_output(result.output)
    assert output["success"] is True


def test_trigger_async_learn_preprocess_failure(tmp_path: Path) -> None:
    """Test that a non-zero exit code from preprocess-session produces an error."""
    runner = CliRunner()
    repo_info = RepoInfo(owner="test-owner", name="test-repo")
    github = FakeGitHub(repo_info=repo_info)
    ctx = ErkContext.for_test(repo_root=tmp_path, github=github, repo_info=repo_info)

    learn_dir = tmp_path / ".erk" / "scratch" / "learn-123"
    learn_dir.mkdir(parents=True)

    mock_subprocess_results = [
        # get-learn-sessions - returns one local session
        MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
                    "success": True,
                    "planning_session_id": "planning-session-1",
                    "session_sources": [
                        {
                            "source_type": "local",
                            "session_id": "planning-session-1",
                            "path": "/fake/path.jsonl",
                            "run_id": None,
                            "gist_url": None,
                        }
                    ],
                }
            ),
            stderr="",
        ),
        # preprocess-session fails with non-zero exit code
        MagicMock(returncode=1, stdout="", stderr="Session file not found"),
    ]

    with patch("subprocess.run", side_effect=mock_subprocess_results):
        result = runner.invoke(trigger_async_learn_command, ["123"], obj=ctx)

    assert result.exit_code == 1
    output = _parse_json_output(result.output)
    assert output["success"] is False
    assert "failed" in str(output["error"]).lower()


# ============================================================================
# Diagnostic Output Tests (Layer 4: Business Logic over Fakes)
# ============================================================================


def test_trigger_async_learn_logs_session_source_summary(tmp_path: Path) -> None:
    """Test that session source summary is logged to stderr after get-learn-sessions."""
    runner = CliRunner()
    repo_info = RepoInfo(owner="test-owner", name="test-repo")
    github = FakeGitHub(repo_info=repo_info)
    ctx = ErkContext.for_test(repo_root=tmp_path, github=github, repo_info=repo_info)

    learn_dir = tmp_path / ".erk" / "scratch" / "learn-123"
    learn_dir.mkdir(parents=True)

    mock_subprocess_results = [
        # get-learn-sessions - returns two sessions (1 planning, 1 impl)
        MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
                    "success": True,
                    "planning_session_id": "plan-sess-1",
                    "session_sources": [
                        {
                            "source_type": "local",
                            "session_id": "plan-sess-1",
                            "path": "/fake/planning.jsonl",
                            "run_id": None,
                            "gist_url": None,
                        },
                        {
                            "source_type": "local",
                            "session_id": "impl-sess-2",
                            "path": "/fake/impl.jsonl",
                            "run_id": None,
                            "gist_url": None,
                        },
                    ],
                }
            ),
            stderr="",
        ),
        # preprocess-session (planning)
        MagicMock(returncode=0, stdout="", stderr=""),
        # preprocess-session (impl)
        MagicMock(returncode=0, stdout="", stderr=""),
        # get-pr-for-plan (no PR)
        MagicMock(
            returncode=0,
            stdout=json.dumps({"success": False}),
            stderr="",
        ),
        # upload-learn-materials
        MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
                    "success": True,
                    "gist_url": "https://gist.github.com/user/abc",
                    "file_count": 0,
                    "total_size": 0,
                }
            ),
            stderr="",
        ),
    ]

    with patch("subprocess.run", side_effect=mock_subprocess_results):
        result = runner.invoke(trigger_async_learn_command, ["123"], obj=ctx)

    assert result.exit_code == 0
    stderr_lines = _get_stderr_lines(result.output)

    # Check session source summary line
    summary_lines = [line for line in stderr_lines if "Found 2 session source(s)" in line]
    assert len(summary_lines) == 1
    assert "1 planning" in summary_lines[0]
    assert "1 impl" in summary_lines[0]

    # Check individual session lines
    planning_lines = [line for line in stderr_lines if "planning: plan-sess-1" in line]
    assert len(planning_lines) == 1
    assert "(local)" in planning_lines[0]

    impl_lines = [line for line in stderr_lines if "impl: impl-sess-2" in line]
    assert len(impl_lines) == 1
    assert "(local)" in impl_lines[0]


def test_trigger_async_learn_forwards_preprocess_stderr(tmp_path: Path) -> None:
    """Test that stderr from preprocess-session is forwarded with prefix."""
    runner = CliRunner()
    repo_info = RepoInfo(owner="test-owner", name="test-repo")
    github = FakeGitHub(repo_info=repo_info)
    ctx = ErkContext.for_test(repo_root=tmp_path, github=github, repo_info=repo_info)

    learn_dir = tmp_path / ".erk" / "scratch" / "learn-123"
    learn_dir.mkdir(parents=True)

    preprocess_stderr = (
        "📉 Token reduction: 50,000 → 20,000 (60% reduction)\n📊 Compression ratio: 2.5x"
    )

    mock_subprocess_results = [
        # get-learn-sessions
        MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
                    "success": True,
                    "planning_session_id": "plan-sess-1",
                    "session_sources": [
                        {
                            "source_type": "local",
                            "session_id": "plan-sess-1",
                            "path": "/fake/planning.jsonl",
                            "run_id": None,
                            "gist_url": None,
                        },
                    ],
                }
            ),
            stderr="",
        ),
        # preprocess-session with stderr diagnostics
        MagicMock(returncode=0, stdout="", stderr=preprocess_stderr),
        # get-pr-for-plan (no PR)
        MagicMock(
            returncode=0,
            stdout=json.dumps({"success": False}),
            stderr="",
        ),
        # upload-learn-materials
        MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
                    "success": True,
                    "gist_url": "https://gist.github.com/user/abc",
                    "file_count": 0,
                    "total_size": 0,
                }
            ),
            stderr="",
        ),
    ]

    with patch("subprocess.run", side_effect=mock_subprocess_results):
        result = runner.invoke(trigger_async_learn_command, ["123"], obj=ctx)

    assert result.exit_code == 0
    stderr_lines = _get_stderr_lines(result.output)

    # Forwarded preprocess stderr lines should appear with prefix
    token_lines = [line for line in stderr_lines if "Token reduction" in line]
    assert len(token_lines) == 1

    compression_lines = [line for line in stderr_lines if "Compression ratio" in line]
    assert len(compression_lines) == 1


def test_trigger_async_learn_logs_gist_size(tmp_path: Path) -> None:
    """Test that gist creation logs file count and total size."""
    runner = CliRunner()
    repo_info = RepoInfo(owner="test-owner", name="test-repo")
    github = FakeGitHub(repo_info=repo_info)
    ctx = ErkContext.for_test(repo_root=tmp_path, github=github, repo_info=repo_info)

    learn_dir = tmp_path / ".erk" / "scratch" / "learn-123"
    learn_dir.mkdir(parents=True)

    mock_subprocess_results = [
        MagicMock(
            returncode=0,
            stdout=json.dumps({"success": True, "session_sources": []}),
            stderr="",
        ),
        MagicMock(
            returncode=0,
            stdout=json.dumps({"success": False}),
            stderr="",
        ),
        MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
                    "success": True,
                    "gist_url": "https://gist.github.com/user/xyz",
                    "file_count": 3,
                    "total_size": 42891,
                }
            ),
            stderr="",
        ),
    ]

    with patch("subprocess.run", side_effect=mock_subprocess_results):
        result = runner.invoke(trigger_async_learn_command, ["123"], obj=ctx)

    assert result.exit_code == 0
    stderr_lines = _get_stderr_lines(result.output)

    gist_lines = [line for line in stderr_lines if "Gist created:" in line]
    assert len(gist_lines) == 1
    assert "3 file(s)" in gist_lines[0]
    assert "42,891 chars" in gist_lines[0]


def test_trigger_async_learn_logs_output_file_sizes(tmp_path: Path) -> None:
    """Test that preprocessed output file sizes are logged."""
    runner = CliRunner()
    repo_info = RepoInfo(owner="test-owner", name="test-repo")
    github = FakeGitHub(repo_info=repo_info)
    ctx = ErkContext.for_test(repo_root=tmp_path, github=github, repo_info=repo_info)

    learn_dir = tmp_path / ".erk" / "scratch" / "learn-123"
    learn_dir.mkdir(parents=True)

    # Create the output file that preprocess would produce
    output_file = learn_dir / "planning-abc123.xml"
    output_file.write_text("<session>test content here</session>", encoding="utf-8")

    mock_subprocess_results = [
        # get-learn-sessions
        MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
                    "success": True,
                    "planning_session_id": "plan-sess-1",
                    "session_sources": [
                        {
                            "source_type": "local",
                            "session_id": "plan-sess-1",
                            "path": "/fake/planning.jsonl",
                            "run_id": None,
                            "gist_url": None,
                        },
                    ],
                }
            ),
            stderr="",
        ),
        # preprocess-session outputs the file path
        MagicMock(returncode=0, stdout=str(output_file) + "\n", stderr=""),
        # get-pr-for-plan (no PR)
        MagicMock(
            returncode=0,
            stdout=json.dumps({"success": False}),
            stderr="",
        ),
        # upload-learn-materials
        MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
                    "success": True,
                    "gist_url": "https://gist.github.com/user/abc",
                    "file_count": 1,
                    "total_size": 100,
                }
            ),
            stderr="",
        ),
    ]

    with patch("subprocess.run", side_effect=mock_subprocess_results):
        result = runner.invoke(trigger_async_learn_command, ["123"], obj=ctx)

    assert result.exit_code == 0
    stderr_lines = _get_stderr_lines(result.output)

    output_lines = [line for line in stderr_lines if "Output: planning-abc123.xml" in line]
    assert len(output_lines) == 1
    assert "chars)" in output_lines[0]
