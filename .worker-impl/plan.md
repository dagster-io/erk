# Plan: Phase 2 - Shell Integration as Optional Enhancement

**Part of Objective #4363, Phase 2 (Steps 2.1-2.3)**

## Goal

Update `erk init` and `erk doctor` to present shell integration as an **optional enhancement** rather than a standard setup step. This changes the mental model: erk works out-of-the-box via subshells, shell integration is a power-user upgrade.

## Summary of Changes

1. **Step 2.1**: Update `erk init` messaging and prompts to frame shell integration as optional
2. **Step 2.2**: Already exists - `is_shell_integration_active()` and `has_shell_integration_in_rc()` detection is implemented
3. **Step 2.3**: Update `erk doctor` to show shell integration as purely informational (no remediation)

## Implementation

### Phase A: Update `erk init` (Step 2.1)

**File:** `src/erk/cli/commands/init.py`

#### A1. Update `perform_shell_setup()` messaging (lines 193-226)

Current messaging:
```python
user_output("Shell integration provides:")
user_output("  - Tab completion for erk commands")
user_output("  - Automatic worktree activation on 'erk br co'")

if not click.confirm("\nShow shell integration setup instructions?", default=True):
```

Change to:
```python
user_output("Shell integration is an optional enhancement that provides:")
user_output("  - Tab completion for erk commands")
user_output("  - Seamless 'cd' behavior on 'erk br co' (instead of subshell)")
user_output("Note: erk works without this - worktree commands spawn subshells by default.")

if not click.confirm("\nSet up shell integration?", default=False):  # default=False is key change
```

**Key change:** `default=False` - shell integration is opt-in, not opt-out.

#### A2. Update skipped message (line 215)

Current:
```python
user_output("Skipping shell integration. You can run 'erk init --shell' later.")
```

Change to:
```python
user_output("Skipping. Erk will use subshells for worktree navigation (works great!).")
user_output("You can add shell integration later with 'erk init --shell'.")
```

#### A3. Update Step 3 header context (line 729)

Current:
```python
user_output("\nStep 3: User configuration...")
```

Change to:
```python
user_output("\nStep 3: Optional enhancements...")
```

### Phase B: Update `erk doctor` (Step 2.3)

**File:** `src/erk/core/health_checks.py`

#### B1. Update `check_shell_integration()` to remove remediation (lines 660-704)

Current return when not configured:
```python
return CheckResult(
    name="shell-integration",
    passed=True,
    message=f"Shell integration not configured ({shell_name})",
    info=True,
    remediation="Run 'erk init' to add shell integration",  # REMOVE this
)
```

Change to:
```python
return CheckResult(
    name="shell-integration",
    passed=True,
    message=f"Shell integration not configured ({shell_name})",
    details="Optional enhancement - erk uses subshells by default",
    info=True,
    # No remediation - this is purely informational
)
```

#### B2. Update success message for clarity

Current:
```python
message=f"Shell integration configured ({shell_name})",
```

Change to:
```python
message=f"Shell integration configured ({shell_name})",
details="Using 'cd' mode instead of subshells",
```

### Phase C: Add Tests

**File:** `tests/commands/doctor/test_shell_integration.py`

- Add test verifying no remediation is returned when shell integration is not configured
- Add test verifying details field explains subshell default

**File:** `tests/commands/init/test_init.py` (or create if needed)

- Add test verifying shell integration prompt defaults to False
- Add test verifying the "optional enhancement" messaging appears

## Files to Modify

| File | Changes |
|------|---------|
| `src/erk/cli/commands/init.py` | Update messaging in `perform_shell_setup()`, Step 3 header |
| `src/erk/core/health_checks.py` | Update `check_shell_integration()` to remove remediation |
| `tests/commands/doctor/test_shell_integration.py` | Add tests for new behavior |

## Acceptance Criteria

1. `erk init` defaults to skipping shell integration (user must explicitly opt-in)
2. `erk init` messaging clearly indicates shell integration is optional
3. `erk doctor` shows shell integration as info-only with no remediation action
4. All existing tests continue to pass

## Related Documentation

- Load `dignified-python` skill for Python coding standards
- Load `fake-driven-testing` skill for test patterns

## Notes

- Step 2.2 (detection) is already implemented via `is_shell_integration_active()` in `src/erk/cli/subshell.py` and `has_shell_integration_in_rc()` in `src/erk/core/init_utils.py` - no changes needed
- The objective specifies this should be a single PR covering all three steps