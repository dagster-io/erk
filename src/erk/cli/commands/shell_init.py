"""Shell initialization command for erk.

Outputs shell code that wraps Claude with seamless worktree switching.
When Claude terminates and a switch-request marker exists, the wrapper
detects it, navigates to the target worktree, and resumes Claude.

Usage:
    # Add to ~/.bashrc or ~/.zshrc
    source <(erk shell-init)
"""

import click

# Shell function that wraps claude with restart loop
SHELL_WRAPPER = r"""
# erk shell integration: claude wrapper with worktree switching
function claude() {
    local _erk_resume_cmd=""
    while true; do
        # Check for pending resume command (from worktree switch)
        if [[ -f ~/.erk/switch-request-command ]]; then
            _erk_resume_cmd=$(cat ~/.erk/switch-request-command)
            rm ~/.erk/switch-request-command
            command claude --continue "$_erk_resume_cmd"
        elif [[ -n "$_erk_resume_cmd" ]]; then
            # Continuing after worktree switch, use --continue
            command claude --continue "$_erk_resume_cmd"
            _erk_resume_cmd=""
        else
            # Normal invocation - pass through arguments as-is
            command claude "$@"
        fi
        exit_code=$?

        # Check for switch request
        if [[ -f ~/.erk/switch-request ]]; then
            target=$(cat ~/.erk/switch-request)
            rm ~/.erk/switch-request
            wt_path=$(erk implement "$target" --path-only 2>/dev/null)
            if [[ -n "$wt_path" ]]; then
                cd "$wt_path" || continue
                [[ -f .venv/bin/activate ]] && source .venv/bin/activate 2>/dev/null
                # Keep _erk_resume_cmd for next iteration if it was set
                continue
            fi
        fi

        return $exit_code
    done
}
"""


@click.command("shell-init")
def shell_init_cmd() -> None:
    """Output shell code for erk integration.

    This outputs a shell function that wraps the `claude` command to enable
    seamless worktree switching. When Claude terminates and an erk switch
    request exists, the wrapper automatically:

    1. Reads the target issue number from the switch request
    2. Sets up the implementation worktree
    3. Changes to the worktree directory
    4. Activates the Python virtual environment
    5. Restarts Claude with the continuation command

    Usage:

    \b
      # Add to ~/.bashrc or ~/.zshrc
      source <(erk shell-init)

    \b
      # Or manually invoke to test
      erk shell-init | source /dev/stdin
    """
    click.echo(SHELL_WRAPPER)
