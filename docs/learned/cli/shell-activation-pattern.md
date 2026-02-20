---
title: Shell Activation Pattern for Worktree Navigation
read_when:
  - "generating commands that switch to a different worktree"
  - "debugging why erk br co doesn't change directory"
  - "building CLI commands that need shell-level directory changes"
  - "understanding why plan checkout commands use source"
tripwires:
  - action: "generating directory-change commands using erk br co without source"
    warning: 'Subprocess directory changes do NOT persist to the parent shell. erk br co runs in a subprocess — its chdir() is invisible to the caller. Use the shell activation pattern: source "$(erk br co <branch> --script)" to actually navigate.'
    score: 9
---

# Shell Activation Pattern for Worktree Navigation

## The Problem

`erk br co <branch>` switches to a worktree by finding which worktree has the branch checked out. However, when run as a subprocess, any directory change it makes is invisible to the calling shell.

**This does NOT navigate the shell:**

```bash
erk br co feature-branch && some-command   # Wrong: chdir() happened in subprocess
```

**This DOES navigate the shell:**

```bash
source "$(erk br co feature-branch --script)"
```

## How It Works

`erk br co --script` prints the path to a shell activation script (`.erk/bin/activate.sh`) instead of executing it. The activation script:

1. Sources the worktree's virtual environment
2. Changes the shell's working directory to the worktree root
3. Loads `.env` files if present

By wrapping in `source "$(...)"`, the shell evaluates the script in the current process, making the directory change persistent.

## Implementation

**Location:** `src/erk/cli/activation.py`

Key functions:

- `activation_config_for_implement()` — Creates config with `implement: True` to append `erk implement` to the source command
- `activation_config_activate_only()` — Creates config for navigation without implementing
- `build_activation_command(config, script_path)` — Builds the final command string

The resulting command format:

```bash
source /path/to/worktree/.erk/bin/activate.sh && erk implement
```

## Usage in TUI and Plan Checkout

The TUI's "copy prepare" commands use `activation_config_for_implement()` to build clipboard commands that navigate to a worktree and start implementation. The `--script` flag on `erk br co` enables this pattern.

## Related Documentation

- [Worktree Management](../erk/) — Worktree lifecycle and pool management
