# Plan: Create Slot Pool Architecture Documentation

## Summary

Create `docs/learned/erk/slot-pool-architecture.md` to document the slot/pool system that manages reusable worktrees. This documentation was identified as a gap during planning for `erk branch delete`.

## Why This Doc Is Needed

During the `erk branch delete` planning, 3 Explore agents were needed to discover:
- What slots are conceptually
- Data structures and their relationships
- Key helper functions and where they live
- The slot lifecycle

With this doc, future agents can skip exploration and go straight to implementation.

## File to Create

### `docs/learned/erk/slot-pool-architecture.md`

**Frontmatter:**
```yaml
---
title: Slot Pool Architecture
read_when:
  - "working with worktree slots"
  - "adding slot-related commands"
  - "understanding pool state"
  - "implementing branch/worktree deletion"
---
```

**Content sections:**

1. **Overview** - What slots are (pre-allocated reusable worktrees for fast branch switching)

2. **Data Structures** (in `core/worktree_pool.py`):
   - `SlotInfo` - initialized slot metadata
   - `SlotAssignment` - links branch to slot
   - `PoolState` - complete pool state (slots + assignments)
   - Persistence: `~/.erk/repos/<repo>/pool.json`

3. **Naming Conventions**:
   - Slot names: `erk-managed-wt-XX` (e.g., `erk-managed-wt-01`)
   - Placeholder branches: `__erk-slot-XX-placeholder__`
   - Default pool size: 4

4. **Lifecycle Diagram**:
   ```
   uninitialized → assigned → active → unassigned (kept) → reused
   ```

5. **Key Helper Functions** (in `slot/common.py`):
   - `find_branch_assignment(state, branch)` - check if branch is in a slot
   - `find_inactive_slot(state, git, repo_root)` - find unassigned slot for reuse
   - `find_next_available_slot(state, worktrees_dir)` - find slot to create
   - `find_oldest_assignment(state)` - for pool-full eviction
   - `handle_pool_full_interactive()` - prompt to unassign oldest
   - `cleanup_worktree_artifacts()` - clean .impl/ and .erk/scratch/ before reuse

6. **Slot Unassignment** (in `slot/unassign_cmd.py`):
   - `execute_unassign()` - core logic for unassigning a slot
   - Checks for uncommitted changes
   - Switches to placeholder branch
   - Removes assignment from pool state (keeps worktree dir)

7. **Slot vs Vanilla Worktree Detection**:
   - Use `find_assignment_by_worktree_path()` from `navigation_helpers.py`
   - Slot: assignment exists in pool state
   - Vanilla: worktree exists but no assignment

8. **Related Files Quick Reference**:
   | Purpose | File |
   |---------|------|
   | Data structures | `core/worktree_pool.py` |
   | Helper functions | `cli/commands/slot/common.py` |
   | Unassign logic | `cli/commands/slot/unassign_cmd.py` |
   | Slot detection | `cli/commands/navigation_helpers.py` |
   | Worktree utilities | `core/worktree_utils.py` |

## Implementation Notes

- Follow existing doc patterns in `docs/learned/erk/`
- Include code snippets for common patterns
- Add tripwire if needed (e.g., "Before modifying pool state...")
- Update `docs/learned/index.md` if needed (auto-generated, may need manual entry)