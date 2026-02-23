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


# Header patterns that should be preserved when syncing PR body from commit
HEADER_PATTERNS = (
    "**Plan:**",
    "**Remotely executed:**",
)


def _scan_header_from_top(content: str) -> str:
    """Scan from the top of content for header pattern lines (legacy format).

    In the old format, header lines appeared at the top of the PR body
    rather than just above the footer separator.
    """
    lines = content.split("\n")
    header_lines: list[str] = []

    for line in lines:
        if not line.strip():
            if header_lines:
                header_lines.append(line)
            continue
        if any(line.startswith(pattern) for pattern in HEADER_PATTERNS):
            header_lines.append(line)
        else:
            break

    if not header_lines:
        return ""

    # Remove leading/trailing blank lines
    while header_lines and not header_lines[0].strip():
        header_lines.pop(0)
    while header_lines and not header_lines[-1].strip():
        header_lines.pop()

    if header_lines:
        return "\n".join(header_lines) + "\n\n"
    return ""


def extract_header_from_body(body: str) -> str:
    """Extract header lines from the PR body.

    Header lines match known patterns like ``**Plan:** #123`` or
    ``**Remotely executed:** [Run #...]``. They may appear either just
    above the footer separator (new format) or at the top of the body
    (legacy format).

    The function tries the new bottom position first, then falls back
    to scanning from the top for backward compatibility with existing PRs.

    Args:
        body: Full PR body content

    Returns:
        Header content (including trailing newlines) or empty string if no header
    """
    if not body:
        return ""

    # Remove footer first
    parts = body.rsplit("\n---\n", 1)
    content_without_footer = parts[0]

    # Scan from the end of the content for header pattern lines (new format)
    lines = content_without_footer.split("\n")
    header_lines: list[str] = []

    for line in reversed(lines):
        if not line.strip():
            if header_lines:
                header_lines.append(line)
            continue
        if any(line.startswith(pattern) for pattern in HEADER_PATTERNS):
            header_lines.append(line)
        else:
            break

    if not header_lines:
        # Fall back to scanning from top (legacy format)
        return _scan_header_from_top(content_without_footer)

    # Reverse to restore original order
    header_lines.reverse()

    # Remove leading/trailing blank lines
    while header_lines and not header_lines[0].strip():
        header_lines.pop(0)
    while header_lines and not header_lines[-1].strip():
        header_lines.pop()

    if header_lines:
        return "\n".join(header_lines) + "\n\n"
    return ""


def is_header_at_legacy_position(body: str) -> bool:
    """Check whether a header exists at the legacy top position but not at the bottom.

    Returns ``True`` when the PR body contains a header block (e.g.
    ``**Plan:** #123``) at the *top* of the description — the old format —
    and there is no header at the bottom (new format).  This is the signal
    that the PR body needs to be migrated.

    Args:
        body: Full PR body content

    Returns:
        True if header is at the legacy top position only
    """
    if not body:
        return False

    # Remove footer first
    parts = body.rsplit("\n---\n", 1)
    content_without_footer = parts[0]

    # Check bottom scan — scan from end for header pattern lines
    lines = content_without_footer.split("\n")
    found_at_bottom = False
    for line in reversed(lines):
        if not line.strip():
            continue
        if any(line.startswith(pattern) for pattern in HEADER_PATTERNS):
            found_at_bottom = True
        break

    if found_at_bottom:
        return False

    # Check top scan — if top has a header, it's legacy
    top_header = _scan_header_from_top(content_without_footer)
    return bool(top_header)


def extract_main_content(body: str) -> str:
    """Extract the main content between start-of-body and header/footer.

    The header sits just above the footer separator. Main content is
    everything before the header (or before the footer if no header).

    Args:
        body: Full PR body content

    Returns:
        Main content without header or footer
    """
    if not body:
        return ""

    # Remove footer first
    parts = body.rsplit("\n---\n", 1)
    content_without_footer = parts[0]

    # Remove header from content (may be at end or beginning)
    header = extract_header_from_body(body)
    if header:
        header_text = header.rstrip("\n")
        stripped = content_without_footer.rstrip()
        # Try removing from end (new format — bottom position)
        if stripped.endswith(header_text):
            content = stripped[: len(stripped) - len(header_text)]
            return content.rstrip()
        # Try removing from beginning (legacy format — top position)
        lstripped = content_without_footer.lstrip()
        if lstripped.startswith(header_text):
            content = lstripped[len(header_text) :]
            return content.strip()

    return content_without_footer.rstrip()


def rebuild_pr_body(
    *,
    header: str,
    content: str,
    footer: str,
) -> str:
    """Reassemble PR body from header, content, and footer.

    Header is placed between content and footer (above the ``---``
    delimiter), matching the convention that metadata appears at the
    bottom of the PR description.

    Args:
        header: Header content (may be empty)
        content: Main body content
        footer: Footer content (may be empty, should NOT include --- delimiter)

    Returns:
        Complete PR body with proper delimiters
    """
    parts: list[str] = []

    parts.append(content.strip())

    if header:
        parts.append("")
        parts.append(header.rstrip("\n"))

    if footer:
        parts.append("")
        parts.append("---")
        parts.append("")
        parts.append(footer.strip())

    return "\n".join(parts)


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
        f'source "$(erk pr checkout {pr_number} --script)" && erk pr sync --dangerous\n'
        f"```\n"
    )

    return "\n".join(parts)
