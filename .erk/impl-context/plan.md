# Use "planned PR" terminology in user-facing output

## Context

The user-facing output after saving a plan says `Plan "..." saved as draft PR #9206` and uses bare `Implement PR #`, `Checkout PR #`, `Dispatch PR #` headers. The correct erk domain term for the GitHub PR entity is "planned PR", not "plan". The plan document itself can still be called a "plan", but once it's saved to GitHub as a PR, it should be referred to as a "planned PR".

## Changes

### 1. `packages/erk-shared/src/erk_shared/output/next_steps.py`

Update section headers in `format_plan_next_steps_plain` (lines 64-76):
- `Implement PR #{pr_number}:` → `Implement planned PR #{pr_number}:`
- `Checkout PR #{pr_number}:` → `Checkout planned PR #{pr_number}:`
- `Dispatch PR #{pr_number}:` → `Dispatch planned PR #{pr_number}:`

Update `format_next_steps_markdown` (line 93):
- `**Checkout PR branch:**` → `**Checkout planned PR branch:**`

### 2. `.claude/commands/erk/plan-save.md`

Update Step 7 display templates:
- Line 169: `Plan already saved as PR #<pr_number> (duplicate skipped)` → `Planned PR #<pr_number> already saved (duplicate skipped)`
- Line 176: `Plan "<title>" saved as draft PR #<pr_number>` → `Planned PR "<title>" saved as #<pr_number>`

### 3. Test updates

- `tests/unit/shared/test_next_steps.py:92` — `"Implement PR #42:"` → `"Implement planned PR #42:"`
- `tests/unit/shared/test_next_steps.py:105` — `"Dispatch PR #42:"` → `"Dispatch planned PR #42:"`
- `tests/commands/pr/test_create.py:34` — `"Checkout PR #999:"` → `"Checkout planned PR #999:"`
- `tests/commands/pr/test_create.py:35` — `"Dispatch PR #999:"` → `"Dispatch planned PR #999:"`
- `tests/unit/cli/commands/exec/scripts/test_exit_plan_mode_hook.py:1010` — `"Dispatch PR #42:"` → `"Dispatch planned PR #42:"`

## Verification

Run affected tests:
```bash
uv run pytest tests/unit/shared/test_next_steps.py tests/commands/pr/test_create.py tests/unit/cli/commands/exec/scripts/test_exit_plan_mode_hook.py -x
```
