# Objective: wt-stack-adoption

## Type

completable

## Desired State

All stack and worktree operations use `ctx.wt_stack` instead of direct `ctx.graphite` calls:

1. **Stack queries** go through WtStack:
   - `ctx.wt_stack.get_parent(branch)` instead of `ctx.graphite.get_parent_branch(...)`
   - `ctx.wt_stack.get_children(branch)` instead of `ctx.graphite.get_child_branches(...)`
   - etc.

2. **Worktree operations** unified:
   - `ctx.wt_stack.list_worktrees()` instead of `ctx.git.list_worktrees(repo.root)`
   - `ctx.wt_stack.find_worktree(branch)` instead of direct git calls

3. **Graphite availability handled internally** - No scattered "is Graphite available?" guards.

## Work Items

Tracked in `wt_stack.py` docstring (source of truth). Flexible ordering:

| #   | Work Item                            | Complexity | Status |
| --- | ------------------------------------ | ---------- | ------ |
| 1   | `get_parent()` migration             | Simplest   | TODO   |
| 2   | `get_children()` migration           | Simple     | TODO   |
| 3   | `get_stack()` migration              | Simple     | TODO   |
| 4   | `is_tracked()` + `track()` migration | Medium     | TODO   |
| 5   | `get_all_branches()` migration       | Medium     | TODO   |
| 6   | `get_prs()` migration                | Medium     | TODO   |
| 7   | Worktree operations                  | Medium     | TODO   |
| 8   | Stack mutations                      | Complex    | TODO   |
| 9   | Context integration                  | N/A        | DONE   |
| 10  | Deprecate direct ctx.graphite        | Final      | TODO   |

## Scope

**In Scope:**

- Files in `src/erk/cli/` calling `ctx.graphite.*` methods
- Files in `src/erk/core/` calling `ctx.graphite.*` methods
- Files in `packages/erk-shared/` calling graphite methods directly
- Implementation of WtStack methods (currently NotImplementedError stubs)
- Tests for each implemented WtStack method

**Out of Scope:**

- `ctx.graphite` calls without WtStack equivalents (auth, URL generation)
- The Graphite ABC/implementation itself
- Test files (they can use direct graphite for test setup)

## Evaluation Prompt

For each of the 10 work items:

1. Check if the WtStack method is implemented (not raising NotImplementedError)
2. Count remaining direct `ctx.graphite.*` / `ctx.git.*` calls that should migrate
3. Report status per work item: DONE, IN_PROGRESS (partially migrated), or TODO

## Plan Sizing

- **Small**: Implement 1 WtStack method + migrate 1-2 call sites
- **Medium**: Implement 1 WtStack method + migrate all its call sites (3-5 files)
- **Large**: Work Item 8 (stack mutations) - complex, multiple methods

Each plan should:

1. Implement the WtStack method(s)
2. Add tests for the new method(s)
3. Migrate all call sites for that method
4. Be independently mergeable

## Completion Criteria

- All WtStack methods implemented (no NotImplementedError)
- All migrateable call sites use ctx.wt_stack
- Tests exist for all WtStack methods
- Direct ctx.graphite usage documented as intentional exceptions

## Related Documentation

- `packages/erk-shared/src/erk_shared/integrations/wt_stack/wt_stack.py` - Source of truth for work items
- `docs/agent/architecture/erk-architecture.md` - Context patterns
