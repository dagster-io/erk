"""Configure a planner box interactively."""

import subprocess

import click

from erk.core.context import ErkContext

SETUP_CHECKLIST = """
┌─────────────────────────────────────────────────────────────────────┐
│                     Planner Setup Checklist                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. Claude Code Authentication                                      │
│     └─ Run: claude                                                  │
│        Follow prompts to authenticate with Anthropic                │
│                                                                     │
│  2. Verify Setup                                                    │
│     └─ gh auth status      (should show logged in)                  │
│     └─ claude doctor       (should show all green)                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
"""


@click.command("configure")
@click.argument("name")
@click.pass_obj
def configure_planner(ctx: ErkContext, name: str) -> None:
    """Configure a planner box with an interactive SSH session.

    Opens an interactive SSH session to the codespace for manual setup
    (installing tools, setting up auth, etc.). When you exit the session,
    you'll be prompted to mark the planner as configured.
    """
    planner = ctx.planner_registry.get(name)
    if planner is None:
        click.echo(f"Error: No planner named '{name}' found.", err=True)
        click.echo("\nUse 'erk planner list' to see registered planners.", err=True)
        raise SystemExit(1)

    if planner.configured:
        click.echo(f"Note: Planner '{name}' is already marked as configured.", err=True)
        if not click.confirm("Continue with configuration session anyway?"):
            raise SystemExit(0)

    click.echo(SETUP_CHECKLIST, err=True)
    click.echo(f"Opening interactive SSH session to '{name}'...", err=True)
    click.echo(
        "Complete the setup steps above, then exit the session (Ctrl+D or 'exit').", err=True
    )
    click.echo("", err=True)

    # Run interactive SSH session (waits for completion)
    result = subprocess.run(
        ["gh", "codespace", "ssh", "-c", planner.gh_name],
        check=False,
    )

    if result.returncode != 0:
        click.echo(f"SSH session ended with error (exit code {result.returncode}).", err=True)
        # Still allow marking as configured if user wants

    # Ask if configuration is complete
    click.echo("", err=True)
    if click.confirm(f"Mark planner '{name}' as configured?"):
        ctx.planner_registry.mark_configured(name)
        click.echo(f"Planner '{name}' marked as configured.", err=True)
    else:
        click.echo(
            f"Planner '{name}' left unconfigured. Run 'erk planner configure {name}' again later.",
            err=True,
        )
