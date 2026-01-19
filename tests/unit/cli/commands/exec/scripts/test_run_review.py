"""Tests for run-review exec command.

Tests focus on file loading and prompt assembly, not subprocess calls.
"""

import json
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from erk.cli.commands.exec.scripts.run_review import run_review
from erk_shared.context.context import ErkContext


def _create_review_file(
    reviews_dir: Path,
    *,
    name: str,
    review_name: str,
    marker: str,
    body: str,
) -> None:
    """Create a review file in the reviews directory."""
    reviews_dir.mkdir(parents=True, exist_ok=True)
    (reviews_dir / f"{name}.md").write_text(
        f"""\
---
name: {review_name}
paths:
  - "**/*.py"
marker: "{marker}"
---

{body}
""",
        encoding="utf-8",
    )


class TestRunReviewPrMode:
    """Tests for run-review PR mode (--pr-number)."""

    def test_dry_run_outputs_prompt(self, tmp_path: Path) -> None:
        """Dry run mode outputs assembled prompt without running Claude."""
        # Create review file
        reviews_dir = tmp_path / ".github" / "reviews"
        reviews_dir.mkdir(parents=True)

        (reviews_dir / "test.md").write_text(
            """\
---
name: Test Review
paths:
  - "**/*.py"
marker: "<!-- test-review -->"
---

Check for issues in the code.
""",
            encoding="utf-8",
        )

        runner = CliRunner()
        result = runner.invoke(
            run_review,
            ["--name", "test", "--pr-number", "123", "--dry-run"],
            obj=ErkContext.for_test(cwd=tmp_path),
        )

        assert result.exit_code == 0
        # Should contain key prompt elements
        assert "PR NUMBER: 123" in result.output
        assert "Test Review: Review code changes." in result.output
        assert "Check for issues in the code." in result.output
        assert "<!-- test-review -->" in result.output
        assert "gh pr diff 123" in result.output

    def test_dry_run_nonexistent_review(self, tmp_path: Path) -> None:
        """Error when review file doesn't exist."""
        reviews_dir = tmp_path / ".github" / "reviews"
        reviews_dir.mkdir(parents=True)

        runner = CliRunner()
        result = runner.invoke(
            run_review,
            ["--name", "nonexistent", "--pr-number", "123", "--dry-run"],
            obj=ErkContext.for_test(cwd=tmp_path),
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error_type"] == "validation_failed"

    def test_dry_run_invalid_review(self, tmp_path: Path) -> None:
        """Error when review file has invalid frontmatter."""
        reviews_dir = tmp_path / ".github" / "reviews"
        reviews_dir.mkdir(parents=True)

        (reviews_dir / "invalid.md").write_text(
            """\
---
name: Invalid
# Missing required fields
---

Body.
""",
            encoding="utf-8",
        )

        runner = CliRunner()
        result = runner.invoke(
            run_review,
            ["--name", "invalid", "--pr-number", "123", "--dry-run"],
            obj=ErkContext.for_test(cwd=tmp_path),
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error_type"] == "validation_failed"

    def test_dry_run_custom_reviews_dir(self, tmp_path: Path) -> None:
        """Use custom reviews directory."""
        custom_dir = tmp_path / "custom" / "reviews"
        custom_dir.mkdir(parents=True)

        (custom_dir / "test.md").write_text(
            """\
---
name: Custom Test
paths:
  - "**/*.py"
marker: "<!-- custom -->"
---

Custom body.
""",
            encoding="utf-8",
        )

        runner = CliRunner()
        result = runner.invoke(
            run_review,
            [
                "--name",
                "test",
                "--pr-number",
                "456",
                "--reviews-dir",
                "custom/reviews",
                "--dry-run",
            ],
            obj=ErkContext.for_test(cwd=tmp_path),
        )

        assert result.exit_code == 0
        assert "PR NUMBER: 456" in result.output
        assert "Custom Test: Review code changes." in result.output


class TestRunReviewLocalMode:
    """Tests for run-review local mode (--local)."""

    def test_local_mode_outputs_prompt(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Local mode outputs prompt with git diff commands."""
        reviews_dir = tmp_path / ".github" / "reviews"
        _create_review_file(
            reviews_dir,
            name="test",
            review_name="Test Review",
            marker="<!-- test-review -->",
            body="Check for issues.",
        )

        # Mock subprocess to return "main" for trunk detection
        def mock_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            cmd = args[0] if args else kwargs.get("args", [])
            if isinstance(cmd, list) and "refs/heads/main" in cmd:
                return subprocess.CompletedProcess(cmd, 0, "", "")
            return subprocess.CompletedProcess(cmd, 1, "", "")

        monkeypatch.setattr(subprocess, "run", mock_run)

        runner = CliRunner()
        result = runner.invoke(
            run_review,
            ["--name", "test", "--local", "--dry-run"],
            obj=ErkContext.for_test(cwd=tmp_path),
        )

        assert result.exit_code == 0
        # Should contain local mode elements
        assert "BASE BRANCH: main" in result.output
        assert "Test Review: Review local code changes" in result.output
        assert "Check for issues." in result.output
        assert "git diff --name-only $(git merge-base main HEAD)...HEAD" in result.output
        # Should NOT contain PR mode elements
        assert "PR NUMBER:" not in result.output
        assert "gh pr diff" not in result.output

    def test_local_mode_with_base_branch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Local mode uses specified base branch."""
        reviews_dir = tmp_path / ".github" / "reviews"
        _create_review_file(
            reviews_dir,
            name="test",
            review_name="Test Review",
            marker="<!-- test -->",
            body="Body.",
        )

        # Mock subprocess (not needed when --base is specified, but include for safety)
        def mock_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(args[0] if args else [], 1, "", "")

        monkeypatch.setattr(subprocess, "run", mock_run)

        runner = CliRunner()
        result = runner.invoke(
            run_review,
            ["--name", "test", "--local", "--base", "develop", "--dry-run"],
            obj=ErkContext.for_test(cwd=tmp_path),
        )

        assert result.exit_code == 0
        assert "BASE BRANCH: develop" in result.output
        assert "git merge-base develop HEAD" in result.output


class TestRunReviewFlagValidation:
    """Tests for flag validation."""

    def test_mutual_exclusion_pr_and_local(self, tmp_path: Path) -> None:
        """Error when both --pr-number and --local specified."""
        reviews_dir = tmp_path / ".github" / "reviews"
        _create_review_file(
            reviews_dir,
            name="test",
            review_name="Test",
            marker="<!-- test -->",
            body="Body.",
        )

        runner = CliRunner()
        result = runner.invoke(
            run_review,
            ["--name", "test", "--pr-number", "123", "--local", "--dry-run"],
            obj=ErkContext.for_test(cwd=tmp_path),
        )

        assert result.exit_code == 2
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error_type"] == "invalid_flags"
        assert "Cannot specify both" in data["message"]

    def test_requires_mode_flag(self, tmp_path: Path) -> None:
        """Error when neither --pr-number nor --local specified."""
        reviews_dir = tmp_path / ".github" / "reviews"
        _create_review_file(
            reviews_dir,
            name="test",
            review_name="Test",
            marker="<!-- test -->",
            body="Body.",
        )

        runner = CliRunner()
        result = runner.invoke(
            run_review,
            ["--name", "test", "--dry-run"],
            obj=ErkContext.for_test(cwd=tmp_path),
        )

        assert result.exit_code == 2
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error_type"] == "invalid_flags"
        assert "Must specify either" in data["message"]

    def test_base_requires_local(self, tmp_path: Path) -> None:
        """Error when --base used without --local."""
        reviews_dir = tmp_path / ".github" / "reviews"
        _create_review_file(
            reviews_dir,
            name="test",
            review_name="Test",
            marker="<!-- test -->",
            body="Body.",
        )

        runner = CliRunner()
        result = runner.invoke(
            run_review,
            ["--name", "test", "--pr-number", "123", "--base", "main", "--dry-run"],
            obj=ErkContext.for_test(cwd=tmp_path),
        )

        assert result.exit_code == 2
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error_type"] == "invalid_flags"
        assert "--base can only be used with --local" in data["message"]
