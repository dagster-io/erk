import click

from erk.core.context import ErkContext
from erk_shared.output.output import machine_output


@click.group("completion")
def completion_group() -> None:
    """Generate shell completion scripts."""


@completion_group.command("bash")
@click.pass_obj
def completion_bash(ctx: ErkContext) -> None:
    """Generate bash completion script.

    \b
    For automatic setup of both completion and auto-activation:
      erk init --shell

    \b
    To load completions in your current shell session:
      source <(erk completion bash)

    \b
    To load completions permanently, add to your ~/.bashrc:
      echo 'source <(erk completion bash)' >> ~/.bashrc

    \b
    Alternatively, you can save the completion script to bash_completion.d:
      erk completion bash > /usr/local/etc/bash_completion.d/erk

    \b
    You will need to start a new shell for this setup to take effect.
    """
    script = ctx.completion.generate_bash()
    machine_output(script, nl=False)


@completion_group.command("zsh")
@click.pass_obj
def completion_zsh(ctx: ErkContext) -> None:
    """Generate zsh completion script.

    \b
    For automatic setup of both completion and auto-activation:
      erk init --shell

    \b
    To load completions in your current shell session:
      source <(erk completion zsh)

    \b
    To load completions permanently, add to your ~/.zshrc:
      echo 'source <(erk completion zsh)' >> ~/.zshrc

    \b
    Note: Make sure compinit is called in your ~/.zshrc after loading completions.

    \b
    You will need to start a new shell for this setup to take effect.
    """
    script = ctx.completion.generate_zsh()
    machine_output(script, nl=False)


@completion_group.command("fish")
@click.pass_obj
def completion_fish(ctx: ErkContext) -> None:
    """Generate fish completion script.

    \b
    For automatic setup of both completion and auto-activation:
      erk init --shell

    \b
    To load completions in your current shell session:
      erk completion fish | source

    \b
    To load completions permanently:
      mkdir -p ~/.config/fish/completions && \\
      erk completion fish > ~/.config/fish/completions/erk.fish

    \b
    You will need to start a new shell for this setup to take effect.
    """
    script = ctx.completion.generate_fish()
    machine_output(script, nl=False)
