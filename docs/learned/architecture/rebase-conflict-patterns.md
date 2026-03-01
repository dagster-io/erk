---
title: Rebase Conflict Patterns
read_when:
  - "resolving merge conflicts after rebase"
  - "debugging test failures after rebase"
  - "handling auto-generated file conflicts"
  - "resuming a rebase with conflicts"
tripwires:
  - action: "running tests immediately after rebase without checking for old symbols"
    warning: "Hidden regressions can exist in non-conflicted files. Grep for old symbols that should have been renamed before running tests."
---

# Rebase Conflict Patterns

Rebase operations can introduce subtle regressions in files that don't show as conflicts. This document covers patterns for preventing and detecting these issues.

## Hidden Regressions in Non-Conflicted Files

After a rebase, git marks files with textual conflicts for manual resolution. However, **semantic** conflicts in non-conflicted files go undetected:

- A function was renamed in the base branch, but call sites in your branch still use the old name
- A type signature changed, but your branch's callers pass the old argument types
- A module was moved, but your branch imports from the old location

These don't produce merge markers — git considers the files cleanly merged because the changes don't overlap textually.

## Prevention: Grep Before Running Tests

After resolving all textual conflicts:

```bash
# Check for old symbols that should have been renamed
grep -r "old_function_name" src/ tests/

# Check for old module paths
grep -r "from old_module" src/ tests/

# Then run tests
make test
```

## Auto-Generated File Resolution

Some files are auto-generated (e.g., `tripwires.md`, `index.md`). For these:

1. Accept either version during conflict resolution
2. Run the regeneration command after resolving all conflicts:
   ```bash
   erk docs sync
   ```
3. The regenerated file will be correct based on current frontmatter state

## Mid-Rebase Recovery with `erk pr rebase`

`erk pr rebase` (and the `/erk:rebase` slash command) can resolve conflicts in a rebase that is already in progress. If you started a `git rebase` manually and hit conflicts you can't resolve, run `erk pr rebase --dangerous` to have Claude pick up where you left off. It will detect the in-progress rebase, resolve the conflicted files, and continue the rebase to completion.

This makes `erk pr rebase` useful as both a start-from-scratch rebase tool and a mid-rebase recovery tool.

## Related Documentation

- [Git and Graphite Edge Cases](git-graphite-quirks.md) — Git/Graphite interaction patterns
- [LibCST Systematic Import Refactoring](../refactoring/libcst-systematic-imports.md) — Batch rename patterns
