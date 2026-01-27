"""Tests for FakeGitStatusOps."""

from pathlib import Path

from erk_shared.gateway.git.status_ops.fake import FakeGitStatusOps


class TestHasStagedChanges:
    def test_returns_false_when_repo_not_in_staged_repos(self) -> None:
        ops = FakeGitStatusOps()
        assert not ops.has_staged_changes(Path("/repo"))

    def test_returns_true_when_repo_in_staged_repos(self) -> None:
        repo = Path("/repo")
        ops = FakeGitStatusOps(staged_repos={repo})
        assert ops.has_staged_changes(repo)


class TestHasUncommittedChanges:
    def test_returns_false_with_no_status(self) -> None:
        ops = FakeGitStatusOps()
        assert not ops.has_uncommitted_changes(Path("/cwd"))

    def test_returns_true_with_staged_files(self) -> None:
        cwd = Path("/cwd")
        ops = FakeGitStatusOps(file_statuses={cwd: (["file.py"], [], [])})
        assert ops.has_uncommitted_changes(cwd)

    def test_returns_true_with_modified_files(self) -> None:
        cwd = Path("/cwd")
        ops = FakeGitStatusOps(file_statuses={cwd: ([], ["file.py"], [])})
        assert ops.has_uncommitted_changes(cwd)

    def test_returns_true_with_untracked_files(self) -> None:
        cwd = Path("/cwd")
        ops = FakeGitStatusOps(file_statuses={cwd: ([], [], ["file.py"])})
        assert ops.has_uncommitted_changes(cwd)


class TestGetFileStatus:
    def test_returns_empty_lists_for_unknown_cwd(self) -> None:
        ops = FakeGitStatusOps()
        staged, modified, untracked = ops.get_file_status(Path("/cwd"))
        assert staged == []
        assert modified == []
        assert untracked == []

    def test_returns_configured_status(self) -> None:
        cwd = Path("/cwd")
        ops = FakeGitStatusOps(
            file_statuses={cwd: (["staged.py"], ["modified.py"], ["untracked.py"])}
        )
        staged, modified, untracked = ops.get_file_status(cwd)
        assert staged == ["staged.py"]
        assert modified == ["modified.py"]
        assert untracked == ["untracked.py"]


class TestCheckMergeConflicts:
    def test_returns_false_for_unknown_branches(self) -> None:
        ops = FakeGitStatusOps()
        assert not ops.check_merge_conflicts(Path("/cwd"), "main", "feature")

    def test_returns_configured_conflict_status(self) -> None:
        ops = FakeGitStatusOps(merge_conflicts={("main", "feature"): True})
        assert ops.check_merge_conflicts(Path("/cwd"), "main", "feature")


class TestGetConflictedFiles:
    def test_returns_empty_list_by_default(self) -> None:
        ops = FakeGitStatusOps()
        assert ops.get_conflicted_files(Path("/cwd")) == []

    def test_returns_configured_conflicted_files(self) -> None:
        ops = FakeGitStatusOps(conflicted_files=["file1.py", "file2.py"])
        assert ops.get_conflicted_files(Path("/cwd")) == ["file1.py", "file2.py"]


class TestLinkState:
    def test_links_to_external_state(self) -> None:
        ops = FakeGitStatusOps()
        repo = Path("/repo")
        cwd = Path("/cwd")

        # External state
        staged_repos: set[Path] = set()
        file_statuses: dict[Path, tuple[list[str], list[str], list[str]]] = {}
        merge_conflicts: dict[tuple[str, str], bool] = {}
        conflicted_files: list[str] = []

        ops.link_state(
            staged_repos=staged_repos,
            file_statuses=file_statuses,
            merge_conflicts=merge_conflicts,
            conflicted_files=conflicted_files,
        )

        # Modify external state
        staged_repos.add(repo)
        file_statuses[cwd] = (["file.py"], [], [])
        merge_conflicts[("main", "feature")] = True
        conflicted_files.append("conflict.py")

        # Verify ops sees changes
        assert ops.has_staged_changes(repo)
        assert ops.has_uncommitted_changes(cwd)
        assert ops.check_merge_conflicts(cwd, "main", "feature")
        assert ops.get_conflicted_files(cwd) == ["conflict.py"]
