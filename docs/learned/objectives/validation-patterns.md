---
title: Caller-Specific Legacy Handling
read_when:
  - "implementing commands that touch objectives"
  - "choosing validation strictness"
  - "debugging legacy format errors"
---

# Caller-Specific Legacy Handling

## Decision Framework

| Operation Type | `allow_legacy` | Rationale                          |
| -------------- | -------------- | ---------------------------------- |
| Read-only      | `True`         | Must work with existing data       |
| Write (new)    | `False`        | Enforce new format for new content |
| Update         | N/A            | Auto-migrates on write, skip check |

## Examples

- `objective-next-plan` (read-only) → `--allow-legacy` required
- `objective-create` (write) → strict validation
- `update-roadmap-step` (update) → format preserved, no explicit check needed

## Implementation

See the `allow_legacy` parameter on `validate_objective()` in `src/erk/cli/commands/objective/check_cmd.py`.

## Related Documentation

- [Check 8: Roadmap Block Format](validation-checks.md) — What Check 8 validates
- [Post-Mutation Validation](mutation-patterns.md) — When validation is required
