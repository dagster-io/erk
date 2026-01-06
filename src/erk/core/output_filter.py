"""Output filtering for Claude CLI stream-json format.

This module provides functions to parse and filter Claude CLI output in stream-json
format, extracting relevant text content and tool summaries while suppressing
verbose/noisy tool invocations.
"""

import json
from pathlib import Path


def extract_text_content(message: dict) -> str | None:
    """Extract Claude's text response from assistant message.

    Args:
        message: Assistant message dict from stream-json

    Returns:
        Extracted text content, or None if no text found

    Example:
        >>> msg = {"type": "assistant_message", "content": [{"type": "text", "text": "Hello"}]}
        >>> extract_text_content(msg)
        'Hello'
    """
    content = message.get("content", [])
    if not isinstance(content, list):
        return None

    text_parts: list[str] = []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                text_parts.append(text.strip())

    if not text_parts:
        return None

    return "\n".join(text_parts)


def summarize_tool_use(tool_use: dict, worktree_path: Path) -> str | None:
    """Create brief summary for important tools, None for suppressible tools.

    Args:
        tool_use: Tool use dict from stream-json content
        worktree_path: Path to worktree for relativizing file paths

    Returns:
        Brief summary string for important tools, None for suppressible tools

    Example:
        >>> tool = {"name": "Edit", "input": {"file_path": "/repo/src/file.py"}}
        >>> summarize_tool_use(tool, Path("/repo"))
        'Editing src/file.py...'
    """
    tool_name = tool_use.get("name")
    if not isinstance(tool_name, str):
        return None

    params = tool_use.get("input", {})
    if not isinstance(params, dict):
        params = {}

    # Suppress common/noisy tools
    if tool_name in ["Read", "Glob", "Grep"]:
        return None

    # Bash commands
    if tool_name == "Bash":
        command = params.get("command", "")
        if not isinstance(command, str):
            return None

        # Check for pytest
        if "pytest" in command:
            return "Running tests..."

        # Check for CI commands
        if "fast-ci" in command or "all-ci" in command:
            return "Running CI checks..."

        # Generic bash command
        return f"Running: {command[:50]}..."

    # Slash commands
    if tool_name == "SlashCommand":
        cmd = params.get("command", "")
        if not isinstance(cmd, str):
            return None

        if "/gt:pr-submit" in cmd or "/erk:git-pr-push" in cmd:
            return "Creating pull request..."

        if "/fast-ci" in cmd or "/all-ci" in cmd:
            return "Running CI checks..."

        return f"Running {cmd}..."

    # File operations
    if tool_name == "Edit":
        filepath = params.get("file_path", "")
        if isinstance(filepath, str):
            relative = make_relative_to_worktree(filepath, worktree_path)
            return f"Editing {relative}..."

    if tool_name == "Write":
        filepath = params.get("file_path", "")
        if isinstance(filepath, str):
            relative = make_relative_to_worktree(filepath, worktree_path)
            return f"Writing {relative}..."

    # Default: show tool name for unknown tools
    return f"Using {tool_name}..."


def make_relative_to_worktree(filepath: str, worktree_path: Path) -> str:
    """Convert absolute path to worktree-relative path.

    Args:
        filepath: Absolute or relative file path
        worktree_path: Path to worktree root

    Returns:
        Path relative to worktree if possible, otherwise original filepath

    Example:
        >>> make_relative_to_worktree("/repo/src/file.py", Path("/repo"))
        'src/file.py'
    """
    path = Path(filepath)

    # Check if path is absolute and relative to worktree
    if path.is_absolute():
        if path.exists() and path.is_relative_to(worktree_path):
            return str(path.relative_to(worktree_path))

    return filepath


def extract_pr_url(tool_result_content: str) -> str | None:
    """Extract PR URL from exec command JSON output.

    Args:
        tool_result_content: Content string from tool_result

    Returns:
        PR URL if found in JSON, None otherwise

    Example:
        >>> content = '{"success": true, "pr_url": "https://github.com/user/repo/pull/123"}'
        >>> extract_pr_url(content)
        'https://github.com/user/repo/pull/123'
    """
    if not isinstance(tool_result_content, str):
        return None

    # Parse JSON safely - JSON parsing requires exception handling
    data: dict | None = None
    if tool_result_content.strip():
        try:
            parsed = json.loads(tool_result_content)
            if isinstance(parsed, dict):
                data = parsed
        except json.JSONDecodeError:
            return None

    if data is None:
        return None

    pr_url = data.get("pr_url")
    if isinstance(pr_url, str):
        return pr_url

    return None


def extract_pr_metadata(tool_result_content: str) -> dict[str, str | int | None]:
    """Extract PR metadata from exec command JSON output.

    Args:
        tool_result_content: Content string from tool_result

    Returns:
        Dict with pr_url, pr_number, pr_title, and issue_number (all may be None)

    Example:
        >>> content = '{"success": true, "pr_url": "https://...", "pr_number": 123, '
        >>> content += '"pr_title": "Fix bug", "issue_number": 456}'
        >>> extract_pr_metadata(content)
        {'pr_url': 'https://...', 'pr_number': 123, 'pr_title': 'Fix bug', 'issue_number': 456}
    """
    if not isinstance(tool_result_content, str):
        return {"pr_url": None, "pr_number": None, "pr_title": None, "issue_number": None}

    # Parse JSON safely - JSON parsing requires exception handling
    data: dict | None = None
    if tool_result_content.strip():
        try:
            parsed = json.loads(tool_result_content)
            if isinstance(parsed, dict):
                data = parsed
        except json.JSONDecodeError:
            return {"pr_url": None, "pr_number": None, "pr_title": None, "issue_number": None}

    if data is None:
        return {"pr_url": None, "pr_number": None, "pr_title": None, "issue_number": None}

    pr_url = data.get("pr_url")
    pr_number = data.get("pr_number")
    pr_title = data.get("pr_title")
    issue_number = data.get("issue_number")

    return {
        "pr_url": pr_url if isinstance(pr_url, str) else None,
        "pr_number": pr_number if isinstance(pr_number, int) else None,
        "pr_title": pr_title if isinstance(pr_title, str) else None,
        "issue_number": issue_number if isinstance(issue_number, int) else None,
    }


def extract_pr_metadata_from_text(text: str) -> dict[str, str | int | None]:
    """Extract PR metadata from agent text output using pattern matching.

    This is simpler and more robust than parsing nested JSON from tool results.
    The agent's text output contains PR info in human-readable format like:
    - "PR #1311" or "**PR #1311**"
    - "https://github.com/.../pull/1311" or "https://app.graphite.com/.../1311"
    - "issue #1308" or "Linked to issue #1308"

    Args:
        text: Agent text output containing PR information

    Returns:
        Dict with pr_url, pr_number, and issue_number (pr_title always None)

    Example:
        >>> text = "**PR #123** created\\n- **Link**: https://github.com/o/r/pull/123"
        >>> extract_pr_metadata_from_text(text)
        {'pr_url': 'https://github.com/o/r/pull/123', 'pr_number': 123, ...}
    """
    import re

    result: dict[str, str | int | None] = {
        "pr_url": None,
        "pr_number": None,
        "pr_title": None,
        "issue_number": None,
    }

    if not isinstance(text, str):
        return result

    # Extract PR number and title from various patterns:
    # - "PR #123: Title" or "PR #123 - Title"
    # - "#123 - Title" or '#123 - "Title"'
    # - "**PR Updated**: #123 - Title"
    pr_with_title_match = re.search(
        r"#(\d+)\s*[-:]\s*[\"']?(.+?)[\"']?(?:\n|$)", text, re.IGNORECASE
    )
    if pr_with_title_match:
        result["pr_number"] = int(pr_with_title_match.group(1))
        result["pr_title"] = pr_with_title_match.group(2).strip().strip("\"'")
    else:
        # Fallback: just extract PR number without title
        pr_num_match = re.search(r"#(\d+)", text)
        if pr_num_match:
            result["pr_number"] = int(pr_num_match.group(1))

    # Extract GitHub PR URL
    github_url_match = re.search(r"https://github\.com/[^/]+/[^/]+/pull/(\d+)", text)
    if github_url_match:
        result["pr_url"] = github_url_match.group(0)
        # Also extract pr_number from URL if not found earlier
        if result["pr_number"] is None:
            result["pr_number"] = int(github_url_match.group(1))

    # Extract Graphite URL as fallback
    if result["pr_url"] is None:
        graphite_url_match = re.search(
            r"https://app\.graphite\.com/github/pr/[^/]+/[^/]+/(\d+)", text
        )
        if graphite_url_match:
            result["pr_url"] = graphite_url_match.group(0)
            if result["pr_number"] is None:
                result["pr_number"] = int(graphite_url_match.group(1))

    # Extract issue number from patterns like "issue #123" or "Linked to issue #123"
    # or "#1308 (will auto-close"
    issue_match = re.search(r"issue\s*#(\d+)", text, re.IGNORECASE)
    if issue_match:
        result["issue_number"] = int(issue_match.group(1))
    else:
        # Try "Closes #123" pattern
        closes_match = re.search(r"Closes\s*#(\d+)", text, re.IGNORECASE)
        if closes_match:
            result["issue_number"] = int(closes_match.group(1))

    return result


def determine_spinner_status(tool_use: dict | None, command: str, worktree_path: Path) -> str:
    """Map current activity to spinner status message.

    Args:
        tool_use: Current tool use dict, or None if no tool running
        command: The slash command being executed
        worktree_path: Path to worktree for relativizing paths

    Returns:
        Status message for spinner

    Example:
        >>> determine_spinner_status(None, "/erk:system:impl-execute", Path("/repo"))
        'Running /erk:system:impl-execute...'
    """
    if tool_use is None:
        return f"Running {command}..."

    # First try to get a detailed summary
    summary = summarize_tool_use(tool_use, worktree_path)
    if summary:
        return summary

    # For suppressed tools (Read, Glob, Grep), provide a generic but distinct message
    tool_name = tool_use.get("name")
    if isinstance(tool_name, str):
        if tool_name == "Read":
            return "Reading files..."
        if tool_name == "Glob":
            return "Searching for files..."
        if tool_name == "Grep":
            return "Searching code..."
        # Fallback for unknown tools
        return f"Using {tool_name}..."

    return f"Running {command}..."
