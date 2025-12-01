---
completed_steps: 0
steps:
- completed: false
  text: 1. Local worktrees (scanned via `.impl/issue.json`)
- completed: false
  text: 2. `worktree_name` field in plan-header metadata (issue body)
- completed: false
  text: 1. After successfully creating/using a branch, call `update_plan_header_worktree_name()`
    to store the branch name
- completed: false
  text: 2. This ensures every submitted plan has a worktree-like name stored in the
    issue body
- completed: false
  text: 1. Parse the existing plan-header from the issue body
- completed: false
  text: 2. Update only the `worktree_name` field
- completed: false
  text: 3. Return the updated issue body
- completed: false
  text: 1. `src/erk/cli/commands/submit.py` - Store branch name in plan-header
- completed: false
  text: 2. `packages/erk-shared/src/erk_shared/github/metadata.py` - Add update function
- completed: false
  text: 3. `src/erk/cli/commands/plan/list_cmd.py` - Update column name and display
    logic
- completed: false
  text: 4. `src/erk/integrations/github/abc.py` - Add ABC method (if needed)
- completed: false
  text: 5. `src/erk/integrations/github/service.py` - Implement update method
- completed: false
  text: 6. `tests/commands/test_dash.py` - Update tests
- completed: false
  text: 7. `tests/commands/test_submit.py` - Add tests
total_steps: 14
---

# Progress Tracking

- [ ] 1. Local worktrees (scanned via `.impl/issue.json`)
- [ ] 2. `worktree_name` field in plan-header metadata (issue body)
- [ ] 1. After successfully creating/using a branch, call `update_plan_header_worktree_name()` to store the branch name
- [ ] 2. This ensures every submitted plan has a worktree-like name stored in the issue body
- [ ] 1. Parse the existing plan-header from the issue body
- [ ] 2. Update only the `worktree_name` field
- [ ] 3. Return the updated issue body
- [ ] 1. `src/erk/cli/commands/submit.py` - Store branch name in plan-header
- [ ] 2. `packages/erk-shared/src/erk_shared/github/metadata.py` - Add update function
- [ ] 3. `src/erk/cli/commands/plan/list_cmd.py` - Update column name and display logic
- [ ] 4. `src/erk/integrations/github/abc.py` - Add ABC method (if needed)
- [ ] 5. `src/erk/integrations/github/service.py` - Implement update method
- [ ] 6. `tests/commands/test_dash.py` - Update tests
- [ ] 7. `tests/commands/test_submit.py` - Add tests