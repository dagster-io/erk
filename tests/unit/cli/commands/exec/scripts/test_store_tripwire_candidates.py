"""Tests for erk exec store-tripwire-candidates command."""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.store_tripwire_candidates import (
    store_tripwire_candidates,
)
from erk_shared.context.context import ErkContext
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo


def _write_candidates_file(tmp_path: Path, candidates: list[dict[str, str]]) -> Path:
    """Write a candidates JSON file and return its path."""
    json_file = tmp_path / "tripwire-candidates.json"
    json_file.write_text(json.dumps({"candidates": candidates}), encoding="utf-8")
    return json_file


def _make_issue(number: int) -> IssueInfo:
    """Create a minimal issue for testing."""
    now = datetime.now(UTC)
    return IssueInfo(
        number=number,
        title=f"Test issue #{number}",
        body="body",
        state="OPEN",
        url=f"https://github.com/test/repo/issues/{number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="testuser",
    )


def test_store_success(tmp_path: Path) -> None:
    """Successfully store tripwire candidates as a metadata comment."""
    candidates_file = _write_candidates_file(
        tmp_path,
        [
            {
                "action": "calling foo()",
                "warning": "Use bar() instead.",
                "target_doc_path": "architecture/foo.md",
            },
        ],
    )

    fake_issues = FakeGitHubIssues(issues={42: _make_issue(42)})
    ctx = ErkContext.for_test(github_issues=fake_issues, repo_root=tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        store_tripwire_candidates,
        [
            "--issue",
            "42",
            "--candidates-file",
            str(candidates_file),
        ],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["count"] == 1


def test_store_empty_candidates(tmp_path: Path) -> None:
    """Empty candidates list succeeds with count 0 and no comment posted."""
    candidates_file = _write_candidates_file(tmp_path, [])

    fake_issues = FakeGitHubIssues()
    ctx = ErkContext.for_test(github_issues=fake_issues, repo_root=tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        store_tripwire_candidates,
        [
            "--issue",
            "42",
            "--candidates-file",
            str(candidates_file),
        ],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["count"] == 0


def test_store_missing_file(tmp_path: Path) -> None:
    """Return error when candidates file does not exist."""
    ctx = ErkContext.for_test(repo_root=tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        store_tripwire_candidates,
        [
            "--issue",
            "42",
            "--candidates-file",
            str(tmp_path / "nonexistent.json"),
        ],
        obj=ctx,
    )

    assert result.exit_code == 1


def test_store_invalid_json(tmp_path: Path) -> None:
    """Return error when candidates file has invalid JSON."""
    json_file = tmp_path / "bad.json"
    json_file.write_text("not json", encoding="utf-8")

    ctx = ErkContext.for_test(repo_root=tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        store_tripwire_candidates,
        [
            "--issue",
            "42",
            "--candidates-file",
            str(json_file),
        ],
        obj=ctx,
    )

    assert result.exit_code == 1


def test_store_invalid_structure(tmp_path: Path) -> None:
    """Return error when candidates file has invalid structure."""
    json_file = tmp_path / "bad_structure.json"
    json_file.write_text(
        '{"candidates": [{"action": "missing fields"}]}',
        encoding="utf-8",
    )

    ctx = ErkContext.for_test(repo_root=tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        store_tripwire_candidates,
        [
            "--issue",
            "42",
            "--candidates-file",
            str(json_file),
        ],
        obj=ctx,
    )

    assert result.exit_code == 1
