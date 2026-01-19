# Shell Integration

Enable automatic directory changes when navigating worktrees.

## Overview

By default, erk uses **activation scripts** for worktree switching—you copy-paste a `source .erk/activate.sh` command that handles the directory change. Shell integration is an alternative that enables automatic `cd` behavior, so navigation commands change your shell's working directory directly.

With shell integration enabled:

- `erk br co <branch>` changes to that branch's worktree
- `erk up` / `erk down` navigate the stack
- `erk wt co <worktree>` switches to a specific worktree
- `erk pr co <number>` checks out a PR and navigates to it

## How to Enable

Shell integration is a global configuration setting. Enable it with:

```bash
erk config set shell_integration true
```

To disable later:

```bash
erk config set shell_integration false
```

Check current status:

```bash
erk config get shell_integration
```

## Supported Shells

Shell integration works with:

- **bash**
- **zsh**
- **fish**

The integration uses shell-specific mechanisms to change the working directory of your current shell session.

## How It Works

When shell integration is enabled, navigation commands output a shell script to stdout instead of printing instructions. A wrapper function in your shell sources this script, which:

1. Changes to the target worktree directory
2. Sets up the environment (virtualenv, .env files)
3. Runs any configured post-create commands

The wrapper function is automatically set up when you first enable shell integration.

## Alternative: Activation Scripts

If you prefer explicit control or shell integration doesn't work in your environment, erk defaults to activation scripts. After a worktree operation, you'll see a command like:

```bash
source /path/to/worktree/.erk/activate.sh
```

Copy-paste and run this to navigate and set up the environment.

## Troubleshooting

### Commands don't change directory

1. Verify shell integration is enabled: `erk config get shell_integration`
2. Check you're using a supported shell (bash, zsh, fish)
3. Try starting a new terminal session

### "Running via uvx" warning

If you installed erk with `uvx erk`, shell integration won't work because each invocation runs in an isolated environment. Install erk persistently instead:

```bash
uv tool install erk
```

### Navigation spawns a subshell

This happens when shell integration detects it can't modify your current shell. Common causes:

- Running in an unsupported shell
- Shell wrapper not properly loaded
- Running inside a script or subprocess

## See Also

- [Navigate Branches and Worktrees](../howto/navigate-branches-worktrees.md) - All navigation commands
- [Worktrees](../topics/worktrees.md) - How worktrees work
- [Prerequisites](prerequisites.md) - Required tools
