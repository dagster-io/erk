---
completed_steps: 0
steps:
  - completed: false
    text:
      '1. **Line 16**: `_SAFE_COMPONENT_RE = re.compile(r"[^A-Za-z0-9._/-]+")` -
      allows `.`'
  - completed: false
    text:
      "2. **Line 106**: `sanitize_worktree_name()` uses `[^a-z0-9.-]+` - explicitly
      allows `.`"
  - completed: false
    text:
      "3. **Line 147**: `sanitize_branch_component()` uses `_SAFE_COMPONENT_RE`
      - allows `.`"
  - completed: false
    text: "1. **Line 16**: Update `_SAFE_COMPONENT_RE` pattern"
  - completed: false
    text: "2. **Line 106**: Update `sanitize_worktree_name()` regex"
  - completed: false
    text: "3. **Update docstrings**: Change `[A-Za-z0-9.-]` → `[A-Za-z0-9-]` in:"
  - completed: false
    text: 1. `packages/erk-shared/src/erk_shared/naming.py` - Core fix
  - completed: false
    text: 2. `tests/core/utils/test_naming.py` - Add test cases
total_steps: 8
---

# Progress Tracking

- [ ] 1. **Line 16**: `_SAFE_COMPONENT_RE = re.compile(r"[^A-Za-z0-9._/-]+")` - allows `.`
- [ ] 2. **Line 106**: `sanitize_worktree_name()` uses `[^a-z0-9.-]+` - explicitly allows `.`
- [ ] 3. **Line 147**: `sanitize_branch_component()` uses `_SAFE_COMPONENT_RE` - allows `.`
- [ ] 1. **Line 16**: Update `_SAFE_COMPONENT_RE` pattern
- [ ] 2. **Line 106**: Update `sanitize_worktree_name()` regex
- [ ] 3. **Update docstrings**: Change `[A-Za-z0-9.-]` → `[A-Za-z0-9-]` in:
- [ ] 1. `packages/erk-shared/src/erk_shared/naming.py` - Core fix
- [ ] 2. `tests/core/utils/test_naming.py` - Add test cases
