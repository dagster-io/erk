"""Slack team management commands for compass-dev."""

import json
from urllib.parse import urlencode

import click
import requests


@click.group()
def slack_team():
    """Slack team management commands."""
    pass


@slack_team.command()
@click.option(
    "--token",
    required=True,
    help="Slack API token with admin.teams:write scope",
)
@click.option(
    "--team-name",
    required=True,
    help="Name of the team to create",
)
@click.option(
    "--team-domain",
    required=True,
    help="Team domain (max 21 characters)",
)
@click.option(
    "--team-description",
    help="Description for the team",
)
@click.option(
    "--team-discoverability",
    type=click.Choice(["open", "closed", "invite_only", "unlisted"]),
    default="invite_only",
    help="Who can join the team (default: invite_only)",
)
def create(
    token: str,
    team_name: str,
    team_domain: str,
    team_description: str | None,
    team_discoverability: str,
):
    """Create a new Slack team in Enterprise Grid workspace.

    This command uses the admin.teams.create API to create a new team.
    Requires a token with admin.teams:write scope and admin permissions.
    """
    # Validate team domain length
    if len(team_domain) > 21:
        click.echo("Error: team-domain must be 21 characters or fewer", err=True)
        raise click.Abort()

    # Prepare API request payload
    payload = {
        "team_name": team_name,
        "team_domain": team_domain,
        "team_discoverability": team_discoverability,
    }

    if team_description:
        payload["team_description"] = team_description

    # Make API request
    try:
        response = requests.post(
            "https://slack.com/api/admin.teams.create",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data=urlencode(payload),
            timeout=30,
        )
        response.raise_for_status()

        result = response.json()

        if result.get("ok"):
            click.echo("✅ Team created successfully!")
            click.echo(f"Team ID: {result.get('team')}")
            click.echo(f"Team Name: {team_name}")
            click.echo(f"Team Domain: {team_domain}")
        else:
            error = result.get("error", "Unknown error")
            click.echo(f"❌ Failed to create team: {error}", err=True)
            if "detail" in result:
                click.echo(f"Details: {result['detail']}", err=True)
            raise click.Abort()

    except requests.RequestException as e:
        click.echo(f"❌ Network error: {e}", err=True)
        raise click.Abort()
    except json.JSONDecodeError:
        click.echo("❌ Invalid response from Slack API", err=True)
        raise click.Abort()
