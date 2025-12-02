"""Tests for erk create command output behavior."""

from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from erk_shared.github.issues import FakeGitHubIssues, IssueInfo

from erk.cli.cli import cli
from tests.fakes.issue_link_branches import FakeIssueLinkBranches
from tests.test_utils.env_helpers import erk_inmem_env, erk_isolated_fs_env


def test_create_from_current_branch_outputs_script_path_to_stdout() -> None:
    """Test that create --from-current-branch outputs script path to stdout, not stderr.

    This test verifies that the shell integration handler can read the script path
    from stdout. If the script path is written to stderr, the handler will miss it
    and display 'no directory change needed' instead of switching to the new worktree.

    See: https://github.com/anthropics/erk/issues/XXX
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / "repos" / env.cwd.name

        # Set up git state: in root worktree on feature branch
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            current_branches={env.cwd: "my-feature"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        test_ctx = env.build_context(git=git_ops)

        # Act: Create worktree from current branch with --script flag
        result = runner.invoke(
            cli,
            ["wt", "create", "--from-current-branch", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Command succeeded
        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")
        assert result.exit_code == 0

        # Assert: Script path is in stdout (for shell integration)
        assert result.stdout.strip() != "", (
            "Script path should be in stdout for shell integration to read. "
            "Currently it's being written to stderr via user_output(), "
            "but should be written to stdout via machine_output()."
        )

        # Assert: Script path is a valid path to activation script
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None, "Script path should reference a valid script"

        # Assert: Script contains cd command to new worktree
        expected_worktree_path = repo_dir / "worktrees" / "my-feature"
        assert str(expected_worktree_path) in script_content, (
            f"Script should cd to {expected_worktree_path}"
        )


def test_create_from_issue_with_valid_issue() -> None:
    """Test erk create --from-issue with valid erk-plan issue."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.erk_root / "repos" / env.cwd.name

        # Set up git state
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up GitHub state with issue
        now = datetime.now(UTC)
        fake_issues = FakeGitHubIssues(
            issues={
                123: IssueInfo(
                    number=123,
                    title="Add User Authentication",
                    body="## Implementation\n\n- Step 1\n- Step 2",
                    state="OPEN",
                    url="https://github.com/owner/repo/issues/123",
                    labels=["erk-plan"],
                    assignees=[],
                    created_at=now,
                    updated_at=now,
                )
            }
        )

        fake_issue_dev = FakeIssueLinkBranches()

        test_ctx = env.build_context(
            git=git_ops, issues=fake_issues, issue_link_branches=fake_issue_dev
        )

        # Act: Run create --from-issue 123
        result = runner.invoke(
            cli,
            ["wt", "create", "--from-issue", "123"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Command succeeded
        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")
        assert result.exit_code == 0

        # Assert: Worktree created with branch name derived from issue title
        # Branch name is sanitize_worktree_name(...) + timestamp suffix "-01-15-1430"
        # "123-Add User Authentication" -> "123-add-user-authentication-01-15-1430"
        worktrees_dir = repo_dir / "worktrees"
        expected_worktree_path = worktrees_dir / "123-add-user-authentication-01-15-1430"
        assert expected_worktree_path.exists(), (
            f"Expected worktree at {expected_worktree_path}, found: {list(worktrees_dir.glob('*'))}"
        )

        # Assert: .impl/ folder exists with correct content
        impl_path = expected_worktree_path / ".impl"
        assert impl_path.exists()

        # Assert: plan.md has issue body
        plan_path = impl_path / "plan.md"
        assert plan_path.exists()
        plan_content = plan_path.read_text(encoding="utf-8")
        assert "## Implementation" in plan_content

        # Assert: issue.json has metadata
        issue_json_path = impl_path / "issue.json"
        assert issue_json_path.exists()
        import json

        issue_json = json.loads(issue_json_path.read_text(encoding="utf-8"))
        assert issue_json["number"] == 123
        assert issue_json["title"] == "Add User Authentication"
        assert issue_json["url"] == "https://github.com/owner/repo/issues/123"


def test_create_from_issue_missing_label() -> None:
    """Test erk create --from-issue fails if issue lacks erk-plan label."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Set up git state
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up GitHub state with issue without erk-plan label
        now = datetime.now(UTC)
        fake_issues = FakeGitHubIssues(
            issues={
                456: IssueInfo(
                    number=456,
                    title="Regular Issue",
                    body="Not a plan",
                    state="OPEN",
                    url="https://github.com/owner/repo/issues/456",
                    labels=["bug", "enhancement"],  # No erk-plan label
                    assignees=[],
                    created_at=now,
                    updated_at=now,
                )
            }
        )

        test_ctx = env.build_context(git=git_ops, issues=fake_issues)

        # Act: Run create --from-issue 456
        result = runner.invoke(
            cli,
            ["wt", "create", "--from-issue", "456"],
            obj=test_ctx,
        )

        # Assert: Error message about missing label
        assert result.exit_code == 1
        assert "must have 'erk-plan' label" in result.output
        assert "gh issue edit 456 --add-label erk-plan" in result.output


def test_create_from_issue_url_parsing() -> None:
    """Test erk create --from-issue with GitHub URL."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Set up git state
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up GitHub state with issue
        now = datetime.now(UTC)
        fake_issues = FakeGitHubIssues(
            issues={
                789: IssueInfo(
                    number=789,
                    title="Feature Request",
                    body="Plan content",
                    state="OPEN",
                    url="https://github.com/owner/repo/issues/789",
                    labels=["erk-plan"],
                    assignees=[],
                    created_at=now,
                    updated_at=now,
                )
            }
        )

        # FakeIssueLinkBranches creates branches named "{issue_number}-issue-branch"
        fake_issue_dev = FakeIssueLinkBranches()

        test_ctx = env.build_context(
            git=git_ops, issues=fake_issues, issue_link_branches=fake_issue_dev
        )

        # Act: Run with full GitHub URL
        result = runner.invoke(
            cli,
            ["wt", "create", "--from-issue", "https://github.com/owner/repo/issues/789"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Success (URL parsed correctly)
        assert result.exit_code == 0
        # Branch name derived from issue title: "789-Feature Request" -> "789-feature-request"
        assert "Created worktree" in result.output or "789-feature-request" in result.output


def test_create_from_issue_name_derivation() -> None:
    """Test worktree name derived from issue title via sanitize_worktree_name."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.erk_root / "repos" / env.cwd.name

        # Set up git state
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up GitHub state with issue with special characters in title
        now = datetime.now(UTC)
        fake_issues = FakeGitHubIssues(
            issues={
                111: IssueInfo(
                    number=111,
                    title="Fix: Database Connection Issues!!!",
                    body="Plan",
                    state="OPEN",
                    url="https://github.com/owner/repo/issues/111",
                    labels=["erk-plan"],
                    assignees=[],
                    created_at=now,
                    updated_at=now,
                )
            }
        )

        fake_issue_dev = FakeIssueLinkBranches()

        test_ctx = env.build_context(
            git=git_ops, issues=fake_issues, issue_link_branches=fake_issue_dev
        )

        # Act
        result = runner.invoke(
            cli,
            ["wt", "create", "--from-issue", "111"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Name = sanitize_worktree_name(...) + timestamp suffix "-01-15-1430"
        # "111-Fix: Database..." -> "111-fix-database-connection-iss-01-15-1430"
        assert result.exit_code == 0
        worktrees_dir = repo_dir / "worktrees"
        expected_worktree_path = worktrees_dir / "111-fix-database-connection-iss-01-15-1430"
        assert expected_worktree_path.exists(), (
            f"Expected worktree at {expected_worktree_path}, found: {list(worktrees_dir.glob('*'))}"
        )


def test_create_from_issue_not_found() -> None:
    """Test erk create --from-issue when issue doesn't exist."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Set up git state
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up GitHub state with no issues
        fake_issues = FakeGitHubIssues()  # Empty

        test_ctx = env.build_context(git=git_ops, issues=fake_issues)

        # Act: Request non-existent issue
        result = runner.invoke(
            cli,
            ["wt", "create", "--from-issue", "999"],
            obj=test_ctx,
        )

        # Assert: Error from integration layer
        assert result.exit_code == 1
        # FakeGitHubIssues raises RuntimeError with "not found" message
        assert "not found" in result.output.lower() or "Issue #999" in result.output


def test_create_from_issue_readonly_operation() -> None:
    """Test that --from-issue doesn't create/modify issues."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Set up git state
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up GitHub state with issue
        now = datetime.now(UTC)
        fake_issues = FakeGitHubIssues(
            issues={
                222: IssueInfo(
                    number=222,
                    title="Test",
                    body="Body",
                    state="OPEN",
                    url="https://example.com",
                    labels=["erk-plan"],
                    assignees=[],
                    created_at=now,
                    updated_at=now,
                )
            }
        )

        # FakeIssueLinkBranches creates branches named "{issue_number}-issue-branch"
        fake_issue_dev = FakeIssueLinkBranches()

        test_ctx = env.build_context(
            git=git_ops, issues=fake_issues, issue_link_branches=fake_issue_dev
        )

        # Act
        result = runner.invoke(
            cli,
            ["wt", "create", "--from-issue", "222"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Command succeeded
        assert result.exit_code == 0

        # Assert: No issues created
        assert len(fake_issues.created_issues) == 0
        # Assert: No comments added
        assert len(fake_issues.added_comments) == 0


def test_create_from_issue_tracks_branch_with_graphite() -> None:
    """Test erk create --from-issue calls ctx.graphite.track_branch() when use_graphite=True.

    Verifies that when:
    1. use_graphite=True in global config
    2. erk wt create --from-issue <issue> is called
    3. Then ctx.graphite.track_branch() is called with the linked branch name and trunk as parent
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.erk_root / "repos" / env.cwd.name

        # Set up git state
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up GitHub state with issue
        now = datetime.now(UTC)
        fake_issues = FakeGitHubIssues(
            issues={
                500: IssueInfo(
                    number=500,
                    title="Test Graphite Tracking",
                    body="## Plan\n\n- Step 1",
                    state="OPEN",
                    url="https://github.com/owner/repo/issues/500",
                    labels=["erk-plan"],
                    assignees=[],
                    created_at=now,
                    updated_at=now,
                )
            }
        )

        fake_issue_dev = FakeIssueLinkBranches()

        # Create FakeGraphite to track calls
        from erk_shared.integrations.graphite.fake import FakeGraphite

        fake_graphite = FakeGraphite()

        # Build context with use_graphite=True
        test_ctx = env.build_context(
            git=git_ops,
            issues=fake_issues,
            issue_link_branches=fake_issue_dev,
            graphite=fake_graphite,
            use_graphite=True,
        )

        # Act: Run create --from-issue 500
        result = runner.invoke(
            cli,
            ["wt", "create", "--from-issue", "500"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Command succeeded
        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")
        assert result.exit_code == 0

        # Assert: Worktree was created
        worktrees_dir = repo_dir / "worktrees"
        assert worktrees_dir.exists(), f"Worktrees dir should exist: {worktrees_dir}"

        # Assert: track_branch was called with correct parameters
        # The branch name is derived from issue title with timestamp suffix
        # Parent should be "main" (the trunk branch)
        assert len(fake_graphite.track_branch_calls) == 1, (
            f"Expected 1 track_branch call, got {len(fake_graphite.track_branch_calls)}: "
            f"{fake_graphite.track_branch_calls}"
        )

        call = fake_graphite.track_branch_calls[0]
        cwd_path, branch_name, parent_branch = call

        # Branch name should contain the issue number
        assert "500" in branch_name, f"Branch name should contain issue number: {branch_name}"

        # Parent should be trunk branch (main)
        assert parent_branch == "main", f"Parent branch should be 'main', got: {parent_branch}"


def test_create_from_issue_no_graphite_tracking_when_disabled() -> None:
    """Test erk create --from-issue does NOT call track_branch when use_graphite=False."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Set up git state
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up GitHub state with issue
        now = datetime.now(UTC)
        fake_issues = FakeGitHubIssues(
            issues={
                501: IssueInfo(
                    number=501,
                    title="Test No Graphite",
                    body="## Plan\n\n- Step 1",
                    state="OPEN",
                    url="https://github.com/owner/repo/issues/501",
                    labels=["erk-plan"],
                    assignees=[],
                    created_at=now,
                    updated_at=now,
                )
            }
        )

        fake_issue_dev = FakeIssueLinkBranches()

        # Create FakeGraphite to track calls
        from erk_shared.integrations.graphite.fake import FakeGraphite

        fake_graphite = FakeGraphite()

        # Build context with use_graphite=False (default)
        test_ctx = env.build_context(
            git=git_ops,
            issues=fake_issues,
            issue_link_branches=fake_issue_dev,
            graphite=fake_graphite,
            use_graphite=False,  # Explicitly disabled
        )

        # Act: Run create --from-issue 501
        result = runner.invoke(
            cli,
            ["wt", "create", "--from-issue", "501"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Command succeeded
        assert result.exit_code == 0

        # Assert: track_branch was NOT called (Graphite disabled)
        assert len(fake_graphite.track_branch_calls) == 0, (
            f"Expected no track_branch calls when Graphite disabled, "
            f"got: {fake_graphite.track_branch_calls}"
        )


def test_create_with_from_branch_trunk_errors() -> None:
    """Test that create --from-branch prevents creating worktree for trunk branch.

    This test verifies that ensure_worktree_for_branch() validation catches
    attempts to create a worktree for the trunk branch via --from-branch flag.
    The error should match the one from checkout command for consistency.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Setup: root worktree on a feature branch (NOT trunk)
        # This way we can test creating a worktree for trunk without "already checked out" error
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="feature-1"),
                ]
            },
            current_branches={env.cwd: "feature-1"},
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-1"]},
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops)

        # Try to create worktree from trunk branch - should error
        result = runner.invoke(
            cli,
            ["wt", "create", "foo", "--from-branch", "main"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Should fail with error
        assert result.exit_code == 1

        # Error message should match checkout command for consistency
        assert "Cannot create worktree for trunk branch" in result.stderr
        assert "main" in result.stderr
        assert "erk checkout root" in result.stderr
        assert "root worktree" in result.stderr

        # Verify no worktree was created
        assert len(git_ops.added_worktrees) == 0


def test_create_from_current_branch_shows_shell_integration_instructions() -> None:
    """Test that create --from-current-branch shows setup instructions without --script."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Set up git state: in root worktree on feature branch
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            current_branches={env.cwd: "my-feature"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        test_ctx = env.build_context(git=git_ops)

        # Act: Create worktree from current branch WITHOUT --script flag
        result = runner.invoke(
            cli,
            ["wt", "create", "--from-current-branch"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Command succeeded
        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")
        assert result.exit_code == 0

        # Assert: Output contains shell integration setup instructions
        assert "Shell integration not detected" in result.stderr
        assert "erk init --shell" in result.stderr
        assert "source <(erk wt create --from-current-branch --script)" in result.stderr


def test_create_from_current_branch_with_stay_flag() -> None:
    """Test that create --from-current-branch --stay shows minimal output."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Set up git state: in root worktree on feature branch
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            current_branches={env.cwd: "my-feature"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        test_ctx = env.build_context(git=git_ops)

        # Act: Create worktree with --stay flag
        result = runner.invoke(
            cli,
            ["wt", "create", "--from-current-branch", "--stay"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Command succeeded
        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")
        assert result.exit_code == 0

        # Assert: Output contains only creation message, no navigation instructions
        assert "Created worktree at" in result.stderr
        assert "Shell integration not detected" not in result.stderr
        assert "erk init --shell" not in result.stderr
        assert "source <(" not in result.stderr
