# Fix TUI "submit" command: rename to "dispatch" and fix broken execution

## Context

The TUI command palette has a "submit" action for planned PRs that is broken in two ways:
1. **Wrong command executed**: Runs `erk plan submit <id>` which doesn't exist. Should run `erk pr dispatch <id>`.
2. **Wrong label**: Should say "dispatch" not "submit" to match the actual CLI command.

## Changes

### 1. Fix executed command — `src/erk/tui/app.py:685`

Change:
```python
["erk", "plan", "submit", str(plan_id)],
```
To:
```python
["erk", "pr", "dispatch", str(plan_id)],
```

Also update the toast messages on lines 682/692 from "Submit"/"Submitted" to "Dispatch"/"Dispatched".

### 2. Rename label — `src/erk/tui/commands/registry.py:197-205`

Change `description` from `"submit"` to `"dispatch"` and `name` from `"Submit to Queue"` to `"Dispatch to Queue"`.

### 3. Update error message — `src/erk/tui/app.py:694-697`

Update the error toast text from "submit" to "dispatch" language.

## Verification

- Run `erk dash -i`, select a plan, open command palette, confirm "dispatch" label appears
- Execute the dispatch action and confirm it runs `erk pr dispatch <id>` successfully
