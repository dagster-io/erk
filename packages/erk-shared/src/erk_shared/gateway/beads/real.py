"""Production implementation of Beads gateway using bd CLI."""

import json
import subprocess
from pathlib import Path

from erk_shared.gateway.beads.abc import BeadsGateway
from erk_shared.gateway.beads.types import BeadsIssue
from erk_shared.gateway.time.abc import Time


class RealBeadsGateway(BeadsGateway):
    """Production implementation using bd CLI.

    All Beads operations execute actual bd commands via subprocess.
    """

    def __init__(self, *, time: Time, cwd: Path | None) -> None:
        """Initialize RealBeadsGateway.

        Args:
            time: Time abstraction for sleep operations (used in future retry logic).
            cwd: Working directory for bd CLI operations. If None, uses current
                directory. The bd command operates on the .beads/ folder in this
                directory.
        """
        self._time = time
        self._cwd = cwd

    def list_issues(
        self,
        *,
        labels: list[str] | None,
        status: str | None,
        limit: int | None,
    ) -> list[BeadsIssue]:
        """Query issues using bd CLI.

        Runs: bd list --json [--label X] [--status Y]
        Parses JSON output into BeadsIssue objects.
        """
        cmd = ["bd", "list", "--json"]

        if labels:
            for label in labels:
                cmd.extend(["--label", label])

        if status is not None:
            cmd.extend(["--status", status])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=self._cwd,
            check=False,
        )

        if result.returncode != 0:
            msg = f"bd list failed: {result.stderr}"
            raise RuntimeError(msg)

        # Handle empty output (no issues)
        stdout = result.stdout.strip()
        if not stdout:
            return []

        data = json.loads(stdout)

        issues = [
            BeadsIssue(
                id=item["id"],
                title=item["title"],
                description=item.get("description", ""),
                status=item["status"],
                labels=tuple(item.get("labels", [])),
                assignee=item.get("assignee"),
                notes=item.get("notes", ""),
                created_at=item["created_at"],
                updated_at=item["updated_at"],
            )
            for item in data
        ]

        # Apply limit if specified
        if limit is not None:
            issues = issues[:limit]

        return issues
