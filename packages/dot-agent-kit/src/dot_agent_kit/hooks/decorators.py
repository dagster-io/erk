"""Decorators for hook commands."""

import functools
from collections.abc import Callable

from dot_agent_kit.hooks.scope import is_in_managed_project


def project_scoped[F: Callable[..., None]](func: F) -> F:
    """Decorator to make a hook only fire within managed projects.

    Usage:
        @click.command()
        @project_scoped
        def my_reminder_hook() -> None:
            click.echo("My reminder message")
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not is_in_managed_project():
            return  # Silent exit
        return func(*args, **kwargs)

    return wrapper  # type: ignore[return-value]
