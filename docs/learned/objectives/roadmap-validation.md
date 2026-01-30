---
title: Roadmap Validation Rules
read_when:
  - "debugging roadmap validation errors"
  - "understanding what the roadmap parser validates"
  - "adding new validation rules to the roadmap parser"
tripwires:
  - action: "modifying roadmap validation without updating this document"
    warning: "Keep this document in sync with validation logic in objective_roadmap_shared.py and objective_roadmap_update.py."
---

# Roadmap Validation Rules

The roadmap parser and update command validate roadmap content at two levels: structural validation (during parsing) and semantic validation (during updates).

## Structural Validation (Parser)

Performed by `parse_roadmap()` in `objective_roadmap_shared.py`:

| Rule                | Severity | Description                                                              |
| ------------------- | -------- | ------------------------------------------------------------------------ | ---- | ----------- | ------ | --- | --------------------------- |
| Phase header format | Warning  | Must match `### Phase N: Name` pattern                                   |
| Table structure     | Warning  | Must have `                                                              | Step | Description | Status | PR  | ` header with separator row |
| Row format          | Warning  | Each row must match `                                                    | id   | desc        | status | pr  | ` pattern                   |
| Step ID format      | Warning  | Letter-format IDs (e.g., `1A.1`) emit a warning; plain numbers preferred |

Validation warnings are collected and returned alongside parsed data — parsing continues even with warnings.

## Semantic Validation (Update Command)

Performed by `objective_roadmap_update.py`:

| Rule                       | Lines   | Check                                                   |
| -------------------------- | ------- | ------------------------------------------------------- |
| At least one flag required | 142–145 | `--status` or `--pr` must be provided                   |
| Issue exists               | 159     | `isinstance(issue, IssueNotFound)` check                |
| Roadmap parseable          | 172     | `if not phases:` — at least one phase must exist        |
| Step ID found              | 186     | `if updated_body is None:` — step must exist in roadmap |
| Post-update validation     | 195–210 | Re-parses after update to verify consistency            |

## Error Categories

| Category       | Example                    | Handling                                                                                                    |
| -------------- | -------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Missing issue  | Issue #999 not found       | Error response, exit 1                                                                                      |
| Empty roadmap  | No phases parsed from body | Error response, exit 1                                                                                      |
| Step not found | Step 9.9 doesn't exist     | Error response, exit 1                                                                                      |
| Stale status   | "blocked" after PR added   | Prevented by status reset (see [Roadmap Mutation Semantics](../architecture/roadmap-mutation-semantics.md)) |

## LBYL Pattern

All validation uses LBYL — conditions are checked before operations:

```python
# Check issue exists before accessing fields
if isinstance(issue, IssueNotFound):
    return error_response(...)

# Check phases exist before iterating
if not phases:
    return error_response(...)

# Check update succeeded before re-validating
if updated_body is None:
    return error_response(...)
```

## Source Locations

- Parser validation: `src/erk/cli/commands/exec/scripts/objective_roadmap_shared.py:70-84`
- Update validation: `src/erk/cli/commands/exec/scripts/objective_roadmap_update.py:142-182`

## Related Documentation

- [Roadmap Parser](roadmap-parser.md) — Parser usage and inference rules
- [Roadmap Parser API Reference](roadmap-parser-api.md) — Function signatures and types
