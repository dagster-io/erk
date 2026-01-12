"""PR body footer generation utilities."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ClosingReference:
    """Represents a parsed closing reference from a PR footer."""

    issue_number: int
    plans_repo: str | None  # None for same-repo, "owner/repo" for cross-repo


def extract_footer_from_body(body: str) -> str | None:
    """Extract the footer section from a PR body.

    The footer is the content after the last `---` delimiter (horizontal rule).

    Args:
        body: Full PR body content

    Returns:
        Footer content (without the delimiter) or None if no footer found
    """
    # Split on horizontal rule delimiter
    parts = body.rsplit("\n---\n", 1)
    if len(parts) < 2:
        return None
    return parts[1]


def extract_closing_reference(footer: str) -> ClosingReference | None:
    """Extract closing reference from a PR footer.

    Parses patterns like:
    - "Closes #123" (same-repo)
    - "Closes owner/repo#123" (cross-repo)

    Args:
        footer: Footer section content

    Returns:
        ClosingReference with issue_number and plans_repo, or None if not found
    """
    # Pattern for "Closes owner/repo#123" (cross-repo)
    cross_repo_match = re.search(r"Closes\s+([\w-]+/[\w.-]+)#(\d+)", footer)
    if cross_repo_match:
        return ClosingReference(
            issue_number=int(cross_repo_match.group(2)),
            plans_repo=cross_repo_match.group(1),
        )

    # Pattern for "Closes #123" (same-repo)
    same_repo_match = re.search(r"Closes\s+#(\d+)", footer)
    if same_repo_match:
        return ClosingReference(
            issue_number=int(same_repo_match.group(1)),
            plans_repo=None,
        )

    return None


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
    issue_number: int | None,
    plans_repo: str | None,
) -> str:
    """Build standardized footer section for PR body.

    Args:
        pr_number: PR number for checkout command
        issue_number: Optional issue number to close on merge
        plans_repo: Target repo in "owner/repo" format for cross-repo,
            or None for same-repo

    Returns:
        Markdown footer string ready to append to PR body
    """
    parts: list[str] = []
    parts.append("\n---\n")

    if issue_number is not None:
        # Format issue reference for same-repo or cross-repo
        if plans_repo is None:
            issue_ref = f"#{issue_number}"
        else:
            issue_ref = f"{plans_repo}#{issue_number}"
        parts.append(f"\nCloses {issue_ref}\n")

    parts.append(
        f"\nTo checkout this PR in a fresh worktree and environment locally, run:\n\n"
        f"```\n"
        f"erk pr checkout {pr_number} && erk pr sync --dangerous\n"
        f"```\n"
    )

    return "\n".join(parts)
