# Fix misleading "PR rewritten" copy in `erk pr rewrite`

## Context

The `erk pr rewrite` command rewrites the PR **title and description** (and squashes/amends the commit message), but its user-facing output says "PR rewritten" which sounds like the code/diff itself was rewritten. This is misleading and should be clarified.

## Changes

### File: `src/erk/cli/commands/pr/rewrite_cmd.py`

Two string literals need to change:

1. **Line 89** - Header message at the start of the command:
   - **Before:** `click.echo(click.style("📝 Rewriting PR...", bold=True))`
   - **After:** `click.echo(click.style("📝 Rewriting PR title and description...", bold=True))`

2. **Line 202** - Completion message at the end of the command:
   - **Before:** `click.echo(f"✅ PR rewritten: {title}")`
   - **After:** `click.echo(f"✅ PR title and description updated: {title}")`

### No other files need changes

- `tests/commands/pr/test_rewrite.py` already asserts `"PR title and description updated"` on lines 125 and 161, so the tests are already aligned with the new copy.
- No other files in `src/` or `tests/` reference the old "PR rewritten" string.

## Implementation Details

This is a two-line string literal change. No logic changes, no new imports, no architectural decisions.

The key pattern: both messages now say "title and description" to make it clear that the command updates the PR metadata, not the code itself. The completion message uses "updated" rather than "rewritten" since "updated" is more accurate for what happened.

## Verification

1. Run the rewrite command tests:
   ```
   pytest tests/commands/pr/test_rewrite.py -v
   ```
   All tests should pass. In particular, `test_pr_rewrite_happy_path` and `test_pr_rewrite_already_single_commit` assert on the updated string.

2. Optionally run `ruff check src/erk/cli/commands/pr/rewrite_cmd.py` to confirm no lint issues.