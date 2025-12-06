"""Kit commands group."""

import click

from dot_agent_kit.commands.kit import check, install, registry, search, show, sync
from dot_agent_kit.commands.kit.list import list_installed_kits, ls
from dot_agent_kit.commands.kit.remove import remove, rm


@click.group()
def kit_group() -> None:
    """Manage kits - install, update, sync, and search.

    Common commands:
      install    Install or update a specific kit
      list/ls    List installed kits
      remove/rm  Remove installed kits
      search     Search or list all available kits
      show       Show detailed information about a kit
      sync       Sync all or specific kits with their sources
      registry   Manage kit documentation registry
    """


# Register all kit commands
kit_group.add_command(check.check)
kit_group.add_command(install.install)
kit_group.add_command(list_installed_kits)
kit_group.add_command(ls)
kit_group.add_command(remove)
kit_group.add_command(rm)
kit_group.add_command(search.search)
kit_group.add_command(show.show)
kit_group.add_command(sync.sync)
kit_group.add_command(registry.registry)
