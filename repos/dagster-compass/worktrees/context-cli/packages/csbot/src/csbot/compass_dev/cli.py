"""Compass developer CLI commands."""

import click

from .add_channels_gitkeep import add_channels_gitkeep
from .agent_record.cli import agent_record
from .ai_pr_update import main as ai_pr_update_main
from .bq_provision import bq_provision
from .context_store import context_store
from .copy_agent import copy_agent
from .copy_bot import copy_bot
from .create_org import create_org
from .create_referral_token import create_referral_token
from .datasets import datasets
from .generate_mock_data import generate_mock_data
from .github_utils import github
from .land_pr import land_pr
from .local_dev import local_dev
from .pr_operations import pr_operations
from .psql import psql
from .render_utils import render
from .slack_oauth import oauth_command
from .slack_oauth_automated import oauth_automated_command
from .slack_team import slack_team
from .slack_utils import slack
from .temporal import temporal
from .thread_health import thread_health
from .thread_utils import thread


@click.group()
def cli():
    """Compass developer tools.

    Collection of developer utilities for the Compass project including:
    - AI-powered PR management and updates
    - BigQuery service account provisioning
    - Agent copying from main dagster repo
    - Mock data generation for testing
    - Graphite-based PR landing automation
    - Advanced PR operations and workflow management
    """
    pass


@cli.command()
def ai_update_pr():
    """Update pull request using AI.

    AI-powered PR update functionality that analyzes commits and generates
    intelligent PR titles and descriptions using Claude Code integration.
    """
    ai_pr_update_main()


# Register all the new commands
cli.add_command(add_channels_gitkeep)
cli.add_command(bq_provision)
cli.add_command(context_store)
cli.add_command(copy_agent)
cli.add_command(create_org)
cli.add_command(copy_bot)
cli.add_command(create_referral_token)
cli.add_command(datasets)
cli.add_command(generate_mock_data)
cli.add_command(github)
cli.add_command(land_pr)
cli.add_command(local_dev)
cli.add_command(pr_operations)
cli.add_command(psql)
cli.add_command(render)
cli.add_command(agent_record)
cli.add_command(oauth_command)
cli.add_command(oauth_automated_command)
cli.add_command(slack_team)
cli.add_command(slack)
cli.add_command(temporal)
cli.add_command(thread_health)
cli.add_command(thread)
