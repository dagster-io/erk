"""Workflow smoke test logic for erk doctor workflow.

Creates throwaway branches and PRs to verify the GitHub Actions
infrastructure works end-to-end. Core logic separated from CLI
for testability with fakes.
"""

from dataclasses import dataclass
from pathlib import Path

from erk.core.context import ErkContext, NoRepoSentinel, RepoContext
from erk_shared.gateway.git.remote_ops.types import PushError
from erk_shared.gateway.github.parsing import construct_workflow_run_url
from erk_shared.naming import format_branch_timestamp_suffix

ONE_SHOT_WORKFLOW = "one-shot.yml"
SMOKE_TEST_BRANCH_PREFIX = "smoke-test/"
SMOKE_TEST_PROMPT = "Add a code comment to any file."


@dataclass(frozen=True)
class SmokeTestResult:
    """Result of a successful smoke test dispatch."""

    branch_name: str
    pr_number: int
    run_id: str
    run_url: str | None


@dataclass(frozen=True)
class SmokeTestError:
    """Error during smoke test dispatch."""

    step: str
    message: str


@dataclass(frozen=True)
class CleanupItem:
    """A single smoke test artifact that was cleaned up."""

    branch_name: str
    pr_number: int | None
    closed_pr: bool
    deleted_branch: bool


def run_smoke_test(ctx: ErkContext) -> SmokeTestResult | SmokeTestError:
    """Create a throwaway branch + PR and dispatch one-shot workflow.

    Args:
        ctx: ErkContext with git/github gateways

    Returns:
        SmokeTestResult on success, SmokeTestError on failure
    """
    if isinstance(ctx.repo, NoRepoSentinel):
        return SmokeTestError(step="validation", message="Not in a git repository")
    repo: RepoContext = ctx.repo

    # Generate branch name: smoke-test/{MM-DD-HHMM}
    timestamp = format_branch_timestamp_suffix(ctx.time.now())
    # timestamp is like "-01-15-1430", strip leading dash for path segment
    branch_name = f"{SMOKE_TEST_BRANCH_PREFIX}{timestamp.lstrip('-')}"

    # Detect trunk branch
    trunk = ctx.git.branch.detect_trunk_branch(repo.root)

    # Create branch from trunk
    ctx.git.branch.create_branch(repo.root, branch_name, trunk, force=False)

    # Commit prompt file to branch (no checkout)
    ctx.git.commit.commit_files_to_branch(
        repo.root,
        branch=branch_name,
        files={".erk/impl-context/prompt.md": SMOKE_TEST_PROMPT + "\n"},
        message=f"Smoke test: {branch_name}",
    )

    # Push to remote
    push_result = ctx.git.remote.push_to_remote(
        repo.root, "origin", branch_name, set_upstream=True, force=False
    )
    if isinstance(push_result, PushError):
        return SmokeTestError(step="push", message=f"Failed to push branch: {push_result.message}")

    # Create draft PR
    pr_title = f"Smoke test: {timestamp.lstrip('-')}"
    pr_body = (
        "_Smoke test created by `erk doctor workflow --smoke-test`._\n\n"
        f"**Prompt:** {SMOKE_TEST_PROMPT}\n\n"
        "This PR can be safely closed and its branch deleted."
    )
    pr_number = ctx.github.create_pr(
        repo.root,
        branch_name,
        pr_title,
        pr_body,
        trunk,
        draft=True,
    )

    # Add erk-plan label
    ctx.github.add_label_to_pr(repo.root, pr_number, "erk-plan")

    # Get username for workflow inputs
    _, username, _ = ctx.github.check_auth_status()
    submitted_by = username or "unknown"

    # Build workflow inputs
    inputs: dict[str, str] = {
        "prompt": SMOKE_TEST_PROMPT,
        "branch_name": branch_name,
        "pr_number": str(pr_number),
        "submitted_by": submitted_by,
        "plan_backend": "planned_pr",
        "plan_issue_number": str(pr_number),
    }

    # Trigger workflow
    run_id = ctx.github.trigger_workflow(
        repo_root=repo.root,
        workflow=ONE_SHOT_WORKFLOW,
        inputs=inputs,
        ref=None,
    )

    # Compute run URL
    run_url: str | None = None
    if repo.github is not None:
        run_url = construct_workflow_run_url(repo.github.owner, repo.github.repo, run_id)

    return SmokeTestResult(
        branch_name=branch_name,
        pr_number=pr_number,
        run_id=run_id,
        run_url=run_url,
    )


def cleanup_smoke_tests(ctx: ErkContext) -> list[CleanupItem]:
    """Find and remove smoke test branches and their PRs.

    Args:
        ctx: ErkContext with git/github gateways

    Returns:
        List of cleaned up items
    """
    if isinstance(ctx.repo, NoRepoSentinel):
        return []
    repo: RepoContext = ctx.repo

    # List remote branches matching smoke-test/*
    remote_branches = ctx.git.branch.list_remote_branches(repo.root)
    smoke_branches = [
        b for b in remote_branches if _extract_branch_name(b).startswith(SMOKE_TEST_BRANCH_PREFIX)
    ]

    if not smoke_branches:
        return []

    cleaned: list[CleanupItem] = []
    for remote_branch in smoke_branches:
        branch_name = _extract_branch_name(remote_branch)

        # Find associated PR
        pr_number = _find_pr_for_branch(ctx, repo.root, branch_name)

        closed_pr = False
        if pr_number is not None:
            ctx.github.close_pr(repo.root, pr_number)
            closed_pr = True

        # Delete remote branch
        deleted = ctx.github.delete_remote_branch(repo.root, branch_name)

        cleaned.append(
            CleanupItem(
                branch_name=branch_name,
                pr_number=pr_number,
                closed_pr=closed_pr,
                deleted_branch=deleted,
            )
        )

    return cleaned


def _extract_branch_name(remote_branch: str) -> str:
    """Extract branch name from remote branch ref.

    Remote branches come as 'origin/branch-name'. Strip the remote prefix.
    """
    if "/" in remote_branch:
        # origin/smoke-test/01-15-1430 -> smoke-test/01-15-1430
        return remote_branch.split("/", 1)[1]
    return remote_branch


def _find_pr_for_branch(ctx: ErkContext, repo_root: Path, branch_name: str) -> int | None:
    """Find the PR number associated with a branch, if any."""
    prs = ctx.github.list_prs(repo_root, state="all")
    if branch_name in prs:
        return prs[branch_name].number
    return None
