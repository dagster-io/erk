"""Real subprocess-based implementation of erk worktree operations interface.

This module provides concrete implementations that wrap subprocess.run calls
for erk and gh commands used by create_wt_from_issue. This is the production
implementation.

Design:
- Each method wraps one subprocess call from original create_wt_from_issue.py
- Returns match interface contracts (use LBYL pattern: None/False on failure)
- Uses check=False to allow LBYL error handling
- Subprocess errors return None/False rather than raising exceptions
"""

import json
import subprocess
import tempfile
from pathlib import Path

from erk_shared.integrations.erk_wt.abc import (
    ErkWtKit,
    IssueData,
    IssueParseResult,
    WorktreeCreationResult,
)


class RealErkWtKit(ErkWtKit):
    """Real erk worktree operations using subprocess."""

    def parse_issue_reference(self, issue_arg: str) -> IssueParseResult:
        """Parse issue reference using erk kit exec CLI command.

        Args:
            issue_arg: Issue number or GitHub URL

        Returns:
            IssueParseResult with success status and parsed issue number or error
        """
        result = subprocess.run(
            ["erk", "kit", "exec", "erk", "parse-issue-reference", issue_arg],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            # Parse error response
            try:
                data = json.loads(result.stdout)
                return IssueParseResult(
                    success=False,
                    error=data.get("error"),
                    message=data.get("message"),
                )
            except json.JSONDecodeError:
                return IssueParseResult(
                    success=False,
                    error="parse_failed",
                    message=f"Failed to parse issue reference: {result.stderr}",
                )

        # Parse success response
        try:
            data = json.loads(result.stdout)
            return IssueParseResult(
                success=True,
                issue_number=data.get("issue_number"),
                message=data.get("message"),
            )
        except json.JSONDecodeError:
            return IssueParseResult(
                success=False,
                error="invalid_json",
                message="Invalid JSON response from parse-issue-reference",
            )

    def fetch_issue(self, issue_number: int) -> IssueData | None:
        """Fetch issue data from GitHub using gh CLI.

        Args:
            issue_number: GitHub issue number

        Returns:
            IssueData if fetch succeeded, None otherwise
        """
        result = subprocess.run(
            [
                "gh",
                "issue",
                "view",
                str(issue_number),
                "--json",
                "number,title,body,state,url,labels",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return None

        try:
            data = json.loads(result.stdout)
            # Extract label names from label objects
            labels = data.get("labels", [])
            label_names: list[str] = []
            for label in labels:
                if isinstance(label, dict):
                    name = label.get("name")
                    if isinstance(name, str):
                        label_names.append(name)

            return IssueData(
                number=data["number"],
                title=data["title"],
                body=data.get("body", ""),
                state=data["state"],
                url=data["url"],
                labels=label_names,
            )
        except (json.JSONDecodeError, KeyError):
            return None

    def create_worktree(self, plan_content: str) -> WorktreeCreationResult:
        """Create worktree from plan content using erk create command.

        Args:
            plan_content: Plan markdown content

        Returns:
            WorktreeCreationResult with success status and worktree details
        """
        # Create temporary directory and file for plan
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            temp_file = temp_dir / "plan.md"
            temp_file.write_text(plan_content, encoding="utf-8")

            result = subprocess.run(
                ["erk", "create", "--from-plan", str(temp_file), "--json", "--stay"],
                capture_output=True,
                text=True,
                check=False,
            )

        if result.returncode != 0:
            return WorktreeCreationResult(success=False)

        try:
            data = json.loads(result.stdout)
            if data.get("status") == "success":
                return WorktreeCreationResult(
                    success=True,
                    worktree_name=data.get("worktree_name"),
                    worktree_path=data.get("worktree_path"),
                    branch_name=data.get("branch_name"),
                )
            return WorktreeCreationResult(success=False)
        except (json.JSONDecodeError, KeyError):
            return WorktreeCreationResult(success=False)

    def post_creation_comment(
        self, issue_number: int, worktree_name: str, branch_name: str
    ) -> bool:
        """Post worktree creation comment to GitHub issue.

        Args:
            issue_number: GitHub issue number
            worktree_name: Name of created worktree
            branch_name: Git branch name

        Returns:
            True if comment posted successfully, False otherwise
        """
        result = subprocess.run(
            [
                "erk",
                "kit",
                "exec",
                "erk",
                "comment-worktree-creation",
                str(issue_number),
                worktree_name,
                branch_name,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        return result.returncode == 0

    def update_issue_body(self, issue_number: int, body: str) -> bool:
        """Update issue body via gh issue edit.

        Args:
            issue_number: GitHub issue number
            body: New issue body content

        Returns:
            True if update succeeded, False otherwise
        """
        result = subprocess.run(
            ["gh", "issue", "edit", str(issue_number), "--body", body],
            capture_output=True,
            text=True,
            check=False,
        )

        return result.returncode == 0
