"""Real implementation of AgentSpawner using Claude CLI with MCP."""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from uuid import uuid4

from erk.slack.agent.abc import AgentResult, AgentSpawner


class RealAgentSpawner(AgentSpawner):
    """Production implementation using Claude CLI with Slack MCP server.

    Spawns a Claude agent process configured with the Slack MCP server
    to handle messages and post replies.

    Attributes:
        bot_token: The Slack Bot User OAuth Token
        team_id: The Slack Workspace ID
    """

    def __init__(self, bot_token: str, team_id: str) -> None:
        """Initialize with Slack credentials.

        Args:
            bot_token: Bot User OAuth Token (SLACK_BOT_TOKEN)
            team_id: Slack Workspace ID (SLACK_TEAM_ID)
        """
        self._bot_token = bot_token
        self._team_id = team_id

    def spawn(
        self,
        channel: str,
        thread_ts: str,
        message: str,
        repo_path: Path,
        session_id: str | None = None,
    ) -> AgentResult:
        """Spawn a Claude agent to handle the message.

        The agent is configured with the Slack MCP server and instructed
        to use mcp__slack__slack_reply_to_thread to post replies.

        Args:
            channel: The Slack channel ID
            thread_ts: The thread timestamp to reply to
            message: The user's message text
            repo_path: Path to the repository for context
            session_id: Optional session ID to resume conversation

        Returns:
            AgentResult with session_id and success status
        """
        # Generate new session ID if not resuming
        new_session_id = session_id if session_id is not None else str(uuid4())

        # Create MCP server configuration
        mcp_config = {
            "mcpServers": {
                "slack": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-slack"],
                    "env": {
                        "SLACK_BOT_TOKEN": self._bot_token,
                        "SLACK_TEAM_ID": self._team_id,
                    },
                }
            }
        }

        # Build system prompt
        tool_name = "mcp__slack__slack_reply_to_thread"
        system_prompt = f"""You are a helpful Slack bot assistant.
You MUST use the {tool_name} tool to respond to the user's message.

Channel: {channel}
Thread: {thread_ts}

Instructions:
1. Read and understand the user's message
2. Provide a helpful response using {tool_name}
3. Always reply in the specified thread

Reply with a brief acknowledgment of the message content."""

        # Build user prompt with the message
        user_prompt = f"User message: {message}"

        # Write MCP config to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(mcp_config, f)
            config_path = f.name

        cmd_args = [
            "claude",
            "--print",
            "--permission-mode",
            "acceptEdits",
            "--mcp-config",
            config_path,
            "--system-prompt",
            system_prompt,
        ]

        # Add session resume if provided
        if session_id is not None:
            cmd_args.extend(["--resume", session_id])

        # Add the user prompt
        cmd_args.append(user_prompt)

        # Set up environment with Slack credentials
        env = os.environ.copy()
        env["SLACK_BOT_TOKEN"] = self._bot_token
        env["SLACK_TEAM_ID"] = self._team_id

        error_message: str | None = None
        success = True

        result = subprocess.run(
            cmd_args,
            cwd=repo_path,
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

        # Clean up temp config file
        if Path(config_path).exists():
            Path(config_path).unlink()

        if result.returncode != 0:
            success = False
            error_message = f"Claude agent failed: {result.stderr}"

        return AgentResult(
            session_id=new_session_id,
            success=success,
            error_message=error_message,
        )
