# Documentation Plan: Add ID Field Naming Convention

## Context

**Source:** PR #5083 review comment - reviewer explicitly stated: "if it is an int or int | None it should have an id suffix"

**Raw Materials:** https://gist.github.com/schrockn/bffd5763a433adb21a5c7a459914b9c0

## Documentation Item

**Location:** `docs/learned/conventions.md`
**Action:** Add new section after "Code Naming" table

### Content to Add

```markdown
## Variable Naming by Type

| Type | Convention | Example |
|------|------------|---------|
| Issue numbers (`int`) | `_id` suffix | `objective_id`, `plan_id` |
| Issue objects | No suffix or `_issue` | `objective`, `plan_issue` |
| String identifiers | `_identifier` or `_name` | `plan_identifier`, `branch_name` |

**Rationale:** When a variable holds an integer ID (like a GitHub issue number), the `_id` suffix makes the type immediately clear. This distinguishes `objective_id: int` (an issue number) from `objective: ObjectiveInfo` (an object).
```

## Verification

1. Read the updated file to confirm formatting
2. Ensure table renders correctly in markdown preview