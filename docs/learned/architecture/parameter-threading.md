---
title: Parameter Threading Pattern
read_when:
  - "adding a parameter to a function used in many places"
  - "threading a new field through multiple layers"
  - "updating function signatures across codebase"
---

# Parameter Threading Pattern

When adding a new parameter to a function that's called from multiple places, you must systematically update all callers.

## The Challenge

Adding a parameter to a widely-used function creates a cascade of changes:

1. The function signature changes
2. All direct callers must be updated
3. Wrapper functions must thread the parameter through
4. Tests that call any of these functions must be updated

Missing any caller results in runtime errors.

## Update Order

Follow this order to minimize iteration:

1. **Core function** - Add parameter to the function being changed
2. **Intermediate functions** - Add parameter to any wrappers/helpers that call it
3. **Callers** - Update all places that call the function(s)
4. **Tests** - Update all test files that call any modified function

## Finding All Callers

```bash
# Find function definition
rg "def create_plan_issue"

# Find all calls (including in tests)
rg "create_plan_issue\(" --type py

# Include test files explicitly
rg "create_plan_issue\(" tests/
```

## Common Mistakes

### Forgetting Test Files

Tests that call modified functions will fail with unexpected keyword argument errors. Always search `tests/` directory:

```bash
rg "function_name\(" tests/
```

### Missing Wrapper Functions

If function A calls function B, and you add a parameter to B, you often need to add the same parameter to A so callers can pass it through.

### Incorrect Default Values

When adding optional parameters, consider:

- Should the parameter be required or optional?
- What's the appropriate default for existing callers?
- Does the default maintain backwards compatibility?

## Checklist

When adding a parameter to a widely-used function:

- [ ] Update function signature with new parameter
- [ ] Update docstring to document the parameter
- [ ] Update all direct callers in production code
- [ ] Update all wrapper/helper functions
- [ ] Update all test files that call any modified function
- [ ] Run full test suite to catch missed callers
- [ ] Run type checker (`ty check`) to catch type mismatches

## Example: Adding created_from_session

The `created_from_session` parameter was added to track which Claude session created a plan. This required updates across multiple files:

1. `create_plan_issue()` function signature
2. `save_plan_to_issue()` wrapper function
3. CLI command that calls `save_plan_to_issue()`
4. Multiple test files that created plan issues

## Type Checker as Safety Net

Running the type checker after signature changes catches missed callers:

```bash
ty check
```

Type errors like "unexpected keyword argument" indicate callers that haven't been updated.

## Related Topics

- [Gateway ABC Implementation](gateway-abc-implementation.md) - Multi-file updates for gateway methods
