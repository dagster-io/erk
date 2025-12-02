# Plan: Invert `erk planner connect` Default to SSH

## Goal

Invert the connection method defaults in `erk planner connect`:
- **Current:** VS Code Desktop is default, `--ssh` flag for SSH connection
- **Desired:** SSH connection is default, `--vscode` flag for VS Code Desktop

## Context

The `erk planner connect` command connects to registered GitHub Codespaces (planner boxes). It currently supports two connection methods:

1. **VS Code Desktop** (`gh codespace code`): Opens the codespace in VS Code, prevents idle timeout, requires manual setup
2. **SSH** (`gh codespace ssh`): Connects via SSH, automatically runs setup and launches Claude

Recent change (commit 2d461b581) made VS Code the default to prevent idle timeout issues. This plan reverses that decision to make SSH the default again.

## Implementation Steps

### 1. Modify Click Option Definition

**File:** `src/erk/cli/commands/planner/connect_cmd.py:12`

Replace the flag definition:
```python
# Current
@click.option("--ssh", is_flag=True, help="Connect via SSH instead of VS Code")

# Change to
@click.option("--vscode", is_flag=True, help="Connect via VS Code instead of SSH")
```

### 2. Update Function Signature and Docstring

**File:** `src/erk/cli/commands/planner/connect_cmd.py:14-22`

Update parameter name and docstring:
```python
# Current signature
def connect_planner(ctx: ErkContext, name: str | None, ssh: bool) -> None:

# Change to
def connect_planner(ctx: ErkContext, name: str | None, vscode: bool) -> None:
```

Update docstring:
```python
"""Connect to a planner box.

If NAME is provided, connects to that planner. Otherwise, connects
to the default planner.

By default, connects via SSH and launches Claude directly. Use --vscode
to open VS Code desktop instead (prevents idle timeout).
"""
```

### 3. Invert Connection Logic

**File:** `src/erk/cli/commands/planner/connect_cmd.py:50-94`

Swap the if/else branches:
```python
# Current structure
if ssh:
    # SSH connection code (lines 52-82)
else:
    # VS Code connection code (lines 84-94)

# Change to
if vscode:
    # VS Code connection code (move from else block)
else:
    # SSH connection code (move from if block, now default)
```

**Specific changes:**
- Line 50: Change `if ssh:` to `if vscode:`
- Lines 52-82: Move this SSH code to the else block
- Lines 84-94: Move this VS Code code to the if block

### 4. Update Test: Default Connection Method

**File:** `tests/commands/planner/test_planner_connect.py:156-180`

Rename and update test for new default:
```python
# Current
def test_connect_default_opens_vscode():
    # Tests that default opens VS Code

# Change to
def test_connect_default_uses_ssh():
    # Tests that default uses SSH
```

Update assertions:
- Change expected command from `["gh", "codespace", "code", ...]` to `["gh", "codespace", "ssh", ...]`
- Verify output mentions "Connecting via SSH..." instead of "Opening VS Code..."
- Check for SSH-related output (bash command, setup steps)

### 5. Update Test: Flag Behavior

**File:** `tests/commands/planner/test_planner_connect.py:182-214`

Rename and update test for new flag:
```python
# Current
def test_connect_with_ssh_flag_uses_ssh():
    # Tests that --ssh uses SSH

# Change to
def test_connect_with_vscode_flag_uses_vscode():
    # Tests that --vscode uses VS Code
```

Update test invocation:
- Change command from `["planner", "connect", "--ssh"]` to `["planner", "connect", "--vscode"]`
- Change expected command from SSH to VS Code
- Verify VS Code-specific output

### 6. Update Test: Unconfigured Planner Warning

**File:** `tests/commands/planner/test_planner_connect.py:94-116`

Update assertion on line 115:
```python
# Current
assert "code" in call_args[0][1]

# Change to
assert "ssh" in call_args[0][1]
assert "codespace" in call_args[0][1]
```

This test verifies the command still attempts connection even for unconfigured planners (default method is now SSH).

### 7. Update Documentation

**File:** `docs/user/planner-setup.md:30-36`

Update connection section:
```markdown
### 3. Connect

```bash
erk planner connect
```

This connects via SSH into the codespace and launches Claude directly.

To open VS Code instead:
```bash
erk planner connect --vscode
```
```

## Critical Files

- `src/erk/cli/commands/planner/connect_cmd.py` - Core logic: flag, parameter, if/else inversion
- `tests/commands/planner/test_planner_connect.py` - Three tests need updates
- `docs/user/planner-setup.md` - Document new default and `--vscode` flag

## Testing

After implementation:
```bash
# Run planner connect tests
uv run pytest tests/commands/planner/test_planner_connect.py -v

# Run all planner tests for regression
uv run pytest tests/commands/planner/ -v
```

## Notes

- **Breaking Change:** The `--ssh` flag no longer exists. Since this is unreleased private software, backwards compatibility is not a concern.
- **Behavior:** Both default and named planner connections (e.g., `erk planner connect my-planner`) use SSH by default.
- **Process Replacement:** Both code paths use `os.execvp()` to replace the current process, so no additional cleanup needed.