"""Static exec group for erk scripts.

Unlike the kit_exec module which dynamically discovers kits, this module
provides a static list of commands from the erk kit for direct access via
`erk exec <command>`.
"""

import importlib
import traceback
from typing import Any

import click

from erk.kits.cli.output import user_output

# Static list of all erk commands
# These are the scripts from packages/erk-kits/src/erk_kits/data/kits/erk/kit.yaml
ERK_COMMANDS = [
    "add-issue-label",
    "add-reaction-to-comment",
    "add-remote-execution-note",
    "check-impl",
    "check-progress",
    "configure-git-user",
    "create-extraction-branch",
    "create-extraction-plan",
    "create-impl-run-info",
    "create-plan-from-context",
    "create-worker-impl-from-issue",
    "detect-trunk-branch",
    "exit-plan-mode-hook",
    "extract-latest-plan",
    "extract-session-from-issue",
    "find-project-dir",
    "format-error",
    "format-success-output",
    "generate-pr-summary",
    "get-closing-text",
    "get-pr-body-footer",
    "get-pr-discussion-comments",
    "get-pr-review-comments",
    "get-progress",
    "impl-init",
    "impl-signal",
    "impl-verify",
    "issue-title-to-filename",
    "list-sessions",
    "mark-impl-ended",
    "mark-impl-started",
    "mark-step",
    "plan-save-to-issue",
    "post-extraction-comment",
    "post-plan-comment",
    "post-pr-comment",
    "post-start-comment",
    "post-workflow-started-comment",
    "preprocess-session",
    "quick-submit",
    "resolve-review-thread",
    "restack-continue",
    "restack-finalize",
    "restack-preflight",
    "session-id-injector-hook",
    "tripwires-reminder-hook",
    "update-dispatch-info",
    "update-pr-body",
    "update-pr-summary",
    "validate-plan-content",
    "wrap-plan-in-metadata-block",
]

# Module prefix for dynamic command imports
ERK_SCRIPTS_MODULE_PREFIX = "erk_kits.data.kits.erk.scripts.erk"


class LazyExecGroup(click.Group):
    """Click group that loads erk scripts lazily on first access.

    Unlike the dynamic kit system, this uses a static list of commands
    for faster startup and simpler code.
    """

    def __init__(self, debug: bool = False, **kwargs: Any) -> None:
        """Initialize lazy exec group.

        Args:
            debug: Whether to show full tracebacks
            **kwargs: Additional arguments passed to click.Group
        """
        super().__init__(**kwargs)
        self._debug = debug
        self._loaded_commands: set[str] = set()

    def list_commands(self, ctx: click.Context) -> list[str]:
        """List available commands from static list."""
        return sorted(ERK_COMMANDS)

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        """Get a command by name, loading it lazily if needed."""
        # Check if already loaded
        if cmd_name in self._loaded_commands:
            return super().get_command(ctx, cmd_name)

        # Check if valid command name
        if cmd_name not in ERK_COMMANDS:
            return None

        # Get debug flag from context if available
        debug = self._debug
        if ctx.obj and hasattr(ctx.obj, "debug"):
            debug = ctx.obj.debug

        # Convert hyphenated name to snake_case for module import
        module_name = cmd_name.replace("-", "_")
        full_module_path = f"{ERK_SCRIPTS_MODULE_PREFIX}.{module_name}"

        # Import the module
        try:
            module = importlib.import_module(full_module_path)
        except ImportError as e:
            error_msg = f"Warning: Failed to import script '{cmd_name}': {e}\n"
            user_output(error_msg)
            if debug:
                user_output(traceback.format_exc())
            return None

        # Get the script function (convert hyphenated name to snake_case)
        function_name = cmd_name.replace("-", "_")
        if not hasattr(module, function_name):
            error_msg = (
                f"Warning: Script '{cmd_name}' does not have expected function "
                f"'{function_name}' in module {full_module_path}\n"
            )
            user_output(error_msg)
            if debug:
                raise click.ClickException(error_msg)
            return None

        script_func = getattr(module, function_name)

        # Add to the group for future access
        self.add_command(script_func, name=cmd_name)
        self._loaded_commands.add(cmd_name)

        return script_func


# Create the exec group
exec_group = LazyExecGroup(
    name="exec",
    help="Execute erk workflow scripts.",
)
