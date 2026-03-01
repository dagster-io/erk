# Plan: Fix pr-address commit instructions for plan-only PRs

## Context

When `pr-address` runs on a plan-only PR (e.g. #8544), the agent edits `.erk/impl-context/plan.md`. But `.erk/impl-context/` is gitignored, so the Step 3 instruction `git add <changed files>` silently fails. The agent had to discover and recover with `git add -f`, wasting 2 extra turns and ~$0.20.

The tripwire in `docs/learned/ci/gitignored-directory-commit-patterns.md` already documents this, but `pr-address.md` doesn't account for it.

## Change

**File:** `.claude/commands/erk/pr-address.md` (~line 200)

Add a note about gitignored files to Step 3:

```markdown
#### Step 3: Commit the Batch

Create a single commit for all changes in the batch:

```bash
git add <changed files>
git commit -m "Address PR review comments (batch N/M)

- <summary of comment 1>
- <summary of comment 2>
..."
```

**Note:** If any changed files are in `.erk/impl-context/` (plan-only PRs), use `git add -f` instead — the directory is gitignored.
```

## Verification

- Grep for other commands/skills that commit `.erk/impl-context/` files to ensure consistency
- No tests needed — this is a documentation-only change
