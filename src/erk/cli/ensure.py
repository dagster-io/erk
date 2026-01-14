"""CLI error handling utilities with styled output.

This module provides the Ensure class for asserting invariants in CLI commands
with consistent, user-friendly error messages. All errors use red "Error:" prefix
for visual consistency.

Domain-Specific Methods:
- Git state validations (branch checks, worktree existence, clean state)
- Configuration validations (required fields, format checks)
- Argument validations (count, type, range)
- File/path validations (readable, writable, not hidden)
- String/collection validations (non-empty, non-null)
- External tool validations (gh CLI installed)
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

import click

from erk_shared.gateway.graphite.disabled import GraphiteDisabled, GraphiteDisabledError
from erk_shared.github.types import PRDetails
from erk_shared.non_ideal_state import (
    BranchDetectionFailed,
    GitHubAPIFailed,
    NonIdealState,
    NoPRForBranch,
    PRNotFoundError,
    SessionNotFound,
)
from erk_shared.output.output import user_output

if TYPE_CHECKING:
    from erk.core.context import ErkContext

T = TypeVar("T")


class Ensure:
    """Helper class for asserting invariants with consistent error handling."""

    @staticmethod
    def invariant(condition: bool, error_message: str) -> None:
        """Ensure condition is true, otherwise output styled error and exit.

        Args:
            condition: Boolean condition to check
            error_message: Error message to display if condition is false.
                          "Error: " prefix will be added automatically in red.

        Raises:
            SystemExit: If condition is false (with exit code 1)
        """
        if not condition:
            user_output(click.style("Error: ", fg="red") + error_message)
            raise SystemExit(1)

    @staticmethod
    def truthy(value: T, error_message: str) -> T:
        """Ensure value is truthy, otherwise output styled error and exit.

        Args:
            value: Value to check for truthiness
            error_message: Error message to display if value is falsy.
                          "Error: " prefix will be added automatically in red.

        Returns:
            The value unchanged if truthy

        Raises:
            SystemExit: If value is falsy (with exit code 1)
        """
        if not value:
            user_output(click.style("Error: ", fg="red") + error_message)
            raise SystemExit(1)
        return value

    @staticmethod
    def not_none(value: T | None, error_message: str) -> T:
        """Ensure value is not None, otherwise output styled error and exit.

        This method provides type narrowing: it takes `T | None` and returns `T`,
        allowing the type checker to understand the value cannot be None after
        this call.

        Args:
            value: Value to check for None
            error_message: Error message to display if value is None.
                          "Error: " prefix will be added automatically in red.

        Returns:
            The value unchanged if not None (with narrowed type T)

        Raises:
            SystemExit: If value is None (with exit code 1)

        Example:
            >>> # Type narrowing in action
            >>> path: Path | None = get_worktree_path()
            >>> safe_path: Path = Ensure.not_none(path, "Worktree path not found")
            >>> # safe_path is now guaranteed to be Path, not Path | None
        """
        if value is None:
            user_output(click.style("Error: ", fg="red") + error_message)
            raise SystemExit(1)
        return value

    @staticmethod
    def path_exists(
        ctx: ErkContext,
        path: Path,
        error_message: str | None = None,
    ) -> None:
        """Ensure path exists, otherwise output styled error and exit.

        This method is designed for validating git-managed paths (worktrees, repos).
        It checks path existence before any operations that would fail on missing paths.

        Supports both real filesystem paths and sentinel paths used in tests by using
        ctx.git.path_exists, which works with both real paths and test sentinels.

        Args:
            ctx: Application context with git integration for path checking
            path: Path to check for existence
            error_message: Optional custom error message. If not provided,
                          uses default "Path not found: {path}".
                          "Error: " prefix will be added automatically in red.

        Raises:
            SystemExit: If path does not exist (with exit code 1)

        Example:
            >>> # Basic usage with default error message
            >>> Ensure.path_exists(ctx, config_path)
            >>>
            >>> # With custom error message
            >>> Ensure.path_exists(ctx, wt_path, f"Worktree not found: {wt_path}")
        """
        if not ctx.git.path_exists(path):
            if error_message is None:
                error_message = f"Path not found: {path}"
            user_output(click.style("Error: ", fg="red") + error_message)
            raise SystemExit(1)

    @staticmethod
    def not_empty(value: str | list | dict | None, error_message: str) -> None:
        """Ensure value is not empty (non-empty string, list, dict), otherwise exit.

        Args:
            value: Value to check for emptiness
            error_message: Error message to display if value is empty.
                          "Error: " prefix will be added automatically in red.

        Raises:
            SystemExit: If value is None, empty string, empty list, or empty dict

        Example:
            >>> Ensure.not_empty(name, "Worktree name cannot be empty")
            >>> Ensure.not_empty(args, "No arguments provided - specify at least one branch")
        """
        if not value:
            user_output(click.style("Error: ", fg="red") + error_message)
            raise SystemExit(1)

    @staticmethod
    def git_worktree_exists(ctx: ErkContext, wt_path: Path, name: str | None = None) -> None:
        """Ensure worktree exists at path, otherwise output styled error and exit.

        Args:
            ctx: Application context with git integration
            wt_path: Path where worktree should exist
            name: Optional worktree name for friendlier error message

        Raises:
            SystemExit: If worktree does not exist

        Example:
            >>> Ensure.git_worktree_exists(ctx, wt_path, "feature-123")
            >>> Ensure.git_worktree_exists(ctx, wt_path)  # Uses path in error
        """
        if name:
            error_message = f"Worktree '{name}' does not exist"
        else:
            error_message = f"Worktree not found: {wt_path}"
        Ensure.path_exists(ctx, wt_path, error_message)

    @staticmethod
    def git_branch_exists(ctx: ErkContext, repo_root: Path, branch: str) -> None:
        """Ensure git branch exists, otherwise output styled error and exit.

        Args:
            ctx: Application context with git integration
            repo_root: Repository root path
            branch: Branch name to check

        Raises:
            SystemExit: If branch does not exist

        Example:
            >>> Ensure.git_branch_exists(ctx, repo.root, "feature-branch")
        """
        local_branches = ctx.git.list_local_branches(repo_root)
        if branch not in local_branches:
            user_output(
                click.style("Error: ", fg="red")
                + f"Branch '{branch}' does not exist - Create it first or check the name"
            )
            raise SystemExit(1)

    @staticmethod
    def in_git_worktree(ctx: ErkContext, current_path: Path | None) -> None:
        """Ensure currently in a git worktree, otherwise output styled error and exit.

        Args:
            ctx: Application context (for error handling)
            current_path: Path to check (typically ctx.cwd or result of get_worktree_path)

        Raises:
            SystemExit: If not in a git worktree

        Example:
            >>> current_wt = ctx.git.get_worktree_path(repo.root, ctx.cwd)
            >>> Ensure.in_git_worktree(ctx, current_wt)
        """
        if current_path is None:
            user_output(
                click.style("Error: ", fg="red")
                + "Not in a git worktree - Run this command from within a worktree directory"
            )
            raise SystemExit(1)

    @staticmethod
    def argument_count(
        args: tuple[Any, ...] | list[Any],
        expected: int,
        error_message: str | None = None,
    ) -> None:
        """Ensure argument count matches expected, otherwise output styled error and exit.

        Args:
            args: Arguments tuple or list to check
            expected: Expected number of arguments
            error_message: Optional custom error message

        Raises:
            SystemExit: If argument count does not match expected

        Example:
            >>> Ensure.argument_count(args, 1, "Expected exactly 1 branch name")
            >>> Ensure.argument_count(args, 0, "This command takes no arguments")
        """
        if len(args) != expected:
            if error_message is None:
                if expected == 0:
                    error_message = f"Expected no arguments, got {len(args)}"
                elif expected == 1:
                    error_message = f"Expected 1 argument, got {len(args)}"
                else:
                    error_message = f"Expected {expected} arguments, got {len(args)}"
            user_output(click.style("Error: ", fg="red") + error_message)
            raise SystemExit(1)

    @staticmethod
    def config_field_set(
        config: Any,
        field_name: str,
        error_message: str | None = None,
    ) -> None:
        """Ensure configuration field is set, otherwise output styled error and exit.

        Args:
            config: Configuration object (must have __getattr__ or __getitem__)
            field_name: Name of the field to check
            error_message: Optional custom error message

        Raises:
            SystemExit: If field is not set (None or missing)

        Example:
            >>> Ensure.config_field_set(
            ...     ctx.local_config,
            ...     "github_token",
            ...     "GitHub token not configured - Run 'erk config set github_token <token>'"
            ... )
        """
        try:
            value = getattr(config, field_name, None)
        except AttributeError:
            try:
                value = config[field_name] if hasattr(config, "__getitem__") else None
            except (KeyError, TypeError):
                value = None

        if value is None:
            if error_message is None:
                error_message = (
                    f"Required configuration '{field_name}' not set - "
                    f"Run 'erk config set {field_name} <value>'"
                )
            user_output(click.style("Error: ", fg="red") + error_message)
            raise SystemExit(1)

    @staticmethod
    def path_is_dir(ctx: ErkContext, path: Path, error_message: str | None = None) -> None:
        """Ensure path exists and is a directory, otherwise output styled error and exit.

        Args:
            ctx: Application context with git integration
            path: Path to check
            error_message: Optional custom error message

        Raises:
            SystemExit: If path doesn't exist or is not a directory

        Example:
            >>> Ensure.path_is_dir(ctx, repo.worktrees_dir, "Worktrees directory not found")
        """
        Ensure.path_exists(ctx, path, error_message)
        if not path.is_dir():
            if error_message is None:
                error_message = f"Path is not a directory: {path}"
            user_output(click.style("Error: ", fg="red") + error_message)
            raise SystemExit(1)

    @staticmethod
    def path_not_exists(ctx: ErkContext, path: Path, error_message: str) -> None:
        """Ensure path does NOT exist, otherwise output styled error and exit.

        Inverse of path_exists - used when creating new resources that must not collide.

        Args:
            ctx: Application context with git integration
            path: Path to check should not exist
            error_message: Error message to display if path exists

        Raises:
            SystemExit: If path already exists

        Example:
            >>> Ensure.path_not_exists(
            ...     ctx,
            ...     new_path,
            ...     f"Destination already exists: {new_path} - "
            ...     f"Choose a different name or delete the existing path"
            ... )
        """
        if ctx.git.path_exists(path):
            user_output(click.style("Error: ", fg="red") + error_message)
            raise SystemExit(1)

    @staticmethod
    def gh_installed() -> None:
        """Ensure GitHub CLI (gh) is installed and available on PATH.

        Uses shutil.which to check for gh availability, which is the LBYL
        approach to validating external tool availability before use.

        Raises:
            SystemExit: If gh CLI is not found on PATH

        Example:
            >>> Ensure.gh_installed()
            >>> # Now safe to call gh commands
            >>> pr_info = ctx.github.get_pr_checkout_info(repo.root, pr_number)
        """
        if shutil.which("gh") is None:
            user_output(
                click.style("Error: ", fg="red")
                + "GitHub CLI (gh) is not installed\n\n"
                + "Install it from: https://cli.github.com/\n"
                + "Then authenticate with: gh auth login"
            )
            raise SystemExit(1)

    @staticmethod
    def gt_installed() -> None:
        """Ensure Graphite CLI (gt) is installed and available on PATH.

        Uses shutil.which to check for gt availability, which is the LBYL
        approach to validating external tool availability before use.

        Raises:
            SystemExit: If gt CLI is not found on PATH

        Example:
            >>> Ensure.gt_installed()
            >>> # Now safe to call gt commands
            >>> ctx.graphite.submit_stack(repo.root)
        """
        if shutil.which("gt") is None:
            user_output(
                click.style("Error: ", fg="red")
                + "Graphite CLI (gt) is not installed\n\n"
                + "Install it from: https://withgraphite.com/docs/getting-started\n"
                + "Or use: npm install -g @withgraphite/graphite-cli"
            )
            raise SystemExit(1)

    @staticmethod
    def graphite_available(ctx: ErkContext) -> None:
        """Ensure Graphite integration is available (enabled and installed).

        Checks if ctx.graphite is a GraphiteDisabled sentinel, and if so,
        outputs a helpful error message based on why Graphite is unavailable
        (config disabled vs not installed).

        This is the LBYL check for commands that require Graphite functionality.

        Args:
            ctx: Application context with graphite integration

        Raises:
            SystemExit: If Graphite is disabled or not installed

        Example:
            >>> Ensure.graphite_available(ctx)
            >>> # Now safe to use Graphite operations
            >>> ctx.graphite.get_parent_branch(ctx.git, repo.root, branch)
        """
        if isinstance(ctx.graphite, GraphiteDisabled):
            error = GraphiteDisabledError(ctx.graphite.reason)
            user_output(click.style("Error: ", fg="red") + str(error))
            raise SystemExit(1)

    @staticmethod
    def claude_installed() -> None:
        """Ensure Claude CLI is installed and available on PATH.

        Uses shutil.which to check for claude availability, which is the LBYL
        approach to validating external tool availability before use.

        Raises:
            SystemExit: If claude CLI is not found on PATH

        Example:
            >>> Ensure.claude_installed()
            >>> # Now safe to call claude commands
            >>> ctx.shell.run_claude_extraction_plan(cwd)
        """
        if shutil.which("claude") is None:
            user_output(
                click.style("Error: ", fg="red")
                + "Claude CLI is not installed\n\n"
                + "Install it from: https://claude.ai/download\n"
                + "Or skip extraction with: erk pr land --no-extract"
            )
            raise SystemExit(1)

    @staticmethod
    def gt_authenticated(ctx: ErkContext) -> None:
        """Ensure Graphite CLI (gt) is authenticated.

        Uses LBYL pattern to check gt authentication status before operations
        that require it (like gt submit).

        Args:
            ctx: Application context with graphite integration

        Raises:
            SystemExit: If gt is not authenticated

        Example:
            >>> Ensure.gt_authenticated(ctx)
            >>> # Now safe to call gt submit
            >>> ctx.graphite.submit_branch(repo.root, branch_name, quiet=True)
        """
        is_authenticated, username, _ = ctx.graphite.check_auth_status()

        if not is_authenticated:
            user_output(
                click.style("Error: ", fg="red")
                + "Graphite CLI (gt) is not authenticated\n\n"
                + "Authenticate with: gt auth\n\n"
                + "This is required before submitting branches or creating PRs."
            )
            raise SystemExit(1)

    @staticmethod
    def gh_authenticated(ctx: ErkContext) -> None:
        """Ensure GitHub CLI (gh) is installed and authenticated.

        Uses LBYL pattern to check gh installation and authentication status
        before operations that require it. This is the canonical check for
        GitHub CLI readiness - callers should use this single method rather
        than calling gh_installed() separately.

        Args:
            ctx: Application context with github integration

        Raises:
            SystemExit: If gh is not installed or not authenticated

        Example:
            >>> Ensure.gh_authenticated(ctx)
            >>> # Now safe to call gh commands
            >>> pr_info = ctx.github.get_pr_status(repo.root, branch)
        """
        Ensure.gh_installed()
        is_authenticated, username, _ = ctx.github.check_auth_status()

        if not is_authenticated:
            user_output(
                click.style("Error: ", fg="red")
                + "GitHub CLI (gh) is not authenticated\n\n"
                + "Authenticate with: gh auth login\n\n"
                + "This is required before submitting branches or creating PRs."
            )
            raise SystemExit(1)

    @staticmethod
    def ideal_state(result: T | NonIdealState) -> T:
        """Ensure result is not a NonIdealState, otherwise exit with error.

        This method provides type narrowing: it takes `T | NonIdealState` and
        returns `T`, allowing the type checker to understand the value cannot
        be a NonIdealState after this call.

        Args:
            result: Value that may be a NonIdealState

        Returns:
            The value unchanged if not NonIdealState (with narrowed type T)

        Raises:
            SystemExit: If result is NonIdealState (with exit code 1)

        Example:
            >>> from erk_shared.non_ideal_state import GitHubChecks
            >>> branch = Ensure.ideal_state(GitHubChecks.branch(raw_branch))
            >>> # branch is now guaranteed to be str, not str | BranchDetectionFailed
        """
        if isinstance(result, NonIdealState):
            user_output(click.style("Error: ", fg="red") + result.message)
            raise SystemExit(1)
        return result

    @staticmethod
    def branch(result: str | BranchDetectionFailed) -> str:
        """Ensure branch detection succeeded.

        Args:
            result: Branch name or BranchDetectionFailed

        Returns:
            The branch name

        Raises:
            SystemExit: If detection failed (with exit code 1)
        """
        if isinstance(result, BranchDetectionFailed):
            user_output(click.style("Error: ", fg="red") + result.message)
            raise SystemExit(1)
        return result

    @staticmethod
    def pr(result: PRDetails | NoPRForBranch | PRNotFoundError) -> PRDetails:
        """Ensure PR lookup succeeded.

        Args:
            result: PRDetails or a not-found error

        Returns:
            The PRDetails

        Raises:
            SystemExit: If PR not found (with exit code 1)
        """
        if isinstance(result, (NoPRForBranch, PRNotFoundError)):
            user_output(click.style("Error: ", fg="red") + result.message)
            raise SystemExit(1)
        return result

    @staticmethod
    def comments(result: list | GitHubAPIFailed) -> list:
        """Ensure comments fetch succeeded.

        Args:
            result: List of comments or GitHubAPIFailed

        Returns:
            The list of comments

        Raises:
            SystemExit: If API call failed (with exit code 1)
        """
        if isinstance(result, GitHubAPIFailed):
            user_output(click.style("Error: ", fg="red") + result.message)
            raise SystemExit(1)
        return result

    @staticmethod
    def void_op(result: None | GitHubAPIFailed) -> None:
        """Ensure void operation succeeded.

        Args:
            result: None (success) or GitHubAPIFailed

        Returns:
            None

        Raises:
            SystemExit: If API call failed (with exit code 1)
        """
        if isinstance(result, GitHubAPIFailed):
            user_output(click.style("Error: ", fg="red") + result.message)
            raise SystemExit(1)
        return result

    @staticmethod
    def session(result: T | SessionNotFound) -> T:
        """Ensure session lookup succeeded.

        Args:
            result: Session or SessionNotFound sentinel

        Returns:
            The Session

        Raises:
            SystemExit: If session not found (with exit code 1)
        """
        if isinstance(result, SessionNotFound):
            user_output(click.style("Error: ", fg="red") + result.message)
            raise SystemExit(1)
        return result

    @staticmethod
    def branch_graphite_tracked_or_new(
        ctx: ErkContext,
        repo_root: Path,
        branch: str,
        base_branch: str,
    ) -> None:
        """Ensure existing branch is Graphite-tracked when Graphite is enabled.

        Pre-flight check that prevents using an untracked branch with Graphite.
        This catches the common mistake of manually creating a git branch and then
        trying to use it with erk commands that expect Graphite tracking.

        If Graphite is disabled, this is a no-op.
        If branch doesn't exist locally, this is a no-op (will be created+tracked).
        If branch exists and IS tracked, this is a no-op.
        If branch exists and is NOT tracked, errors with remediation steps.

        Args:
            ctx: Application context with git and graphite integration
            repo_root: Repository root path
            branch: Branch name to check
            base_branch: The expected parent/base branch (for remediation message)

        Raises:
            SystemExit: If branch exists but is not Graphite-tracked
        """
        # Skip check if Graphite is disabled
        if isinstance(ctx.graphite, GraphiteDisabled):
            return

        # Check if branch exists locally
        local_branches = ctx.git.list_local_branches(repo_root)
        if branch not in local_branches:
            # Branch doesn't exist - will be created and tracked, so no issue
            return

        # Branch exists - check if it's tracked by Graphite
        all_branches = ctx.graphite.get_all_branches(ctx.git, repo_root)
        if branch in all_branches:
            # Branch is tracked - no issue
            return

        # Branch exists but is not tracked - error with remediation
        user_output(
            click.style("Error: ", fg="red")
            + f"Branch '{branch}' exists but is not tracked by Graphite.\n\n"
            + "This branch was created outside of erk/Graphite workflow. To proceed, either:\n\n"
            + "  1. Track it manually:\n"
            + f"     gt track --parent {base_branch}\n\n"
            + "  2. Delete it and let erk create it:\n"
            + f"     git branch -D {branch}\n\n"
            + "  3. Disable Graphite for this repository:\n"
            + "     erk config set use_graphite false"
        )
        raise SystemExit(1)
