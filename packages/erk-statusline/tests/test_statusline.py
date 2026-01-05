"""Tests for statusline.py GitHub integration."""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from erk_shared.branch_manager.fake import FakeBranchManager
from erk_shared.branch_manager.types import PrInfo
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_statusline.context import StatuslineContext
from erk_statusline.statusline import (
    CACHE_TTL_SECONDS,
    GitHubData,
    PRDetailsResult,
    RepoInfo,
    _categorize_check_buckets,
    _fetch_check_runs,
    _fetch_pr_details,
    _get_cache_path,
    _get_cached_pr_info,
    _parse_github_repo_from_url,
    _set_cached_pr_info,
    build_gh_label,
    build_new_plan_label,
    build_plan_label,
    fetch_github_data_via_gateway,
    find_new_plan_file,
    get_checks_status,
    get_git_root_via_gateway,
    get_git_status_via_gateway,
    get_github_repo_via_gateway,
    get_issue_number,
    get_pr_info_via_branch_manager,
    get_repo_info,
    get_worktree_info_via_gateway,
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


class TestBuildPlanLabel:
    """Test plan label building."""

    def test_returns_simple_label(self) -> None:
        """Should return (.impl) label."""
        result = build_plan_label()
        assert result.text == "(.impl)"


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


class TestFetchPrDetails:
    """Test PR details fetching."""

    @patch("erk_statusline.statusline.subprocess.run")
    def test_returns_mergeable_on_success(self, mock_run: MagicMock) -> None:
        """Should return MERGEABLE when PR is mergeable."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
                    "mergeable": True,
                    "mergeable_state": "clean",
                    "head": {"sha": "abc123def"},
                }
            ),
        )

        result = _fetch_pr_details("owner", "repo", 123, "/cwd", 1.5)

        assert result.mergeable == "MERGEABLE"
        assert result.head_sha == "abc123def"

    @patch("erk_statusline.statusline.subprocess.run")
    def test_returns_conflicting_on_dirty_state(self, mock_run: MagicMock) -> None:
        """Should return CONFLICTING when mergeable_state is dirty."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
                    "mergeable": False,
                    "mergeable_state": "dirty",
                    "head": {"sha": "def456"},
                }
            ),
        )

        result = _fetch_pr_details("owner", "repo", 123, "/cwd", 1.5)

        assert result.mergeable == "CONFLICTING"
        assert result.head_sha == "def456"

    @patch("erk_statusline.statusline.subprocess.run")
    def test_returns_unknown_on_failure(self, mock_run: MagicMock) -> None:
        """Should return UNKNOWN on API failure."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        result = _fetch_pr_details("owner", "repo", 123, "/cwd", 1.5)

        assert result.mergeable == "UNKNOWN"
        assert result.head_sha == ""


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


class TestParseGitHubRepoFromUrl:
    """Test URL parsing helper function."""

    def test_ssh_format_with_dot_git(self) -> None:
        """Should parse SSH format with .git suffix."""
        result = _parse_github_repo_from_url("git@github.com:owner/repo.git")
        assert result == ("owner", "repo")

    def test_ssh_format_without_dot_git(self) -> None:
        """Should parse SSH format without .git suffix."""
        result = _parse_github_repo_from_url("git@github.com:owner/repo")
        assert result == ("owner", "repo")

    def test_https_format_with_dot_git(self) -> None:
        """Should parse HTTPS format with .git suffix."""
        result = _parse_github_repo_from_url("https://github.com/owner/repo.git")
        assert result == ("owner", "repo")

    def test_https_format_without_dot_git(self) -> None:
        """Should parse HTTPS format without .git suffix."""
        result = _parse_github_repo_from_url("https://github.com/owner/repo")
        assert result == ("owner", "repo")

    def test_empty_url_returns_none(self) -> None:
        """Empty URL should return None."""
        result = _parse_github_repo_from_url("")
        assert result is None

    def test_non_github_url_returns_none(self) -> None:
        """Non-GitHub URL should return None."""
        result = _parse_github_repo_from_url("https://gitlab.com/owner/repo")
        assert result is None


class TestGetGitRootViaGateway:
    """Test git root lookup via gateway."""

    def test_returns_repository_root(self) -> None:
        """Should return repository root path."""
        repo_root = Path("/fake/repo")
        fake_git = FakeGit(repository_roots={repo_root: repo_root})
        ctx = StatuslineContext(
            cwd=repo_root,
            git=fake_git,
            graphite=FakeGraphite(),
            github=FakeGitHub(),
            branch_manager=FakeBranchManager(),
        )

        result = get_git_root_via_gateway(ctx)

        assert result == repo_root


class TestGetGitStatusViaGateway:
    """Test git status lookup via gateway."""

    def test_returns_branch_and_dirty_status(self) -> None:
        """Should return current branch and dirty status."""
        repo_root = Path("/fake/repo")
        fake_git = FakeGit(
            current_branches={repo_root: "feature-branch"},
            file_statuses={repo_root: (["staged.txt"], [], [])},
        )
        ctx = StatuslineContext(
            cwd=repo_root,
            git=fake_git,
            graphite=FakeGraphite(),
            github=FakeGitHub(),
            branch_manager=FakeBranchManager(),
        )

        branch, is_dirty = get_git_status_via_gateway(ctx)

        assert branch == "feature-branch"
        assert is_dirty is True

    def test_no_branch_returns_empty(self) -> None:
        """Should return empty branch when not on a branch."""
        repo_root = Path("/fake/repo")
        fake_git = FakeGit(current_branches={repo_root: None})
        ctx = StatuslineContext(
            cwd=repo_root,
            git=fake_git,
            graphite=FakeGraphite(),
            github=FakeGitHub(),
            branch_manager=FakeBranchManager(),
        )

        branch, is_dirty = get_git_status_via_gateway(ctx)

        assert branch == ""
        assert is_dirty is False


class TestGetWorktreeInfoViaGateway:
    """Test worktree info lookup via gateway."""

    def test_root_worktree_returns_not_linked(self) -> None:
        """Root worktree should have is_linked=False."""
        repo_root = Path("/fake/repo")
        fake_git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main", is_root=True),
                ]
            }
        )
        ctx = StatuslineContext(
            cwd=repo_root,
            git=fake_git,
            graphite=FakeGraphite(),
            github=FakeGitHub(),
            branch_manager=FakeBranchManager(),
        )

        is_linked, wt_name = get_worktree_info_via_gateway(ctx, repo_root)

        assert is_linked is False
        assert wt_name == "repo"

    def test_linked_worktree_returns_is_linked(self) -> None:
        """Linked worktree should have is_linked=True."""
        repo_root = Path("/fake/repo")
        linked_wt = Path("/fake/worktrees/feature")
        fake_git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main", is_root=True),
                    WorktreeInfo(path=linked_wt, branch="feature", is_root=False),
                ]
            }
        )
        # Context cwd is the linked worktree
        ctx = StatuslineContext(
            cwd=linked_wt,
            git=fake_git,
            graphite=FakeGraphite(),
            github=FakeGitHub(),
            branch_manager=FakeBranchManager(),
        )

        is_linked, wt_name = get_worktree_info_via_gateway(ctx, linked_wt)

        assert is_linked is True
        assert wt_name == "feature"


class TestGetGitHubRepoViaGateway:
    """Test GitHub repo lookup via gateway."""

    def test_returns_owner_and_repo(self) -> None:
        """Should return owner and repo from remote URL."""
        repo_root = Path("/fake/repo")
        fake_git = FakeGit(remote_urls={(repo_root, "origin"): "git@github.com:owner/testrepo.git"})
        ctx = StatuslineContext(
            cwd=repo_root,
            git=fake_git,
            graphite=FakeGraphite(),
            github=FakeGitHub(),
            branch_manager=FakeBranchManager(),
        )

        result = get_github_repo_via_gateway(ctx, repo_root)

        assert result == ("owner", "testrepo")

    def test_no_remote_returns_none(self) -> None:
        """Should return None when no remote exists."""
        repo_root = Path("/fake/repo")
        fake_git = FakeGit()  # No remotes configured
        ctx = StatuslineContext(
            cwd=repo_root,
            git=fake_git,
            graphite=FakeGraphite(),
            github=FakeGitHub(),
            branch_manager=FakeBranchManager(),
        )

        result = get_github_repo_via_gateway(ctx, repo_root)

        assert result is None


class TestGetPrInfoViaBranchManager:
    """Test PR info lookup via BranchManager."""

    def test_returns_pr_info_when_found(self) -> None:
        """Should return PR info when branch has a PR."""
        repo_root = Path("/fake/repo")
        fake_branch_manager = FakeBranchManager(
            pr_info={
                "feature-branch": PrInfo(
                    number=123,
                    state="OPEN",
                    is_draft=True,
                )
            }
        )
        ctx = StatuslineContext(
            cwd=repo_root,
            git=FakeGit(),
            graphite=FakeGraphite(),
            github=FakeGitHub(),
            branch_manager=fake_branch_manager,
        )

        result = get_pr_info_via_branch_manager(ctx, repo_root, "feature-branch")

        assert result is not None
        assert result == (123, "OPEN", True)

    def test_returns_none_when_no_pr(self) -> None:
        """Should return None when branch has no PR."""
        repo_root = Path("/fake/repo")
        fake_branch_manager = FakeBranchManager(pr_info={})
        ctx = StatuslineContext(
            cwd=repo_root,
            git=FakeGit(),
            graphite=FakeGraphite(),
            github=FakeGitHub(),
            branch_manager=fake_branch_manager,
        )

        result = get_pr_info_via_branch_manager(ctx, repo_root, "no-pr-branch")

        assert result is None


class TestFetchGitHubDataViaGateway:
    """Test full GitHub data fetch via gateways."""

    def test_no_remote_returns_none(self) -> None:
        """Should return None when no GitHub remote configured."""
        repo_root = Path("/fake/repo")
        fake_git = FakeGit()  # No remotes configured
        ctx = StatuslineContext(
            cwd=repo_root,
            git=fake_git,
            graphite=FakeGraphite(),
            github=FakeGitHub(),
            branch_manager=FakeBranchManager(),
        )

        result = fetch_github_data_via_gateway(ctx, repo_root, "feature")

        assert result is None

    def test_no_pr_returns_github_data_with_zero_pr(self) -> None:
        """Should return GitHubData with pr_number=0 when no PR exists."""
        repo_root = Path("/fake/repo")
        fake_git = FakeGit(remote_urls={(repo_root, "origin"): "git@github.com:owner/repo.git"})
        fake_branch_manager = FakeBranchManager(pr_info={})  # No PRs
        ctx = StatuslineContext(
            cwd=repo_root,
            git=fake_git,
            graphite=FakeGraphite(),
            github=FakeGitHub(),
            branch_manager=fake_branch_manager,
        )

        result = fetch_github_data_via_gateway(ctx, repo_root, "no-pr-branch")

        assert result is not None
        assert result.owner == "owner"
        assert result.repo == "repo"
        assert result.pr_number == 0
        assert result.pr_state == ""

    @patch("erk_statusline.statusline._fetch_check_runs")
    @patch("erk_statusline.statusline._fetch_pr_details")
    def test_with_pr_returns_github_data(
        self, mock_fetch_details: MagicMock, mock_fetch_checks: MagicMock
    ) -> None:
        """Should return full GitHubData when PR exists."""
        repo_root = Path("/fake/repo")
        fake_git = FakeGit(
            remote_urls={(repo_root, "origin"): "git@github.com:owner/repo.git"},
            branch_heads={"feature-branch": "abc123"},
        )
        fake_branch_manager = FakeBranchManager(
            pr_info={
                "feature-branch": PrInfo(
                    number=456,
                    state="OPEN",
                    is_draft=False,
                )
            }
        )
        ctx = StatuslineContext(
            cwd=repo_root,
            git=fake_git,
            graphite=FakeGraphite(),
            github=FakeGitHub(),
            branch_manager=fake_branch_manager,
        )

        # Mock the REST API calls for checks and mergeable status
        mock_fetch_details.return_value = PRDetailsResult(mergeable="MERGEABLE", head_sha="abc123")
        mock_fetch_checks.return_value = [
            {
                "__typename": "CheckRun",
                "conclusion": "SUCCESS",
                "status": "COMPLETED",
                "name": "test",
            }
        ]

        result = fetch_github_data_via_gateway(ctx, repo_root, "feature-branch")

        assert result is not None
        assert result.owner == "owner"
        assert result.repo == "repo"
        assert result.pr_number == 456
        assert result.pr_state == "OPEN"
        assert result.is_draft is False
        assert result.mergeable == "MERGEABLE"
        assert len(result.check_contexts) == 1
