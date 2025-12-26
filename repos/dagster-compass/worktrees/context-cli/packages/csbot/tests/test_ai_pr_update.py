"""Tests for AI PR update functionality."""

import subprocess
import sys
from unittest.mock import Mock, call, patch

import pytest

from csbot.compass_dev.ai_pr_update import (
    PRUpdateError,
    generate_pr_summary,
    get_current_branch_changes,
    get_previous_branch,
    main,
    run_command,
    update_pr_and_commit,
)


class TestRunCommand:
    """Tests for the run_command function."""

    @patch("subprocess.run")
    def test_run_command_success(self, mock_run):
        """Test successful command execution."""
        mock_result = Mock()
        mock_result.stdout = "command output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = run_command(["git", "status"], capture_output=True)

        mock_run.assert_called_once_with(
            ["git", "status"], capture_output=True, text=True, check=True
        )
        assert result == mock_result

    @patch("subprocess.run")
    def test_run_command_called_process_error(self, mock_run):
        """Test handling of CalledProcessError."""
        error = subprocess.CalledProcessError(1, ["git", "status"])
        error.stderr = "git error"
        mock_run.side_effect = error

        with pytest.raises(PRUpdateError, match="Command failed: git status"):
            run_command(["git", "status"], capture_output=True)

    @patch("subprocess.run")
    def test_run_command_file_not_found(self, mock_run):
        """Test handling of FileNotFoundError."""
        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(PRUpdateError, match="Command not found: git"):
            run_command(["git", "status"], capture_output=True)

    @patch("subprocess.run")
    def test_run_command_no_capture_output(self, mock_run):
        """Test command execution without capturing output."""
        mock_result = Mock()
        mock_run.return_value = mock_result

        result = run_command(["git", "status"], capture_output=False)

        mock_run.assert_called_once_with(
            ["git", "status"], capture_output=False, text=True, check=True
        )
        assert result == mock_result


class TestGetPreviousBranch:
    """Tests for the get_previous_branch function."""

    @patch("csbot.compass_dev.ai_pr_update.run_command")
    def test_get_previous_branch_success(self, mock_run_command):
        """Test successful identification of previous branch."""
        mock_result = Mock()
        mock_result.stdout = """◉  feature/current-branch
◯  feature/previous-branch
◯  master"""
        mock_run_command.return_value = mock_result

        result = get_previous_branch()

        mock_run_command.assert_called_once_with(["gt", "ls", "-s"], capture_output=True)
        assert result == "feature/previous-branch"

    @patch("csbot.compass_dev.ai_pr_update.run_command")
    def test_get_previous_branch_with_spacing(self, mock_run_command):
        """Test parsing with different spacing."""
        mock_result = Mock()
        mock_result.stdout = """  ◉    feature/current-branch
  ◯    feature/other-branch
  ◯    master"""
        mock_run_command.return_value = mock_result

        result = get_previous_branch()

        assert result == "feature/other-branch"

    @patch("csbot.compass_dev.ai_pr_update.run_command")
    def test_get_previous_branch_no_current_branch(self, mock_run_command):
        """Test error when no current branch is found."""
        mock_result = Mock()
        mock_result.stdout = """◯  feature/branch1
◯  feature/branch2
◯  master"""
        mock_run_command.return_value = mock_result

        with pytest.raises(PRUpdateError, match="Could not identify previous branch"):
            get_previous_branch()

    @patch("csbot.compass_dev.ai_pr_update.run_command")
    def test_get_previous_branch_no_previous_branch(self, mock_run_command):
        """Test error when no previous branch is found after current."""
        mock_result = Mock()
        mock_result.stdout = """◉  feature/current-branch"""
        mock_run_command.return_value = mock_result

        with pytest.raises(PRUpdateError, match="Could not identify previous branch"):
            get_previous_branch()

    @patch("csbot.compass_dev.ai_pr_update.run_command")
    def test_get_previous_branch_empty_output(self, mock_run_command):
        """Test error handling with empty gt output."""
        mock_result = Mock()
        mock_result.stdout = ""
        mock_run_command.return_value = mock_result

        with pytest.raises(PRUpdateError, match="Could not identify previous branch"):
            get_previous_branch()


class TestGetCurrentBranchChanges:
    """Tests for the get_current_branch_changes function."""

    @patch("csbot.compass_dev.ai_pr_update.run_command")
    def test_get_current_branch_changes_success(self, mock_run_command):
        """Test successful retrieval of branch changes."""
        diff_result = Mock()
        diff_result.stdout = "diff --git a/file.py b/file.py\n+new line"
        log_result = Mock()
        log_result.stdout = "abc123 Add new feature\ndef456 Fix bug"

        mock_run_command.side_effect = [diff_result, log_result]

        diff_output, commit_log = get_current_branch_changes("feature/previous")

        expected_calls = [
            call(["git", "diff", "feature/previous..HEAD"], capture_output=True),
            call(["git", "log", "--oneline", "feature/previous..HEAD"], capture_output=True),
        ]
        mock_run_command.assert_has_calls(expected_calls)
        assert diff_output == "diff --git a/file.py b/file.py\n+new line"
        assert commit_log == "abc123 Add new feature\ndef456 Fix bug"


class TestGeneratePRSummary:
    """Tests for the generate_pr_summary function."""

    def test_generate_pr_summary_single_file(self):
        """Test PR summary generation for single file changes."""
        diff_output = """diff --git a/test.py b/test.py
index 1234567..abcdefg 100644
--- a/test.py
+++ b/test.py
@@ -1,3 +1,4 @@
 def hello():
+    # New comment
     pass
     return "world\""""
        commit_log = "abc123 Add comment to function"

        result = generate_pr_summary(diff_output, commit_log)

        assert "Updates `test.py`" in result
        assert "(1 additions)" in result
        assert "## Summary & Motivation" in result
        assert "## How I Tested These Changes" in result
        assert "## Changelog" in result

    def test_generate_pr_summary_multiple_files(self):
        """Test PR summary generation for multiple file changes."""
        diff_output = """diff --git a/file1.py b/file1.py
index 1234567..abcdefg 100644
--- a/file1.py
+++ b/file1.py
@@ -1,2 +1,3 @@
 def test():
+    pass
-    old_line
diff --git a/file2.py b/file2.py
index 1234567..abcdefg 100644
--- a/file2.py
+++ b/file2.py
@@ -1,2 +1,3 @@
 def another():
+    new_line"""
        commit_log = "abc123 Update multiple files"

        result = generate_pr_summary(diff_output, commit_log)

        assert "Updates 2 files" in result
        assert "(2 additions, 1 deletions)" in result

    def test_generate_pr_summary_with_function_definition(self):
        """Test PR summary generation with new function definition."""
        diff_output = """diff --git a/module.py b/module.py
index 1234567..abcdefg 100644
--- a/module.py
+++ b/module.py
@@ -1,2 +1,4 @@
 import os
+def new_function(param: str) -> str:
+    return param.upper()"""
        commit_log = "abc123 Add new function"

        result = generate_pr_summary(diff_output, commit_log)

        assert "Updates `module.py`" in result
        assert "```python" in result
        assert "def new_function(param: str) -> str:" in result

    def test_generate_pr_summary_no_changes(self):
        """Test PR summary generation with no changes."""
        diff_output = ""
        commit_log = "abc123 Empty commit"

        result = generate_pr_summary(diff_output, commit_log)

        assert "Minor changes" in result
        assert "## Summary & Motivation" in result

    def test_generate_pr_summary_deletions_only(self):
        """Test PR summary generation with only deletions."""
        diff_output = """diff --git a/test.py b/test.py
index 1234567..abcdefg 100644
--- a/test.py
+++ b/test.py
@@ -1,3 +1,1 @@
 def hello():
-    old_line
-    another_old_line"""
        commit_log = "abc123 Remove old code"

        result = generate_pr_summary(diff_output, commit_log)

        assert "Updates `test.py`" in result
        assert "(2 deletions)" in result


class TestUpdatePRAndCommit:
    """Tests for the update_pr_and_commit function."""

    @patch("csbot.compass_dev.ai_pr_update.run_command")
    def test_update_pr_and_commit_success(self, mock_run_command):
        """Test successful PR and commit update."""
        # Mock successful PR view
        pr_view_result = Mock()
        pr_view_result.stdout = "#123 Current PR"
        mock_run_command.return_value = pr_view_result

        pr_summary = """## Summary & Motivation

Updates test.py with new functionality.

## How I Tested These Changes

Unit tests added.

## Changelog

Added new public API method."""

        with patch("builtins.print") as mock_print:
            update_pr_and_commit(pr_summary)

        # Verify all commands were called
        expected_calls = [
            call(["gh", "pr", "view"], capture_output=True),
            call(
                ["gh", "pr", "edit", "--title", "Updates test.py with new functionality"],
                capture_output=False,
            ),
            call(["gh", "pr", "edit", "--body", pr_summary], capture_output=False),
            call(
                [
                    "git",
                    "commit",
                    "--amend",
                    "-m",
                    f"Updates test.py with new functionality\n\n{pr_summary}",
                ],
                capture_output=False,
            ),
        ]
        mock_run_command.assert_has_calls(expected_calls)

        # Verify success messages were printed
        mock_print.assert_has_calls(
            [
                call("✅ Updated PR title: Updates test.py with new functionality"),
                call("✅ Updated PR description"),
                call("✅ Updated commit message"),
            ]
        )

    @patch("csbot.compass_dev.ai_pr_update.run_command")
    def test_update_pr_and_commit_no_pr(self, mock_run_command):
        """Test error when no PR exists."""
        mock_run_command.side_effect = PRUpdateError("No PR found")

        pr_summary = "## Summary\nTest summary"

        with pytest.raises(PRUpdateError, match="No PR found for current branch"):
            update_pr_and_commit(pr_summary)

    @patch("csbot.compass_dev.ai_pr_update.run_command")
    def test_update_pr_and_commit_long_title(self, mock_run_command):
        """Test title truncation for very long summaries."""
        pr_view_result = Mock()
        mock_run_command.return_value = pr_view_result

        long_line = (
            "This is a very long summary line that exceeds the 72 character limit "
            "for PR titles and should be truncated appropriately"
        )
        pr_summary = f"""## Summary & Motivation

{long_line}.

## How I Tested These Changes

Tests."""

        update_pr_and_commit(pr_summary)

        # Check that title was truncated
        title_call = mock_run_command.call_args_list[1]  # Second call should be title edit
        # The call should be ["gh", "pr", "edit", "--title", "truncated_title"]
        assert title_call[0][0][0] == "gh"
        assert title_call[0][0][1] == "pr"
        assert title_call[0][0][2] == "edit"
        assert title_call[0][0][3] == "--title"
        title = title_call[0][0][4]  # The actual title
        assert len(title) <= 72
        assert title.endswith("...")

    @patch("csbot.compass_dev.ai_pr_update.run_command")
    def test_update_pr_and_commit_no_content_line(self, mock_run_command):
        """Test fallback title when no content line is found."""
        pr_view_result = Mock()
        mock_run_command.return_value = pr_view_result

        pr_summary = """## Summary & Motivation

## How I Tested These Changes

Tests."""

        update_pr_and_commit(pr_summary)

        # Check that fallback title was used
        title_call = mock_run_command.call_args_list[1]
        title = title_call[0][0][4]  # Fifth argument of the title edit call
        assert title == "Tests"  # Content comes from "Tests." line


class TestMain:
    """Tests for the main function."""

    @patch("csbot.compass_dev.ai_pr_update.update_pr_and_commit")
    @patch("csbot.compass_dev.ai_pr_update.generate_pr_summary")
    @patch("csbot.compass_dev.ai_pr_update.get_current_branch_changes")
    @patch("csbot.compass_dev.ai_pr_update.get_previous_branch")
    def test_main_success(
        self,
        mock_get_previous_branch,
        mock_get_current_branch_changes,
        mock_generate_pr_summary,
        mock_update_pr_and_commit,
    ):
        """Test successful execution of main function."""
        mock_get_previous_branch.return_value = "feature/prev"
        mock_get_current_branch_changes.return_value = ("diff content", "commit1\ncommit2")
        mock_generate_pr_summary.return_value = "PR summary"

        with patch("builtins.print") as mock_print:
            main()

        # Verify all functions were called
        mock_get_previous_branch.assert_called_once()
        mock_get_current_branch_changes.assert_called_once_with("feature/prev")
        mock_generate_pr_summary.assert_called_once_with("diff content", "commit1\ncommit2")
        mock_update_pr_and_commit.assert_called_once_with("PR summary")

        # Verify progress messages
        mock_print.assert_any_call("🔍 Step 1: Identifying previous branch...")
        mock_print.assert_any_call("   Previous branch: feature/prev")
        mock_print.assert_any_call("📊 Step 2: Getting changes for current branch...")
        mock_print.assert_any_call("   Found 2 commit(s) in current branch")
        mock_print.assert_any_call("✍️  Step 3: Generating and updating PR summary...")
        mock_print.assert_any_call("🎉 PR update completed successfully!")

    @patch("csbot.compass_dev.ai_pr_update.get_previous_branch")
    def test_main_pr_update_error(self, mock_get_previous_branch):
        """Test main function handling PRUpdateError."""
        mock_get_previous_branch.side_effect = PRUpdateError("Test error")

        with patch("builtins.print") as mock_print, patch("sys.exit") as mock_exit:
            main()

        mock_print.assert_any_call("❌ Error: Test error", file=sys.stderr)
        mock_exit.assert_called_once_with(1)

    @patch("csbot.compass_dev.ai_pr_update.get_previous_branch")
    def test_main_keyboard_interrupt(self, mock_get_previous_branch):
        """Test main function handling KeyboardInterrupt."""
        mock_get_previous_branch.side_effect = KeyboardInterrupt()

        with patch("builtins.print") as mock_print, patch("sys.exit") as mock_exit:
            main()

        mock_print.assert_any_call("\n❌ Cancelled by user", file=sys.stderr)
        mock_exit.assert_called_once_with(1)

    @patch("csbot.compass_dev.ai_pr_update.update_pr_and_commit")
    @patch("csbot.compass_dev.ai_pr_update.generate_pr_summary")
    @patch("csbot.compass_dev.ai_pr_update.get_current_branch_changes")
    @patch("csbot.compass_dev.ai_pr_update.get_previous_branch")
    def test_main_many_commits_warning(
        self,
        mock_get_previous_branch,
        mock_get_current_branch_changes,
        mock_generate_pr_summary,
        mock_update_pr_and_commit,
    ):
        """Test warning message for many commits."""
        mock_get_previous_branch.return_value = "feature/prev"
        # Create commit log with more than 5 commits
        mock_get_current_branch_changes.return_value = (
            "diff content",
            "\n".join([f"commit{i} Message {i}" for i in range(1, 8)]),
        )
        mock_generate_pr_summary.return_value = "PR summary"

        with patch("builtins.print") as mock_print:
            main()

        # Check that warning was printed
        mock_print.assert_any_call(
            "⚠️  Warning: Found 7 commits. "
            "Double-check that 'feature/prev' is the correct previous branch."
        )
