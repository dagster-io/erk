---
title: Shell Aliases and Shell Integration
read_when:
  - "setting up shell aliases for erk commands"
  - "debugging shell integration issues"
  - "understanding why a command leaves shell stranded"
---

# Shell Aliases and Shell Integration

## The Problem: Aliases Bypass Shell Integration

Direct shell aliases bypass the `erk()` wrapper function, breaking shell integration for commands that need it.

```bash
# ❌ DANGEROUS: This alias bypasses shell integration
alias land='erk pr land'

# When you run `land`, it calls `erk pr land` directly,
# NOT through the erk() wrapper function
# Result: shell gets stranded in deleted worktree
```

## How the erk() Wrapper Function Works

The shell integration relies on a wrapper function that intercepts erk commands:

```bash
# Installed by `erk init --shell` in ~/.erk/shell/init.zsh
erk() {
    local cmd_output
    cmd_output=$("$ERK_BIN" "$@" --script 2>&1)

    # If output is a script path, source it
    if [[ -f "$cmd_output" ]]; then
        source "$cmd_output"
    else
        # Otherwise just run the command normally
        "$ERK_BIN" "$@"
    fi
}
```

**Key insight**: When you create an alias like `alias land='erk pr land'`, the shell expands `land` to `erk pr land` **before** looking for functions. Since `erk pr land` is not invoking the `erk` function (it's a literal command), the wrapper is bypassed.

## Safe vs Unsafe Alias Patterns

### ❌ UNSAFE: Direct command aliases

These bypass shell integration and break worktree-deleting commands:

```bash
# DON'T use these patterns
alias land='erk pr land'
alias down='erk down'
alias up='erk up'
alias rm='erk rm'
```

### ✅ SAFE: Read-only command aliases

Aliases are safe for commands that don't require shell integration:

```bash
# These are fine - no directory changes needed
alias es='erk status'
alias el='erk list'
alias et='erk tree'
alias ed='erk dash'
```

### ✅ SAFE: Function wrappers

If you want short commands for shell-integrated operations, use functions:

```bash
# Wrap through the erk function instead of direct alias
land() {
    erk pr land "$@"
}

# Or use the source pattern directly
land() {
    source <(command erk pr land --script "$@")
}
```

### ✅ SAFE: Aliases that go through the function

If you must use aliases, make them invoke the erk function:

```bash
# This works because 'erk' resolves to the function
alias land='erk pr land'  # ❌ WRONG - 'erk' is literal here

# But this approach doesn't work for the reason above
# The expansion happens before function lookup
```

## Commands Requiring Shell Integration

These commands MUST go through the `erk()` wrapper function:

| Command                     | Reason                               |
| --------------------------- | ------------------------------------ |
| `erk pr land`               | Deletes current worktree             |
| `erk down --delete-current` | Deletes current worktree, moves down |
| `erk up --delete-current`   | Deletes current worktree, moves up   |
| `erk rm`                    | May delete current worktree          |
| `erk checkout`              | Changes directory to worktree        |
| `erk implement`             | Creates and switches to worktree     |

## Debugging Shell Integration Issues

### Symptom: Shell stranded in deleted directory

```bash
$ land  # Alias to 'erk pr land'
# PR landed successfully, but...
$ pwd
/Users/you/erks/erk/my-feature  # Directory is deleted!
$ ls
ls: .: No such file or directory
```

### Diagnosis

1. Check if you're using an alias:

   ```bash
   type land
   # If output is: land is aliased to `erk pr land`
   # That's the problem!
   ```

2. Check if the erk function is defined:

   ```bash
   type erk
   # Should show: erk is a function
   # If it shows: erk is /path/to/erk
   # Shell integration isn't set up
   ```

### Fix

1. Remove the alias:

   ```bash
   unalias land
   ```

2. If you want a short command, use a function:

   ```bash
   land() { erk pr land "$@"; }
   ```

3. Ensure shell integration is active:

   ```bash
   erk init --shell
   # Then restart your shell or source the init script
   source ~/.erk/shell/init.zsh  # or init.bash
   ```

## Setup Verification

Verify shell integration is working:

```bash
# 1. Check erk is a function
type erk
# Expected: erk is a function

# 2. Check function is sourced
echo $ERK_SHELL_INTEGRATION
# Expected: 1 (or similar indicator)

# 3. Test with a safe command
erk checkout some-worktree
# Should change directory AND update pwd
```

## Best Practice: ~/.zshrc or ~/.bashrc Setup

```bash
# Source erk shell integration
if [[ -f ~/.erk/shell/init.zsh ]]; then
    source ~/.erk/shell/init.zsh
fi

# AFTER sourcing erk, define safe aliases only
alias es='erk status'
alias el='erk list'
alias et='erk tree'

# For commands needing shell integration, use functions
land() { erk pr land "$@"; }
down() { erk down "$@"; }
up() { erk up "$@"; }
```

## Related Documentation

- [Shell Integration Constraint](../architecture/shell-integration-constraint.md) - Why subprocesses can't change parent cwd
- [Script Mode](script-mode.md) - Implementing the `--script` flag
- [Glossary: Shell Integration](../glossary.md#shell-integration) - Definition and components
