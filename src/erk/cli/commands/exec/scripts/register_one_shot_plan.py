"""Register a one-shot plan: dispatch metadata, queued comment, PR closing ref.

Composes three independent operations that ``erk plan submit`` performs but
one-shot cannot do at submit time (the plan issue doesn't exist yet).
Each operation is best-effort; failures are logged but don't block others.
"""

import json
from datetime import UTC, datetime

import click

from erk.cli.commands.pr.metadata_helpers import write_dispatch_metadata
from erk.cli.config import load_config
from erk_shared.context.helpers import (
    require_github,
    require_issues,
    require_plan_backend,
    require_repo_root,
)
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.types import PRNotFound


@click.command(name="register-one-shot-plan")
@click.option("--issue-number", type=int, required=True)
@click.option("--run-id", type=str, required=True)
@click.option("--pr-number", type=int, required=True)
@click.option("--submitted-by", type=str, required=True)
@click.option("--run-url", type=str, required=True)
@click.pass_context
def register_one_shot_plan(
    ctx: click.Context,
    *,
    issue_number: int,
    run_id: str,
    pr_number: int,
    submitted_by: str,
    run_url: str,
) -> None:
    """Register a one-shot plan with issue metadata, comment, and PR closing ref."""
    issues = require_issues(ctx)
    github = require_github(ctx)
    plan_backend = require_plan_backend(ctx)
    repo_root = require_repo_root(ctx)
    plans_repo = load_config(repo_root).plans_repo
    results: dict[str, object] = {}

    # Op 1: dispatch metadata
    try:
        write_dispatch_metadata(
            plan_backend=plan_backend,
            github=github,
            repo_root=repo_root,
            issue_number=issue_number,
            run_id=run_id,
            dispatched_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        results["dispatch_metadata"] = {"success": True}
    except Exception as exc:
        results["dispatch_metadata"] = {"success": False, "error": str(exc)}

    # Op 2: queued comment
    try:
        issue = issues.get_issue(repo_root, issue_number)
        if isinstance(issue, IssueNotFound):
            raise RuntimeError(f"Issue #{issue_number} not found")
        # Extract owner/repo from run_url for the PR link
        url_parts = run_url.split("/")
        repo_slug = next(
            (
                f"{url_parts[i + 1]}/{url_parts[i + 2]}"
                for i, p in enumerate(url_parts)
                if p == "github.com" and i + 2 < len(url_parts)
            ),
            "",
        )
        issues.add_comment(
            repo_root,
            issue_number,
            f"\U0001f504 **Queued for Implementation**\n\n"
            f"**Submitted by:** @{submitted_by}\n"
            f"**PR:** [#{pr_number}](https://github.com/{repo_slug}/pull/{pr_number})\n"
            f"**Workflow run:** [View run]({run_url})\n",
        )
        results["queued_comment"] = {"success": True}
    except Exception as exc:
        results["queued_comment"] = {"success": False, "error": str(exc)}

    # Op 3: PR closing reference
    # Guard: skip when issue_number == pr_number (draft_pr mode).
    # The draft PR IS the plan — Closes #N would be self-referential.
    if issue_number == pr_number:
        results["pr_closing_ref"] = {"success": True, "skipped": "self-referential"}
    else:
        try:
            pr = github.get_pr(repo_root, pr_number)
            if isinstance(pr, PRNotFound):
                raise RuntimeError(f"PR #{pr_number} not found")
            ref = f"Closes {plans_repo}#{issue_number}" if plans_repo else f"Closes #{issue_number}"
            github.update_pr_body(repo_root, pr_number, f"{pr.body}\n\n---\n\n{ref}")
            results["pr_closing_ref"] = {"success": True}
        except Exception as exc:
            results["pr_closing_ref"] = {"success": False, "error": str(exc)}

    # Op 4: update lifecycle stage to "planned"
    try:
        plan_backend.update_metadata(
            repo_root,
            str(issue_number),
            metadata={"lifecycle_stage": "planned"},
        )
        results["lifecycle_stage"] = {"success": True}
    except Exception as exc:
        results["lifecycle_stage"] = {"success": False, "error": str(exc)}

    click.echo(json.dumps(results, indent=2))
    if not any(v["success"] for v in results.values()):  # type: ignore[union-attr]
        raise SystemExit(1)
