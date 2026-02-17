"""Post a formatted action comment to an objective issue.

Takes structured JSON on stdin and formats it using the standard action comment
template, then posts it via the GitHub issues API.

Usage:
    echo '{"issue_number": 6423, ...}' | erk exec objective-post-action-comment

Input JSON:
    {
        "issue_number": 6423,
        "date": "2026-02-17",
        "pr_number": 6517,
        "phase_step": "1.1, 1.2",
        "title": "Brief title of what was accomplished",
        "what_was_done": ["Concrete action 1", "Concrete action 2"],
        "lessons_learned": ["Insight 1"],
        "roadmap_updates": ["Step 1.1: pending -> done"],
        "body_reconciliation": [{"section": "Design Decisions", "change": "Updated X"}]
    }

Output:
    JSON with {success, comment_id} or {success, error}

Exit Codes:
    0: Success - comment posted
    1: Error - invalid input or API failure
"""

import json
import sys

import click

from erk_shared.context.helpers import require_issues, require_repo_root


def _format_action_comment(
    *,
    title: str,
    date: str,
    pr_number: int,
    phase_step: str,
    what_was_done: list[str],
    lessons_learned: list[str],
    roadmap_updates: list[str],
    body_reconciliation: list[dict[str, str]],
) -> str:
    """Format structured data into the standard action comment template."""
    lines: list[str] = []

    lines.append(f"## Action: {title}")
    lines.append("")
    lines.append(f"**Date:** {date}")
    lines.append(f"**PR:** #{pr_number}")
    lines.append(f"**Phase/Step:** {phase_step}")
    lines.append("")

    lines.append("### What Was Done")
    lines.append("")
    for item in what_was_done:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("### Lessons Learned")
    lines.append("")
    for item in lessons_learned:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("### Roadmap Updates")
    lines.append("")
    for item in roadmap_updates:
        lines.append(f"- {item}")

    if body_reconciliation:
        lines.append("")
        lines.append("### Body Reconciliation")
        lines.append("")
        for entry in body_reconciliation:
            section = entry.get("section", "Unknown")
            change = entry.get("change", "")
            lines.append(f"- **{section}**: {change}")

    return "\n".join(lines)


@click.command(name="objective-post-action-comment")
@click.pass_context
def objective_post_action_comment(ctx: click.Context) -> None:
    """Post a formatted action comment to an objective issue.

    Reads structured JSON from stdin and posts the formatted comment.
    """
    issues = require_issues(ctx)
    repo_root = require_repo_root(ctx)

    raw_input = sys.stdin.read()
    if not raw_input.strip():
        click.echo(json.dumps({"success": False, "error": "No input provided on stdin"}))
        raise SystemExit(1)

    data = json.loads(raw_input)

    # Validate required fields
    required_fields = ["issue_number", "date", "pr_number", "phase_step", "title", "what_was_done"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        msg = f"Missing required fields: {', '.join(missing)}"
        click.echo(json.dumps({"success": False, "error": msg}))
        raise SystemExit(1)

    comment_body = _format_action_comment(
        title=data["title"],
        date=data["date"],
        pr_number=data["pr_number"],
        phase_step=data["phase_step"],
        what_was_done=data["what_was_done"],
        lessons_learned=data.get("lessons_learned", []),
        roadmap_updates=data.get("roadmap_updates", []),
        body_reconciliation=data.get("body_reconciliation", []),
    )

    comment_id = issues.add_comment(repo_root, data["issue_number"], comment_body)

    click.echo(json.dumps({"success": True, "comment_id": comment_id}))
