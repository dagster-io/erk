"""Health check implementations for erk doctor command.

This module provides diagnostic checks for erk setup, including
CLI availability, repository configuration, and Claude settings.

Submodules:
    models                    - CheckResult dataclass
    erk_version               - check_erk_version
    required_tool_version     - check_required_tool_version
    claude_cli                - check_claude_cli
    graphite_cli              - check_graphite_cli
    github_cli                - check_github_cli
    github_auth               - check_github_auth
    workflow_permissions       - check_workflow_permissions
    erk_queue_pat_secret      - check_erk_queue_pat_secret
    anthropic_api_secret      - check_anthropic_api_secret
    uv_version                - check_uv_version
    hooks_disabled            - check_hooks_disabled
    statusline_configured     - check_statusline_configured
    gitignore_entries         - check_gitignore_entries
    post_plan_implement_ci_hook - check_post_plan_implement_ci_hook
    post_init_hook            - check_post_init_hook
    legacy_prompt_hooks       - check_legacy_prompt_hooks
    claude_erk_permission     - check_claude_erk_permission
    plans_repo_labels         - check_plans_repo_labels
    repository                - check_repository
    claude_settings           - check_claude_settings
    user_prompt_hook          - check_user_prompt_hook
    exit_plan_hook            - check_exit_plan_hook
    hook_health               - check_hook_health
    managed_artifacts         - check_managed_artifacts
    legacy_slot_naming        - check_legacy_slot_naming
"""

from erk.artifacts.paths import ErkPackageInfo
from erk.artifacts.state import load_installed_capabilities
from erk.core.context import ErkContext
from erk.core.health_checks.anthropic_api_secret import check_anthropic_api_secret
from erk.core.health_checks.claude_cli import check_claude_cli
from erk.core.health_checks.claude_erk_permission import check_claude_erk_permission
from erk.core.health_checks.claude_settings import check_claude_settings
from erk.core.health_checks.erk_queue_pat_secret import check_erk_queue_pat_secret
from erk.core.health_checks.erk_version import check_erk_version
from erk.core.health_checks.exit_plan_hook import check_exit_plan_hook
from erk.core.health_checks.github_auth import check_github_auth
from erk.core.health_checks.github_cli import check_github_cli
from erk.core.health_checks.gitignore_entries import check_gitignore_entries
from erk.core.health_checks.graphite_cli import check_graphite_cli
from erk.core.health_checks.hook_health import check_hook_health
from erk.core.health_checks.hooks_disabled import check_hooks_disabled
from erk.core.health_checks.legacy_prompt_hooks import check_legacy_prompt_hooks
from erk.core.health_checks.legacy_slot_naming import check_legacy_slot_naming
from erk.core.health_checks.managed_artifacts import check_managed_artifacts
from erk.core.health_checks.models import CheckResult
from erk.core.health_checks.plans_repo_labels import check_plans_repo_labels
from erk.core.health_checks.post_init_hook import check_post_init_hook
from erk.core.health_checks.post_plan_implement_ci_hook import check_post_plan_implement_ci_hook
from erk.core.health_checks.repository import check_repository
from erk.core.health_checks.required_tool_version import check_required_tool_version
from erk.core.health_checks.statusline_configured import check_statusline_configured
from erk.core.health_checks.user_prompt_hook import check_user_prompt_hook
from erk.core.health_checks.uv_version import check_uv_version
from erk.core.health_checks.workflow_permissions import check_workflow_permissions
from erk.core.repo_discovery import RepoContext

__all__ = [
    "CheckResult",
    "check_anthropic_api_secret",
    "check_claude_cli",
    "check_claude_erk_permission",
    "check_claude_settings",
    "check_erk_queue_pat_secret",
    "check_erk_version",
    "check_exit_plan_hook",
    "check_gitignore_entries",
    "check_github_auth",
    "check_github_cli",
    "check_graphite_cli",
    "check_hook_health",
    "check_hooks_disabled",
    "check_legacy_prompt_hooks",
    "check_legacy_slot_naming",
    "check_managed_artifacts",
    "check_plans_repo_labels",
    "check_post_init_hook",
    "check_post_plan_implement_ci_hook",
    "check_repository",
    "check_required_tool_version",
    "check_statusline_configured",
    "check_user_prompt_hook",
    "check_uv_version",
    "check_workflow_permissions",
    "run_all_checks",
]


def run_all_checks(ctx: ErkContext, *, check_hooks: bool) -> list[CheckResult]:
    """Run all health checks and return results.

    Args:
        ctx: ErkContext for repository checks (includes github_admin)
        check_hooks: If True, include hook execution health check

    Returns:
        List of CheckResult objects
    """
    shell = ctx.shell
    admin = ctx.github_admin

    claude_installation = ctx.claude_installation

    results = [
        check_erk_version(),
        check_claude_cli(shell),
        check_graphite_cli(shell),
        check_github_cli(shell),
        check_github_auth(shell, admin),
        check_uv_version(shell),
        check_hooks_disabled(claude_installation),
        check_statusline_configured(claude_installation),
    ]

    # Add repository check
    results.append(check_repository(ctx))

    # Check Claude settings, gitignore, and GitHub checks if we're in a repo
    # (get_git_common_dir returns None if not in a repo)
    git_dir = ctx.git.repo.get_git_common_dir(ctx.cwd)
    if git_dir is not None:
        repo_root = ctx.git.repo.get_repository_root(ctx.cwd)
        results.append(check_claude_erk_permission(repo_root))
        results.append(check_claude_settings(repo_root))
        results.append(check_user_prompt_hook(repo_root))
        results.append(check_exit_plan_hook(repo_root))
        results.append(check_gitignore_entries(repo_root))
        results.append(check_required_tool_version(repo_root))
        results.append(check_legacy_prompt_hooks(repo_root))
        results.append(check_post_plan_implement_ci_hook(repo_root))
        results.append(check_post_init_hook(repo_root))
        # Hook health check (opt-in via --check-hooks)
        if check_hooks:
            results.append(check_hook_health(repo_root))
        # GitHub workflow permissions check (requires repo context)
        results.append(check_workflow_permissions(ctx, repo_root, admin))
        # ERK_QUEUE_GH_PAT secret check (required for remote implementation)
        results.append(check_erk_queue_pat_secret(ctx, repo_root, admin))
        # Anthropic API secret check (required for Claude in GitHub Actions)
        results.append(check_anthropic_api_secret(ctx, repo_root, admin))
        # Managed artifacts check (consolidated from orphaned + missing)
        package = ErkPackageInfo.from_project_dir(repo_root)
        managed_capabilities: frozenset[str] | None = None
        if not package.in_erk_repo:
            managed_capabilities = load_installed_capabilities(repo_root)
        results.append(
            check_managed_artifacts(
                repo_root,
                package=package,
                installed_capabilities=managed_capabilities,
            )
        )

        # Check plans_repo labels if configured
        from erk.cli.config import load_config as load_repo_config
        from erk_shared.gateway.github.issues.real import RealGitHubIssues

        repo_config = load_repo_config(repo_root)
        if repo_config.plans_repo is not None:
            from erk_shared.gateway.time.real import RealTime

            github_issues = RealGitHubIssues(target_repo=repo_config.plans_repo, time=RealTime())
            results.append(
                check_plans_repo_labels(repo_root, repo_config.plans_repo, github_issues)
            )

        from erk.core.health_checks_dogfooder import run_early_dogfooder_checks

        # Get metadata_dir if we have a RepoContext (for legacy config detection)
        metadata_dir = ctx.repo.repo_dir if isinstance(ctx.repo, RepoContext) else None
        results.extend(run_early_dogfooder_checks(repo_root, metadata_dir))

        # Legacy slot naming check (requires RepoContext)
        if isinstance(ctx.repo, RepoContext):
            results.append(check_legacy_slot_naming(ctx.repo))

    return results
