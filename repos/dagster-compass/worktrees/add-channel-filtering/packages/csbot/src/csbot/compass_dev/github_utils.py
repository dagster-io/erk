"""GitHub utility commands."""

import asyncio

import click

from csbot.local_context_store.github.config import GithubConfig
from csbot.slackbot.slackbot_core import load_bot_server_config_from_path
from csbot.slackbot.slackbot_github_monitor import GithubMonitor, SlackbotGithubMonitor


@click.group()
def github():
    """GitHub utility commands."""
    pass


@github.command()
@click.option(
    "--config-file",
    required=True,
    help="Path to bot configuration YAML file",
)
@click.option(
    "--repo-name",
    required=True,
    help="Repository name in format 'owner/repo'",
)
def rate_limits(config_file: str, repo_name: str):
    """Check GitHub API rate limits.

    Example:
        compass-dev github rate-limits --config-file local.csbot.config.yaml --repo-name owner/repo
    """
    # Load bot config
    bot_config = load_bot_server_config_from_path(config_file)

    auth_source = bot_config.github.get_auth_source()

    github_config = GithubConfig(
        auth_source=auth_source,
        repo_name=repo_name,
    )

    # Get rate limits
    github_client = github_config.auth_source.get_github_client()
    rate_limit = github_client.get_rate_limit()
    click.echo(str(rate_limit))


@github.command()
@click.option(
    "--config-file",
    required=True,
    help="Path to bot configuration YAML file",
)
@click.option(
    "--repo-name",
    required=True,
    help="Repository name in format 'owner/repo'",
)
@click.option(
    "--limit",
    default=10,
    help="Number of recent events to fetch (default: 10)",
)
def recent_events(config_file: str, repo_name: str, limit: int):
    """Fetch and print recent GitHub events (issues/PRs created, merged, closed).

    This command fetches recent issue and PR activity from a GitHub repository,
    similar to the github_monitor_event_tick logic.

    Example:
        compass-dev github recent-events \\
            --config-file local.csbot.config.yaml \\
            --repo-name owner/repo \\
            --limit 20
    """
    from datetime import timedelta

    # Load bot config
    bot_config = load_bot_server_config_from_path(config_file)

    auth_source = bot_config.github.get_auth_source()

    github_config = GithubConfig(
        auth_source=auth_source,
        repo_name=repo_name,
    )

    # Get the repository
    g = github_config.auth_source.get_github_client()
    repo = g.get_repo(github_config.repo_name)

    # Get recent issues sorted by most recently updated
    first_page = repo.get_issues(state="all", sort="updated", direction="desc").get_page(0)

    if not first_page:
        click.echo("No issues or PRs found in repository")
        return

    most_recent_updated = first_page[0].updated_at
    click.echo(f"📊 Recent GitHub Events for {repo_name}")
    click.echo("=" * 60)
    click.echo(f"Most Recent Update: {most_recent_updated.isoformat()}")
    click.echo(f"Fetching last {limit} events...")
    click.echo()

    # Calculate since timestamp (look back a reasonable amount)
    since = most_recent_updated - timedelta(days=30)

    # Get issues sorted by update time ascending (so we process oldest first)
    issues = repo.get_issues(
        state="all",
        sort="updated",
        direction="asc",
        since=since,
    )

    events = []
    for issue in issues:
        if issue.closed_at:
            if issue.pull_request:
                # Check if PR was merged
                if issue.pull_request.merged_at:
                    events.append(
                        {
                            "type": "PR Merged",
                            "url": issue.html_url,
                            "title": issue.title,
                            "timestamp": issue.closed_at,
                        }
                    )
                else:
                    events.append(
                        {
                            "type": "PR Closed",
                            "url": issue.html_url,
                            "title": issue.title,
                            "timestamp": issue.closed_at,
                        }
                    )
            else:
                events.append(
                    {
                        "type": "Issue Closed",
                        "url": issue.html_url,
                        "title": issue.title,
                        "timestamp": issue.closed_at,
                    }
                )
        else:
            if issue.pull_request:
                events.append(
                    {
                        "type": "PR Created",
                        "url": issue.html_url,
                        "title": issue.title,
                        "timestamp": issue.created_at,
                    }
                )
            else:
                events.append(
                    {
                        "type": "Issue Opened",
                        "url": issue.html_url,
                        "title": issue.title,
                        "timestamp": issue.created_at,
                    }
                )

    # Sort by timestamp descending (most recent first) and limit
    events.sort(key=lambda e: e["timestamp"], reverse=True)
    events = events[:limit]

    click.echo(f"Found {len(events)} recent events:")
    click.echo()

    for i, event in enumerate(events, 1):
        event_type = event["type"]
        title = event["title"]
        url = event["url"]
        timestamp = event["timestamp"].isoformat()

        # Pick emoji based on event type
        if "Merged" in event_type:
            emoji = "✅"
        elif "Closed" in event_type:
            emoji = "❌"
        elif "Created" in event_type or "Opened" in event_type:
            emoji = "🆕"
        else:
            emoji = "📝"

        click.echo(f"{i}. {emoji} {event_type}")
        click.echo(f"   Title: {title}")
        click.echo(f"   URL: {url}")
        click.echo(f"   Time: {timestamp}")
        click.echo()


@github.command()
@click.option(
    "--config-file",
    required=True,
    help="Path to bot configuration YAML file",
)
@click.option(
    "--repo-name",
    required=True,
    help="Repository name in format 'owner/repo'",
)
@click.argument("pr_url", type=str)
def pr_details(config_file: str, repo_name: str, pr_url: str):
    """Get details for a GitHub pull request.

    This command fetches the title, body, and file contents of a PR.
    Returns None if the PR is too large (>10 files or >1000 lines changed).

    Example:
        compass-dev github pr-details \\
            --config-file local.csbot.config.yaml \\
            --repo-name owner/repo \\
            https://github.com/owner/repo/pull/123
    """
    # Load bot config
    bot_config = load_bot_server_config_from_path(config_file)

    auth_source = bot_config.github.get_auth_source()

    github_config = GithubConfig(
        auth_source=auth_source,
        repo_name=repo_name,
    )

    # Create GithubMonitor and get PR details
    monitor = GithubMonitor(github_config)

    async def fetch_details():
        return await monitor.get_pr_details(pr_url)

    details = asyncio.run(fetch_details())

    if details is None:
        click.echo("❌ PR is too large (>10 files or >1000 lines changed) or not found")
        return

    click.echo("📋 Pull Request Details")
    click.echo("=" * 80)
    click.echo()

    click.echo(f"🔗 URL: {pr_url}")
    click.echo(f"📝 Title: {details['title']}")
    click.echo()

    if details.get("body"):
        click.echo("📄 Body:")
        click.echo("-" * 80)
        for line in details["body"].split("\n"):
            click.echo(line)
        click.echo("-" * 80)
        click.echo()

    # Display files
    files = details.get("files", {})
    if isinstance(files, dict):
        click.echo(f"📁 Files Changed: {len(files)}")
        click.echo()
        for filename, content in sorted(files.items()):
            click.echo(f"  📄 {filename}")
            click.echo(f"     Length: {len(content)} characters")
            click.echo()
    else:
        click.echo("📁 Files: (summary only)")
        click.echo(f"  {files}")
        click.echo()


@github.command()
@click.option(
    "--config-file",
    required=True,
    help="Path to bot configuration YAML file",
)
@click.argument("pr_url", type=str)
@click.argument("channel_name", type=str)
def promote_pr_to_channel(config_file: str, pr_url: str, channel_name: str):
    """Promote a PR's general changes to channel-specific changes.

    This command:
    1. Extracts repo name from PR URL
    2. Creates a SlackbotGithubMonitor
    3. Calls handle_pr_approve_channel with automerge=False
    4. Commits the promoted changes to the PR branch

    Example:
        compass-dev github promote-pr-to-channel \\
            --config-file local.csbot.config.yaml \\
            https://github.com/owner/repo/pull/123 \\
            my-channel
    """
    import logging

    # Extract repo name from PR URL
    if "github.com" not in pr_url:
        click.echo("❌ Invalid PR URL: must be a GitHub URL", err=True)
        return

    try:
        parts = pr_url.split("github.com/")[1].split("/")
        if len(parts) < 4 or parts[2] != "pull":
            click.echo(
                "❌ Invalid PR URL format: expected https://github.com/owner/repo/pull/123",
                err=True,
            )
            return
        repo_name = f"{parts[0]}/{parts[1]}"
    except (IndexError, ValueError) as e:
        click.echo(f"❌ Failed to parse PR URL: {e}", err=True)
        return

    # Load bot config
    bot_config = load_bot_server_config_from_path(config_file)
    auth_source = bot_config.github.get_auth_source()

    github_config = GithubConfig(
        auth_source=auth_source,
        repo_name=repo_name,
    )

    click.echo(f"🔍 Promoting PR to channel: {channel_name}")
    click.echo(f"   PR URL: {pr_url}")
    click.echo(f"   Repo: {repo_name}")
    click.echo("=" * 80)
    click.echo()

    # Create GithubMonitor
    github_monitor = GithubMonitor(github_config)

    # Create SlackbotGithubMonitor with null values for unused parameters
    slackbot_monitor = SlackbotGithubMonitor(
        channel_name=channel_name,
        github_monitor=github_monitor,
        kv_store=None,  # type: ignore[arg-type]
        client=None,  # type: ignore[arg-type]
        logger=logging.getLogger(__name__),
        agent=None,  # type: ignore[arg-type]
    )

    # Call handle_pr_approve_channel with automerge=False
    async def promote():
        await slackbot_monitor.handle_pr_approve_channel(pr_url, "CLI User", automerge=False)

    try:
        asyncio.run(promote())
        click.echo()
        click.echo("=" * 80)
        click.echo("✅ Successfully promoted changes to channel-specific")
        click.echo(f"   Channel: {channel_name}")
        click.echo(f"   PR URL: {pr_url}")
        click.echo()
        click.echo("The PR has been updated with channel-specific changes.")
        click.echo("You can now review and merge it manually.")
    except Exception as e:
        import traceback

        click.echo()
        click.echo("=" * 80)
        click.echo(f"❌ Failed to promote changes: {e}", err=True)
        click.echo()
        click.echo("Traceback:", err=True)
        click.echo(traceback.format_exc(), err=True)
