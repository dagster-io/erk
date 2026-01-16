# Plan: Update BranchManager gateway-inventory documentation

## Summary

Update the BranchManager "Key Methods" section in `docs/learned/architecture/gateway-inventory.md` to include all current methods that were added in plan #4963.

## Implementation Steps

1. Read `docs/learned/architecture/gateway-inventory.md` to see current state
2. Update the BranchManager "Key Methods" section to include:
   - `get_parent_branch()`: Get parent branch (Graphite) or None (Git)
   - `get_child_branches()`: Get child branches (Graphite) or empty list (Git)
   - `delete_branch()`: Delete branch with mode-appropriate cleanup
   - `submit_branch()`: Push branch to remote (git push or gt submit)
   - `get_branch_stack()`: Get full stack for a branch (Graphite) or None (Git)
   - `track_branch()`: Register branch with parent (Graphite) or no-op (Git)

## Files to Modify

- `docs/learned/architecture/gateway-inventory.md`

## Verification

- Read the updated file to confirm changes are correct
- Run `erk docs sync` if needed to update any auto-generated content