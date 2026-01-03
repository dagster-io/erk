"""Tests for statusline.py GitHub integration."""

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from erk_statusline.statusline import (
    CACHE_TTL_SECONDS,
    GitHubData,
    RepoInfo,
    _categorize_check_buckets,
    _fetch_check_runs,
    _fetch_github_data_rest,
    _fetch_pr_details,
    _fetch_pr_list,
    _get_cache_path,
    _get_cached_pr_info,
    _parse_github_repo_from_remote,
    _set_cached_pr_info,
    build_gh_label,
    build_new_plan_label,
    build_plan_label,
    find_new_plan_file,
    get_checks_status,
    get_issue_number,
    get_plan_progress,
    get_repo_info,
)


class TestCategorizeCheckBuckets:
    """Test check context categorization logic."""

    def test_empty_contexts_returns_empty_string(self) -> None:
        """Empty check contexts should return empty string."""
        result = _categorize_check_buckets([])
        assert result == ""

    def test_checkrun_success_returns_green_check(self) -> None:
        """CheckRun with SUCCESS conclusion should return green check."""
        contexts = [
            {
                "__typename": "CheckRun",
                "conclusion": "SUCCESS",
                "status": "COMPLETED",
                "name": "test",
            }
        ]
        result = _categorize_check_buckets(contexts)
        assert result == "\u2705"

    def test_checkrun_failure_returns_red_x(self) -> None:
        """CheckRun with FAILURE conclusion should return red X."""
        contexts = [
            {
                "__typename": "CheckRun",
                "conclusion": "FAILURE",
                "status": "COMPLETED",
                "name": "test",
            }
        ]
        result = _categorize_check_buckets(contexts)
        assert result == "\U0001f6ab"

    def test_checkrun_in_progress_returns_pending(self) -> None:
        """CheckRun with IN_PROGRESS status should return pending."""
        contexts = [
            {"__typename": "CheckRun", "conclusion": "", "status": "IN_PROGRESS", "name": "test"}
        ]
        result = _categorize_check_buckets(contexts)
        assert result == "\U0001f504"

    def test_statuscontext_success_returns_green_check(self) -> None:
        """StatusContext with SUCCESS state should return green check."""
        contexts = [{"__typename": "StatusContext", "state": "SUCCESS", "context": "test"}]
        result = _categorize_check_buckets(contexts)
        assert result == "\u2705"

    def test_mixed_fail_has_priority_over_pending(self) -> None:
        """Fail state should have priority over pending."""
        contexts = [
            {
                "__typename": "CheckRun",
                "conclusion": "SUCCESS",
                "status": "COMPLETED",
                "name": "test1",
            },
            {"__typename": "CheckRun", "conclusion": "", "status": "IN_PROGRESS", "name": "test2"},
            {
                "__typename": "CheckRun",
                "conclusion": "FAILURE",
                "status": "COMPLETED",
                "name": "test3",
            },
        ]
        result = _categorize_check_buckets(contexts)
        assert result == "\U0001f6ab"


class TestGetRepoInfo:
    """Test GitHubData to RepoInfo conversion."""

    def test_none_input_returns_empty_repo_info(self) -> None:
        """None input should return empty RepoInfo."""
        result = get_repo_info(None)
        assert result == RepoInfo(
            owner="",
            repo="",
            pr_number="",
            pr_url="",
            pr_state="",
            has_conflicts=False,
        )

    def test_draft_pr_returns_draft_state(self) -> None:
        """Draft PR should have pr_state='draft'."""
        github_data = GitHubData(
            owner="testowner",
            repo="testrepo",
            pr_number=123,
            pr_state="OPEN",
            is_draft=True,
            mergeable="MERGEABLE",
            check_contexts=[],
        )
        result = get_repo_info(github_data)
        assert result.pr_state == "draft"
        assert result.pr_number == "123"
        assert result.pr_url == "https://app.graphite.dev/github/pr/testowner/testrepo/123/"
        assert result.has_conflicts is False

    def test_conflicting_mergeable_sets_has_conflicts(self) -> None:
        """Mergeable=CONFLICTING should set has_conflicts=True."""
        github_data = GitHubData(
            owner="testowner",
            repo="testrepo",
            pr_number=111,
            pr_state="OPEN",
            is_draft=False,
            mergeable="CONFLICTING",
            check_contexts=[],
        )
        result = get_repo_info(github_data)
        assert result.has_conflicts is True


class TestGetChecksStatus:
    """Test checks status extraction."""

    def test_none_input_returns_empty_string(self) -> None:
        """None input should return empty string."""
        result = get_checks_status(None)
        assert result == ""

    def test_delegates_to_categorize_check_buckets(self) -> None:
        """Should delegate to _categorize_check_buckets with check_contexts."""
        github_data = GitHubData(
            owner="testowner",
            repo="testrepo",
            pr_number=123,
            pr_state="OPEN",
            is_draft=False,
            mergeable="MERGEABLE",
            check_contexts=[
                {
                    "__typename": "CheckRun",
                    "conclusion": "SUCCESS",
                    "status": "COMPLETED",
                    "name": "test",
                }
            ],
        )
        result = get_checks_status(github_data)
        assert result == "\u2705"


class TestBuildGhLabel:
    """Test GitHub label building."""

    def test_no_pr_returns_wrapped_no_pr_label(self) -> None:
        """When there's no PR, should return (gh:no-pr) wrapped in parentheses."""
        repo_info = RepoInfo(
            owner="testowner",
            repo="testrepo",
            pr_number="",  # No PR
            pr_url="",
            pr_state="",
            has_conflicts=False,
        )
        github_data = None

        result = build_gh_label(repo_info, github_data)

        # Render TokenSeq to text to verify format
        result_text = result.render()
        assert result_text.startswith("(gh:")
        assert "no-pr" in result_text
        assert result_text.endswith(")")

    def test_with_pr_returns_wrapped_pr_number(self) -> None:
        """When there's a PR, should return (gh:#123 ...) wrapped in parentheses."""
        repo_info = RepoInfo(
            owner="testowner",
            repo="testrepo",
            pr_number="123",
            pr_url="https://app.graphite.dev/github/pr/testowner/testrepo/123/",
            pr_state="published",
            has_conflicts=False,
        )
        github_data = GitHubData(
            owner="testowner",
            repo="testrepo",
            pr_number=123,
            pr_state="OPEN",
            is_draft=False,
            mergeable="MERGEABLE",
            check_contexts=[],
        )

        result = build_gh_label(repo_info, github_data)

        # Render TokenSeq to text to verify format
        result_text = result.render()
        assert result_text.startswith("(gh:")
        assert "#123" in result_text
        assert result_text.endswith(")")

    def test_with_issue_number_includes_issue(self) -> None:
        """When issue number is provided, should include plan:#456 in label."""
        repo_info = RepoInfo(
            owner="testowner",
            repo="testrepo",
            pr_number="123",
            pr_url="https://app.graphite.dev/github/pr/testowner/testrepo/123/",
            pr_state="published",
            has_conflicts=False,
        )
        github_data = GitHubData(
            owner="testowner",
            repo="testrepo",
            pr_number=123,
            pr_state="OPEN",
            is_draft=False,
            mergeable="MERGEABLE",
            check_contexts=[],
        )

        result = build_gh_label(repo_info, github_data, issue_number=456)

        # Render TokenSeq to text to verify format
        result_text = result.render()
        assert result_text.startswith("(gh:")
        assert "#123" in result_text
        assert "plan:" in result_text
        assert "#456" in result_text
        assert result_text.endswith(")")

    def test_without_issue_number_omits_issue(self) -> None:
        """When issue number is None, should not include plan: in label."""
        repo_info = RepoInfo(
            owner="testowner",
            repo="testrepo",
            pr_number="123",
            pr_url="https://app.graphite.dev/github/pr/testowner/testrepo/123/",
            pr_state="published",
            has_conflicts=False,
        )
        github_data = None

        result = build_gh_label(repo_info, github_data, issue_number=None)

        # Render TokenSeq to text to verify format
        result_text = result.render()
        assert "plan:" not in result_text


class TestGetIssueNumber:
    """Test issue number loading from .impl/issue.json."""

    def test_no_git_root_returns_none(self) -> None:
        """Empty git root should return None."""
        result = get_issue_number("")
        assert result is None

    def test_missing_issue_file_returns_none(self) -> None:
        """Missing issue.json file should return None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = get_issue_number(tmpdir)
            assert result is None

    def test_valid_issue_json_returns_number(self) -> None:
        """Valid issue.json with number field should return the number."""
        with tempfile.TemporaryDirectory() as tmpdir:
            impl_dir = Path(tmpdir) / ".impl"
            impl_dir.mkdir()
            issue_file = impl_dir / "issue.json"
            issue_file.write_text('{"number": 456}')

            result = get_issue_number(tmpdir)
            assert result == 456

    def test_valid_issue_json_with_issue_number_key(self) -> None:
        """Valid issue.json with issue_number field should return the number."""
        with tempfile.TemporaryDirectory() as tmpdir:
            impl_dir = Path(tmpdir) / ".impl"
            impl_dir.mkdir()
            issue_file = impl_dir / "issue.json"
            issue_file.write_text(
                '{"issue_number": 901, "issue_url": "https://github.com/owner/repo/issues/901"}'
            )

            result = get_issue_number(tmpdir)
            assert result == 901

    def test_issue_json_with_extra_fields(self) -> None:
        """issue.json with extra fields should still return the number."""
        with tempfile.TemporaryDirectory() as tmpdir:
            impl_dir = Path(tmpdir) / ".impl"
            impl_dir.mkdir()
            issue_file = impl_dir / "issue.json"
            issue_file.write_text('{"number": 789, "title": "Fix bug", "state": "open"}')

            result = get_issue_number(tmpdir)
            assert result == 789

    def test_malformed_json_returns_none(self) -> None:
        """Malformed JSON should return None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            impl_dir = Path(tmpdir) / ".impl"
            impl_dir.mkdir()
            issue_file = impl_dir / "issue.json"
            issue_file.write_text('{"number": not valid json}')

            result = get_issue_number(tmpdir)
            assert result is None

    def test_missing_number_field_returns_none(self) -> None:
        """JSON without number field should return None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            impl_dir = Path(tmpdir) / ".impl"
            impl_dir.mkdir()
            issue_file = impl_dir / "issue.json"
            issue_file.write_text('{"title": "Some issue"}')

            result = get_issue_number(tmpdir)
            assert result is None

    def test_non_integer_number_returns_none(self) -> None:
        """JSON with non-integer number field should return None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            impl_dir = Path(tmpdir) / ".impl"
            impl_dir.mkdir()
            issue_file = impl_dir / "issue.json"
            issue_file.write_text('{"number": "not an int"}')

            result = get_issue_number(tmpdir)
            assert result is None


class TestParseGitHubRepoFromRemote:
    """Test parsing GitHub owner/repo from git remote URL."""

    @patch("erk_statusline.statusline.run_git")
    def test_ssh_format_with_dot_git(self, mock_run_git: MagicMock) -> None:
        """Should parse SSH format with .git suffix."""
        mock_run_git.return_value = "git@github.com:dagster-io/dagster.git"

        result = _parse_github_repo_from_remote("/fake/cwd")

        assert result is not None
        assert result == ("dagster-io", "dagster")

    @patch("erk_statusline.statusline.run_git")
    def test_ssh_format_without_dot_git(self, mock_run_git: MagicMock) -> None:
        """Should parse SSH format without .git suffix."""
        mock_run_git.return_value = "git@github.com:owner/repo"

        result = _parse_github_repo_from_remote("/fake/cwd")

        assert result is not None
        assert result == ("owner", "repo")

    @patch("erk_statusline.statusline.run_git")
    def test_https_format_with_dot_git(self, mock_run_git: MagicMock) -> None:
        """Should parse HTTPS format with .git suffix."""
        mock_run_git.return_value = "https://github.com/facebook/react.git"

        result = _parse_github_repo_from_remote("/fake/cwd")

        assert result is not None
        assert result == ("facebook", "react")

    @patch("erk_statusline.statusline.run_git")
    def test_https_format_without_dot_git(self, mock_run_git: MagicMock) -> None:
        """Should parse HTTPS format without .git suffix."""
        mock_run_git.return_value = "https://github.com/microsoft/vscode"

        result = _parse_github_repo_from_remote("/fake/cwd")

        assert result is not None
        assert result == ("microsoft", "vscode")

    @patch("erk_statusline.statusline.run_git")
    def test_no_remote_returns_none(self, mock_run_git: MagicMock) -> None:
        """Should return None when git remote fails."""
        mock_run_git.return_value = ""

        result = _parse_github_repo_from_remote("/fake/cwd")

        assert result is None

    @patch("erk_statusline.statusline.run_git")
    def test_invalid_url_returns_none(self, mock_run_git: MagicMock) -> None:
        """Should return None for non-GitHub URLs."""
        mock_run_git.return_value = "https://gitlab.com/owner/repo.git"

        result = _parse_github_repo_from_remote("/fake/cwd")

        assert result is None

    @patch("erk_statusline.statusline.run_git")
    def test_malformed_url_returns_none(self, mock_run_git: MagicMock) -> None:
        """Should return None for malformed URLs."""
        mock_run_git.return_value = "git@github.com:noslash"

        result = _parse_github_repo_from_remote("/fake/cwd")

        assert result is None

    @patch("erk_statusline.statusline.run_git")
    def test_spoofed_github_url_returns_none(self, mock_run_git: MagicMock) -> None:
        """Should return None for URLs with github.com in subdirectory (security fix)."""
        mock_run_git.return_value = "https://evil.com/github.com/owner/repo"

        result = _parse_github_repo_from_remote("/fake/cwd")

        assert result is None


class TestFetchGitHubDataRest:
    """Test REST API data fetching with mocked subprocess."""

    @patch("erk_statusline.statusline.run_git")
    def test_branch_detection_failure_returns_none(self, mock_run_git: MagicMock) -> None:
        """Failed branch detection should return None."""
        mock_run_git.return_value = ""

        result = _fetch_github_data_rest("/fake/cwd")
        assert result is None

    @patch("erk_statusline.statusline.subprocess.run")
    @patch("erk_statusline.statusline.run_git")
    def test_no_pr_for_branch_returns_data_with_zero_pr(
        self, mock_run_git: MagicMock, mock_subprocess: MagicMock
    ) -> None:
        """No PR for branch should return GitHubData with pr_number=0."""
        mock_run_git.side_effect = [
            "feature-branch",
            "git@github.com:owner/repo.git",
        ]

        # REST API returns empty array when no PRs
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="[]")

        result = _fetch_github_data_rest("/fake/cwd")
        assert result is not None
        assert result.owner == "owner"
        assert result.repo == "repo"
        assert result.pr_number == 0
        assert result.pr_state == ""
        assert result.is_draft is False
        assert result.mergeable == ""
        assert result.check_contexts == []

    @patch("erk_statusline.statusline._fetch_check_runs")
    @patch("erk_statusline.statusline._fetch_pr_details")
    @patch("erk_statusline.statusline._fetch_pr_list")
    @patch("erk_statusline.statusline._get_cached_pr_info")
    @patch("erk_statusline.statusline.run_git")
    def test_returns_open_pr_when_multiple_exist(
        self,
        mock_run_git: MagicMock,
        mock_get_cache: MagicMock,
        mock_fetch_pr_list: MagicMock,
        mock_fetch_details: MagicMock,
        mock_fetch_checks: MagicMock,
    ) -> None:
        """REST API should return OPEN PR first when both OPEN and MERGED exist."""
        mock_run_git.side_effect = [
            "feature-branch",
            "git@github.com:owner/repo.git",
        ]
        mock_get_cache.return_value = None
        # _fetch_pr_list returns the first PR (OPEN one) with its data
        mock_fetch_pr_list.return_value = (456, "abc123", "OPEN", False)
        mock_fetch_details.return_value = "MERGEABLE"
        mock_fetch_checks.return_value = []

        result = _fetch_github_data_rest("/fake/cwd")
        assert result is not None
        assert result.pr_number == 456  # Should return the OPEN PR
        assert result.pr_state == "OPEN"

    @patch("erk_statusline.statusline._fetch_check_runs")
    @patch("erk_statusline.statusline._fetch_pr_details")
    @patch("erk_statusline.statusline._fetch_pr_list")
    @patch("erk_statusline.statusline._get_cached_pr_info")
    @patch("erk_statusline.statusline.run_git")
    def test_maps_rest_fields_to_github_data(
        self,
        mock_run_git: MagicMock,
        mock_get_cache: MagicMock,
        mock_fetch_pr_list: MagicMock,
        mock_fetch_details: MagicMock,
        mock_fetch_checks: MagicMock,
    ) -> None:
        """REST fields should map correctly to GitHubData."""
        mock_run_git.side_effect = [
            "feature-branch",
            "https://github.com/owner/repo.git",
        ]
        mock_get_cache.return_value = None  # Cache miss
        mock_fetch_pr_list.return_value = (123, "abc123", "OPEN", True)
        mock_fetch_details.return_value = "CONFLICTING"
        mock_fetch_checks.return_value = [
            {
                "__typename": "CheckRun",
                "conclusion": "SUCCESS",
                "status": "COMPLETED",
                "name": "test",
            },
            {"__typename": "CheckRun", "conclusion": "", "status": "IN_PROGRESS", "name": "build"},
        ]

        result = _fetch_github_data_rest("/fake/cwd")
        assert result is not None
        assert result.owner == "owner"
        assert result.repo == "repo"
        assert result.pr_number == 123
        assert result.pr_state == "OPEN"
        assert result.is_draft is True
        assert result.mergeable == "CONFLICTING"
        assert len(result.check_contexts) == 2
        assert result.check_contexts[0]["__typename"] == "CheckRun"
        assert result.check_contexts[0]["conclusion"] == "SUCCESS"
        assert result.check_contexts[0]["status"] == "COMPLETED"
        assert result.check_contexts[1]["status"] == "IN_PROGRESS"

    @patch("erk_statusline.statusline._fetch_check_runs")
    @patch("erk_statusline.statusline._fetch_pr_details")
    @patch("erk_statusline.statusline._fetch_pr_list")
    @patch("erk_statusline.statusline._get_cached_pr_info")
    @patch("erk_statusline.statusline.run_git")
    def test_mergeable_true_maps_to_mergeable(
        self,
        mock_run_git: MagicMock,
        mock_get_cache: MagicMock,
        mock_fetch_pr_list: MagicMock,
        mock_fetch_details: MagicMock,
        mock_fetch_checks: MagicMock,
    ) -> None:
        """REST mergeable=True should map to MERGEABLE."""
        mock_run_git.side_effect = [
            "feature-branch",
            "git@github.com:owner/repo.git",
        ]
        mock_get_cache.return_value = None
        mock_fetch_pr_list.return_value = (123, "abc123", "OPEN", False)
        mock_fetch_details.return_value = "MERGEABLE"
        mock_fetch_checks.return_value = []

        result = _fetch_github_data_rest("/fake/cwd")
        assert result is not None
        assert result.mergeable == "MERGEABLE"

    @patch("erk_statusline.statusline._fetch_check_runs")
    @patch("erk_statusline.statusline._fetch_pr_details")
    @patch("erk_statusline.statusline._fetch_pr_list")
    @patch("erk_statusline.statusline._get_cached_pr_info")
    @patch("erk_statusline.statusline.run_git")
    def test_mergeable_null_maps_to_unknown(
        self,
        mock_run_git: MagicMock,
        mock_get_cache: MagicMock,
        mock_fetch_pr_list: MagicMock,
        mock_fetch_details: MagicMock,
        mock_fetch_checks: MagicMock,
    ) -> None:
        """REST mergeable=null should map to UNKNOWN."""
        mock_run_git.side_effect = [
            "feature-branch",
            "git@github.com:owner/repo.git",
        ]
        mock_get_cache.return_value = None
        mock_fetch_pr_list.return_value = (123, "abc123", "OPEN", False)
        mock_fetch_details.return_value = "UNKNOWN"
        mock_fetch_checks.return_value = []

        result = _fetch_github_data_rest("/fake/cwd")
        assert result is not None
        assert result.mergeable == "UNKNOWN"

    @patch("erk_statusline.statusline._fetch_pr_list")
    @patch("erk_statusline.statusline._get_cached_pr_info")
    @patch("erk_statusline.statusline.run_git")
    def test_list_prs_failure_returns_none(
        self,
        mock_run_git: MagicMock,
        mock_get_cache: MagicMock,
        mock_fetch_pr_list: MagicMock,
    ) -> None:
        """Failed list PRs call should return None."""
        mock_run_git.side_effect = [
            "feature-branch",
            "git@github.com:owner/repo.git",
        ]
        mock_get_cache.return_value = None
        mock_fetch_pr_list.return_value = None  # API failure

        result = _fetch_github_data_rest("/fake/cwd")
        assert result is None


class TestGetPlanProgress:
    """Test plan progress parsing."""

    def test_no_git_root_returns_none(self) -> None:
        """Empty git root should return None."""
        result = get_plan_progress("")
        assert result is None

    def test_missing_progress_file_returns_none(self) -> None:
        """Missing progress.md file should return None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = get_plan_progress(tmpdir)
            assert result is None

    def test_parse_yaml_frontmatter_with_steps(self) -> None:
        """Should parse YAML frontmatter with completed_steps and total_steps."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_dir = Path(tmpdir) / ".impl"
            plan_dir.mkdir()
            progress_file = plan_dir / "progress.md"
            progress_file.write_text(
                """---
completed_steps: 3
total_steps: 10
---

# Progress Tracking

- [x] Task 1
- [x] Task 2
- [x] Task 3
- [ ] Task 4
"""
            )

            result = get_plan_progress(tmpdir)
            assert result is not None
            assert result == (3, 10)

    def test_fallback_to_checkbox_counting(self) -> None:
        """Should count checkboxes when YAML frontmatter is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_dir = Path(tmpdir) / ".impl"
            plan_dir.mkdir()
            progress_file = plan_dir / "progress.md"
            progress_file.write_text(
                """# Progress Tracking

- [x] Task 1
- [x] Task 2
- [ ] Task 3
- [ ] Task 4
- [ ] Task 5
"""
            )

            result = get_plan_progress(tmpdir)
            assert result is not None
            assert result == (2, 5)

    def test_zero_completed_steps(self) -> None:
        """Should handle zero completed steps correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_dir = Path(tmpdir) / ".impl"
            plan_dir.mkdir()
            progress_file = plan_dir / "progress.md"
            progress_file.write_text(
                """---
completed_steps: 0
total_steps: 5
---

# Progress Tracking

- [ ] Task 1
- [ ] Task 2
"""
            )

            result = get_plan_progress(tmpdir)
            assert result is not None
            assert result == (0, 5)

    def test_all_completed_steps(self) -> None:
        """Should handle all steps completed correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_dir = Path(tmpdir) / ".impl"
            plan_dir.mkdir()
            progress_file = plan_dir / "progress.md"
            progress_file.write_text(
                """---
completed_steps: 5
total_steps: 5
---

# Progress Tracking

- [x] Task 1
- [x] Task 2
- [x] Task 3
- [x] Task 4
- [x] Task 5
"""
            )

            result = get_plan_progress(tmpdir)
            assert result is not None
            assert result == (5, 5)

    def test_no_checkboxes_returns_none(self) -> None:
        """Should return None when there are no checkboxes and no YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_dir = Path(tmpdir) / ".impl"
            plan_dir.mkdir()
            progress_file = plan_dir / "progress.md"
            progress_file.write_text(
                """# Progress Tracking

Just some text with no checkboxes.
"""
            )

            result = get_plan_progress(tmpdir)
            assert result is None

    def test_malformed_yaml_falls_back_to_checkboxes(self) -> None:
        """Should fall back to checkbox counting when YAML is malformed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_dir = Path(tmpdir) / ".impl"
            plan_dir.mkdir()
            progress_file = plan_dir / "progress.md"
            progress_file.write_text(
                """---
completed_steps: not_a_number
total_steps: also_not_a_number
---

# Progress Tracking

- [x] Task 1
- [ ] Task 2
"""
            )

            result = get_plan_progress(tmpdir)
            assert result is not None
            assert result == (1, 2)


class TestBuildPlanLabel:
    """Test plan label building."""

    def test_none_progress_returns_simple_label(self) -> None:
        """None progress should return (.impl) without indicator."""
        result = build_plan_label(None)
        assert result.text == "(.impl)"

    def test_zero_total_returns_simple_label(self) -> None:
        """Zero total steps should return (.impl) without indicator."""
        result = build_plan_label((0, 0))
        assert result.text == "(.impl)"

    def test_zero_percent_shows_white_circle(self) -> None:
        """0% completion should show white circle indicator."""
        result = build_plan_label((0, 10))
        assert "⚪" in result.text
        assert "0/10" in result.text

    def test_partial_progress_shows_yellow_circle(self) -> None:
        """Partial progress should show yellow circle indicator."""
        result = build_plan_label((3, 10))
        assert "🟡" in result.text
        assert "3/10" in result.text

    def test_ninety_nine_percent_shows_yellow_circle(self) -> None:
        """99% completion should still show yellow circle."""
        result = build_plan_label((99, 100))
        assert "🟡" in result.text
        assert "99/100" in result.text

    def test_complete_shows_green_check(self) -> None:
        """100% completion should show green check indicator."""
        result = build_plan_label((10, 10))
        assert "✅" in result.text
        assert "10/10" in result.text

    def test_label_format(self) -> None:
        """Label should have correct format (.impl INDICATOR X/Y)."""
        result = build_plan_label((5, 8))
        assert result.text.startswith("(.impl ")
        assert result.text.endswith(")")
        assert "5/8" in result.text


class TestFindNewPlanFile:
    """Test new plan file detection."""

    def test_finds_file_with_correct_frontmatter(self) -> None:
        """Should find plan file with erk_plan: true."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_file = Path(tmpdir) / "add-lorem-ipsum-impl.md"
            plan_file.write_text(
                """---
erk_plan: true
---

## Implementation Plan
"""
            )

            result = find_new_plan_file(tmpdir)
            assert result is not None
            assert result == "add-lorem-ipsum-impl.md"

    def test_returns_none_when_no_plan_files_exist(self) -> None:
        """Should return None when no plan files exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = find_new_plan_file(tmpdir)
            assert result is None

    def test_returns_none_when_plan_file_lacks_frontmatter(self) -> None:
        """Should return None when plan file has no YAML frontmatter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_file = Path(tmpdir) / "feature-impl.md"
            plan_file.write_text(
                """## Implementation Plan

Just content, no frontmatter.
"""
            )

            result = find_new_plan_file(tmpdir)
            assert result is None

    def test_returns_none_when_frontmatter_has_false(self) -> None:
        """Should return None when erk_plan is false."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_file = Path(tmpdir) / "feature-impl.md"
            plan_file.write_text(
                """---
erk_plan: false
---

## Implementation Plan
"""
            )

            result = find_new_plan_file(tmpdir)
            assert result is None

    def test_ignores_non_markdown_files(self) -> None:
        """Should ignore non-.md files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a non-markdown file
            text_file = Path(tmpdir) / "feature-impl.txt"
            text_file.write_text(
                """---
enriched_by_persist_plan: true
---

## Implementation Plan
"""
            )

            result = find_new_plan_file(tmpdir)
            assert result is None

    def test_returns_first_match_when_multiple_exist(self) -> None:
        """Should return first matching plan file when multiple exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create two plan files with correct frontmatter
            plan1 = Path(tmpdir) / "feature-a-impl.md"
            plan1.write_text(
                """---
erk_plan: true
---

## Plan A
"""
            )
            plan2 = Path(tmpdir) / "feature-b-impl.md"
            plan2.write_text(
                """---
erk_plan: true
---

## Plan B
"""
            )

            result = find_new_plan_file(tmpdir)
            assert result is not None
            # Should return one of them (order may vary)
            assert result in ["feature-a-impl.md", "feature-b-impl.md"]


class TestBuildNewPlanLabel:
    """Test new plan label building."""

    def test_formats_label_correctly(self) -> None:
        """Should format label as (🆕:basename) without -impl.md suffix."""
        result = build_new_plan_label("add-lorem-ipsum-to-readme-impl.md")
        assert result.text == "(🆕:add-lorem-ipsum-to-readme)"

    def test_removes_plan_suffix(self) -> None:
        """Should remove -impl.md suffix correctly."""
        result = build_new_plan_label("feature-impl.md")
        assert result.text == "(🆕:feature)"

    def test_handles_short_names(self) -> None:
        """Should handle short filenames correctly."""
        result = build_new_plan_label("fix-impl.md")
        assert result.text == "(🆕:fix)"

    def test_handles_long_names(self) -> None:
        """Should handle long filenames without truncation."""
        result = build_new_plan_label("very-long-feature-name-with-many-words-impl.md")
        assert result.text == "(🆕:very-long-feature-name-with-many-words)"


class TestNewPlanFileIntegration:
    """Test integration of new plan file detection and label building."""

    def test_finds_file_and_builds_label_end_to_end(self) -> None:
        """Should find plan file with correct frontmatter and build label."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a plan file with correct frontmatter
            plan_file = Path(tmpdir) / "add-feature-x-impl.md"
            plan_file.write_text(
                """---
erk_plan: true
---

## Implementation Plan
"""
            )

            # Find the file
            filename = find_new_plan_file(tmpdir)
            assert filename is not None
            assert filename == "add-feature-x-impl.md"

            # Build the label
            label = build_new_plan_label(filename)
            assert label.text == "(🆕:add-feature-x)"

    def test_returns_none_when_no_matching_file(self) -> None:
        """Should return None when no plan file matches criteria."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a plan file without correct frontmatter
            plan_file = Path(tmpdir) / "feature-impl.md"
            plan_file.write_text(
                """---
erk_plan: false
---

## Implementation Plan
"""
            )

            # Should not find the file
            filename = find_new_plan_file(tmpdir)
            assert filename is None


class TestPrInfoCache:
    """Test PR info caching functionality."""

    def test_cache_miss_returns_none(self) -> None:
        """Non-existent cache should return None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("erk_statusline.statusline.CACHE_DIR", Path(tmpdir) / "cache"):
                result = _get_cached_pr_info("owner", "repo", "branch")
                assert result is None

    def test_cache_hit_returns_data(self) -> None:
        """Valid cache should return (pr_number, head_sha) tuple."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "cache"
            with patch("erk_statusline.statusline.CACHE_DIR", cache_dir):
                # Set cache
                _set_cached_pr_info("owner", "repo", "feature-branch", 123, "abc123def")

                # Read cache
                result = _get_cached_pr_info("owner", "repo", "feature-branch")
                assert result is not None
                assert result == (123, "abc123def")

    def test_cache_expired_returns_none(self) -> None:
        """Cache older than TTL should return None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "cache"
            with patch("erk_statusline.statusline.CACHE_DIR", cache_dir):
                # Set cache
                _set_cached_pr_info("owner", "repo", "old-branch", 456, "old123sha")

                # Get cache path and backdate the file modification time
                cache_path = _get_cache_path("owner", "repo", "old-branch")
                old_time = time.time() - CACHE_TTL_SECONDS - 10  # 10 seconds past expiry
                import os

                os.utime(cache_path, (old_time, old_time))

                # Read cache - should be expired
                result = _get_cached_pr_info("owner", "repo", "old-branch")
                assert result is None

    def test_cache_write_creates_file(self) -> None:
        """Writing cache should create the cache file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "cache"
            with patch("erk_statusline.statusline.CACHE_DIR", cache_dir):
                _set_cached_pr_info("owner", "repo", "new-branch", 789, "newsha456")

                cache_path = _get_cache_path("owner", "repo", "new-branch")
                assert cache_path.exists()

                # Verify contents
                content = json.loads(cache_path.read_text(encoding="utf-8"))
                assert content["pr_number"] == 789
                assert content["head_sha"] == "newsha456"

    def test_cache_path_uses_hash_for_branch(self) -> None:
        """Cache path should use hash of branch name to handle special chars."""
        path1 = _get_cache_path("owner", "repo", "feature/foo")
        path2 = _get_cache_path("owner", "repo", "feature/bar")

        # Different branches should have different cache files
        assert path1 != path2

        # Path should not contain the special character
        assert "/" not in path1.name.split("-", 2)[2]

    def test_cache_malformed_json_returns_none(self) -> None:
        """Malformed JSON cache should return None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "cache"
            cache_dir.mkdir(parents=True)
            with patch("erk_statusline.statusline.CACHE_DIR", cache_dir):
                cache_path = _get_cache_path("owner", "repo", "broken-branch")
                cache_path.write_text("not valid json", encoding="utf-8")

                result = _get_cached_pr_info("owner", "repo", "broken-branch")
                assert result is None


class TestFetchPrList:
    """Test PR list fetching."""

    @patch("erk_statusline.statusline.subprocess.run")
    def test_returns_pr_info_on_success(self, mock_run: MagicMock) -> None:
        """Should return PR info tuple on successful API call."""
        prs_response = [{"number": 123, "state": "open", "draft": True, "head": {"sha": "abc123"}}]
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(prs_response))

        result = _fetch_pr_list("owner", "repo", "branch", "/cwd", 1.5)

        assert result is not None
        assert result == (123, "abc123", "OPEN", True)

    @patch("erk_statusline.statusline.subprocess.run")
    def test_returns_zero_pr_when_no_prs(self, mock_run: MagicMock) -> None:
        """Should return (0, '', '', False) when no PRs exist."""
        mock_run.return_value = MagicMock(returncode=0, stdout="[]")

        result = _fetch_pr_list("owner", "repo", "branch", "/cwd", 1.5)

        assert result is not None
        assert result == (0, "", "", False)

    @patch("erk_statusline.statusline.subprocess.run")
    def test_returns_none_on_api_failure(self, mock_run: MagicMock) -> None:
        """Should return None on API failure."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        result = _fetch_pr_list("owner", "repo", "branch", "/cwd", 1.5)

        assert result is None


class TestFetchPrDetails:
    """Test PR details fetching."""

    @patch("erk_statusline.statusline.subprocess.run")
    def test_returns_mergeable_on_success(self, mock_run: MagicMock) -> None:
        """Should return MERGEABLE when PR is mergeable."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps({"mergeable": True, "mergeable_state": "clean"})
        )

        result = _fetch_pr_details("owner", "repo", 123, "/cwd", 1.5)

        assert result == "MERGEABLE"

    @patch("erk_statusline.statusline.subprocess.run")
    def test_returns_conflicting_on_dirty_state(self, mock_run: MagicMock) -> None:
        """Should return CONFLICTING when mergeable_state is dirty."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps({"mergeable": False, "mergeable_state": "dirty"})
        )

        result = _fetch_pr_details("owner", "repo", 123, "/cwd", 1.5)

        assert result == "CONFLICTING"

    @patch("erk_statusline.statusline.subprocess.run")
    def test_returns_unknown_on_failure(self, mock_run: MagicMock) -> None:
        """Should return UNKNOWN on API failure."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        result = _fetch_pr_details("owner", "repo", 123, "/cwd", 1.5)

        assert result == "UNKNOWN"


class TestFetchCheckRuns:
    """Test check runs fetching."""

    @patch("erk_statusline.statusline.subprocess.run")
    def test_returns_check_contexts_on_success(self, mock_run: MagicMock) -> None:
        """Should return properly formatted check contexts."""
        check_runs_response = {
            "check_runs": [
                {"name": "test", "status": "completed", "conclusion": "success"},
                {"name": "lint", "status": "in_progress", "conclusion": None},
            ]
        }
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(check_runs_response))

        result = _fetch_check_runs("owner", "repo", "sha123", "/cwd", 1.5)

        assert len(result) == 2
        assert result[0]["__typename"] == "CheckRun"
        assert result[0]["conclusion"] == "SUCCESS"
        assert result[0]["status"] == "COMPLETED"
        assert result[1]["status"] == "IN_PROGRESS"

    @patch("erk_statusline.statusline.subprocess.run")
    def test_returns_empty_on_failure(self, mock_run: MagicMock) -> None:
        """Should return empty list on API failure."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        result = _fetch_check_runs("owner", "repo", "sha123", "/cwd", 1.5)

        assert result == []


class TestParallelFetch:
    """Test parallel fetching of PR details and check runs."""

    @patch("erk_statusline.statusline._fetch_check_runs")
    @patch("erk_statusline.statusline._fetch_pr_details")
    @patch("erk_statusline.statusline._fetch_pr_list")
    @patch("erk_statusline.statusline._get_cached_pr_info")
    @patch("erk_statusline.statusline._parse_github_repo_from_remote")
    @patch("erk_statusline.statusline.run_git")
    def test_uses_cache_when_available(
        self,
        mock_run_git: MagicMock,
        mock_parse_repo: MagicMock,
        mock_get_cache: MagicMock,
        mock_fetch_pr_list: MagicMock,
        mock_fetch_details: MagicMock,
        mock_fetch_checks: MagicMock,
    ) -> None:
        """Should use cached PR info instead of fetching PR list."""
        mock_run_git.return_value = "feature-branch"
        mock_parse_repo.return_value = ("owner", "repo")
        mock_get_cache.return_value = (123, "cached-sha")
        mock_fetch_details.return_value = "MERGEABLE"
        mock_fetch_checks.return_value = []

        result = _fetch_github_data_rest("/fake/cwd")

        assert result is not None
        assert result.pr_number == 123
        # Should NOT have called _fetch_pr_list since we hit cache
        mock_fetch_pr_list.assert_not_called()
        # Should have called details and checks
        mock_fetch_details.assert_called_once()
        mock_fetch_checks.assert_called_once()

    @patch("erk_statusline.statusline._set_cached_pr_info")
    @patch("erk_statusline.statusline._fetch_check_runs")
    @patch("erk_statusline.statusline._fetch_pr_details")
    @patch("erk_statusline.statusline._fetch_pr_list")
    @patch("erk_statusline.statusline._get_cached_pr_info")
    @patch("erk_statusline.statusline._parse_github_repo_from_remote")
    @patch("erk_statusline.statusline.run_git")
    def test_caches_pr_info_on_miss(
        self,
        mock_run_git: MagicMock,
        mock_parse_repo: MagicMock,
        mock_get_cache: MagicMock,
        mock_fetch_pr_list: MagicMock,
        mock_fetch_details: MagicMock,
        mock_fetch_checks: MagicMock,
        mock_set_cache: MagicMock,
    ) -> None:
        """Should cache PR info after fetching on cache miss."""
        mock_run_git.return_value = "feature-branch"
        mock_parse_repo.return_value = ("owner", "repo")
        mock_get_cache.return_value = None  # Cache miss
        mock_fetch_pr_list.return_value = (456, "new-sha", "OPEN", False)
        mock_fetch_details.return_value = "MERGEABLE"
        mock_fetch_checks.return_value = []

        result = _fetch_github_data_rest("/fake/cwd")

        assert result is not None
        assert result.pr_number == 456
        # Should have cached the result
        mock_set_cache.assert_called_once_with("owner", "repo", "feature-branch", 456, "new-sha")

    @patch("erk_statusline.statusline._fetch_check_runs")
    @patch("erk_statusline.statusline._fetch_pr_details")
    @patch("erk_statusline.statusline._get_cached_pr_info")
    @patch("erk_statusline.statusline._parse_github_repo_from_remote")
    @patch("erk_statusline.statusline.run_git")
    def test_parallel_calls_use_thread_pool(
        self,
        mock_run_git: MagicMock,
        mock_parse_repo: MagicMock,
        mock_get_cache: MagicMock,
        mock_fetch_details: MagicMock,
        mock_fetch_checks: MagicMock,
    ) -> None:
        """Should execute PR details and check runs in parallel."""
        mock_run_git.return_value = "feature-branch"
        mock_parse_repo.return_value = ("owner", "repo")
        mock_get_cache.return_value = (123, "sha123")
        mock_fetch_details.return_value = "MERGEABLE"
        mock_fetch_checks.return_value = [
            {
                "__typename": "CheckRun",
                "conclusion": "SUCCESS",
                "status": "COMPLETED",
                "name": "test",
            }
        ]

        result = _fetch_github_data_rest("/fake/cwd")

        assert result is not None
        assert result.mergeable == "MERGEABLE"
        assert len(result.check_contexts) == 1
        # Both should be called
        mock_fetch_details.assert_called_once()
        mock_fetch_checks.assert_called_once()

    @patch("erk_statusline.statusline._set_cached_pr_info")
    @patch("erk_statusline.statusline._fetch_pr_list")
    @patch("erk_statusline.statusline._get_cached_pr_info")
    @patch("erk_statusline.statusline._parse_github_repo_from_remote")
    @patch("erk_statusline.statusline.run_git")
    def test_no_pr_returns_early(
        self,
        mock_run_git: MagicMock,
        mock_parse_repo: MagicMock,
        mock_get_cache: MagicMock,
        mock_fetch_pr_list: MagicMock,
        mock_set_cache: MagicMock,
    ) -> None:
        """Should return early with empty PR data when no PR exists."""
        mock_run_git.return_value = "feature-branch"
        mock_parse_repo.return_value = ("owner", "repo")
        mock_get_cache.return_value = None  # Cache miss
        mock_fetch_pr_list.return_value = (0, "", "", False)  # No PR

        result = _fetch_github_data_rest("/fake/cwd")

        assert result is not None
        assert result.pr_number == 0
        assert result.pr_state == ""
        # Should NOT cache when there's no PR
        mock_set_cache.assert_not_called()
