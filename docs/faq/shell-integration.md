# Shell Integration FAQ

Troubleshooting directory switching and navigation problems.

## Common Issues

### Navigation commands don't change my directory

**Symptom:** Running `erk br co <branch>` or `erk up` shows output but doesn't change your working directory.

**Cause:** Shell integration is not enabled or not working.

**Solution:**

1. Enable shell integration: `erk config set shell_integration true`
2. Start a new terminal session
3. Try the navigation command again

If still not working, see the [Shell Integration tutorial](../tutorials/shell-integration.md) for troubleshooting.

### "Running via uvx" warning

**Symptom:** You see a warning about running erk via uvx and shell integration not working.

**Cause:** `uvx erk` runs each command in an isolated environment, preventing shell integration from modifying your current shell.

**Solution:** Install erk persistently:

```bash
uv tool install erk
```

Then ensure `~/.local/bin` is in your PATH.

### Commands spawn a subshell instead of navigating

**Symptom:** Navigation opens a new shell session instead of changing the current directory.

**Cause:** The shell wrapper couldn't be set up, so erk falls back to subshell behavior.

**Solution:**

1. Check you're using a supported shell (bash, zsh, fish)
2. Try re-enabling shell integration: `erk config set shell_integration true`
3. Start a fresh terminal session

### Activation script doesn't exist

**Symptom:** Error about missing `.erk/activate.sh` file.

**Cause:** The worktree was created before activation scripts were enabled, or the file was deleted.

**Solution:** Re-run any navigation or checkout command—erk regenerates activation scripts automatically.

## See Also

- [Shell Integration Tutorial](../tutorials/shell-integration.md) - Full setup guide
- [Navigate Branches and Worktrees](../howto/navigate-branches-worktrees.md) - Navigation commands reference
