import json

import click
from csadmin.utils import get_project_path

from csbot.contextengine.context_engine import (
    ContextSearcher,
)
from csbot.local_context_store.git.file_tree import create_git_commit_file_tree


@click.group()
def context():
    """Context management commands"""
    pass


@context.command()
@click.option("--query", "-q", required=True, help="Search query string")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["console", "json"]),
    default="console",
    help="Output format (console or json)",
)
@click.option(
    "--team",
    "-t",
    multiple=True,
    help="Include team contexts (can be specified multiple times)",
)
@click.option("--user", "-u", help="Include user context")
@click.option("--all", is_flag=True, default=False, help="Add context for all users and teams")
def search_context(query, format, team, user, all):
    """Search context using full-text search"""
    try:
        click.echo(click.style("Searching context...", fg="white"))

        project_path = get_project_path()
        if project_path is None:
            click.echo(click.style("No contextstore project found", fg="red"))
            return

        with create_git_commit_file_tree(project_path, f"local:{project_path}") as tree:
            from csbot.contextengine.loader import load_context_store

            context_store = load_context_store(tree)
            searcher = ContextSearcher(context_store=context_store, channel_name=None)
            results = searcher.search(query)

        if format == "json":
            click.echo(
                json.dumps(
                    [[file_path, context.model_dump()] for file_path, context in results],
                    indent=2,
                )
            )
        else:
            if not results:
                click.echo(click.style("No results found", fg="yellow"))
            else:
                output = []
                for file_path, context in results:
                    output.append(f"File: {file_path}")
                    output.append(f"Topic: {context.topic}")
                    output.append(f"Incorrect Understanding: {context.incorrect_understanding}")
                    output.append(f"Correct Understanding: {context.correct_understanding}")
                    output.append("---")
                click.echo("\n".join(output))

    except Exception as e:
        click.echo(click.style(f"❌ Error searching context: {str(e)}", fg="red"), err=True)
        raise click.Abort()
