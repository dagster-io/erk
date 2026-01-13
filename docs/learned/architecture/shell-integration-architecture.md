---
title: Shell Integration Architecture
read_when:
  - "working on shell integration"
  - "modifying erk-sh-bootstrap package"
  - "adding commands that need directory switching"
  - "understanding uvx delegation pattern"
  - "debugging shell wrapper behavior"
---

# Shell Integration Architecture

How erk provides seamless CLI experience with per-project isolation.

## Problem Statement

Erk needs to:

1. Allow different projects to use different erk versions
2. Not require global installation
3. Support commands that change the shell's working directory (worktree switching)
4. Work across bash, zsh, and fish shells

## Architecture Overview

Erk uses a **three-layer delegation architecture**:

```
┌─────────────────────────────────────────────────────────────┐
│  User types: erk wt checkout my-feature                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Shell Wrapper (bash/zsh/fish function)            │
│  Location: src/erk/cli/shell_integration/*_wrapper.*        │
│  Purpose: Intercept erk commands, source scripts for cd     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: erk-sh-bootstrap (PyPI package via uvx)           │
│  Location: packages/erk-sh-bootstrap/                       │
│  Purpose: Find project-local .venv/bin/erk, delegate        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Project-Local Erk (.venv/bin/erk)                 │
│  Location: Each project's virtualenv                        │
│  Purpose: Actual CLI implementation                         │
└─────────────────────────────────────────────────────────────┘
```

## Layer 1: Shell Wrappers

Shell wrappers are installed via `erk init --shell`. They define an `erk()` function that intercepts commands.

**Key behaviors:**

1. **Shell completion**: When `_ERK_COMPLETE` is set, delegate directly to bootstrap
2. **Command interception**: Call `uvx erk-sh-bootstrap __shell "$@"` to get a script path
3. **Script sourcing**: Source the returned script (enables `cd` in caller's shell)
4. **Passthrough mode**: If script path is `__ERK_PASSTHROUGH__`, run command directly

**Why script sourcing?**

Subprocesses cannot change the parent shell's working directory. Commands like `erk wt checkout` need to `cd` into a new worktree. The shell wrapper sources a script file that contains the `cd` command, executing it in the caller's shell context.

**Example flow for `erk wt checkout my-feature`:**

```bash
# Shell wrapper calls:
script_path=$(ERK_SHELL=bash uvx erk-sh-bootstrap __shell wt checkout my-feature)
# Returns: /tmp/erk-shell-abc123.sh

# Script contains:
cd /path/to/worktree/my-feature

# Shell wrapper sources it:
source /tmp/erk-shell-abc123.sh
# Now the user's shell is in the worktree directory
```

## Layer 2: erk-sh-bootstrap

A **zero-dependency** Python package published to PyPI. Design goals:

- **Minimal**: Only finds local erk and delegates
- **Zero dependencies**: Installs instantly via uvx
- **Stable**: Rarely needs updates (version 1.0.0)

**Algorithm (`find_local_erk`):**

1. Check `ERK_VENV` environment variable for explicit override
2. Walk up from `cwd` looking for `.venv/bin/erk` or `venv/bin/erk`
3. Return path if found, None otherwise

**Delegation:**

- Uses `os.execv()` to replace the bootstrap process with project-local erk
- Same PID, same stdin/stdout/stderr
- No overhead after delegation

**Error handling:**

If no local erk found, prints helpful error:

```
erk: No .venv/bin/erk found in current directory or parents
hint: Run 'uv add erk && uv sync' in your project
hint: Set ERK_VENV=/path/to/venv for non-standard locations
```

## Layer 3: Shell Integration Handler

The project-local erk's `__shell` subcommand (handler.py) determines what shell integration is needed.

**Key concepts:**

| Term                         | Meaning                                         |
| ---------------------------- | ----------------------------------------------- |
| `SHELL_INTEGRATION_COMMANDS` | Commands that need directory switching          |
| `PASSTHROUGH_MARKER`         | Signal to run command without shell integration |
| Script file                  | Temporary file with shell commands to source    |

**Decision flow:**

1. Parse command to determine if it needs shell integration
2. If not (e.g., `erk version`), return `__ERK_PASSTHROUGH__`
3. If yes, run command and generate script with post-command shell actions
4. Return script path

## Commands Requiring Shell Integration

Defined in `handler.py:SHELL_INTEGRATION_COMMANDS`:

| Command             | Why                                   |
| ------------------- | ------------------------------------- |
| `checkout`, `co`    | Switches to worktree directory        |
| `wt create`         | Creates worktree and switches to it   |
| `wt checkout`       | Switches to existing worktree         |
| `implement`, `impl` | May switch to implementation worktree |
| `up`, `down`        | Navigation within stack               |
| `land`              | May switch worktrees after landing    |
| `stack consolidate` | May switch during consolidation       |

## Publishing erk-sh-bootstrap

**Important**: `erk-sh-bootstrap` has independent versioning (currently 1.0.0) and is published separately from main erk.

**Why separate?**

- Stability: Bootstrap rarely changes
- Independence: Users shouldn't need to update bootstrap when erk updates
- Simplicity: No version coordination needed

**Manual publish process:**

```bash
uv build --package erk-sh-bootstrap -o dist/
uvx uv-publish dist/erk_sh_bootstrap-1.0.0*
rm -rf dist/
```

**When to publish:**

Only when the bootstrap delegation logic changes (rare). String renames or documentation updates don't require republishing if version is unchanged.

## Adding New Shell-Integrated Commands

1. Add command to `SHELL_INTEGRATION_COMMANDS` in `handler.py`
2. Include all alias variants (e.g., `br land`, `branch land`)
3. Test with `ERK_KEEP_SCRIPTS=1` to inspect generated scripts

## Debugging

**Environment variables:**

| Variable           | Purpose                                  |
| ------------------ | ---------------------------------------- |
| `ERK_VENV`         | Override venv location                   |
| `ERK_SHELL`        | Shell type (bash/zsh/fish)               |
| `ERK_KEEP_SCRIPTS` | Don't delete script files after sourcing |
| `_ERK_COMPLETE`    | Signals shell completion mode            |

**Common issues:**

- "No .venv/bin/erk found" - Not in a project with erk installed
- Script not sourced - Shell integration not set up (`erk init --shell`)
- Wrong erk version - Check `ERK_VENV` override

## Related Documentation

- [Shell Integration Constraint](shell-integration-constraint.md) - The Unix process model limitation
- [Script Mode](../cli/script-mode.md) - Implementing `--script` flag pattern
- [Glossary: Shell Integration](../glossary.md#shell-integration) - Definition and setup
