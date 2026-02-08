---
title: SSH Command Execution Patterns
read_when:
  - implementing remote command execution via SSH
  - working with codespace connections
  - debugging remote setup commands
  - choosing between subprocess and exec for SSH
last_audited: "2026-02-07 21:36 PT"
audit_result: clean
tripwires:
  - action: "Using run_ssh_command() for interactive TUI processes causes apparent hangs"
    warning: "Use exec_ssh_interactive() for TUI programs"
  - action: "SSH command must be a single string argument, not multiple shell words"
    warning: "Multiple arguments break command execution"
  - action: "Missing -t flag prevents TTY allocation and breaks interactive programs"
    warning: "Interactive programs fail without TTY"
---

# SSH Command Execution Patterns

This document explains **why** erk uses two distinct SSH execution patterns and how to choose between them.

## The Core Decision: Subprocess vs Process Replacement

<!-- Source: packages/erk-shared/src/erk_shared/gateway/codespace/abc.py, Codespace.run_ssh_command and Codespace.exec_ssh_interactive -->

Erk provides two fundamentally different ways to execute SSH commands, each with different OS-level behavior:

1. **`run_ssh_command()`** — spawns subprocess, returns exit code, allows post-execution code
2. **`exec_ssh_interactive()`** — replaces current process with SSH, never returns

The distinction isn't just about interactivity. It's about **whether you need control back** after the command runs.

### Decision Table

| Question                                            | Answer | Use                      |
| --------------------------------------------------- | ------ | ------------------------ |
| Does the command need real-time streaming output?   | Yes    | `exec_ssh_interactive()` |
| Does the user need to interact with the program?    | Yes    | `exec_ssh_interactive()` |
| Do you need to run code after the command finishes? | Yes    | `run_ssh_command()`      |
| Do you need to check the exit code?                 | Yes    | `run_ssh_command()`      |
| Is this a setup/automation step?                    | Yes    | `run_ssh_command()`      |

If you need control back, use `run_ssh_command()`. If the command IS the final action, use `exec_ssh_interactive()`.

## Why exec_ssh_interactive() Uses os.execvp()

<!-- Source: packages/erk-shared/src/erk_shared/gateway/codespace/real.py, RealCodespace.exec_ssh_interactive -->

Process replacement via `os.execvp()` isn't just an implementation detail — it's the correct semantic for "connect to remote session":

1. **No orphan parent process** — the SSH connection becomes PID of the original command
2. **Proper signal handling** — Ctrl+C, terminal resize, etc. propagate correctly
3. **No resource overhead** — parent process isn't sitting idle waiting for child
4. **Matches mental model** — `erk codespace connect` replaces itself with the SSH session

When you run `erk codespace connect`, you **become** the remote session. The local erk process doesn't supervise it.

## The TTY Allocation Trap

<!-- Source: packages/erk-shared/src/erk_shared/gateway/codespace/real.py, comparing exec_ssh_interactive vs run_ssh_command -->

The `-t` flag isn't about "making things interactive." It's about **allocating a pseudo-terminal**.

**Without `-t`:**

- Remote program has no controlling TTY
- Programs that expect terminal features (cursor movement, color, raw input) block or fail
- Interactive TUI apps appear to hang waiting for input that can never arrive

**With `-t`:**

- SSH allocates a pseudo-terminal on the remote side
- Terminal features work as expected
- User input flows bidirectionally

This is why `exec_ssh_interactive()` always passes `-t`, but `run_ssh_command()` doesn't. Non-interactive commands (setup scripts, git pulls) work fine without a TTY. TUI programs (Claude Code) require it.

### Anti-Pattern: Using run_ssh_command for Claude

**WRONG:**

```python
# This appears to hang
ctx.codespace.run_ssh_command(codespace.gh_name, "claude --dangerously-skip-permissions")
```

**Why it fails:** Claude's TUI tries to enter raw mode, set up a display, and read keyboard input. Without a TTY, all of these operations block indefinitely.

**Correct:**

```python
# This replaces the process with the SSH session
ctx.codespace.exec_ssh_interactive(codespace.gh_name, "bash -l -c 'claude --dangerously-skip-permissions'")
```

## SSH Single-Argument Requirement

<!-- Source: src/erk/cli/commands/codespace/connect_cmd.py, comment explaining SSH concatenation behavior -->

SSH's command handling is subtle: **all arguments after the hostname are concatenated with spaces**.

This breaks shell quoting:

```bash
# WRONG - SSH sees three separate arguments
ssh host bash -l -c 'echo hello'
# SSH executes: bash -l -c echo hello (invalid - 'c' expects one argument)

# CORRECT - SSH sees one argument
ssh host "bash -l -c 'echo hello'"
# SSH executes: bash -l -c 'echo hello'
```

In Python code, this means the `remote_command` parameter must be pre-composed as a single string, not a list of shell words.

## Setup vs Shell Mode Pattern

<!-- Source: src/erk/cli/commands/codespace/connect_cmd.py, connect_codespace function -->

The `--shell` flag demonstrates the two use cases:

**Full setup mode (default):**

- Pulls latest code
- Syncs Python dependencies
- Activates virtualenv
- Launches Claude with permissions disabled (codespace isolation provides safety)

**Shell mode:**

- Just drops into bash
- Used for debugging when the full setup command is broken

The key architectural insight: both modes use `exec_ssh_interactive()` because both are "become the remote session" operations, not "run a command and continue."

## Why Login Shell (`bash -l`)

The `-l` flag ensures PATH includes `~/.claude/local/`, where Claude Code installs itself. Without it, the `claude` command wouldn't be found.

This is a general pattern for SSH commands that rely on user-specific binaries: either use login shell or specify the full path.

## Cross-References

- See `Codespace` ABC in `packages/erk-shared/src/erk_shared/gateway/codespace/abc.py` for the gateway contract
- See `RealCodespace` in `packages/erk-shared/src/erk_shared/gateway/codespace/real.py` for production implementation
- See `connect_codespace()` in `src/erk/cli/commands/codespace/connect_cmd.py` for usage example
- [Testing Interactive/NoReturn Gateway Methods](../testing/exec-script-testing.md#testing-interactive-noreturn-gateway-methods) — how to test exec-style gateways
- [CLI Output Styling Guide](../cli/output-styling.md) — using `err=True` for progress messages before exec
