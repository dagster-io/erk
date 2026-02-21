# Context-Aware Next Steps After Plan Save (Worktree-Per-Stack)

## Context

After saving a plan via `/erk:plan-save`, the "next steps" output always suggests `erk br create --for-plan <issue>` with wording implying a new worktree ("Prepare worktree"). However, `erk br create` already has built-in "stack in place" behavior — when run from within an assigned slot, it updates the slot's branch tip instead of allocating a new worktree (`create_cmd.py:211-232`). The messaging should reflect this and make "worktree per stack" the default mental model when already in a worktree.

**Desired behavior:**
- **On master** (not in a slot): Default = create new worktree (same as current)
- **In a worktree** (in a slot): Default = stack branch in current worktree. "New worktree" shown as an advanced copy-pasteable option.

## Changes

### 1. `packages/erk-shared/src/erk_shared/output/next_steps.py` — Add `WorktreeContext` and update format functions

Add a frozen dataclass for worktree context:

```python
@dataclass(frozen=True)
class WorktreeContext:
    is_in_slot: bool
    slot_name: str | None
```

Update `format_next_steps_plain` signature:
```python
def format_next_steps_plain(issue_number: int, *, worktree_context: WorktreeContext | None) -> str:
```

When `worktree_context` is not None and `is_in_slot` is True, change the output:

```
Next steps:

View Issue: gh issue view {N} --web

In Claude Code:
  Prepare (stacks in current worktree): /erk:prepare
  Submit to queue: /erk:plan-submit

OR exit Claude Code first, then run one of:
  Stack here: erk br create --for-plan {N}
  Stack+Implement: source "$(erk br create --for-plan {N} --script)" && erk implement --dangerous
  Submit to Queue: erk plan submit {N}

Advanced — new worktree (run from root worktree):
  erk br create --for-plan {N}
```

When not in a slot: same output as today.

Same treatment for `format_draft_pr_next_steps_plain` — add `worktree_context` kwarg, show "Stack here" vs "Local" labeling, add advanced section.

`format_next_steps_markdown` is NOT changed (used in issue bodies, no worktree context).

### 2. `src/erk/cli/commands/exec/scripts/plan_save_to_issue.py` — Detect slot context and pass to formatter

Add a helper function to detect if cwd is in a pool slot. Import `find_assignment_by_worktree_path` from `navigation_helpers` and `load_pool_state` from `worktree_pool`. Uses `discover_repo_context` already available through the click context.

At the display output (line 305):
```python
wt_ctx = _detect_worktree_context(repo_root, repo)
click.echo(format_next_steps_plain(result.issue_number, worktree_context=wt_ctx))
```

At the JSON output (lines 307-316), add `is_in_slot` and `slot_name` fields when in a slot, so the agent skill can use them.

### 3. `src/erk/cli/commands/exec/scripts/plan_save.py` — Same context detection for draft PR path

At line 256, pass `worktree_context` to `format_draft_pr_next_steps_plain`.
At JSON output (lines 258-268), add `is_in_slot`/`slot_name` fields.

### 4. `.claude/commands/erk/plan-save.md` — Context-aware agent display instructions

Update Step 4 (Display Results) to branch on `is_in_slot` from JSON output:

**When `is_in_slot` is `true`:**
- Use "Stack here" labeling instead of "Local"
- Add "Advanced — new worktree" section with copy-pasteable command
- Note that `erk br create --for-plan` will stack in the current worktree

**When `is_in_slot` is absent or `false`:**
- Keep existing text unchanged (create new worktree is the natural path)

### 5. Tests

**`packages/erk-shared/tests/unit/output/test_next_steps.py`** and **`tests/unit/shared/test_next_steps.py`**:
- Update all existing calls to pass `worktree_context=None`
- Add tests for `WorktreeContext(is_in_slot=True, slot_name="erk-slot-01")` verifying:
  - "Stack here" appears in output
  - "Advanced" section appears
  - "root worktree" mentioned

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| No `--new-slot` flag | Scope control; "run from root worktree" is sufficient for now |
| `is_in_slot` in JSON output | Lets agent skill (plan-save.md) make display decisions |
| `WorktreeContext` dataclass | Clean separation; format functions stay pure |
| Same command, different labels | `erk br create --for-plan` already does the right thing per context |

## Files Modified

1. `packages/erk-shared/src/erk_shared/output/next_steps.py`
2. `src/erk/cli/commands/exec/scripts/plan_save_to_issue.py`
3. `src/erk/cli/commands/exec/scripts/plan_save.py`
4. `.claude/commands/erk/plan-save.md`
5. `packages/erk-shared/tests/unit/output/test_next_steps.py`
6. `tests/unit/shared/test_next_steps.py`

## Verification

1. Run unit tests: `pytest packages/erk-shared/tests/unit/output/test_next_steps.py tests/unit/shared/test_next_steps.py`
2. Manual test from master: `erk exec plan-save --format display` — should show current-style output
3. Manual test from a slot worktree: `erk exec plan-save --format display` — should show "Stack here" and "Advanced" sections
4. Manual test JSON output: verify `is_in_slot` field appears when in a slot
