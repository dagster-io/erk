---
title: Command Deletion Patterns
read_when:
  - "deleting a CLI command or command group"
  - "removing dead code after a feature deletion"
  - "identifying vestigial features for removal"
tripwires:
  - action: "deleting a CLI command without checking integration tests"
    warning: "Grep tests/integration/ before deleting gateway methods used by the command. Integration tests may directly exercise the deleted method."
  - action: "removing a command without checking docs/learned/ for references"
    warning: "Run the post-refactoring documentation audit (post-refactor-documentation-audit.md) after any command deletion."
---

# Command Deletion Patterns

Patterns for safely deleting CLI commands, command groups, and associated dead code. Based on real deletions including `erk pr sync` (PR #8245, 373 lines) and dead type cleanup (PR #8254, 6 types × 3 variants).

## 4-Phase Deletion

### Phase 1: File Removal

Remove the command file and any command-specific modules:

```bash
git rm src/erk/cli/commands/pr/sync_cmd.py
```

### Phase 2: Registration Removal

Remove the command registration from the group's `__init__.py`:

```python
# In src/erk/cli/commands/pr/__init__.py
# Remove: pr_group.add_command(sync_cmd)
```

### Phase 3: Documentation Updates

Run the [Post-Refactoring Documentation Audit](../refactoring/post-refactor-documentation-audit.md):

1. `grep -r "erk pr sync" docs/learned/` — Find stale command references
2. Update glossary if the command had an entry
3. Update command-organization.md if affected
4. Run `erk docs sync`

### Phase 4: Verification

```bash
# Verify no remaining references
grep -r "sync_cmd\|erk pr sync" src/ tests/ docs/
```

## Dead Type Cleanup: Multiplicative Pattern

When a type is deleted, its variants multiply the cleanup:

```
N types × M variants = total deletions
```

Example from PR #8254: 6 types × 3 variants (type, import, test reference) = 18 individual deletions.

Search systematically:

```bash
# For each deleted type
grep -r "SyncResult\|SyncError\|SyncState" src/ tests/
```

## Vestigial Feature Detection

A feature is vestigial when three signals align:

1. **Docstring admits redundancy**: "This is now handled by X"
2. **Zero programmatic invocations**: No code calls the function/command
3. **Documentation lists alternatives**: Docs say "use X instead"

When all three signals are present, the feature is safe to delete.

## Integration Test Co-Evolution

Before deleting a gateway method:

```bash
grep -r "deleted_method_name" tests/integration/
```

Integration tests may directly exercise methods that unit tests access through commands. Deleting the method without updating integration tests causes CI failures.

## Related Documentation

- [Post-Refactoring Documentation Audit](../refactoring/post-refactor-documentation-audit.md) — 5-step documentation cleanup checklist
- [Feature Removal Checklist](../refactoring/feature-removal-checklist.md) — Complete feature removal process
- [Incomplete Command Removal Pattern](incomplete-command-removal.md) — Common mistakes in command removal
