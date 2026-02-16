---
title: Post-Mutation Validation
read_when:
  - "creating commands that modify objectives"
  - "implementing inference-driven updates"
  - "debugging objective corruption"
tripwires:
  - action: "creating or modifying command that mutates objective state"
    warning: "MUST call erk objective check at the end, especially if mutation uses inference."
---

# Post-Mutation Validation

## Requirement

Commands that mutate objective state MUST call `erk objective check` after mutation.

## Why It Matters

Inference-driven mutations (like reconciliation in `objective-update-with-landed-pr`) are error-prone:

- Wrong status derivation
- Inconsistent PR/plan cells
- Format corruption

## Pattern

After any mutation operation, run validation:

```bash
erk objective check <issue-number> --json-output --allow-legacy
```

Use `--allow-legacy` when working with pre-migration objectives.

## Examples

See `/erk:objective-update-with-landed-pr` step 7 for the validation pattern.

## Related Documentation

- [Validation Patterns](validation-patterns.md) — When to use allow_legacy
- [Roadmap Mutation Patterns](roadmap-mutation-patterns.md) — Surgical vs full-body updates
