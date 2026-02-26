# Change dispatch keyboard shortcut from 's' to 'd' in TUI launch popup

## Context

In the erk dash TUI "planned PRs" screen, pressing `l` opens a launch popup that shows ACTION commands with single-key shortcuts. Currently the "Dispatch to Queue" action (`submit_to_queue`) is mapped to the `s` key. The user wants it changed to `d` (for "dispatch"), which is more mnemonic and avoids the potential confusion with the app-level `s` binding for sort.

Note: In the Objectives view, `s` is reused for `one_shot_plan` — that mapping is **not** changing. Only the plan-view dispatch action changes from `s` to `d`.

## Changes

### 1. `src/erk/tui/screens/launch_screen.py` — Change LAUNCH_KEYS mapping

**Line 22:** Change the `submit_to_queue` key from `"s"` to `"d"`.

```python
# Before:
"submit_to_queue": "s",

# After:
"submit_to_queue": "d",
```

No other lines in this file change. The `one_shot_plan` objective key stays as `"s"`.

### 2. `src/erk/tui/commands/registry.py` — Change shortcut in CommandDefinition

**Lines 197-205:** Change the `shortcut` field of the `submit_to_queue` CommandDefinition from `"s"` to `"d"`.

```python
# Before:
CommandDefinition(
    id="submit_to_queue",
    name="Dispatch to Queue",
    description="dispatch",
    category=CommandCategory.ACTION,
    shortcut="s",
    is_available=lambda ctx: _is_plan_view(ctx) and ctx.row.plan_url is not None,
    get_display_name=_display_submit_to_queue,
),

# After:
CommandDefinition(
    id="submit_to_queue",
    name="Dispatch to Queue",
    description="dispatch",
    category=CommandCategory.ACTION,
    shortcut="d",
    is_available=lambda ctx: _is_plan_view(ctx) and ctx.row.plan_url is not None,
    get_display_name=_display_submit_to_queue,
),
```

### 3. `tests/tui/screens/test_launch_screen.py` — Update test assertions

Three tests reference the `"s"` key for `submit_to_queue` in plan view. Update each to `"d"`:

**`test_launch_screen_builds_key_mapping_for_plan_view` (line 57):**
```python
# Before:
assert "s" in screen._key_to_command_id  # submit_to_queue

# After:
assert "d" in screen._key_to_command_id  # submit_to_queue
```

**`test_launch_screen_excludes_unavailable_commands` (line 98):**
```python
# Before:
assert "s" in screen._key_to_command_id

# After:
assert "d" in screen._key_to_command_id
```

**`test_launch_screen_maps_command_ids_correctly` (line 120):**
```python
# Before:
assert screen._key_to_command_id["s"] == "submit_to_queue"

# After:
assert screen._key_to_command_id["d"] == "submit_to_queue"
```

Note: `test_launch_screen_builds_key_mapping_for_objectives_view` (line 77) asserts `"s"` maps to `one_shot_plan` — this does NOT change.

## Files NOT changing

- `src/erk/tui/app.py` — The app-level `s` binding for sort is unrelated; no change needed.
- Objective-view keyboard shortcuts — `one_shot_plan` stays mapped to `"s"` in both `LAUNCH_KEYS` and its `CommandDefinition`.
- No other files reference the `submit_to_queue` shortcut.

## Key conflict check

The `"d"` key is not used anywhere in the launch screen's key space or in the plan-view action keys. The app-level bindings also do not use `"d"`. No conflicts.

## Verification

1. Run `pytest tests/tui/screens/test_launch_screen.py -v` — all tests should pass.
2. Run `pytest tests/tui/ -v` — full TUI test suite should pass.
3. Run `ruff check src/erk/tui/screens/launch_screen.py src/erk/tui/commands/registry.py` — no lint errors.
4. Run `ty check src/erk/tui/screens/launch_screen.py src/erk/tui/commands/registry.py` — no type errors.