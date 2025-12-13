import click

from csbot.ctx_admin.cli.context_commands import context
from csbot.ctx_admin.cli.migration_commands import migration
from csbot.ctx_admin.cli.project_commands import project


@click.group()
def cli():
    """ctx-admin - contextstore CLI admin tool"""
    pass


# Register command groups
cli.add_command(project)
cli.add_command(context)
cli.add_command(migration)


# Add individual commands to maintain backward compatibility with original flat structure
# Project commands
cli.add_command(project.commands["init"], name="init")

# Context commands
cli.add_command(context.commands["add-context"], name="add-context")
cli.add_command(context.commands["search-context"], name="search-context")

# Migration commands
cli.add_command(migration.commands["migrate"], name="migrate")
cli.add_command(migration.commands["check"], name="check")


if __name__ == "__main__":
    cli()
