"""Shell detection and tool availability operations.

This module provides abstraction over shell-specific operations like detecting
the current shell and checking if command-line tools are installed. This abstraction
enables dependency injection for testing without mock.patch.

The Shell ABC and implementations (RealShell, FakeShell) are defined in erk_shared
and re-exported here. Erk-specific helper functions remain in this module.
"""

import json

# Re-export all Shell types from erk_shared
from erk_shared.integrations.shell import FakeShell as FakeShell
from erk_shared.integrations.shell import RealShell as RealShell
from erk_shared.integrations.shell import Shell as Shell
from erk_shared.integrations.shell import detect_shell_from_env as detect_shell_from_env
from erk_shared.subprocess_utils import run_subprocess_with_context as run_subprocess_with_context


def _extract_issue_url_from_output(output: str) -> str | None:
    """Extract issue_url from Claude CLI output that may contain mixed content.

    Claude CLI with --print mode can output conversation/thinking text before
    the final JSON. This function searches from the end of the output to find
    a JSON object containing issue_url.

    Args:
        output: The stdout from Claude CLI (may contain non-JSON text)

    Returns:
        The issue_url string if found, None otherwise.
    """
    if not output:
        return None

    # Search from the end of output to find JSON with issue_url
    for line in reversed(output.strip().split("\n")):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            if isinstance(data, dict):
                issue_url = data.get("issue_url")
                if isinstance(issue_url, str):
                    return issue_url
        except json.JSONDecodeError:
            continue

    return None
