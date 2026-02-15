# Fix: CI autofix prompt ordering — docs-sync before prettier

## Context

In CI autofix, the prompt that guides the Claude agent lists fix actions in an order where `prettier --write` comes before `make docs-sync`. If both prettier and docs-check fail, the agent could format existing files first, then docs-sync generates new/updated markdown that misses formatting. The verify step would then fail on unformatted generated docs, requiring another CI round.

All other locations (parallel CI check jobs, Makefile check targets, ci-verify-autofix) use read-only `--check` commands where ordering is irrelevant.

## Change

**File:** `.github/prompts/ci-autofix.md` (lines 23-24)

Swap the order of the prettier and docs-sync rules so doc mutations happen before formatting:

```markdown
# Before (current)
- For prettier errors: run `prettier --write <file>` for each markdown file
- For docs errors: run `make docs-sync` if generated docs are out of sync

# After (fixed)
- For docs errors: run `make docs-sync` if generated docs are out of sync
- For prettier errors: run `prettier --write <file>` for each markdown file
```

This ensures the agent is guided to generate docs first, then format everything (including any newly generated files).

## Verification

- Review the prompt to confirm the new ordering reads naturally
- No tests to run — this is a prompt template file