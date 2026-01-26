"""Local runner for plan implementations using tmux + git worktrees."""

import re
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path

from erk_shared.output.output import user_output


@dataclass(frozen=True)
class LocalRunnerCredentials:
    """Credentials for local runner execution."""

    github_pat: str
    claude_oauth_token: str
    anthropic_api_key: str

    @staticmethod
    def load_from_config() -> "LocalRunnerCredentials":
        """Load credentials from ~/.erk/local-runner-config.toml.

        Returns:
            LocalRunnerCredentials with loaded values

        Raises:
            ValueError: If config file is missing or incomplete
        """
        config_path = Path.home() / ".erk" / "local-runner-config.toml"
        if not config_path.exists():
            msg = (
                "Missing ~/.erk/local-runner-config.toml\n\n"
                "Create it with:\n"
                "[credentials]\n"
                'github_pat = "ghp_..."\n'
                'claude_oauth_token = "..."\n'
                'anthropic_api_key = "sk-ant-..."\n'
            )
            raise ValueError(msg)

        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        creds = data.get("credentials", {})

        # Validate required fields
        required_fields = ["github_pat", "claude_oauth_token", "anthropic_api_key"]
        missing = [f for f in required_fields if f not in creds]
        if missing:
            msg = (
                f"Missing required credential(s): {', '.join(missing)}\n\n"
                "Check ~/.erk/local-runner-config.toml format"
            )
            raise ValueError(msg)

        return LocalRunnerCredentials(
            github_pat=creds["github_pat"],
            claude_oauth_token=creds["claude_oauth_token"],
            anthropic_api_key=creds["anthropic_api_key"],
        )


def _extract_worktree_path(activation_script: str) -> Path:
    """Extract worktree path from erk prepare --script output.

    Args:
        activation_script: Output from 'erk prepare --script'

    Returns:
        Path to the worktree

    Raises:
        ValueError: If path cannot be parsed from script
    """
    # Script format: source <(echo "cd /path/to/worktree && ...")
    match = re.search(r"cd ([^\s;&]+)", activation_script)
    if not match:
        msg = f"Could not parse worktree path from: {activation_script}"
        raise ValueError(msg)
    return Path(match.group(1))


def execute_local_implementation(
    *,
    issue_number: int,
    submitted_by: str,
) -> None:
    """Execute plan implementation locally using tmux + worktree.

    Args:
        issue_number: GitHub issue number to implement
        submitted_by: GitHub username for commit attribution
    """
    # Load credentials
    try:
        creds = LocalRunnerCredentials.load_from_config()
    except ValueError as e:
        user_output(f"Error: {e}")
        raise SystemExit(1) from None

    # Create worktree via erk prepare
    user_output(f"Creating worktree for issue #{issue_number}...")
    try:
        prepare_result = subprocess.run(
            ["erk", "prepare", str(issue_number), "--script"],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        user_output(f"Error creating worktree: {e.stderr}")
        raise SystemExit(1) from None

    # Parse activation script to extract worktree path
    activation_script = prepare_result.stdout.strip()
    try:
        worktree_path = _extract_worktree_path(activation_script)
    except ValueError as e:
        user_output(f"Error: {e}")
        raise SystemExit(1) from None

    # Create tmux session name
    session_name = f"erk-impl-{issue_number}"

    # Build implementation command with environment variables
    impl_command = f"""
set -euo pipefail

# Export credentials
export GITHUB_TOKEN="{creds.github_pat}"
export CLAUDE_CODE_OAUTH_TOKEN="{creds.claude_oauth_token}"
export ANTHROPIC_API_KEY="{creds.anthropic_api_key}"
export GIT_AUTHOR_NAME="{submitted_by}"
export GIT_AUTHOR_EMAIL="{submitted_by}@users.noreply.github.com"
export GIT_COMMITTER_NAME="{submitted_by}"
export GIT_COMMITTER_EMAIL="{submitted_by}@users.noreply.github.com"

# Run implementation
echo "Starting implementation for issue #{issue_number}..."
erk impl {issue_number}

# Capture exit code
EXIT_CODE=$?
echo "Implementation completed with exit code: $EXIT_CODE"

# Keep tmux session open for inspection
echo ""
echo "Press Enter to exit or review logs above"
read -r
"""

    # Launch tmux session
    user_output(f"Launching tmux session: {session_name}")
    try:
        subprocess.run(
            [
                "tmux",
                "new-session",
                "-d",
                "-s",
                session_name,
                "-c",
                str(worktree_path),
                "bash",
                "-c",
                impl_command,
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        user_output(f"Error launching tmux: {e}")
        raise SystemExit(1) from None

    # Output success message with monitoring commands
    user_output("")
    user_output(
        f"Local implementation started for issue #{issue_number}\n"
        f"Session: {session_name}\n"
        f"Worktree: {worktree_path}\n\n"
        f"Monitor:\n"
        f"  tmux attach -t {session_name}\n"
        f"  erk local-runner logs {issue_number}\n\n"
        f"Stop:\n"
        f"  erk local-runner stop {issue_number}"
    )
