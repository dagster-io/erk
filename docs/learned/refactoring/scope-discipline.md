---
title: Scope Discipline in Renames
read_when:
  - "renaming fields that appear in multiple layers"
  - "distinguishing TUI changes from API changes"
  - "avoiding over-renaming during bulk refactors"
---

# Scope Discipline in Renames

When renaming domain terms (like `issue_number`), distinguish semantic domains.

## TUI Layer (Should Rename)

- `PlanRowData` fields — these are TUI abstractions
- Display strings and user-facing messages
- TUI widget field references
- Data provider method parameters (ABC interface)

## API Layer (Should NOT Rename)

- GitHub API response parsing
- `.impl/issue.json` file format
- Plan header YAML fields
- Anything that maps directly to external API field names

## How to Identify

Use grep to distinguish consumers from producers:

```bash
# TUI layer files (should rename)
rg "issue_number" src/erk/tui/

# API layer files (should NOT rename)
rg "issue_number" src/erk/gateway/github/  # GitHub API mapping
```

## The PR #7473 Example

Renamed in TUI layer:

- `PlanRowData.issue_number` -> `plan_id`
- `SortKey.ISSUE_NUMBER` -> `PLAN_ID`
- Display strings "Opened issue #" -> "Opened plan #"

Preserved in API layer:

- `.impl/issue.json` field names
- Plan header YAML `issue_number:` field

## Related Documentation

- [Bulk Rename Scope Verification](bulk-rename-scope-verification.md) — verifying only expected files changed
- [Systematic Terminology Renames](systematic-terminology-renames.md) — three-phase rename workflow
