"""Tests for run-review exec command.

Tests focus on file loading, prompt assembly, and gateway integration.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.run_review import run_review
from erk_shared.context.context import ErkContext
from erk_shared.core.fakes import FakeClaudeExecutor
from erk_shared.gateway.git.fake import FakeGit


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
        reviews_dir = tmp_path / ".claude" / "reviews"
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
        reviews_dir = tmp_path / ".claude" / "reviews"
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
        reviews_dir = tmp_path / ".claude" / "reviews"
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


class TestRunReviewExecution:
    """Tests for run-review execution mode (non-dry-run)."""

    def test_executes_claude_via_gateway(self, tmp_path: Path) -> None:
        """Non-dry-run mode executes Claude via ClaudeExecutor gateway."""
        reviews_dir = tmp_path / ".claude" / "reviews"
        reviews_dir.mkdir(parents=True)

        (reviews_dir / "test.md").write_text(
            """\
---
name: Test Review
paths:
  - "**/*.py"
marker: "<!-- test-review -->"
model: sonnet
allowed_tools: Read,Bash,Grep
---

Check for issues in the code.
""",
            encoding="utf-8",
        )

        fake_executor = FakeClaudeExecutor(passthrough_exit_code=0)

        runner = CliRunner()
        result = runner.invoke(
            run_review,
            ["--name", "test", "--pr-number", "123"],
            obj=ErkContext.for_test(cwd=tmp_path, claude_executor=fake_executor),
        )

        assert result.exit_code == 0
        assert len(fake_executor.passthrough_calls) == 1
        call = fake_executor.passthrough_calls[0]
        assert "PR NUMBER: 123" in call.prompt
        assert call.model == "sonnet"
        assert call.tools == ["Read", "Bash", "Grep"]
        assert call.cwd == tmp_path
        assert call.dangerous is True

    def test_propagates_claude_exit_code(self, tmp_path: Path) -> None:
        """Exit code from Claude is propagated."""
        reviews_dir = tmp_path / ".claude" / "reviews"
        reviews_dir.mkdir(parents=True)

        (reviews_dir / "test.md").write_text(
            """\
---
name: Test Review
paths:
  - "**/*.py"
marker: "<!-- test-review -->"
---

Check for issues.
""",
            encoding="utf-8",
        )

        fake_executor = FakeClaudeExecutor(passthrough_exit_code=42)

        runner = CliRunner()
        result = runner.invoke(
            run_review,
            ["--name", "test", "--pr-number", "123"],
            obj=ErkContext.for_test(cwd=tmp_path, claude_executor=fake_executor),
        )

        assert result.exit_code == 42

    def test_uses_default_allowed_tools(self, tmp_path: Path) -> None:
        """Uses default allowed_tools when not explicitly specified."""
        reviews_dir = tmp_path / ".claude" / "reviews"
        reviews_dir.mkdir(parents=True)

        (reviews_dir / "test.md").write_text(
            """\
---
name: Simple Review
paths:
  - "**/*.py"
marker: "<!-- simple -->"
---

Simple check.
""",
            encoding="utf-8",
        )

        fake_executor = FakeClaudeExecutor()

        runner = CliRunner()
        result = runner.invoke(
            run_review,
            ["--name", "test", "--pr-number", "456"],
            obj=ErkContext.for_test(cwd=tmp_path, claude_executor=fake_executor),
        )

        assert result.exit_code == 0
        assert len(fake_executor.passthrough_calls) == 1
        call = fake_executor.passthrough_calls[0]
        # Default allowed_tools is parsed from DEFAULT_ALLOWED_TOOLS constant
        assert call.tools is not None
        assert "Bash(gh:*)" in call.tools
        assert "Read(*)" in call.tools


class TestRunReviewLocalMode:
    """Tests for run-review local mode (--local)."""

    def test_local_mode_outputs_prompt(self, tmp_path: Path) -> None:
        """Local mode outputs prompt with git diff commands."""
        reviews_dir = tmp_path / ".claude" / "reviews"
        _create_review_file(
            reviews_dir,
            name="test",
            review_name="Test Review",
            marker="<!-- test-review -->",
            body="Check for issues.",
        )

        # Use FakeGit to return "main" for trunk detection
        fake_git = FakeGit(trunk_branches=["main"])

        runner = CliRunner()
        result = runner.invoke(
            run_review,
            ["--name", "test", "--local", "--dry-run"],
            obj=ErkContext.for_test(cwd=tmp_path, git=fake_git),
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

    def test_local_mode_with_base_branch(self, tmp_path: Path) -> None:
        """Local mode uses specified base branch."""
        reviews_dir = tmp_path / ".claude" / "reviews"
        _create_review_file(
            reviews_dir,
            name="test",
            review_name="Test Review",
            marker="<!-- test -->",
            body="Body.",
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


class TestRunReviewFlagValidation:
    """Tests for flag validation."""

    def test_mutual_exclusion_pr_and_local(self, tmp_path: Path) -> None:
        """Error when both --pr-number and --local specified."""
        reviews_dir = tmp_path / ".claude" / "reviews"
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
        reviews_dir = tmp_path / ".claude" / "reviews"
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
        reviews_dir = tmp_path / ".claude" / "reviews"
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
