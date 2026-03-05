# Plan: Add branch-name objective inference to objective-plan command

## Context

When running `/erk:objective-plan` without arguments on a branch like `plnd/O8762-add-frontmatter-life-03-05-0831`, the command currently goes through a multi-step plan metadata lookup to find the objective number. But the objective number (`8762`) is right there in the branch name. Adding a direct branch-name extraction step would be faster and work even when plan metadata isn't available.

## Change

Edit `.claude/commands/erk/objective-plan.md` Step 1 to add a new inference path **before** the plan metadata lookup:

**Current order:**
1. Check for explicit argument
2. Look up plan metadata via `ref.json` → `get-plan-metadata`
3. Fall back to prompting

**New order:**
1. Check for explicit argument
2. **Extract objective from branch name** using regex `^pl(?:an(?:ned)?|nd)/[Oo](\d+)-` (same pattern as `extract_objective_number()` in `packages/erk-shared/src/erk_shared/naming.py:715`)
3. Look up plan metadata via `ref.json` → `get-plan-metadata` (existing fallback)
4. Fall back to prompting

### Specific edit to `.claude/commands/erk/objective-plan.md`

After the "Get current branch name" step (line 55), add a new sub-step before the `ref.json` check:

```
2. Check if the branch name contains an objective number directly:
   - Pattern: `^pl(?:an(?:ned)?|nd)/[Oo](\d+)-` (e.g., `plnd/O8762-some-slug-01-15-1430`)
   - If matched, use the extracted number as the objective and inform the user:
     "Using objective #<number> from branch name. Run with explicit argument to override."
   - If matched, skip the plan metadata lookup below and proceed to Step 2.
```

Renumber the existing `ref.json` / plan metadata lookup as step 3, making it a fallback when the branch name doesn't contain an objective number.

## Files to modify

- `.claude/commands/erk/objective-plan.md` — lines ~50-93 (Step 1 inference logic)

## Verification

- Read the updated command and confirm the inference order is: explicit arg → branch name pattern → plan metadata → prompt
- The regex matches the same pattern as `extract_objective_number()` in `erk_shared/naming.py`
