"""Standalone CLI for erk-slack-serve."""

from pathlib import Path

import click


@click.command()
@click.option(
    "--repo",
    type=click.Path(exists=True, path_type=Path),
    help="Repository path for agent context (defaults to current directory)",
)
def main(repo: Path | None) -> None:
    """Start the erk Slack bot server.

    The bot connects to Slack via Socket Mode and listens for app mentions.
    When mentioned, it spawns a Claude agent to handle the conversation.

    Environment variables required:
        SLACK_BOT_TOKEN: Bot User OAuth Token (xoxb-...)
        SLACK_APP_TOKEN: App-Level Token for Socket Mode (xapp-...)
        SLACK_TEAM_ID: Workspace ID for MCP server
    """
    from erk.slack.app import run_bot

    repo_path = repo if repo is not None else Path.cwd()
    run_bot(repo_path)


if __name__ == "__main__":
    main()
