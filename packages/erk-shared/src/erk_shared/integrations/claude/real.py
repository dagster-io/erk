"""Real Claude session detection using lsof.

This module provides a production implementation that uses lsof to detect
if any Claude Code process has files open in a given directory.
"""

import subprocess
from pathlib import Path

from erk_shared.integrations.claude.abc import ClaudeSessionDetector


class RealClaudeSessionDetector(ClaudeSessionDetector):
    """Production implementation using lsof to detect Claude sessions.

    Uses `lsof +D <directory>` to check if any process named 'claude' has
    files open within the specified directory tree.
    """

    def has_active_session(self, directory: Path) -> bool:
        """Check if the given directory has an active Claude Code session.

        Uses lsof to find any Claude processes with files open in the directory.
        This is a LBYL-compliant approach since we check before attempting deletion.

        Note: This function uses try/except as an error boundary for the subprocess
        call, which is acceptable per LBYL guidelines since subprocess.run() provides
        no way to check if the command will succeed beforehand.

        Args:
            directory: Path to check for active Claude sessions

        Returns:
            True if an active Claude session is detected, False otherwise
        """
        # Check if directory exists first (LBYL)
        if not directory.exists():
            return False

        resolved_path = directory.resolve()

        # Use lsof to find open files in the directory
        # lsof +D lists all open files in the directory tree
        # We then filter for claude-related processes
        try:
            result = subprocess.run(
                ["lsof", "+D", str(resolved_path)],
                capture_output=True,
                text=True,
                check=False,  # lsof returns 1 if no files found
            )
            # lsof output format: COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME
            # Check if any line contains 'claude' in the command name (first column)
            for line in result.stdout.splitlines():
                # Skip header line
                if line.startswith("COMMAND"):
                    continue
                # Split and check command name (first field)
                parts = line.split()
                if parts:
                    command = parts[0].lower()
                    # Match claude, claude-code, or similar
                    if "claude" in command:
                        return True
            return False
        except FileNotFoundError:
            # lsof not available on this system (edge case)
            # Fail open - return False to allow operation
            return False
        except subprocess.SubprocessError:
            # Other subprocess errors - fail open
            return False
