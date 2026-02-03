---
title: Gateway Removal Pattern
tripwires:
  - action: "deleting a gateway after consolidating into another"
    warning: "Follow complete removal checklist: verify no references, delete all 5 layers, clean up ErkContext, update docs, run full test suite."
read_when:
  - "Consolidating two gateways into one"
  - "Removing deprecated gateway implementations"
  - "Refactoring gateway hierarchies"
---

# Gateway Removal Pattern

## Overview

After consolidating two gateway abstractions into one (e.g., merging ClaudeExecutor into PromptExecutor), the old gateway should be deleted completely. This document describes when to delete a gateway and the complete removal checklist.

## When to Delete a Gateway

Delete a gateway after consolidation when:

1. **All callers migrated** - No code imports or uses the old gateway
2. **Functionality merged** - The new gateway provides all old gateway capabilities
3. **Tests migrated** - Old gateway's test coverage moved to new gateway tests
4. **No backward compatibility needed** - Erk is unreleased software, no external users

## Complete Removal Checklist

### 1. Verify No Remaining References

Search the entire codebase for imports and usages:

```bash
# Check for imports
rg "from.*OldGateway|import.*OldGateway"

# Check for type annotations
rg ":\s*OldGateway"

# Check for instantiation
rg "OldGateway\("
```

All searches should return **zero results** before proceeding.

### 2. Delete Gateway Implementation Files

Remove all 5 implementation layers:

- `src/erk/gateway/old_gateway/abc.py` - ABC layer
- `src/erk/gateway/old_gateway/real.py` - Real implementation
- `src/erk/gateway/old_gateway/fake.py` - Fake for testing
- `src/erk/gateway/old_gateway/dry_run.py` - DryRun wrapper
- `src/erk/gateway/old_gateway/printing.py` - Printing wrapper

Delete the entire directory:

```bash
git rm -rf src/erk/gateway/old_gateway/
```

### 3. Delete Gateway Tests

Remove corresponding test files:

```bash
git rm -rf tests/unit/gateway/old_gateway/
```

**IMPORTANT**: Verify the new gateway's tests provide equivalent coverage. Do not delete tests without migrating their coverage.

### 4. Clean Up ErkContext

Remove gateway property from ErkContext:

1. **Delete property from ErkContext ABC** (if it exists as a direct property)
2. **Remove from RealErkContext construction**
3. **Remove from FakeErkContext**
4. **Remove from DryRunErkContext wrapper**
5. **Remove from PrintingErkContext wrapper**

If the gateway was accessed through a subgateway pattern (e.g., `ctx.some_parent.old_gateway`), delete the property from the parent gateway instead.

### 5. Update Documentation

- [ ] Remove gateway from architecture docs
- [ ] Update migration guides if the removal affects user workflows
- [ ] Add entry to CHANGELOG documenting the removal

### 6. Run Full Test Suite

```bash
make test-unit
make test-integration
```

All tests must pass. Any failures indicate missed references.

## Example: PromptExecutor Consolidation (PR #6587)

The ClaudeExecutor gateway was merged into PromptExecutor. The removal process:

1. **Migration phase** - All callers updated to use PromptExecutor
2. **Verification** - Grepped for ClaudeExecutor, found zero references
3. **Deletion** - Removed `src/erk/gateway/claude_executor/` directory
4. **Test cleanup** - Removed `tests/unit/gateway/claude_executor/`
5. **Context update** - Removed `claude_executor` property from ErkContext
6. **Test run** - `make test-unit` passed with zero failures

## Why Complete Deletion?

### No Backward Compatibility in Erk

Erk is unreleased, completely private software. There are no external users to support. When code is deprecated:

- **Delete it immediately** - No deprecation warnings or shims
- **Break callers** - Migration is mandatory, not optional
- **No legacy support** - The old code ceases to exist

### Benefits of Complete Removal

1. **Zero maintenance burden** - No legacy code to update
2. **Clear codebase** - One way to do each operation
3. **Faster iteration** - No need to maintain parallel implementations
4. **Simpler tests** - No testing deprecated paths

## Anti-Patterns

**Keeping "just the ABC"** - Deleting implementations but leaving the ABC "for reference"

- **Problem:** Creates dead code that confuses future developers
- **Fix:** Delete the entire gateway, including the ABC

**Leaving empty directories** - Removing files but not the directory structure

- **Problem:** Empty `__init__.py` files clutter the package
- **Fix:** Use `git rm -rf` to remove the directory entirely

**Commenting out code** - Leaving old code as comments "in case we need it"

- **Problem:** Git history already preserves the old code
- **Fix:** Delete completely and rely on git for archaeology

## Related Documentation

- [Gateway ABC Implementation](gateway-abc-implementation.md) - Full 5-layer gateway pattern
- [Flatten Subgateway Pattern](flatten-subgateway-pattern.md) - How subgateways are exposed
- [LibCST Systematic Imports](../refactoring/libcst-systematic-imports.md) - Batch migration tooling
