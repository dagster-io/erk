"""Context management commands for csadmin."""

import json

import click
from csbot.contextengine.context_engine import (
    ContextSearcher,
)
from csbot.ctx_admin.cli.cli_utils import get_project_path
from csbot.local_context_store.git.file_tree import create_git_commit_file_tree


@click.group()
def context():
    """Context management commands."""
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
def search(query: str, format: str):
    """Search context using full-text search."""
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


@context.command()
@click.argument("file_path", required=True)
def rm(file_path: str):
    """Remove a context file."""
    try:
        project_path = get_project_path()
        if project_path is None:
            click.echo(click.style("No contextstore project found", fg="red"))
            return

        # Construct full path relative to project

        full_path = project_path / file_path

        if not full_path.exists():
            click.echo(click.style(f"❌ File not found: {file_path}", fg="red"))
            return

        # Verify it's within the context directory
        try:
            full_path.relative_to(project_path / "context")
        except ValueError:
            click.echo(
                click.style(f"❌ File must be within context/ directory: {file_path}", fg="red")
            )
            return

        # Confirm deletion
        click.confirm(f"Delete {file_path}?", abort=True)

        full_path.unlink()
        click.echo(click.style(f"✅ Deleted {file_path}", fg="green"))

    except click.Abort:
        click.echo(click.style("Cancelled", fg="yellow"))
    except Exception as e:
        click.echo(click.style(f"❌ Error removing context: {str(e)}", fg="red"), err=True)
        raise click.Abort()
