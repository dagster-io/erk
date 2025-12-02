"""Shim for idempotent_squash kit CLI command.

The canonical implementation is in erk_shared.integrations.gt.kit_cli_commands.gt.idempotent_squash.
This file exists only to provide the entry point for the kit CLI system.
Import symbols directly from the canonical location.
"""

from erk_shared.integrations.gt.kit_cli_commands.gt.idempotent_squash import (
    idempotent_squash as idempotent_squash,
)
