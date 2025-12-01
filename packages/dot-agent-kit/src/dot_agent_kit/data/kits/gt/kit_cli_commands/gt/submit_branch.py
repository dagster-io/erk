"""Shim for submit_branch kit CLI command.

The canonical implementation is in erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch.
This file exists only to provide the entry point for the kit CLI system.
Import symbols directly from the canonical location.
"""

from erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch import (
    pr_submit as pr_submit,
)
