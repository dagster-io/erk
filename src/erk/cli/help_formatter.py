"""Custom Click help formatter for organized command display."""

from collections.abc import Callable
from typing import Any, TypeVar, cast

import click

from erk_shared.gateway.erk_installation.real import RealErkInstallation

F = TypeVar("F", bound=Callable[..., object])


def _get_show_hidden_from_context(ctx: click.Context) -> bool:
    """Check if hidden items should be shown based on config.

    Checks ctx.obj.global_config if available (tests),
    otherwise loads config from disk (direct CLI invocation).
    """
    if ctx.obj is not None:
        config = getattr(ctx.obj, "global_config", None)
        if config is not None:
            return bool(getattr(config, "show_hidden_commands", False))
    # Fallback to loading from disk
    installation = RealErkInstallation()
    if installation.config_exists():
        return installation.load_config().show_hidden_commands
    return False


def _set_param_hidden(param: click.Parameter, hidden: bool) -> None:
    """Set hidden attribute on Click parameter.

    Click's Option class has a 'hidden' attribute, but Parameter (the base class)
    doesn't expose it in type stubs. We use cast(Any, ...) since we've already
    verified via getattr that this parameter has the 'hidden' attribute.
    """
    cast(Any, param).hidden = hidden


class CommandWithHiddenOptions(click.Command):
    """Command that respects show_hidden_commands config for hidden options.

    Use this class for any command with hidden options (like --script).
    Hidden options are shown in a separate "Hidden Options" section when
    show_hidden_commands is enabled in config.
    """

    def format_options(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """Format options, showing hidden ones if config allows."""
        show_hidden = _get_show_hidden_from_context(ctx)

        opts = []
        hidden_opts = []
        for param in self.get_params(ctx):
            # Use getattr since only Option has 'hidden', not all Parameter types
            is_hidden = getattr(param, "hidden", False)

            if is_hidden:
                if show_hidden:
                    # Temporarily unhide to get help record (Click returns None for hidden)
                    _set_param_hidden(param, hidden=False)
                    rv = param.get_help_record(ctx)
                    _set_param_hidden(param, hidden=True)
                    if rv is not None:
                        hidden_opts.append(rv)
            else:
                rv = param.get_help_record(ctx)
                if rv is not None:
                    opts.append(rv)

        if opts:
            with formatter.section("Options"):
                formatter.write_dl(opts)

        if hidden_opts:
            with formatter.section("Hidden Options"):
                formatter.write_dl(hidden_opts)


def script_option(fn: F) -> F:
    """Decorator that adds --script option with proper settings.

    Must be applied to a function decorated with @click.command(cls=CommandWithHiddenOptions).
    The --script flag is hidden by default but visible when show_hidden_commands=True.

    Example:
        @click.command("up", cls=CommandWithHiddenOptions)
        @script_option
        def up_cmd(ctx: ErkContext, script: bool) -> None:
            ...
    """
    return click.option(
        "--script",
        is_flag=True,
        hidden=True,
        help="Output shell script for integration. NOT a dry run.",
    )(fn)
