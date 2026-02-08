---
audit_result: edited
last_audited: "2026-02-08"
read_when:
  - adding a new codespace SSH operation to the gateway
  - deciding whether a new gateway needs dry-run and printing implementations
  - testing code that uses os.execvp or NoReturn methods
  - choosing between exec_ssh_interactive and run_ssh_command
title: Codespace Gateway Pattern
tripwires:
  - action: implementing codespace gateway
    warning: Use 3-place pattern (abc, real, fake) without dry-run or print implementations.
  - action: adding dry-run or printing implementation for codespace gateway
    warning:
      Codespace operations are all-or-nothing remote execution. Dry-run and printing
      don't apply.
  - action: adding -t flag to run_ssh_command or omitting it from exec_ssh_interactive
    warning:
      The -t flag controls TTY allocation. Interactive needs it (rendering);
      non-interactive breaks with it (buffering). See the two execution modes section.
---

# Codespace Gateway Pattern

The codespace gateway uses a **3-place pattern** (ABC, real, fake) instead of the standard 5-place gateway pattern. This document explains when to omit dry-run and printing implementations — a decision that generalizes to any gateway wrapping process-replacing or inherently remote operations.

## When to Use 3-Place vs 5-Place

The standard gateway has 5 implementations (abc, real, fake, dry_run, printing). The 3-place variant drops dry-run and printing. The deciding question: **can you give the user a meaningful preview of the operation?**

| Characteristic             | 5-place (standard)                     | 3-place (codespace, agent_launcher)            |
| -------------------------- | -------------------------------------- | ---------------------------------------------- |
| Operations are previewable | Yes — can show "would create branch X" | No — process replacement or remote execution   |
| Dry-run adds value         | Yes — read-only operations still work  | No — no local equivalent to "pretend to SSH"   |
| Methods return values      | Yes — callers branch on results        | Mixed — `NoReturn` methods replace the process |
| Side effects are local     | Yes — filesystem, git                  | No — remote machine state, process table       |

**Why fakes suffice without dry-run**: Dry-run exists to let users preview mutations before committing. When the operation is all-or-nothing remote execution (`os.execvp`, SSH), there's nothing meaningful to preview. The fake serves the testing role that dry-run would otherwise fill for local operations.

Both codespace and agent_launcher gateways use this 3-place pattern, making them the reference implementations for any future gateway wrapping `os.execvp()` or remote-only operations.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/codespace/abc.py, Codespace -->

See the `Codespace` ABC in `packages/erk-shared/src/erk_shared/gateway/codespace/abc.py` for the contract.

## Two Execution Modes: Why the Wrong Choice Causes Subtle Bugs

The gateway exposes two SSH paths that differ in a single flag (`-t` for TTY allocation), but choosing wrong produces hard-to-diagnose failures:

| Method                   | Mechanism          | Returns?           | Use when                                          |
| ------------------------ | ------------------ | ------------------ | ------------------------------------------------- |
| `exec_ssh_interactive()` | `os.execvp()`      | Never (`NoReturn`) | TUI, interactive sessions, anything needing a TTY |
| `run_ssh_command()`      | `subprocess.run()` | Exit code (`int`)  | Automated commands where you need the result      |

**The `-t` flag trap**: `exec_ssh_interactive()` passes `-t` to allocate a pseudo-terminal (required for interactive TUI rendering). `run_ssh_command()` deliberately omits it. Adding `-t` to non-interactive commands causes output buffering issues; omitting it from interactive commands causes terminal rendering failures. Neither failure produces an obvious error message — both manifest as garbled output or hangs.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/codespace/real.py, RealCodespace -->

See `RealCodespace` in `packages/erk-shared/src/erk_shared/gateway/codespace/real.py` for the flag distinction between the two methods.

## GitHub API Workaround for Codespace Start

`start_codespace()` uses the REST API (`gh api --method POST /user/codespaces/{name}/start`) instead of `gh codespace start` because the CLI subcommand doesn't exist. This is a known GitHub CLI gap — see [GitHub CLI Limits](../architecture/github-cli-limits.md) for the full list of operations requiring REST API fallbacks.

## Testing NoReturn Methods: The SystemExit Pattern

Testing `os.execvp()` wrappers poses a fundamental problem: the real method replaces the process, so no assertion code can run after it. The erk-wide solution is `raise SystemExit(0)` in the fake, which means tests must use `pytest.raises(SystemExit)`.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/codespace/fake.py, FakeCodespace -->

See `FakeCodespace` in `packages/erk-shared/src/erk_shared/gateway/codespace/fake.py` for the tracking and `SystemExit` simulation.

This pattern is shared by `FakeAgentLauncher` — both gateways wrap `os.execvp()` and use the same `SystemExit(0)` simulation. When adding any future `NoReturn` gateway method, follow this established pattern.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/agent_launcher/fake.py, FakeAgentLauncher -->

See `FakeAgentLauncher` in `packages/erk-shared/src/erk_shared/gateway/agent_launcher/fake.py` for the parallel implementation.

**Anti-pattern**: Catching `SystemExit` broadly in test code that calls `exec_ssh_interactive()`. The `SystemExit` is intentional — swallowing it silently masks whether the method was actually invoked. Always use `pytest.raises(SystemExit)` to both catch and assert the call happened.

## Related Documentation

- [Codespace Remote Execution](../erk/codespace-remote-execution.md) — bootstrap wrapper, environment setup, debugging failures
- [Gateway ABC Implementation](../architecture/gateway-abc-implementation.md) — 5-place pattern, 3-place variant decision criteria
- [SSH Command Execution](../architecture/ssh-command-execution.md) — exec vs subprocess, TTY allocation, SSH argument semantics
- [GitHub CLI Limits](../architecture/github-cli-limits.md) — why `gh codespace start` doesn't work
- [Composable Remote Commands](../architecture/composable-remote-commands.md) — five-step pattern for adding new remote commands
