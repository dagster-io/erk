"""Script-mode error handling for --script commands.

Provides a context manager that catches errors and emits a valid error script
so that ``source "$(erk ... --script)"`` never receives empty stdout.
"""

import contextlib
import sys
from collections.abc import Generator

import click

from erk_shared.context.context import ErkContext
from erk_shared.output.output import user_output


def _write_error_script_and_exit(ctx: ErkContext) -> None:
    """Write a minimal error script and output its path, then exit 1.

    Used by ``script_error_handler`` to ensure ``source "$(erk br co --script)"``
    always receives a valid file path — even on failure — so the shell never
    sees ``source ""``.
    """
    result = ctx.script_writer.write_activation_script(
        "# erk error\nreturn 1\n",
        command_name="checkout",
        comment="checkout error",
    )
    result.output_for_script_handler()
    sys.exit(1)


@contextlib.contextmanager
def script_error_handler(ctx: ErkContext) -> Generator[None]:
    """Catch errors in --script mode and emit an error script instead of empty stdout.

    Wraps the checkout body so that any error path produces a valid script
    file on stdout. Without this, ``source "$(erk br co --script)"`` receives
    an empty string when the command fails, causing a confusing
    ``source: no such file or directory:`` error.

    Exception handling:
    - ``SystemExit(0)``: Re-raised (success exit from e.g. ``_setup_impl_for_plan``).
    - ``SystemExit(non-zero)``: Error already printed via ``user_output()``;
      write error script and exit 1.
    - ``click.ClickException``: Format the error ourselves (Click's handler
      won't run since we catch first), write error script, exit 1.
    - ``RuntimeError``: Print to stderr, write error script, exit 1.
    """
    try:
        yield
    except SystemExit as exc:
        if exc.code == 0:
            raise
        _write_error_script_and_exit(ctx)
    except click.ClickException as exc:
        user_output(f"Error: {exc.format_message()}")
        _write_error_script_and_exit(ctx)
    except RuntimeError as exc:
        user_output(f"Error: {exc}")
        _write_error_script_and_exit(ctx)
