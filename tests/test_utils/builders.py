"""Test data builders for common scenarios.

This module provides fluent APIs for building test data, reducing setup duplication
across the test suite. Use these builders instead of manually constructing complex
test scenarios.

Examples:
    # Build Graphite cache
    cache = (
        GraphiteCacheBuilder()
        .add_trunk("main", children=["feature"])
        .add_branch("feature", parent="main")
        .write_to(git_dir)
    )

    # Build PR with specific state
    pr = PullRequestInfoBuilder(123).with_failing_checks().as_draft().build()

    # Build complete test scenario
    scenario = (
        WorktreeScenario(tmp_path)
        .with_main_branch()
        .with_feature_branch("feature")
        .with_pr("feature", 123, checks_passing=True)
        .build()
    )
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PullRequestInfo
from erk_shared.integrations.graphite.fake import FakeGraphite
from erk_shared.integrations.graphite.types import BranchMetadata

from erk.core.config_store import GlobalConfig
from erk.core.context import context_for_test
from tests.fakes.shell import FakeShell


class GraphiteCacheBuilder:
    """Fluent API for building graphite cache structures.

    Use this builder to create .graphite_cache_persist files for testing without
    manually constructing the JSON structure.

    Examples:
        # Simple stack
        cache = (
            GraphiteCacheBuilder()
            .add_trunk("main")
            .add_branch("feature", parent="main")
            .build()
        )

        # Multi-level stack
        cache = (
            GraphiteCacheBuilder()
            .add_trunk("main", children=["level-1"])
            .add_branch("level-1", parent="main", children=["level-2"])
            .add_branch("level-2", parent="level-1")
            .write_to(git_dir)
        )
    """

    def __init__(self) -> None:
        """Initialize empty cache builder."""
        self._branches: list[tuple[str, dict[str, Any]]] = []
        self._trunk_branches: set[str] = set()

    def add_trunk(self, name: str, children: list[str] | None = None) -> "GraphiteCacheBuilder":
        """Add a trunk branch (main, master, develop).

        Args:
            name: Branch name
            children: Optional list of direct child branches

        Returns:
            Self for method chaining
        """
        self._trunk_branches.add(name)
        self._branches.append(
            (
                name,
                {
                    "validationResult": "TRUNK",
                    "children": children or [],
                },
            )
        )
        return self

    def add_branch(
        self, name: str, parent: str, children: list[str] | None = None
    ) -> "GraphiteCacheBuilder":
        """Add a feature branch with parent.

        Args:
            name: Branch name
            parent: Parent branch name
            children: Optional list of direct child branches

        Returns:
            Self for method chaining
        """
        self._branches.append(
            (
                name,
                {
                    "parentBranchName": parent,
                    "children": children or [],
                },
            )
        )
        return self

    def build(self) -> dict[str, Any]:
        """Build the graphite cache dictionary.

        Returns:
            Dictionary suitable for JSON serialization
        """
        return {"branches": self._branches}

    def write_to(self, git_dir: Path) -> Path:
        """Write cache to .graphite_cache_persist file.

        Args:
            git_dir: Path to .git directory

        Returns:
            Path to created cache file
        """
        cache_file = git_dir / ".graphite_cache_persist"
        cache_file.write_text(json.dumps(self.build()), encoding="utf-8")
        return cache_file


class PullRequestInfoBuilder:
    """Factory for creating PR test data with sensible defaults.

    Use this builder to create PullRequestInfo objects without manually specifying
    all fields.

    Examples:
        # PR with failing checks
        pr = PullRequestInfoBuilder(123).with_failing_checks().build()

        # Draft PR
        pr = PullRequestInfoBuilder(456).as_draft().build()

        # Merged PR
        pr = PullRequestInfoBuilder(789).as_merged().build()
    """

    def __init__(self, number: int, branch: str = "feature") -> None:
        """Initialize PR builder with required fields.

        Args:
            number: PR number
            branch: Branch name (default: "feature")
        """
        self.number = number
        self.branch = branch
        self.state = "OPEN"
        self.is_draft = False
        self.checks_passing: bool | None = None
        self.owner = "owner"
        self.repo = "repo"
        self.has_conflicts: bool | None = None
        self.will_close_target: bool = False

    def with_passing_checks(self) -> "PullRequestInfoBuilder":
        """Configure PR with passing checks.

        Returns:
            Self for method chaining
        """
        self.checks_passing = True
        return self

    def with_failing_checks(self) -> "PullRequestInfoBuilder":
        """Configure PR with failing checks.

        Returns:
            Self for method chaining
        """
        self.checks_passing = False
        return self

    def as_draft(self) -> "PullRequestInfoBuilder":
        """Configure PR as draft.

        Returns:
            Self for method chaining
        """
        self.is_draft = True
        return self

    def as_merged(self) -> "PullRequestInfoBuilder":
        """Configure PR as merged.

        Returns:
            Self for method chaining
        """
        self.state = "MERGED"
        return self

    def as_closed(self) -> "PullRequestInfoBuilder":
        """Configure PR as closed (not merged).

        Returns:
            Self for method chaining
        """
        self.state = "CLOSED"
        return self

    def with_conflicts(self) -> "PullRequestInfoBuilder":
        """Configure PR as having merge conflicts.

        Returns:
            Self for method chaining
        """
        self.has_conflicts = True
        return self

    def as_closing(self) -> "PullRequestInfoBuilder":
        """Configure PR as one that will close the linked issue when merged.

        Returns:
            Self for method chaining
        """
        self.will_close_target = True
        return self

    def build(self) -> PullRequestInfo:
        """Build PullRequestInfo object.

        Returns:
            Configured PullRequestInfo
        """
        return PullRequestInfo(
            number=self.number,
            state=self.state,
            url=f"https://github.com/{self.owner}/{self.repo}/pull/{self.number}",
            is_draft=self.is_draft,
            title=f"PR #{self.number}: {self.branch}",
            checks_passing=self.checks_passing,
            owner=self.owner,
            repo=self.repo,
            has_conflicts=self.has_conflicts,
            will_close_target=self.will_close_target,
        )


@dataclass
class WorktreeScenario:
    """Complete test scenario with worktrees, git ops, and context.

    This builder creates a full test environment including:
    - Directory structure (repo root, erks directory)
    - Fake operations (git, github, graphite, shell, config)
    - ErkContext ready for CLI testing

    Use this when you need a complete test setup. For simpler cases, consider
    using pytest fixtures instead.

    Examples:
        # Basic scenario
        scenario = (
            WorktreeScenario(tmp_path)
            .with_main_branch()
            .with_feature_branch("my-feature")
            .build()
        )
        result = runner.invoke(cli, ["list"], obj=scenario.ctx)

        # Scenario with PR and Graphite
        scenario = (
            WorktreeScenario(tmp_path)
            .with_main_branch()
            .with_feature_branch("my-feature")
            .with_pr("my-feature", number=123, checks_passing=True)
            .with_graphite_stack(["main", "my-feature"])
            .build()
        )
    """

    base_path: Path
    repo_name: str = "repo"

    def __post_init__(self) -> None:
        """Initialize directory structure and internal state."""
        self.repo_root = self.base_path / self.repo_name
        self.git_dir = self.repo_root / ".git"
        self.erk_root = self.base_path / "erks"
        self.repo_dir = self.erk_root / self.repo_name

        self._worktrees: dict[Path, list[WorktreeInfo]] = {}
        self._git_common_dirs: dict[Path, Path] = {}
        self._current_branches: dict[Path, str | None] = {}
        self._prs: dict[str, PullRequestInfo] = {}
        self._graphite_stacks: dict[str, list[str]] = {}
        self._use_graphite = False
        self._show_pr_info = False

    def with_main_branch(self, name: str = "main") -> "WorktreeScenario":
        """Add main/root worktree.

        Args:
            name: Branch name (default: "main")

        Returns:
            Self for method chaining
        """
        self.repo_root.mkdir(parents=True, exist_ok=True)
        self.git_dir.mkdir(parents=True, exist_ok=True)

        self._worktrees.setdefault(self.repo_root, []).append(
            WorktreeInfo(path=self.repo_root, branch=name, is_root=True)
        )
        self._git_common_dirs[self.repo_root] = self.git_dir
        self._current_branches[self.repo_root] = name
        return self

    def with_feature_branch(self, name: str, parent: str = "main") -> "WorktreeScenario":
        """Add feature branch worktree.

        Args:
            name: Branch name
            parent: Parent branch name (default: "main", not used by builder
                but available for context)

        Returns:
            Self for method chaining
        """
        worktree_path = self.repo_dir / name
        worktree_path.mkdir(parents=True, exist_ok=True)

        self._worktrees.setdefault(self.repo_root, []).append(
            WorktreeInfo(path=worktree_path, branch=name, is_root=False)
        )
        self._git_common_dirs[worktree_path] = self.git_dir
        self._current_branches[worktree_path] = name
        return self

    def with_pr(
        self,
        branch: str,
        number: int,
        checks_passing: bool | None = None,
        is_draft: bool = False,
        state: str = "OPEN",
    ) -> "WorktreeScenario":
        """Add PR for a branch.

        Args:
            branch: Branch name
            number: PR number
            checks_passing: Optional check status
            is_draft: Whether PR is draft
            state: PR state ("OPEN", "MERGED", "CLOSED")

        Returns:
            Self for method chaining
        """
        self._show_pr_info = True
        builder = PullRequestInfoBuilder(number, branch)
        builder.state = state
        builder.is_draft = is_draft
        builder.checks_passing = checks_passing
        self._prs[branch] = builder.build()
        return self

    def with_graphite_stack(self, branches: list[str]) -> "WorktreeScenario":
        """Add worktree stack for a branch (last branch is current).

        Args:
            branches: List of branch names from trunk to current

        Returns:
            Self for method chaining
        """
        self._use_graphite = True
        current_branch = branches[-1]
        self._graphite_stacks[current_branch] = branches
        return self

    def build(self) -> "WorktreeScenario":
        """Build the scenario and create fakes.

        Returns:
            Self with ctx attribute populated
        """
        self.git = FakeGit(
            worktrees=self._worktrees,
            git_common_dirs=self._git_common_dirs,
            current_branches=self._current_branches,
        )

        self.github = FakeGitHub(prs=self._prs)

        # PRs now come from Graphite, not GitHub
        self.graphite = FakeGraphite(stacks=self._graphite_stacks, pr_info=self._prs)

        global_config = GlobalConfig.test(
            self.erk_root,
            use_graphite=self._use_graphite,
            shell_setup_complete=False,
            show_pr_info=self._show_pr_info,
        )

        self.shell = FakeShell()

        self.ctx = context_for_test(
            git=self.git,
            global_config=global_config,
            github=self.github,
            graphite=self.graphite,
            shell=self.shell,
            cwd=self.repo_root,
            dry_run=False,
        )

        return self


class BranchStackBuilder:
    """Fluent builder for constructing BranchMetadata stacks.

    Simplifies creation of linear and tree-structured branch stacks
    for testing Graphite workflows.

    Examples:
        # Simple linear stack
        branches = BranchStackBuilder().add_linear_stack("feat-1", "feat-2").build()

        # Custom trunk
        branches = (
            BranchStackBuilder(trunk="develop")
            .add_linear_stack("feature-a", "feature-b")
            .build()
        )

        # Tree structure
        branches = (
            BranchStackBuilder()
            .add_branch("feat-1", parent="main", children=["feat-2a", "feat-2b"])
            .add_branch("feat-2a", parent="feat-1")
            .add_branch("feat-2b", parent="feat-1")
            .build()
        )

        # With commit SHAs
        branches = (
            BranchStackBuilder()
            .add_linear_stack("feat-1")
            .with_commit_sha("feat-1", "abc123")
            .build()
        )
    """

    def __init__(self, trunk: str = "main") -> None:
        """Initialize builder with trunk branch name.

        Args:
            trunk: Name of trunk branch (default: "main")
        """
        self._trunk = trunk
        self._branches: dict[str, BranchMetadata] = {}
        self._commit_shas: dict[str, str] = {}

    def add_linear_stack(self, *branches: str) -> "BranchStackBuilder":
        """Add branches in linear parent→child order.

        Creates chain: trunk → branch[0] → branch[1] → ... → branch[N]

        Args:
            *branches: Branch names in stack order (parent to child)

        Returns:
            Self for method chaining

        Example:
            >>> builder.add_linear_stack("feat-1", "feat-2", "feat-3")
            # Creates: main → feat-1 → feat-2 → feat-3
        """
        if not branches:
            return self

        # First branch has trunk as parent
        parent = self._trunk
        for i, branch in enumerate(branches):
            # Determine children
            children = [branches[i + 1]] if i < len(branches) - 1 else []

            self._branches[branch] = BranchMetadata.branch(
                name=branch, parent=parent, children=children
            )
            parent = branch

        return self

    def add_branch(
        self,
        name: str,
        parent: str,
        children: list[str] | None = None,
        commit_sha: str | None = None,
    ) -> "BranchStackBuilder":
        """Add a single branch with explicit parent and children.

        Args:
            name: Branch name
            parent: Parent branch name
            children: Optional list of child branch names
            commit_sha: Optional commit SHA for this branch

        Returns:
            Self for method chaining

        Example:
            >>> builder.add_branch("feat-1", parent="main", children=["feat-2a", "feat-2b"])
        """
        self._branches[name] = BranchMetadata.branch(
            name=name, parent=parent, children=children or []
        )

        if commit_sha is not None:
            self._commit_shas[name] = commit_sha

        return self

    def with_commit_sha(self, branch: str, sha: str) -> "BranchStackBuilder":
        """Set commit SHA for a branch.

        Args:
            branch: Branch name
            sha: Commit SHA

        Returns:
            Self for method chaining

        Raises:
            KeyError: If branch doesn't exist in the stack
        """
        if branch not in self._branches:
            raise KeyError(f"Branch '{branch}' not found in stack")

        self._commit_shas[branch] = sha
        return self

    def build(self) -> dict[str, BranchMetadata]:
        """Build and return the branch metadata dictionary.

        Creates trunk branch if not already present and applies any
        configured commit SHAs.

        Returns:
            Dictionary mapping branch names to BranchMetadata instances
        """
        # Determine trunk children (branches with trunk as parent)
        trunk_children = [
            name for name, metadata in self._branches.items() if metadata.parent == self._trunk
        ]

        # Create trunk branch with proper children
        result = {
            self._trunk: BranchMetadata.trunk(
                name=self._trunk,
                children=trunk_children,
                commit_sha=self._commit_shas.get(self._trunk),
            )
        }

        # Add all other branches, applying commit SHAs if configured
        for name, metadata in self._branches.items():
            # Parent should never be None for feature branches, but type-check requires guard
            if metadata.parent is None:
                continue

            if name in self._commit_shas:
                # Recreate with SHA
                result[name] = BranchMetadata.branch(
                    name=metadata.name,
                    parent=metadata.parent,
                    children=metadata.children,
                    commit_sha=self._commit_shas[name],
                )
            else:
                result[name] = metadata

        return result
