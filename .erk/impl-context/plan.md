# Remove plan number argument from `/erk:pr-dispatch` in next-steps menu

## Context

After saving a plan, the next-steps menu displays a "Dispatch plan" section that includes both a CLI command and a slash command:

```
Dispatch plan #8779:
  CLI command:    erk pr dispatch 8779
  Slash command:  /erk:pr-dispatch 8779
```

The `/erk:pr-dispatch` slash command (`.claude/commands/erk/pr-dispatch.md`) auto-detects the plan number from conversation context — it searches the conversation for the most recent plan reference (e.g., "saved as draft PR #8779"). It does not need an explicit argument when used in-context after saving a plan. The argument should be removed from the slash command line in the menu output.

The CLI command `erk pr dispatch 8779` is correct and should keep its argument — it's a shell command that needs explicit arguments.

## Changes

### 1. `packages/erk-shared/src/erk_shared/output/next_steps.py`

**Property `dispatch_slash_command` (line 30-31):** Change from dynamic to static. The slash command doesn't need the plan number since it auto-detects from conversation context.

```python
# Before
@property
def dispatch_slash_command(self) -> str:
    return f"/erk:pr-dispatch {self.plan_number}"

# After
@property
def dispatch_slash_command(self) -> str:
    return "/erk:pr-dispatch"
```

This can also just use the existing `DISPATCH_SLASH_COMMAND` constant (line 57), which is already defined as `"/erk:pr-dispatch"` but currently unused by any formatter. Either approach is fine — using the constant is slightly more DRY but the property body is trivial. Implementer's choice.

### 2. `tests/unit/shared/test_next_steps.py`

**`test_dispatch_slash_command` (line 81-86):** Update the expected value.

```python
# Before
assert steps.dispatch_slash_command == "/erk:pr-dispatch 42"

# After
assert steps.dispatch_slash_command == "/erk:pr-dispatch"
```

**`test_contains_dispatch` (line 105-109):** Update the assertion for the slash command.

```python
# Before
assert "/erk:pr-dispatch 42" in output

# After
assert "/erk:pr-dispatch" in output
```

Note: The `assert "erk pr dispatch 42" in output` line stays unchanged — the CLI command still includes the plan number.

### 3. `packages/erk-shared/tests/unit/output/test_next_steps.py`

This test file does NOT have a test for `dispatch_slash_command` directly, but `test_format_plan_next_steps_plain_contains_dispatch` (line 100-103) only checks for `"erk pr dispatch 42"` (the CLI command). No changes needed here, since the assertion `assert "erk pr dispatch 42" in output` is about the CLI command, not the slash command.

However — line 78 asserts `"Dispatch to queue:"` but the actual source code produces `"Dispatch plan #{plan_number}:"`. This is a pre-existing mismatch (this test may already be failing). **Do not fix this** — it's out of scope.

## Files NOT Changing

- `.claude/commands/erk/pr-dispatch.md` — the slash command definition is correct; it already auto-detects plan numbers from conversation context
- `src/erk/cli/commands/pr/dispatch_cmd.py` — the CLI command itself is unchanged
- `docs/learned/planning/next-steps-output.md` — documentation update is out of scope for this change; the doc already notes that `DISPATCH_SLASH_COMMAND` exists without the plan number
- `format_next_steps_markdown()` — the markdown formatter doesn't include the slash command at all

## Verification

1. Run the unit tests:
   ```bash
   pytest tests/unit/shared/test_next_steps.py -v
   pytest packages/erk-shared/tests/unit/output/test_next_steps.py -v
   ```

2. Run type checking:
   ```bash
   ty check packages/erk-shared/src/erk_shared/output/next_steps.py
   ```

3. Verify the formatted output looks correct by inspecting:
   ```python
   from erk_shared.output.next_steps import format_plan_next_steps_plain
   print(format_plan_next_steps_plain(42, url="https://github.com/org/repo/pull/42"))
   ```

   Expected "Dispatch plan" section:
   ```
   Dispatch plan #42:
     CLI command:    erk pr dispatch 42
     Slash command:  /erk:pr-dispatch
   ```