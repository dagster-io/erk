import click


@click.command("shell-init")
@click.pass_obj
def shell_init_cmd(ctx: object) -> None:
    """Initialize shell integration for erk."""
    print("test")
