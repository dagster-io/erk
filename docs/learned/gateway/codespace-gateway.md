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
last_audited: "2026-02-05 12:48 PT"
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

The `Codespace` ABC defines three operations:

### 1. start_codespace()

Ensures a codespace is running before SSH operations. No-op if already running.

**Real implementation**: Uses `gh api --method POST user/codespaces/{name}/start` (NOT `gh codespace start`, which doesn't exist - see [GitHub CLI Limits](../architecture/github-cli-limits.md))

### 2. run_ssh_command()

Execute a command via SSH and wait for completion. Returns exit code.

**Common use**: Streaming remote commands - see [Codespace Remote Execution](../erk/codespace-remote-execution.md)

### 3. exec_ssh_interactive()

Replace current process with an SSH session (via `os.execvp`). This method never returns — the process is replaced.

**Use case**: Interactive shells or commands that need terminal control

## Implementation Locations

| Implementation | Path                                                           | Purpose                      |
| -------------- | -------------------------------------------------------------- | ---------------------------- |
| ABC            | `packages/erk-shared/src/erk_shared/gateway/codespace/abc.py`  | Interface definition         |
| Real           | `packages/erk-shared/src/erk_shared/gateway/codespace/real.py` | Production implementation    |
| Fake           | `packages/erk-shared/src/erk_shared/gateway/codespace/fake.py` | Test double with call traces |

## Testing Pattern

The fake implementation uses `SSHCall` dataclass objects to track calls for verification:

```python
from erk_shared.gateway.codespace.fake import FakeCodespace, SSHCall

# Test code
fake_codespace = FakeCodespace()
fake_codespace.run_ssh_command("mycodespace", "echo hello")

# Verify
assert fake_codespace.ssh_calls == [
    SSHCall(gh_name="mycodespace", remote_command="echo hello", interactive=False)
]
```

Additional properties for assertions:

- `fake_codespace.started_codespaces` - list of codespace names passed to `start_codespace()`
- `fake_codespace.exec_called` - bool indicating if `exec_ssh_interactive()` was called
- `fake_codespace.last_call` - the most recent `SSHCall`, or `None`

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
