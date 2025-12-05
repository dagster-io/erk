---
completed_steps: 0
steps:
- completed: false
  text: 1. .impl/issue.json (explicit issue reference)
- completed: false
  text: '2. Branch name parsing (convention: {issue_number}-{slug}-{date})'
- completed: false
  text: 1. `packages/erk-shared/src/erk_shared/naming.py` - Add `parse_issue_number_from_branch()`
- completed: false
  text: 2. `packages/erk-shared/src/erk_shared/impl_folder.py` - Add `resolve_issue_number()`
- completed: false
  text: 3. `packages/erk-shared/src/erk_shared/integrations/gt/operations/preflight.py`
    - Use shared resolution
- completed: false
  text: 4. `packages/erk-shared/src/erk_shared/integrations/gt/operations/finalize.py`
    - Use shared resolution
- completed: false
  text: 5. Tests for both new functions
total_steps: 7
---

# Progress Tracking

- [ ] 1. .impl/issue.json (explicit issue reference)
- [ ] 2. Branch name parsing (convention: {issue_number}-{slug}-{date})
- [ ] 1. `packages/erk-shared/src/erk_shared/naming.py` - Add `parse_issue_number_from_branch()`
- [ ] 2. `packages/erk-shared/src/erk_shared/impl_folder.py` - Add `resolve_issue_number()`
- [ ] 3. `packages/erk-shared/src/erk_shared/integrations/gt/operations/preflight.py` - Use shared resolution
- [ ] 4. `packages/erk-shared/src/erk_shared/integrations/gt/operations/finalize.py` - Use shared resolution
- [ ] 5. Tests for both new functions