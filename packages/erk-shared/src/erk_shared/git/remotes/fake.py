"""Fake git remote operations for testing."""

from pathlib import Path

from erk_shared.git.remotes.abc import GitRemotes


class FakeGitRemotes(GitRemotes):
    """In-memory fake implementation of git remote operations.

    State Management:
    - remote_branches: dict[Path, dict[str, list[str]]] - repo_root -> remote -> branches
    - remote_urls: dict[Path, dict[str, str]] - repo_root -> remote -> URL

    Mutation Tracking:
    - fetched_branches: list[tuple[str, str]] - (remote, branch) pairs
    - pulled_branches: list[tuple[str, str, bool]] - (remote, branch, ff_only) tuples
    - pushed_branches: list[tuple[str, str, bool]] - (remote, branch, set_upstream) tuples
    - fetched_pr_refs: list[tuple[str, int, str]] - (remote, pr_number, local_branch) tuples
    """

    def __init__(
        self,
        *,
        remote_branches: dict[Path, dict[str, list[str]]] | None = None,
        remote_urls: dict[Path, dict[str, str]] | None = None,
    ) -> None:
        self._remote_branches = remote_branches or {}
        self._remote_urls = remote_urls or {}

        # Mutation tracking
        self._fetched_branches: list[tuple[str, str]] = []
        self._pulled_branches: list[tuple[str, str, bool]] = []
        self._pushed_branches: list[tuple[str, str, bool]] = []
        self._fetched_pr_refs: list[tuple[str, int, str]] = []

    def fetch_branch(self, repo_root: Path, remote: str, branch: str) -> None:
        self._fetched_branches.append((remote, branch))

    def pull_branch(self, repo_root: Path, remote: str, branch: str, *, ff_only: bool) -> None:
        self._pulled_branches.append((remote, branch, ff_only))

    def push_to_remote(
        self, cwd: Path, remote: str, branch: str, *, set_upstream: bool = False
    ) -> None:
        self._pushed_branches.append((remote, branch, set_upstream))

    def branch_exists_on_remote(self, repo_root: Path, remote: str, branch: str) -> bool:
        repo_remotes = self._remote_branches.get(repo_root, {})
        branches = repo_remotes.get(remote, [])
        return branch in branches

    def get_remote_url(self, repo_root: Path, remote: str = "origin") -> str:
        repo_urls = self._remote_urls.get(repo_root, {})
        if remote not in repo_urls:
            msg = f"Remote '{remote}' not found"
            raise ValueError(msg)
        return repo_urls[remote]

    def fetch_pr_ref(self, repo_root: Path, remote: str, pr_number: int, local_branch: str) -> None:
        self._fetched_pr_refs.append((remote, pr_number, local_branch))

    # Read-only properties for test assertions
    @property
    def fetched_branches(self) -> list[tuple[str, str]]:
        return self._fetched_branches.copy()

    @property
    def pulled_branches(self) -> list[tuple[str, str, bool]]:
        return self._pulled_branches.copy()

    @property
    def pushed_branches(self) -> list[tuple[str, str, bool]]:
        return self._pushed_branches.copy()

    @property
    def fetched_pr_refs(self) -> list[tuple[str, int, str]]:
        return self._fetched_pr_refs.copy()
