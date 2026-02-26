# Fix: Modal dismiss keys (Esc/q/Space) not working in TUI (again)

## Context

Modal screens in `erk dash -i` display "Press Esc, q, or Space to close" but those keys do nothing. Any *other* key (like Ctrl+W) dismisses the modal instead. This is the same bug that was fixed before and then regressed.

### Regression timeline

1. **`0d105f359` (#8299)** — Introduced `on_key()` handlers with `not in` logic to prevent keystroke leakage. The `not in` logic was accidentally inverted — it dismisses on every key *except* the intended close keys.

2. **`e7e8f8470` (#8309)** — Fixed all three files: `not in` → `in`.

3. **`5eabe3946` (#8304)** — **THE REGRESSION.** "Add integration tests for modal on_key() handlers." This PR was stacked on #8299 (the buggy PR) and authored before #8309 fixed it. When squash-merged after #8309, it re-introduced the buggy `not in` code in all three files. The diff explicitly shows `in` → `not in` reversions.

4. **`e5ad757a8` (#8275)** — Only changed a docstring in plan_body_screen.py (not the culprit).

### Why existing tests didn't catch it

The tests added in #8304 only verify that **unmapped keys dismiss** the modal (pressing "j" or "x"). They don't test that **escape/q/space dismiss**. With the `not in` bug:
- Unmapped keys DO dismiss → tests pass
- escape/q/space do NOT dismiss → bug, but untested

## Changes

### 1. Fix `on_key()` logic in three screen files

**`src/erk/tui/screens/plan_body_screen.py:193`**
```python
# Before:  if event.key not in ("escape", "q", "space"):
# After:   if event.key in ("escape", "q", "space"):
```

**`src/erk/tui/screens/help_screen.py:107`**
```python
# Before:  if event.key not in ("escape", "q", "question_mark"):
# After:   if event.key in ("escape", "q", "question_mark"):
```

**`src/erk/tui/screens/launch_screen.py:128`**
```python
# Before:  elif event.key not in ("escape", "q"):
# After:   else:
```

### 2. Fix existing tests that assert wrong behavior

The "unmapped key dismisses" tests now assert the wrong thing — with `in` logic, unmapped keys are consumed but don't dismiss. Update:

- `tests/tui/app/test_core.py:123` — `test_help_screen_dismisses_on_unmapped_key`: Change to assert modal is NOT dismissed on unmapped key "j" (it should stay open). Or rename to test that dismiss keys work.
- `tests/tui/app/test_actions.py:183` — `test_launch_screen_dismisses_on_unmapped_key`: LaunchScreen uses `else` so unmapped keys DO dismiss. This test stays correct.
- `tests/tui/app/test_plan_body_screen.py:280` — `test_plan_body_screen_dismisses_on_unmapped_key`: Change to assert modal is NOT dismissed on unmapped key "j".
- `tests/tui/app/test_plan_body_screen.py:142` — `test_issue_body_screen_dismisses_on_arbitrary_key`: Same fix, arbitrary keys should NOT dismiss.

### 3. Add tests for the actual dismiss keys

Add tests that verify escape/q/space DO dismiss the modals (the tests that should have existed to prevent this regression):

- `test_help_screen_dismisses_on_escape` — press Esc, verify HelpScreen dismissed
- `test_plan_body_screen_dismisses_on_q` — press q, verify PlanBodyScreen dismissed
- `test_plan_body_screen_dismisses_on_space` — press Space, verify PlanBodyScreen dismissed

## Verification

1. Run `pytest tests/tui/` — all tests pass
2. Manual: `erk dash -i` → open objective view → press Esc/q/Space → modal closes
3. Manual: verify random keys do NOT leak to underlying view
