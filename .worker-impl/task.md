In `erk pr rewrite`, the output copy says "PR rewritten" which is misleading. The command rewrites the PR title and description (and squashes/amends the commit message), but "PR rewritten" sounds like the code/diff itself was rewritten.

Fix the user-facing copy in `src/erk/cli/commands/pr/rewrite_cmd.py`:

1. The header "📝 Rewriting PR..." should be changed to something more accurate like "📝 Rewriting PR title and description..."
2. The completion message "✅ PR rewritten: {title}" should clarify what was actually rewritten, e.g. "✅ PR title and description updated: {title}"

Also update any test assertions in `tests/commands/pr/test_rewrite.py` that check for the old copy strings.

