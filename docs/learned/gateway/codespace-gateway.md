---
title: Codespace Gateway Pattern
read_when:
  - "implementing codespace SSH operations"
  - "working with the Codespace gateway ABC"
  - "testing code that executes commands on codespaces"
  - "adding new codespace operations"
tripwires:
  - action: "implementing codespace gateway"
    warning: "Use 3-place pattern (abc, real, fake) without dry-run or print implementations."
last_audited: "2026-02-05 13:26 PT"
audit_result: edited
---

# Codespace Gateway Pattern

The codespace gateway provides an abstraction for SSH operations on GitHub Codespaces, following a **3-place pattern** (ABC, real, fake).

## The 3-Place Pattern

Unlike most gateways (which have 5 places: abc, real, fake, dry-run, print), the codespace gateway has only 3:

1. **ABC**: `packages/erk-shared/src/erk_shared/gateway/codespace/abc.py`
2. **Real**: `packages/erk-shared/src/erk_shared/gateway/codespace/real.py`
3. **Fake**: `packages/erk-shared/src/erk_shared/gateway/codespace/fake.py`

**No dry-run or print implementations** - codespace operations are inherently remote and can't be meaningfully dry-run locally.

## Gateway Interface

The `Codespace` ABC in `abc.py` defines three operations:

- **`start_codespace()`** — Ensures a codespace is running before SSH operations. Real implementation uses `gh api --method POST` (NOT `gh codespace start`, which doesn't exist — see [GitHub CLI Limits](../architecture/github-cli-limits.md)).
- **`run_ssh_command()`** — Execute a command via SSH and wait for completion. Returns exit code. See [Codespace Remote Execution](../erk/codespace-remote-execution.md).
- **`exec_ssh_interactive()`** — Replace current process with an SSH session via `os.execvp`. Never returns (`NoReturn`).

## Testing Pattern

The `FakeCodespace` in `fake.py` tracks all calls via `SSHCall` dataclass objects. See `tests/unit/gateways/codespace/test_fake_codespace.py` for usage examples. Key assertion properties: `ssh_calls`, `started_codespaces`, `exec_called`, `last_call`.

## Why No Dry-Run?

Dry-run is designed for local filesystem operations that can be simulated. Codespace operations are:

- **Remote**: No local equivalent to "pretend to SSH"
- **Stateful**: Can't show what would happen without side effects
- **Interactive**: exec_ssh_interactive() replaces the process entirely

The fake implementation serves the testing role that dry-run would fill.

## Related Documentation

- [Codespace Remote Execution](../erk/codespace-remote-execution.md) - Streaming command execution pattern
- [Gateway ABC Implementation](../architecture/gateway-abc-implementation.md) - General gateway patterns
- [GitHub CLI Limits](../architecture/github-cli-limits.md) - Why gh codespace start doesn't work
- [Composable Remote Commands](../architecture/composable-remote-commands.md) - Template for new commands
