---
title: Codespace Gateway Pattern
read_when:
  - "adding a new codespace SSH operation to the gateway"
  - "deciding whether a new gateway needs dry-run/printing implementations"
  - "testing code that executes commands on codespaces"
tripwires:
  - action: "implementing codespace gateway"
    warning: "Use 3-place pattern (abc, real, fake) without dry-run or print implementations."
  - action: "adding dry-run or printing implementation for codespace gateway"
    warning: "Codespace operations are all-or-nothing remote execution. Dry-run and printing don't apply. See 'When to Use 3-Place vs 5-Place' section."
last_audited: "2026-02-08"
audit_result: regenerated
---

# Codespace Gateway Pattern

The codespace gateway uses a **3-place pattern** (ABC, real, fake) instead of the standard 5-place gateway pattern. This document explains when and why to omit dry-run and printing implementations — a decision that applies to any gateway wrapping process-replacing or inherently remote operations.

## When to Use 3-Place vs 5-Place

The standard gateway pattern has 5 implementations (abc, real, fake, dry_run, printing). The 3-place variant drops dry-run and printing. The decision is based on whether a meaningful preview exists:

| Characteristic                        | 5-place (standard)                     | 3-place (codespace, agent_launcher)            |
| ------------------------------------- | -------------------------------------- | ---------------------------------------------- |
| Operations are reversible/previewable | Yes — can show "would create branch X" | No — process replacement or remote execution   |
| Dry-run adds value                    | Yes — read-only operations still work  | No — no local equivalent to "pretend to SSH"   |
| Methods return values                 | Yes — callers branch on results        | Mixed — `NoReturn` methods replace the process |
| Side effects are local                | Yes — filesystem, git                  | No — remote machine state, process table       |

**The key insight**: Dry-run exists to let users preview mutations before committing. When the operation is all-or-nothing remote execution (`os.execvp`, SSH), there's nothing meaningful to preview. The fake serves the testing role that dry-run would otherwise fill for local operations.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/codespace/abc.py, Codespace -->

See the `Codespace` ABC in `packages/erk-shared/src/erk_shared/gateway/codespace/abc.py` for the three abstract methods.

## Two Execution Modes and Their Implications

The gateway exposes two fundamentally different SSH execution paths, and choosing wrong causes subtle bugs:

| Method                   | Mechanism                                | Returns?           | When to use                                       |
| ------------------------ | ---------------------------------------- | ------------------ | ------------------------------------------------- |
| `exec_ssh_interactive()` | `os.execvp()` — replaces current process | Never (`NoReturn`) | TUI, interactive sessions, anything needing a TTY |
| `run_ssh_command()`      | `subprocess.run()` — child process       | Exit code (`int`)  | Automated commands where you need the result      |

**Why this matters**: `exec_ssh_interactive()` uses the `-t` flag for TTY allocation (required for interactive TUI), while `run_ssh_command()` omits it. Adding `-t` to non-interactive commands causes buffering issues; omitting it from interactive commands causes rendering failures.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/codespace/real.py, RealCodespace -->

See `RealCodespace` in `packages/erk-shared/src/erk_shared/gateway/codespace/real.py` for the `-t` flag distinction.

## GitHub API Workaround for Codespace Start

`start_codespace()` uses the REST API (`gh api --method POST /user/codespaces/{name}/start`) instead of `gh codespace start` because the latter doesn't exist as a gh CLI subcommand. This is a known GitHub CLI limitation — see [GitHub CLI Limits](../architecture/github-cli-limits.md) for the full list of operations requiring REST API fallbacks.

## Testing: Simulating Process Replacement

The fake faces a unique challenge: how do you test a method that replaces the current process? The `FakeCodespace` solves this by raising `SystemExit(0)` from `exec_ssh_interactive()`, which means tests must wrap calls in `pytest.raises(SystemExit)`.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/codespace/fake.py, FakeCodespace -->

See `FakeCodespace` in `packages/erk-shared/src/erk_shared/gateway/codespace/fake.py` for the tracking implementation.

**Anti-pattern**: Catching `SystemExit` broadly in test code that also calls `exec_ssh_interactive()`. The `SystemExit` from the fake is intentional — swallowing it silently masks whether the method was actually called.

The AgentLauncher gateway uses the same `SystemExit` simulation pattern for its `os.execvp()` wrapper, confirming this as the standard approach for `NoReturn` fakes in erk.

## Related Documentation

- [Codespace Remote Execution](../erk/codespace-remote-execution.md) — bootstrap wrapper, environment setup, debugging failures
- [Gateway ABC Implementation](../architecture/gateway-abc-implementation.md) — 5-place pattern, 3-place variant decision criteria
- [SSH Command Execution](../architecture/ssh-command-execution.md) — exec vs subprocess, TTY allocation, SSH argument semantics
- [GitHub CLI Limits](../architecture/github-cli-limits.md) — why `gh codespace start` doesn't work
- [Composable Remote Commands](../architecture/composable-remote-commands.md) — five-step pattern for adding new remote commands
