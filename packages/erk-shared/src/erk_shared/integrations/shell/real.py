"""Real implementation of Shell using system environment."""

import json
import os
import shutil
import subprocess
from pathlib import Path

from erk_shared.integrations.shell.abc import Shell, detect_shell_from_env


class RealShell(Shell):
    """Production implementation using system environment and PATH."""

    def detect_shell(self) -> tuple[str, Path] | None:
        """Detect current shell from SHELL environment variable.

        Implementation details:
        - Reads $SHELL environment variable
        - Extracts shell name from path (e.g., /bin/bash -> bash)
        - Maps to appropriate RC file location
        """
        shell_env = os.environ.get("SHELL", "")
        return detect_shell_from_env(shell_env)

    def get_installed_tool_path(self, tool_name: str) -> str | None:
        """Check if tool is in PATH using shutil.which."""
        return shutil.which(tool_name)

    def run_claude_extraction_plan(self, cwd: Path) -> str | None:
        """Run Claude CLI to create an extraction plan from session logs.

        Spawns Claude in non-interactive mode with permission bypass to
        automatically create an extraction plan. Returns the issue URL
        if present in the JSON output.

        Note: Claude CLI with --print mode may output conversation/thinking text
        before the final JSON. We search from the end of stdout to find the JSON
        line containing issue_url.
        """
        cmd = [
            "claude",
            "--print",
            "--permission-mode",
            "bypassPermissions",
            "/erk:create-raw-extraction-plan",
        ]

        result = subprocess.run(
            cmd,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )

        # Parse JSON output to extract issue_url
        # Claude may output non-JSON text before the JSON result,
        # so we search from the end of stdout to find the JSON line
        return _extract_issue_url_from_output(result.stdout)


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
