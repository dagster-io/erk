# Simplify Plan Next-Steps Output: Remove source Wrappers

## Context

After saving a plan, erk displays "next steps" commands to the user. The "Implement plan" section currently shows complex `source "$(erk br co --for-plan N --script)" && erk implement` commands that combine worktree checkout with implementation.

The user's feedback: the `source` wrappers in the implement section are unnecessary because:
1. `erk implement N` already handles fetching the plan from GitHub and setting up `.erk/impl-context/` in the current directory
2. The "Checkout plan" section already shows `erk br co --for-plan N` separately for navigating to a worktree
3. Users don't need a combined checkout+implement one-liner in the CLI output — they can just `erk implement N` directly

The goal: simplify the "Implement plan" section to show direct `erk implement N` commands, remove the "In current wt" / "In new wt" sub-sections from the implement block, and keep the checkout section separate.

## Changes

### 1. Simplify `PlanNextSteps` dataclass

**File:** `packages/erk-shared/src/erk_shared/output/next_steps.py`

**Remove** these 4 properties that use the `source` wrapper pattern:
- `implement_current_wt`
- `implement_current_wt_dangerous`
- `implement_new_wt`
- `implement_new_wt_dangerous`

**Replace** with 2 simpler properties:
- `implement` → `f"erk implement {self.plan_number}"`
- `implement_dangerous` → `f"erk implement {self.plan_number} --dangerous"`

### 2. Simplify `format_plan_next_steps_plain` output

**File:** `packages/erk-shared/src/erk_shared/output/next_steps.py`

Change the output from:

```
Implement plan #42:
  In current wt:    source "$(erk br co --for-plan 42 --script)" && erk implement
    (dangerously):  source "$(erk br co --for-plan 42 --script)" && erk implement -d
  In new wt:        source "$(erk br co --new-slot --for-plan 42 --script)" && erk implement
    (dangerously):  source "$(erk br co --new-slot --for-plan 42 --script)" && erk implement -d
```

To:

```
Implement plan #42:
  CLI command:    erk implement 42
  (dangerously):  erk implement 42 --dangerous
```

Notes:
- Use `--dangerous` (long form) not `-d` (short form) — the next-steps output should be clear and self-documenting
- Keep the checkout section unchanged — it already shows the right commands
- Keep the dispatch section unchanged

The full output format becomes:

```python
def format_plan_next_steps_plain(plan_number: int, *, url: str) -> str:
    s = PlanNextSteps(plan_number=plan_number, url=url)
    return f"""Implement plan #{plan_number}:
  CLI command:    {s.implement}
  (dangerously):  {s.implement_dangerous}

Checkout plan #{plan_number}:
  In current wt:  {s.checkout}
  In new wt:      {s.checkout_new_slot}

Dispatch plan #{plan_number}:
  CLI command:    {s.dispatch}
  Slash command:  {s.dispatch_slash_command}"""
```

### 3. Update tests in `packages/erk-shared/tests/unit/output/test_next_steps.py`

**Remove** tests for the old properties:
- `test_plan_next_steps_implement_current_wt`
- `test_plan_next_steps_implement_current_wt_dangerous`
- `test_plan_next_steps_implement_new_wt`
- `test_plan_next_steps_implement_new_wt_dangerous`

**Add** tests for new properties:
- `test_plan_next_steps_implement` — asserts `s.implement == "erk implement 42"`
- `test_plan_next_steps_implement_dangerous` — asserts `s.implement_dangerous == "erk implement 42 --dangerous"`

**Update** `test_format_plan_next_steps_plain_hierarchical_format`:
- Remove assertions for "In current wt:" and "In new wt:" (no longer in implement section)
- Remove assertion for "(dangerously):" → add assertion for "(dangerously):" (still present)
- Keep assertion for "Implement plan #42:" (still present)

**Update** `test_format_plan_next_steps_plain_contains_implement`:
- Change to check for `erk implement 42` (no source wrapper)
- Check for `erk implement 42 --dangerous` instead of `erk implement -d`

### 4. Update tests in `tests/unit/shared/test_next_steps.py`

Same changes as step 3 — this is the duplicate test file. Apply the same updates:
- Remove tests for old properties (`implement_current_wt`, etc.)
- Add tests for new properties (`implement`, `implement_dangerous`)
- Update format tests

### 5. Update test in `tests/unit/cli/commands/exec/scripts/test_exit_plan_mode_hook.py`

**Modify** `test_contains_implement_current_wt_command`:
- Rename to `test_contains_implement_command`
- Change assertion from checking for `"erk br co --for-plan 42 --script"` to checking for `"erk implement 42"`
- Keep assertion for `"erk implement"` in message

**Modify** `test_contains_implement_new_wt_command`:
- Rename to `test_contains_implement_dangerous_command`
- Change assertion to check for `"erk implement 42 --dangerous"` in message

## Files NOT changing

- `src/erk/cli/activation.py` — Shell activation pattern is unaffected (still used by TUI and other commands)
- `src/erk/cli/commands/checkout_helpers.py` — Checkout navigation helpers unchanged
- `src/erk/cli/commands/branch/checkout_cmd.py` — `erk br co` command unchanged
- `src/erk/cli/commands/implement.py` — `erk implement` command unchanged
- `src/erk/tui/commands/registry.py` — TUI commands still use `source` pattern for their clipboard copy actions (TUI is a different UX — users copy-paste from TUI, and the source pattern gives a one-liner for that use case)
- `src/erk/tui/screens/plan_detail_screen.py` — TUI detail screen unchanged (same reasoning as registry)
- `docs/learned/cli/shell-activation-pattern.md` — The shell activation pattern documentation stays; it's still used by TUI and `erk br co --script`
- `packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py` — Uses `format_next_steps_markdown()` which doesn't include implement commands
- `src/erk/cli/commands/exec/scripts/plan_save.py` — Calls `format_plan_next_steps_plain()` (will automatically get the new output)
- `src/erk/cli/commands/exec/scripts/exit_plan_mode_hook.py` — Calls `format_plan_next_steps_plain()` (will automatically get the new output)
- `src/erk/cli/commands/pr/create_cmd.py` — Calls `format_plan_next_steps_plain()` (will automatically get the new output)

## Verification

1. Run unit tests: `pytest packages/erk-shared/tests/unit/output/test_next_steps.py tests/unit/shared/test_next_steps.py tests/unit/cli/commands/exec/scripts/test_exit_plan_mode_hook.py -v`
2. Run ty type checker: `ty check packages/erk-shared/src/erk_shared/output/next_steps.py`
3. Run ruff linter
4. Verify the formatted output manually by running a quick test or printing the output