"""Tests for run-review exec command.

Tests focus on file loading and prompt assembly, not subprocess calls.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.run_review import run_review
from erk_shared.context.context import ErkContext


class TestRunReviewDryRun:
    """Tests for run-review --dry-run mode."""

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
    """Tests for run-review --local mode."""

    def test_local_mode_outputs_prompt(self, tmp_path: Path) -> None:
        """Local mode outputs assembled prompt with git diff commands."""
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
            ["--name", "test", "--local", "--dry-run"],
            obj=ErkContext.for_test(cwd=tmp_path),
        )

        assert result.exit_code == 0
        # Should contain local mode elements
        assert "BASE BRANCH:" in result.output
        assert "Test Review: Review code changes." in result.output
        assert "Check for issues in the code." in result.output
        assert "git diff --name-only" in result.output
        assert "git merge-base" in result.output
        # Should NOT contain PR mode elements
        assert "PR NUMBER:" not in result.output
        assert "gh pr diff" not in result.output

    def test_local_mode_with_base_branch(self, tmp_path: Path) -> None:
        """Local mode uses custom base branch when specified."""
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

Body.
""",
            encoding="utf-8",
        )

        runner = CliRunner()
        result = runner.invoke(
            run_review,
            ["--name", "test", "--local", "--base", "develop", "--dry-run"],
            obj=ErkContext.for_test(cwd=tmp_path),
        )

        assert result.exit_code == 0
        assert "BASE BRANCH: develop" in result.output
        assert "git merge-base develop HEAD" in result.output


class TestRunReviewModeValidation:
    """Tests for mode flag validation."""

    def test_mutual_exclusion_pr_and_local(self, tmp_path: Path) -> None:
        """Error when both --pr-number and --local are specified."""
        reviews_dir = tmp_path / ".github" / "reviews"
        reviews_dir.mkdir(parents=True)

        (reviews_dir / "test.md").write_text(
            """\
---
name: Test
paths:
  - "**/*.py"
marker: "<!-- test -->"
---

Body.
""",
            encoding="utf-8",
        )

        runner = CliRunner()
        result = runner.invoke(
            run_review,
            ["--name", "test", "--pr-number", "123", "--local", "--dry-run"],
            obj=ErkContext.for_test(cwd=tmp_path),
        )

        assert result.exit_code == 1
        # Error output goes to stderr, but CliRunner captures both
        output = result.output
        assert "invalid_flags" in output
        assert "Cannot specify both --pr-number and --local" in output

    def test_requires_mode_flag(self, tmp_path: Path) -> None:
        """Error when neither --pr-number nor --local is specified."""
        reviews_dir = tmp_path / ".github" / "reviews"
        reviews_dir.mkdir(parents=True)

        (reviews_dir / "test.md").write_text(
            """\
---
name: Test
paths:
  - "**/*.py"
marker: "<!-- test -->"
---

Body.
""",
            encoding="utf-8",
        )

        runner = CliRunner()
        result = runner.invoke(
            run_review,
            ["--name", "test", "--dry-run"],
            obj=ErkContext.for_test(cwd=tmp_path),
        )

        assert result.exit_code == 1
        output = result.output
        assert "invalid_flags" in output
        assert "Must specify either --pr-number or --local" in output

    def test_base_without_local_errors(self, tmp_path: Path) -> None:
        """Error when --base is used without --local."""
        reviews_dir = tmp_path / ".github" / "reviews"
        reviews_dir.mkdir(parents=True)

        (reviews_dir / "test.md").write_text(
            """\
---
name: Test
paths:
  - "**/*.py"
marker: "<!-- test -->"
---

Body.
""",
            encoding="utf-8",
        )

        runner = CliRunner()
        result = runner.invoke(
            run_review,
            ["--name", "test", "--pr-number", "123", "--base", "develop", "--dry-run"],
            obj=ErkContext.for_test(cwd=tmp_path),
        )

        assert result.exit_code == 1
        output = result.output
        assert "invalid_flags" in output
        assert "--base can only be used with --local" in output
