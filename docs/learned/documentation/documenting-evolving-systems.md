---
title: Documenting Evolving Systems
read_when:
  - "writing documentation during a migration"
  - "auditing docs after a migration completes"
  - "documentation references features that were recently changed or removed"
tripwires:
  - action: "writing documentation during an active migration without marking transitional state"
    warning: "Documentation written during migration captures transitional state. Mark with status (pre-migration, transitional, post-migration) and audit after migration completes."
    score: 5
---

# Documenting Evolving Systems

Documentation written during migrations captures transitional state that becomes stale quickly. This pattern prevents documentation drift during system evolution.

## The Problem

When a system is actively being migrated (e.g., renaming APIs, changing storage formats, removing features), documentation written during the migration may reference:

- Old names alongside new names (for "backwards compatibility")
- Intermediate states that exist only during the migration
- Fallback paths that will be removed once migration completes

This documentation becomes actively misleading once the migration finishes.

## Case Study: issue.json to plan-ref.json Migration

The `.erk/impl-context/issue.json` format was being replaced by `plan-ref.json`. During the migration:

1. Documentation was written describing the three-level fallback: `plan-ref.json` -> `ref.json` -> `issue.json`
2. PR #8388 removed `issue.json` support entirely, one day after the docs were written
3. All "legacy fallback" documentation became stale immediately

## Pattern: Status-Marked Documentation

When writing docs during a migration, mark the document's migration status:

```yaml
---
title: Feature X Migration
migration_status: transitional # pre-migration | transitional | post-migration
migration_target: "PR #1234" # The PR that completes the migration
---
```

### Status Definitions

| Status           | Meaning                             | Action                         |
| ---------------- | ----------------------------------- | ------------------------------ |
| `pre-migration`  | Written before migration starts     | Update when migration begins   |
| `transitional`   | Describes both old and new behavior | Audit when migration completes |
| `post-migration` | Describes only the final state      | No action needed               |

## Rule: Post-Migration Audit

After a migration completes, audit all docs written during the migration for stale references:

```bash
# Find docs that might reference the migrated feature
grep -r "old_name\|OldName\|old-name" docs/learned/
```

Remove or update:

- References to removed fallback paths
- "Legacy" sections that no longer apply
- Backwards compatibility notes for removed features

## Related Documentation

- [Feature Removal Checklist](../refactoring/feature-removal-checklist.md) — Checklist for complete feature removal
