"""Renderer functions for plan command output.

JSON renderers serialize IR types to stdout. Human renderers reproduce
existing Rich/click output to stderr.

Part of Approach A prototype for standardized --json-output (Objective #8088).
"""

from __future__ import annotations

import json

import click

from erk.cli.commands.plan.ir_types import PlanListOutput, PlanViewOutput


def render_plan_list_json(output: PlanListOutput) -> None:
    """Render plan list as structured JSON to stdout.

    Groups fields into logical sub-objects for readability:
    pr, location, workflow_run, comments.

    Args:
        output: Plan list IR output
    """
    plans_json = []
    for entry in output.plans:
        plans_json.append(
            {
                "plan_id": entry.plan_id,
                "plan_url": entry.plan_url,
                "title": entry.title,
                "author": entry.author,
                "created_at": entry.created_at,
                "pr": {
                    "number": entry.pr_number,
                    "url": entry.pr_url,
                    "state": entry.pr_state,
                    "head_branch": entry.pr_head_branch,
                },
                "location": {
                    "exists_locally": entry.exists_locally,
                    "worktree_branch": entry.worktree_branch,
                },
                "workflow_run": {
                    "run_id": entry.run_id,
                    "url": entry.run_url,
                    "status": entry.run_status,
                    "conclusion": entry.run_conclusion,
                },
                "objective_issue": entry.objective_issue,
                "comments": {
                    "resolved": entry.resolved_comment_count,
                    "total": entry.total_comment_count,
                },
            }
        )

    click.echo(json.dumps({"plans": plans_json, "total_count": output.total_count}))


def render_plan_view_json(output: PlanViewOutput) -> None:
    """Render plan view as structured JSON to stdout.

    Groups header fields into logical sub-objects:
    local_impl, remote, learn.

    Args:
        output: Plan view IR output
    """
    result: dict[str, object] = {
        "plan_id": output.plan_id,
        "title": output.title,
        "state": output.state,
        "url": output.url,
        "labels": list(output.labels),
        "assignees": list(output.assignees),
        "created_at": output.created_at,
        "updated_at": output.updated_at,
        "branch_name": output.branch_name,
        "body": output.body,
    }

    if output.header is not None:
        header = output.header
        result["header"] = {
            "created_by": header.created_by,
            "schema_version": header.schema_version,
            "worktree_name": header.worktree_name,
            "objective_issue": header.objective_issue,
            "source_repo": header.source_repo,
            "local_impl": {
                "last_at": header.last_local_impl_at,
                "last_event": header.last_local_impl_event,
                "last_session": header.last_local_impl_session,
                "last_user": header.last_local_impl_user,
            },
            "remote": {
                "last_impl_at": header.last_remote_impl_at,
                "last_dispatched_at": header.last_dispatched_at,
                "last_dispatched_run_id": header.last_dispatched_run_id,
            },
            "learn": {
                "status": header.learn_status,
                "plan_issue": header.learn_plan_issue,
                "plan_pr": header.learn_plan_pr,
                "run_url": header.learn_run_url,
                "created_from_session": header.created_from_session,
                "last_session": header.last_learn_session,
            },
        }
    else:
        result["header"] = None

    click.echo(json.dumps(result))
