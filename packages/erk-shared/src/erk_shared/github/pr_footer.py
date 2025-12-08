"""PR body footer generation utilities."""


def build_remote_execution_note(workflow_run_id: str, workflow_run_url: str) -> str:
    """Build a remote execution tracking note for PR body.

    Args:
        workflow_run_id: The GitHub Actions workflow run ID
        workflow_run_url: Full URL to the workflow run

    Returns:
        Markdown string with remote execution link
    """
    return f"\n**Remotely executed:** [Run #{workflow_run_id}]({workflow_run_url})"


def build_pr_body_footer(
    pr_number: int,
    *,
    issue_number: int | None = None,
) -> str:
    """Build standardized footer section for PR body.

    Args:
        pr_number: PR number for checkout command
        issue_number: Optional issue number to close on merge

    Returns:
        Markdown footer string ready to append to PR body
    """
    parts: list[str] = []
    parts.append("\n---\n")

    if issue_number is not None:
        parts.append(f"\nCloses #{issue_number}\n")

    parts.append(
        f"\nTo checkout this PR in a fresh worktree and environment locally, run:\n\n"
        f"```\n"
        f"erk pr checkout {pr_number} && erk pr sync\n"
        f"```\n"
    )

    return "\n".join(parts)
