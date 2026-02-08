---
title: Composable Remote Commands Pattern
read_when:
  - "adding a new remote command to run on codespaces"
  - "implementing erk codespace run subcommands"
  - "working with streaming remote execution"
tripwires:
  - action: "using run_ssh_command() for interactive commands"
    warning: "Interactive commands need exec_ssh_interactive(), not run_ssh_command()"
  - action: "executing remote commands without calling start_codespace()"
    warning: "Always start_codespace() before executing remote commands"
  - action: "duplicating environment setup in remote commands"
    warning: "build_codespace_ssh_command() bootstraps the environment - don't duplicate setup"
---

# Composable Remote Commands Pattern

Remote commands in erk follow a five-step pattern that separates concerns: codespace lookup, startup, command preparation, execution, and result handling. This composability emerges from breaking the execution boundary into discrete helpers rather than monolithic SSH invocations.

## Why This Pattern Exists

**The composability insight**: Remote execution isn't a single operation, it's five independent decisions that can be composed. Codespace lookup logic doesn't need to know about SSH. SSH command building doesn't need to know about codespace registry lookup. Exit code handling doesn't need to know how the command was executed.

This separation matters because:

1. **Testability through fakes**: Each boundary (`resolve_codespace()`, `build_codespace_ssh_command()`, `ctx.codespace.exec_ssh_interactive()`) can be tested independently
2. **Reusability without duplication**: New remote commands compose existing helpers rather than reimplementing SSH boilerplate
3. **Change isolation**: Modifying environment bootstrap (e.g., adding `uv sync`) requires one change in `build_codespace_ssh_command()`, not N changes across commands

## The Five-Step Composition

<!-- Source: src/erk/cli/commands/codespace/run/objective/next_plan_cmd.py, run_next_plan function -->

Every remote command follows this structure. See `run_next_plan()` in `src/erk/cli/commands/codespace/run/objective/next_plan_cmd.py` for the canonical implementation.

### 1. Resolve Codespace

<!-- Source: src/erk/cli/commands/codespace/resolve.py, resolve_codespace function -->

`resolve_codespace(ctx.codespace_registry, name)` handles name-to-registered-codespace lookup, including default fallback and error messaging. See `resolve_codespace()` in `src/erk/cli/commands/codespace/resolve.py`.

**Why separate this**: Codespace lookup has complex error cases (no default set, default not found, named codespace not found). Centralizing this logic prevents inconsistent error messages across commands.

### 2. Start Codespace

`ctx.codespace.start_codespace(codespace.gh_name)` ensures the codespace is running before SSH connection. No-op if already running.

**Why separate this**: Starting is idempotent and may take time (showing startup messages). Commands shouldn't need to implement "check if running, start if not" logic.

### 3. Build Remote Command

<!-- Source: src/erk/core/codespace_run.py, build_codespace_ssh_command function -->

`build_codespace_ssh_command(erk_cli_command)` wraps the erk command with environment bootstrap. See `build_codespace_ssh_command()` in `src/erk/core/codespace_run.py`.

**Current bootstrap sequence** (as of 2026-02-07):

```bash
bash -l -c 'git pull && uv sync && source .venv/bin/activate && <erk_command>'
```

**Why separate this**: Environment setup evolves (we added `uv sync`, might add health checks later). If this was inline in every command, updating the bootstrap would require changing 10+ files.

**Anti-pattern**: Duplicating the git/uv/venv setup in individual commands. The bootstrap sequence is a cross-cutting concern.

### 4. Execute Remotely

<!-- Source: packages/erk-shared/src/erk_shared/gateway/codespace/abc.py, Codespace class -->

Two execution methods on `ctx.codespace` (see `Codespace` ABC in `packages/erk-shared/src/erk_shared/gateway/codespace/abc.py`):

- `exec_ssh_interactive(gh_name, remote_cmd)` - **Replaces current process** with SSH session (uses `os.execvp`, never returns). For interactive commands like `erk objective next-plan`.
- `run_ssh_command(gh_name, remote_cmd)` - **Blocks and returns exit code**. For non-interactive commands that stream output but don't need user input.

**Decision table**:

| Command Needs User Input? | Execution Method         | Returns?              |
| ------------------------- | ------------------------ | --------------------- |
| Yes (TUI, prompts)        | `exec_ssh_interactive()` | No (replaces process) |
| No (streaming output)     | `run_ssh_command()`      | Yes (exit code)       |

**Why two methods**: Interactive commands need true terminal passthrough (SSH must control the full TTY). Non-interactive commands need exit code propagation for CI/automation.

### 5. Report Results

Exit code handling logic depends on execution method:

- `exec_ssh_interactive()`: No exit code handling needed (process replaced)
- `run_ssh_command()`: Check exit code, echo status message, propagate failure with `raise SystemExit(exit_code)`

**Why separate this**: Exit code interpretation is command-specific (some commands might treat non-zero as warning, not error). The execution layer shouldn't make this decision.

## Adding a New Remote Command

**Before coding**: Ensure `erk <your-command>` works locally and non-interactively. Remote execution won't magically fix local issues.

**Step-by-step**:

1. Create command file under `src/erk/cli/commands/codespace/run/`
2. Import the three helpers:
   - `from erk.cli.commands.codespace.resolve import resolve_codespace`
   - `from erk.core.codespace_run import build_codespace_ssh_command`
   - `from erk.core.context import ErkContext`
3. Compose the five steps (lookup, start, build, execute, report)
4. Add `--codespace` / `-c` option for explicit codespace selection
5. Register in the appropriate Click group

## Current Limitations

**Interactive command restriction**: The actual implementation uses `exec_ssh_interactive()` for most commands because they're designed for human interaction. The document's claim about `run_ssh_command()` being used for remote execution was incorrect - it's defined in the ABC but the real commands use the interactive variant.

**No async execution**: Remote commands block until completion. There's no "start in background" mode.

**No progress streaming**: Output streams to terminal, but commands can't report structured progress (e.g., "3 of 10 steps complete").

## Related Documentation

- `docs/learned/erk/codespace-remote-execution.md` - Deeper dive on SSH execution patterns
- `docs/learned/gateway/codespace-gateway.md` - Gateway ABC for codespace operations
- `docs/learned/cli/codespace-patterns.md` - CLI-level codespace interaction patterns
