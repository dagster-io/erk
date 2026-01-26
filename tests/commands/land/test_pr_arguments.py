"""Tests for erk land command with PR arguments.

The land command can accept:
- PR number (e.g., erk land 123)
- PR URL (e.g., erk land https://github.com/owner/repo/pull/123)
- Branch name (e.g., erk land feature-1)
"""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.types import PRDetails, PullRequestInfo
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata
from tests.test_utils.env_helpers import erk_inmem_env


def test_land_by_number() -> None:
    """Test erk land 123 outputs deferred execution script for PR by number."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        from pathlib import Path

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={env.cwd: "main"},  # Running from main, not feature-1
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch("feature-1", "main", commit_sha="def456"),
            }
        )

        github_ops = FakeGitHub(
            prs={
                "feature-1": PullRequestInfo(
                    number=123,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    title="Feature 1",
                    checks_passing=None,
                    owner="owner",
                    repo="repo",
                    has_conflicts=None,
                ),
            },
            pr_details={
                123: PRDetails(
                    number=123,
                    url="https://github.com/owner/repo/pull/123",
                    title="Feature 1",
                    body="PR body",
                    state="OPEN",
                    is_draft=False,
                    base_ref_name="main",
                    head_ref_name="feature-1",
                    is_cross_repository=False,
                    mergeable="MERGEABLE",
                    merge_state_status="CLEAN",
                    owner="owner",
                    repo="repo",
                )
            },
            pr_bases={123: "main"},
            merge_should_succeed=True,
        )

        issues_ops = FakeGitHubIssues(username="testuser")

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            issues=issues_ops,
        )

        # Pass "123" as the PR number argument with --force to skip confirmation
        result = runner.invoke(
            cli, ["land", "123", "--script", "--force"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0

        # Verify PR was NOT merged yet (deferred to script execution)
        assert 123 not in github_ops.merged_prs

        # Verify script was generated with correct parameters
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        assert "erk exec land-execute" in script_content
        # Script uses shell variables (passed as arguments to source command)
        assert '--pr-number="$PR_NUMBER"' in script_content
        assert '--branch="$BRANCH"' in script_content
        # Verify shell variable definitions
        assert 'PR_NUMBER="${1:?Error: PR number required}"' in script_content
        assert 'BRANCH="${2:?Error: Branch name required}"' in script_content


def test_land_by_url() -> None:
    """Test erk land <url> outputs deferred execution script for PR by URL."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        from pathlib import Path

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch("feature-1", "main", commit_sha="def456"),
            }
        )

        github_ops = FakeGitHub(
            prs={
                "feature-1": PullRequestInfo(
                    number=456,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/456",
                    is_draft=False,
                    title="Feature 1",
                    checks_passing=None,
                    owner="owner",
                    repo="repo",
                    has_conflicts=None,
                ),
            },
            pr_details={
                456: PRDetails(
                    number=456,
                    url="https://github.com/owner/repo/pull/456",
                    title="Feature 1",
                    body="PR body",
                    state="OPEN",
                    is_draft=False,
                    base_ref_name="main",
                    head_ref_name="feature-1",
                    is_cross_repository=False,
                    mergeable="MERGEABLE",
                    merge_state_status="CLEAN",
                    owner="owner",
                    repo="repo",
                )
            },
            pr_bases={456: "main"},
            merge_should_succeed=True,
        )

        issues_ops = FakeGitHubIssues(username="testuser")

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            issues=issues_ops,
        )

        # Pass URL as the argument
        result = runner.invoke(
            cli,
            ["land", "https://github.com/owner/repo/pull/456", "--script", "--force"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # Verify PR was NOT merged yet (deferred to script execution)
        assert 456 not in github_ops.merged_prs

        # Verify script was generated with correct parameters
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        assert "erk exec land-execute" in script_content
        # Script uses shell variables (passed as arguments to source command)
        assert '--pr-number="$PR_NUMBER"' in script_content
        assert '--branch="$BRANCH"' in script_content
        # Verify shell variable definitions
        assert 'PR_NUMBER="${1:?Error: PR number required}"' in script_content
        assert 'BRANCH="${2:?Error: Branch name required}"' in script_content


def test_land_by_branch_name() -> None:
    """Test erk land <branch> outputs deferred execution script for branch's PR."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        from pathlib import Path

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={env.cwd: "main"},  # Running from main
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch("feature-1", "main", commit_sha="def456"),
            }
        )

        github_ops = FakeGitHub(
            prs={
                "feature-1": PullRequestInfo(
                    number=123,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    title="Feature 1",
                    checks_passing=None,
                    owner="owner",
                    repo="repo",
                    has_conflicts=None,
                ),
            },
            pr_details={
                123: PRDetails(
                    number=123,
                    url="https://github.com/owner/repo/pull/123",
                    title="Feature 1",
                    body="PR body",
                    state="OPEN",
                    is_draft=False,
                    base_ref_name="main",
                    head_ref_name="feature-1",
                    is_cross_repository=False,
                    mergeable="MERGEABLE",
                    merge_state_status="CLEAN",
                    owner="owner",
                    repo="repo",
                )
            },
            pr_bases={123: "main"},
            merge_should_succeed=True,
        )

        issues_ops = FakeGitHubIssues(username="testuser")

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            issues=issues_ops,
        )

        result = runner.invoke(
            cli,
            ["land", "feature-1", "--script", "--force"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # Verify PR was NOT merged yet (deferred to script execution)
        assert 123 not in github_ops.merged_prs

        # Verify script was generated with correct parameters
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        assert "erk exec land-execute" in script_content
        # Script uses shell variables (passed as arguments to source command)
        assert '--pr-number="$PR_NUMBER"' in script_content
        assert '--branch="$BRANCH"' in script_content
        # Verify shell variable definitions
        assert 'PR_NUMBER="${1:?Error: PR number required}"' in script_content
        assert 'BRANCH="${2:?Error: Branch name required}"' in script_content


def test_land_fork_pr() -> None:
    """Test landing a fork PR outputs deferred script with pr/{number} branch naming."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        from pathlib import Path

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", repo_dir=repo_dir),
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", commit_sha="abc123"),
            }
        )

        # Fork PR - is_cross_repository=True
        github_ops = FakeGitHub(
            pr_details={
                789: PRDetails(
                    number=789,
                    url="https://github.com/owner/repo/pull/789",
                    title="Fork PR",
                    body="PR from fork",
                    state="OPEN",
                    is_draft=False,
                    base_ref_name="main",
                    head_ref_name="contributor-feature",  # Fork branch name
                    is_cross_repository=True,  # Fork PR
                    mergeable="MERGEABLE",
                    merge_state_status="CLEAN",
                    owner="owner",
                    repo="repo",
                )
            },
            pr_bases={789: "main"},
            merge_should_succeed=True,
        )

        issues_ops = FakeGitHubIssues(username="testuser")

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            issues=issues_ops,
        )

        result = runner.invoke(
            cli, ["land", "789", "--script", "--force"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0

        # Verify PR was NOT merged yet (deferred to script execution)
        assert 789 not in github_ops.merged_prs

        # Verify script was generated with correct parameters
        # For fork PRs, the branch name is "pr/{number}"
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        assert "erk exec land-execute" in script_content
        # Script uses shell variables (passed as arguments to source command)
        assert '--pr-number="$PR_NUMBER"' in script_content
        assert '--branch="$BRANCH"' in script_content
        # Verify shell variable definitions
        assert 'PR_NUMBER="${1:?Error: PR number required}"' in script_content
        assert 'BRANCH="${2:?Error: Branch name required}"' in script_content
