---
audit_result: edited
last_audited: "2026-02-08"
read_when:
  - modifying the codespace environment bootstrap sequence
  - debugging why a remote erk command fails before reaching the actual command
  - deciding whether a new remote command needs build_codespace_ssh_command
title: Codespace Remote Execution Pattern
tripwires:
  - action: duplicating git pull / uv sync / venv activation in a codespace command
    warning:
      Use build_codespace_ssh_command() — bootstrap logic is centralized there.
      See composable-remote-commands.md for the five-step pattern.
  - action: adding a new step to the bootstrap sequence
    warning:
      This affects ALL remote commands. The bootstrap runs on every SSH invocation,
      so added steps must be idempotent and fast.
  - action: embedding single quotes in a remote erk command argument
    warning:
      The bootstrap wraps the entire command in single quotes. Single quotes
      in arguments will break the shell string.
---

# Codespace Remote Execution Pattern

This document covers the **centralized environment bootstrap** for remote codespace commands — why it exists, how it fails, and when to bypass it. For the five-step composition pattern (resolve → start → build → execute → report), see [Composable Remote Commands](../architecture/composable-remote-commands.md). For choosing between `exec_ssh_interactive()` and `run_ssh_command()`, see [SSH Command Execution](../architecture/ssh-command-execution.md).

## Why a Centralized Bootstrap Wrapper

Remote erk commands can't assume the codespace environment is ready. Between SSH connections, the codespace may have stale code, missing dependencies, or a deactivated virtualenv. Rather than making each remote command handle its own setup, erk centralizes the bootstrap in a single function.

<!-- Source: src/erk/core/codespace_run.py, build_codespace_ssh_command -->

See `build_codespace_ssh_command()` in `src/erk/core/codespace_run.py` for the implementation.

**The core design decision**: Bootstrap is a cross-cutting concern. If each command inlined its own setup steps, adding a new bootstrap step (e.g., a health check) would require touching every remote command file. Centralization means bootstrap changes propagate automatically.

## Bootstrap Sequence Design

The wrapper chains four operations with `&&` inside `bash -l -c '...'`:

1. **`git pull`** — ensures the remote has latest code, since the codespace may have been idle for hours or days
2. **`uv sync`** — installs any new/changed dependencies from the (potentially updated) `pyproject.toml`
3. **`source .venv/bin/activate`** — activates the virtualenv so `erk` resolves to the project's entry point
4. **The actual erk command** — runs only if all three setup steps succeed

### Why These Design Choices

**Fail-fast chaining (`&&`)**: If `git pull` fails (merge conflict, network issue), the erk command never runs against stale code. This prevents subtly wrong results that are harder to debug than a visible bootstrap failure.

**Login shell (`bash -l`)**: Ensures `~/.profile` and `~/.bash_profile` are sourced, which is required for user-local binaries like Claude Code (installed to `~/.claude/local/`). Without `-l`, the `claude` command isn't found.

**Sequential ordering**: The steps have strict dependencies — `uv sync` must run after `git pull` (new code may add dependencies), and venv activation must happen after sync.

**Anti-pattern**: Skipping `git pull` for "speed." A codespace running against stale code produces subtly wrong results that are much harder to debug than a slow startup.

## Debugging Bootstrap Failures

The `&&`-chain means the actual error appears in terminal output, but knowing _which_ step failed requires interpreting the output:

| Symptom                     | Likely failed step            | Recovery                                              |
| --------------------------- | ----------------------------- | ----------------------------------------------------- |
| Merge conflict messages     | `git pull`                    | `erk codespace connect --shell`, resolve manually     |
| Package resolution errors   | `uv sync`                     | Run `uv sync` interactively to see full error details |
| "command not found: erk"    | `source .venv/bin/activate`   | Venv may be corrupted — recreate with `uv venv`       |
| "command not found: claude" | `bash -l` not loading profile | Check `~/.bash_profile` on the codespace              |

**Key strategy**: Use `erk codespace connect --shell` to drop into a bare shell, then run bootstrap steps manually one at a time to isolate the failure.

## When to Use vs When to Bypass

<!-- Source: src/erk/cli/commands/codespace/connect_cmd.py, connect_codespace -->

Not all codespace commands use `build_codespace_ssh_command()`. The `connect` command (see `connect_codespace()` in `src/erk/cli/commands/codespace/connect_cmd.py`) builds its own command string because its `--shell` mode skips setup entirely (just `bash -l`). This shell escape hatch exists precisely for debugging when the bootstrap itself is broken.

**Decision rule**: Use `build_codespace_ssh_command()` for any command running a specific erk CLI remotely. Build the string manually only when the command needs a fundamentally different setup flow (like shell-only mode).

## Design Constraints

**Idempotency requirement**: Every bootstrap step must be safe to run repeatedly. Codespaces may be warm (ran a command 5 minutes ago) or cold (idle for 12 hours). The same bootstrap runs either way.

**No partial bootstrap**: You can't skip `git pull` even if you just pushed. The wrapper always runs the full sequence — simplicity over optimization.

**Single-quote escaping limitation**: The erk command is embedded inside single quotes. Commands with single quotes in their arguments will break the shell wrapping. This hasn't been a practical issue because erk CLI arguments don't contain quotes, but it's a structural constraint to be aware of.

**Single-argument SSH constraint**: The entire `bash -l -c '...'` string must be passed as one argument to SSH. See [SSH Command Execution](../architecture/ssh-command-execution.md) for why SSH's argument concatenation breaks multi-argument commands.

## Related Documentation

- [SSH Command Execution](../architecture/ssh-command-execution.md) — exec vs subprocess decision, TTY allocation, SSH argument semantics
- [Composable Remote Commands](../architecture/composable-remote-commands.md) — five-step pattern for adding new remote commands
- [Codespace Gateway](../gateway/codespace-gateway.md) — gateway ABC (3-place pattern, no dry-run)
- [Codespace Patterns](../cli/codespace-patterns.md) — CLI-level resolution, naming, and API workarounds
