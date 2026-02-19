---
title: Context-Preserved Naming in Plan Formats
read_when:
  - "renaming issue_* to plan_* in TUI layer"
  - "working with .impl/issue.json format"
  - "understanding which fields to rename vs preserve"
tripwires:
  - action: "renaming issue_* fields in .impl/issue.json or plan header YAML"
    warning: "Preserve issue_* in: .impl/issue.json format, plan header YAML issue_number, learn fields (learn_plan_issue, objective_issue). These formats represent the underlying GitHub data model, not the TUI's plan abstraction."
---

# Context-Preserved Naming in Plan Formats

When renaming `issue_*` -> `plan_*` in the TUI layer, some fields must be preserved.

## What to Rename (TUI Layer)

- `PlanRowData.issue_number` -> `plan_id`
- Display strings ("Opened issue #" -> "Opened plan #")
- Method parameters in data providers

## What to Preserve (File Formats)

- `.impl/issue.json` field names
- Plan header YAML fields (`issue_number:`)
- Learn issue metadata fields

## Why the Distinction

These formats represent the underlying GitHub data model, not the TUI's plan abstraction. The TUI uses `plan_id` but the persisted data still refers to GitHub issues.

## Related Documentation

- [Scope Discipline in Renames](../refactoring/scope-discipline.md) — TUI vs API layer boundaries
