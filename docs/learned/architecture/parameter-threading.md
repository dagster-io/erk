---
title: Parameter Threading Pattern
read_when:
  - "adding a parameter to a function used in many places"
  - "threading a new field through multiple layers"
  - "updating function signatures across codebase"
---

# Parameter Threading Pattern

When adding a new parameter to a function that's called from multiple places, you must systematically update all callers.

## Example: Adding created_from_session to Plan Issues

The `created_from_session` parameter was added to track which session created a plan. This required updates across 5+ files.

### Update Order

1. **Core function** - Add parameter to the function being changed
2. **Intermediate functions** - Add parameter to any wrappers
3. **Callers** - Update all places that call the function
4. **Tests** - Update all test files that call the function

### Finding All Callers

```bash
# Find function definition
rg "def create_plan_issue"

# Find all calls
rg "create_plan_issue\(" --type py
```

### Common Mistake

Forgetting to update test files. Tests that call the modified function will fail with unexpected keyword argument errors.

### Checklist

- [ ] Update function signature with new parameter
- [ ] Update docstring
- [ ] Update all direct callers
- [ ] Update all wrapper functions
- [ ] Update all test files
- [ ] Run full test suite to catch any missed callers
