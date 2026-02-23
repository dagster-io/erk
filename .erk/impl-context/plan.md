# Add `erk admin claude-ci` command

## Context

The `CLAUDE_ENABLED` GitHub Actions repository variable already gates 7 CI workflows (code-reviews, autofix, learn, one-shot, plan-implement, pr-address, pr-fix-conflicts). Currently it can only be toggled via `gh variable set` directly. Add an `erk admin claude-ci` command to provide a discoverable CLI for toggling it, following the established `--enable`/`--disable`/status pattern from existing admin commands.

## Implementation

### 1. Extend `GitHubAdmin` ABC with variable methods

**File:** `packages/erk-shared/src/erk_shared/gateway/github_admin/abc.py`

Add two abstract methods:
- `get_variable(location, variable_name) -> str | None` — returns variable value, or None if not set
- `set_variable(location, variable_name, value) -> None` — sets a repository variable

### 2. Implement in `RealGitHubAdmin`

**File:** `packages/erk-shared/src/erk_shared/gateway/github_admin/real.py`

- `get_variable`: Run `gh variable get <name> --repo owner/repo`, return stdout stripped. Return `None` if command fails (variable not set).
- `set_variable`: Run `gh variable set <name> --body <value> --repo owner/repo`

Both use `run_subprocess_with_context`.

### 3. Implement in `FakeGitHubAdmin`

**File:** `packages/erk-shared/src/erk_shared/gateway/github_admin/fake.py`

- Constructor: add `variables: dict[str, str] | None = None` parameter
- `get_variable`: return from `_variables` dict, None if missing
- `set_variable`: record in `_set_variable_calls` mutation tracker, update `_variables`
- Add `set_variable_calls` read-only property for test assertions

### 4. Implement in `NoopGitHubAdmin`

**File:** `packages/erk-shared/src/erk_shared/gateway/github_admin/noop.py`

- `get_variable`: delegate to wrapped (read operation)
- `set_variable`: no-op (write operation)

### 5. Implement in `PrintingGitHubAdmin`

**File:** `packages/erk-shared/src/erk_shared/gateway/github_admin/printing.py`

- `get_variable`: delegate to wrapped (read, no printing)
- `set_variable`: print command, then delegate

### 6. Add CLI command

**File:** `src/erk/cli/commands/admin.py`

Add `claude-ci` command to `admin_group`, following the `gh-actions-api-key` pattern:

```
erk admin claude-ci           # Show current status
erk admin claude-ci --enable  # Set CLAUDE_ENABLED=true
erk admin claude-ci --disable # Set CLAUDE_ENABLED=false
```

- Status mode: call `admin.get_variable(location, "CLAUDE_ENABLED")`, display enabled/disabled/not set
- Enable: call `admin.set_variable(location, "CLAUDE_ENABLED", "true")`
- Disable: call `admin.set_variable(location, "CLAUDE_ENABLED", "false")`

List affected workflows in the status output.

### 7. Tests

**File:** `tests/unit/cli/commands/test_admin_claude_ci.py`

Following the pattern from `test_admin_gh_actions_api_key.py`:
- `test_status_enabled` — variable is "true", shows Enabled
- `test_status_disabled` — variable is "false", shows Disabled
- `test_status_not_set` — variable not set, shows Enabled (default behavior)
- `test_enable_sets_variable` — `--enable` calls `set_variable` with "true"
- `test_disable_sets_variable` — `--disable` calls `set_variable` with "false"

## Files Modified

1. `packages/erk-shared/src/erk_shared/gateway/github_admin/abc.py`
2. `packages/erk-shared/src/erk_shared/gateway/github_admin/real.py`
3. `packages/erk-shared/src/erk_shared/gateway/github_admin/fake.py`
4. `packages/erk-shared/src/erk_shared/gateway/github_admin/noop.py`
5. `packages/erk-shared/src/erk_shared/gateway/github_admin/printing.py`
6. `src/erk/cli/commands/admin.py`
7. `tests/unit/cli/commands/test_admin_claude_ci.py` (new)

## Verification

1. Run `pytest tests/unit/cli/commands/test_admin_claude_ci.py`
2. Run `erk admin claude-ci` to verify status display
3. Run `erk admin claude-ci --disable` and verify with `gh variable get CLAUDE_ENABLED`
4. Run `erk admin claude-ci --enable` and verify
