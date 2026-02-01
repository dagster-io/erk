---
title: Codespace Gateway
read_when:
  - "extending the Codespace gateway with new methods"
  - "implementing codespace operations via ABC pattern"
  - "adding new codespace capabilities to RealCodespace or FakeCodespace"
  - "writing tests that verify codespace interactions"
tripwires:
  - action: "extending Codespace gateway with new methods"
    warning: "Follow 3-place pattern (ABC, Real, Fake). Add abstract method to ABC, implement in RealCodespace with subprocess, implement in FakeCodespace with test tracking. See Gateway ABC Implementation Checklist for 3-place vs 5-place decision."
---

# Codespace Gateway

The `Codespace` gateway provides an abstraction for GitHub Codespace operations, following erk's 3-place gateway pattern (ABC, Real, Fake).

## Gateway Overview

**Location:**
- **ABC:** `packages/erk-shared/src/erk_shared/gateway/codespace/abc.py`
- **Real:** `packages/erk-shared/src/erk_shared/gateway/codespace/real.py`
- **Fake:** `packages/erk-shared/src/erk_shared/gateway/codespace/fake.py`

**Pattern: 3-place, not 5-place**

The Codespace gateway uses a **3-place pattern** (ABC, Real, Fake) rather than the standard 5-place pattern (ABC, Real, Fake, Dry Run, Print).

**Reason:** Process replacement via `os.execvp` doesn't benefit from dry-run or print modes. Operations like SSH connection replacement cannot be simulated meaningfully—they either execute or don't.

For comparison, see [Gateway ABC Implementation Checklist](../architecture/gateway-abc-implementation.md) for 5-place pattern details.

## Core Methods

### `start_codespace()`

**Purpose:** Ensure codespace is running before SSH operations.

**Why needed:** Stopped codespaces cause SSH connection failures. Starting a stopped codespace takes time, so this method handles the startup explicitly before attempting SSH connections.

**Signature:**

```python
@abstractmethod
def start_codespace(self, gh_name: str) -> None:
    """Start the codespace if stopped. No-op if already running."""
```

**Behavior:**
- If codespace is already running: no-op (returns immediately)
- If codespace is stopped: starts it via `gh codespace start`
- If codespace doesn't exist: command fails with error

### `run_ssh_command()`

**Purpose:** Execute a shell command on the codespace via SSH.

**Signature:**

```python
@abstractmethod
def run_ssh_command(self, gh_name: str, command: str) -> int:
    """Execute command on codespace via SSH, return exit code."""
```

**Behavior:**
- Connects to codespace via `gh codespace ssh`
- Executes the provided shell command
- Returns the exit code from the command

**Note:** This does NOT start the codespace automatically. Call `start_codespace()` first.

## Implementation Pattern (Tripwire)

When adding new methods to the Codespace gateway, follow this 3-place pattern:

### 1. ABC: Define Abstract Method

Add abstract method to `Codespace` ABC with clear contract:

```python
@abstractmethod
def start_codespace(self, gh_name: str) -> None:
    """
    Start the codespace if stopped. No-op if already running.

    Args:
        gh_name: GitHub codespace name (e.g., 'octocat-friendly-space-xyzzy')

    Raises:
        subprocess.CalledProcessError: If gh command fails
    """
```

**Requirements:**
- Clear docstring explaining purpose and behavior
- Explicit parameter documentation
- Document exceptions that may be raised

### 2. Real: Implement with subprocess

Implement in `RealCodespace` using subprocess to call `gh` CLI:

```python
def start_codespace(self, gh_name: str) -> None:
    """Start the codespace if stopped. No-op if already running."""
    subprocess.run(
        ["gh", "codespace", "start", "-c", gh_name],
        check=True,
        capture_output=True,
        text=True,
    )
```

**Requirements:**
- Use `subprocess.run()` with appropriate arguments
- Set `check=True` to raise on failure
- Capture output if needed for error reporting

### 3. Fake: Implement with Test Tracking

Implement in `FakeCodespace` with tracking for test assertions:

```python
@dataclass(frozen=True)
class FakeCodespace(Codespace):
    _started_codespaces: list[str] = field(default_factory=list)

    def start_codespace(self, gh_name: str) -> None:
        """Track codespace starts for test assertions."""
        self._started_codespaces.append(gh_name)

    @property
    def started_codespaces(self) -> list[str]:
        """Return defensive copy of started codespace names."""
        return list(self._started_codespaces)
```

**Requirements:**
- Track calls in internal list for test assertions
- Provide property to access tracking data
- Use defensive copy to prevent external mutation
- Minimal logic: fakes don't validate, they track

## Integration Points

### Used by Remote Commands

The `start_codespace()` method is called before any SSH-based remote execution:

```python
# In erk codespace run objective next-plan
ctx.codespace.start_codespace(codespace.gh_name)
remote_cmd = build_codespace_run_command(f"erk objective next-plan {issue_ref}")
exit_code = ctx.codespace.run_ssh_command(codespace.gh_name, remote_cmd)
```

**Pattern:**
1. Start codespace (ensures running)
2. Build remote command (environment setup)
3. Execute via SSH (dispatch)

### Gateway Context Access

Commands access the gateway via Click context:

```python
@click.pass_context
def my_command(ctx: click.Context) -> None:
    cmd_ctx = get_command_context(ctx)
    cmd_ctx.codespace.start_codespace(name)
```

## Testing Pattern

### Unit Tests with FakeCodespace

Verify gateway calls in tests:

```python
def test_starts_codespace_before_ssh() -> None:
    fake_codespace = FakeCodespace()
    # ... run command ...
    assert "my-codespace" in fake_codespace.started_codespaces
```

**Test tracking properties:**
- `started_codespaces`: List of codespace names passed to `start_codespace()`
- `ssh_commands`: List of (codespace, command) tuples passed to `run_ssh_command()`

**Defensive copying:**

The fake returns a copy, not the internal list:

```python
@property
def started_codespaces(self) -> list[str]:
    return list(self._started_codespaces)  # Defensive copy
```

This prevents tests from accidentally mutating internal state.

### Integration Tests

Integration tests use `RealCodespace` and require:
- GitHub CLI installed and authenticated
- Access to a real codespace for testing

Most tests should use `FakeCodespace` for speed and isolation.

## 3-Place vs 5-Place Decision

**Why not 5-place?**

Standard gateway pattern has 5 implementations:
1. ABC (contract)
2. Real (actual operations)
3. Fake (test doubles)
4. Dry Run (preview mode)
5. Print (display mode)

**Codespace uses 3-place because:**

- **Process replacement:** `os.execvp()` replaces current process—no return
- **SSH sessions:** Interactive sessions cannot be "printed" meaningfully
- **No preview value:** Dry-run of "connect to codespace" isn't useful

**When to use 3-place:**
- Process replacement operations
- Interactive terminal sessions
- Operations that cannot be simulated or previewed

**When to use 5-place:**
- File operations (show what would be written)
- Git operations (show what would be committed)
- API calls (show what would be sent)

See [Gateway ABC Implementation Checklist](../architecture/gateway-abc-implementation.md) for full 5-place pattern details.

## Related Documentation

- [Gateway ABC Implementation](../architecture/gateway-abc-implementation.md) - 5-place pattern details
- [Codespace Remote Execution](../erk/codespace-remote-execution.md) - Usage of `start_codespace()`
- [Codespace Registry](codespace-registry.md) - Codespace lookup and configuration

## Source Attribution

**Established in:**
- Plan #6396: `[erk-plan] erk codespace run objective next-plan ISSUE_REF`
- PR #6408: Add `erk codespace run objective next-plan` for remote execution
- `start_codespace()` method added as part of remote execution pattern

**Implementation location:**
- ABC: `packages/erk-shared/src/erk_shared/gateway/codespace/abc.py`
- Real: `packages/erk-shared/src/erk_shared/gateway/codespace/real.py`
- Fake: `packages/erk-shared/src/erk_shared/gateway/codespace/fake.py`
