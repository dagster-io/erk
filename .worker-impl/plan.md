# Fix: pr-fix-conflicts "Argument list too long" error

## Problem

The "Post status comment to PR" step in `.github/workflows/pr-fix-conflicts.yml:116-134` fails with `Argument list too long` when `REBASE_OUTPUT` is large.

The current code passes the rebase output through shell variable expansion into `gh pr comment --body "$(echo -e "$BODY")"`, which hits Linux's `ARG_MAX` limit (~2MB) when the output is large.

## Fix

**File:** `.github/workflows/pr-fix-conflicts.yml`

In the "Post status comment to PR" step (lines 124-134):

1. Write the comment body to a temp file using `printf` + redirection (avoids shell argument limits)
2. Use `gh pr comment --body-file` instead of `--body` (reads from file, no argument size issue)

This is the same pattern documented in `docs/learned/architecture/github-cli-limits.md` — avoid passing large content as CLI arguments.

## Verification

Re-trigger the workflow on the same PR (#6356) and confirm the status comment posts successfully.