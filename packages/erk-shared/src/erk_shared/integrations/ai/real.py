"""Real implementation of AI executor using Claude CLI.

Uses subprocess to invoke Claude CLI with the commit-message-generator
subagent. This implementation should only be used at runtime; tests
should use FakeClaudeCLIExecutor.
"""

import subprocess
from pathlib import Path

from erk_shared.integrations.ai.abc import ClaudeCLIExecutor, CommitMessageResult


class RealClaudeCLIExecutor(ClaudeCLIExecutor):
    """Production implementation using Claude CLI with subagent.

    Invokes Claude CLI with --print mode to delegate to the
    commit-message-generator subagent for structured output.
    """

    def generate_commit_message(
        self,
        diff_file: Path,
        repo_root: Path,
        current_branch: str,
        parent_branch: str,
    ) -> CommitMessageResult:
        """Generate commit message by invoking Claude CLI.

        Uses the commit-message-generator subagent to analyze the diff
        and produce a structured commit message.
        """
        # Construct prompt for commit-message-generator subagent
        prompt = f"""Use the Task tool to delegate to the commit-message-generator subagent:

Task(
    subagent_type="commit-message-generator",
    description="Generate commit message from diff",
    prompt="Analyze the git diff and generate a commit message.

Diff file: {diff_file}
Repository root: {repo_root}
Current branch: {current_branch}
Parent branch: {parent_branch}

Use the Read tool to load the diff file."
)

Return ONLY the raw output from the subagent (the commit message text).
Do NOT add any commentary, headers, or formatting around it."""

        result = subprocess.run(
            ["claude", "--print", "--output-format", "text", prompt],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )

        output = result.stdout.strip()
        if not output:
            raise RuntimeError("AI generation returned empty output")

        # Parse: first line is title, rest is body
        lines = output.split("\n", 1)
        title = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else ""

        return CommitMessageResult(title=title, body=body)
