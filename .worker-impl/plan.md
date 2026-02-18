# Fix misleading "PR rewritten" copy in `erk pr rewrite`

## Context

The `erk pr rewrite` command rewrites the PR **title and description** (and squashes/amends the commit message), but its user-facing output says "PR rewritten" which implies the code/diff itself was rewritten. This is misleading. The copy should clarify that only the title and description were updated.

## Changes

### 1. `src/erk/cli/commands/pr/rewrite_cmd.py`

Two string changes:

- **Line 89**: Change the header from `"📝 Rewriting PR..."` to `"📝 Rewriting PR title and description..."`
- **Line 202**: Change the completion message from `f"✅ PR rewritten: {title}"` to `f"✅ PR title and description updated: {title}"`

### 2. `tests/commands/pr/test_rewrite.py`

Update test assertions that check for the old copy strings:

- **Line 125** (`test_pr_rewrite_happy_path`): Change `assert "PR rewritten" in result.output` to `assert "PR title and description updated" in result.output`
- **Line 161** (`test_pr_rewrite_already_single_commit`): Change `assert "PR rewritten" in result.output` to `assert "PR title and description updated" in result.output`

## Files NOT Changing

- No other files reference these specific copy strings
- The CLI help text / docstring for the command does not need changes (it already accurately describes what the command does)
- No changes to the command logic, only user-facing output strings

## Verification

Run the rewrite command tests to confirm assertions pass with the new copy:

```bash
pytest tests/commands/pr/test_rewrite.py -v
```