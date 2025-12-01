"""Shim for pr_update kit CLI command.

The canonical implementation is in erk_shared.integrations.gt.kit_cli_commands.gt.pr_update.
This file exists only to provide the entry point for the kit CLI system.
Import symbols directly from the canonical location.
"""

from erk_shared.integrations.gt.kit_cli_commands.gt.pr_update import (
    pr_update as pr_update,
)
