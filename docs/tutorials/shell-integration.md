# Shell Integration

An optional enhancement that provides seamless `cd` behavior when switching worktrees.

## Do You Need This?

**No.** `erk` works out-of-the-box without shell integration.

When you run worktree-entering commands like `erk implement` or `erk wt checkout`, erk spawns a subshell in the target directory. Type `exit` when you're done to return to your previous directory.

Shell integration changes this behavior: instead of spawning a subshell, erk changes your current shell's directory (like `cd`). Some users prefer this workflow.

| Behavior              | Without Shell Integration       | With Shell Integration |
| --------------------- | ------------------------------- | ---------------------- |
| Directory change      | Subshell (use `exit` to return) | In-place `cd`          |
| Shell history         | Separate per subshell           | Continuous             |
| Environment variables | Fresh in each subshell          | Preserved              |

## When to Consider Shell Integration

You might want shell integration if you:

- Switch between worktrees frequently and dislike typing `exit`
- Want a single continuous shell history
- Prefer `cd` semantics over subshell semantics

You probably don't need it if you:

- Only occasionally switch worktrees
- Like the isolation of subshells (fresh environment each time)
- Are just getting started with erk

## Setup

Run `erk init --shell` to see the setup instructions for your shell:

```bash
erk init --shell
```

This will:

1. Detect your current shell (bash, zsh, or fish)
2. Show the code to add to your shell configuration file

### Zsh

Add the following to your `~/.zshrc`:

```bash
# erk shell integration
eval "$(erk init --shell)"
```

Then reload your shell:

```bash
source ~/.zshrc
```

### Bash

Add the following to your `~/.bashrc`:

```bash
# erk shell integration
eval "$(erk init --shell)"
```

Then reload your shell:

```bash
source ~/.bashrc
```

### Fish

Add the following to your `~/.config/fish/config.fish`:

```fish
# erk shell integration
erk init --shell | source
```

Then reload your shell:

```fish
source ~/.config/fish/config.fish
```

## Verification

After setting up, verify it's working:

```bash
# Should show the shell function, not just the binary path
type erk
```

You should see something like:

```
erk is a shell function from /path/to/your/config
```

If you see only `erk is /path/to/erk`, shell integration isn't loaded.

## Commands That Use Shell Integration

These commands change directories when shell integration is enabled:

- `erk implement` / `erk impl` - Start implementing a plan
- `erk wt checkout` / `erk wt co` - Switch to a worktree
- `erk wt create` - Create and enter a new worktree
- `erk branch checkout` / `erk br co` - Switch to a branch's worktree
- `erk pr checkout` / `erk pr co` - Check out a PR
- `erk land` / `erk branch land` - Land a PR and navigate to the next worktree
- `erk up` / `erk down` - Navigate the worktree stack

Without shell integration, these commands spawn subshells instead.

## Troubleshooting

### Changes directory but doesn't show in prompt

Some prompts cache the current directory. After switching worktrees, try:

```bash
cd .
```

Or check if your prompt has a refresh command.

### "command not found" after setup

Make sure you sourced your shell config file:

```bash
source ~/.zshrc   # or ~/.bashrc for bash
```

Or start a new terminal session.

### Shell integration not loading in new terminals

Check that the `eval` line is in the correct config file for your shell. Interactive shells load:

- Zsh: `~/.zshrc`
- Bash: `~/.bashrc`
- Fish: `~/.config/fish/config.fish`

### Want to disable temporarily

You can run the raw command without shell integration by using `command`:

```bash
command erk wt checkout my-feature
```

This bypasses the shell function and spawns a subshell as usual.

## Next Steps

- [Graphite Integration](graphite-integration.md) - Stacked PR workflows
- [Shell Integration Troubleshooting](../faq/shell-integration.md) - Detailed problem solving
