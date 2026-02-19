---
title: Display String Terminology
read_when:
  - "adding new TUI status messages or display strings"
  - "writing user-facing text in TUI widgets"
  - "creating command display name generators"
tripwires:
  - action: "using 'issue' terminology in TUI display strings"
    warning: "Use 'plan' terminology (not 'issue') to maintain consistency with backend-agnostic naming. Examples: 'Opened plan #123' (not 'Opened issue #123'), 'by plan#' sort label (not 'by issue#'), info row label 'Plan' (not 'Issue')."
---

# Display String Terminology

TUI display strings use backend-agnostic plan terminology.

## Correct Terminology

| Context         | Correct            | Incorrect           |
| --------------- | ------------------ | ------------------- |
| Opening a plan  | "Opened plan #123" | "Opened issue #123" |
| Sort labels     | "by plan#"         | "by issue#"         |
| Info row labels | "Plan"             | "Issue"             |
| Command names   | "Open plan"        | "Open issue"        |

## Display Name Generators

Display name generators in the command registry reference plan data using backend-agnostic field names:

```python
def _display_name_generator(ctx: CommandContext) -> str:
    return f"Open plan #{ctx.row.plan_id}"  # Not issue_number
```

## Field References

Use these field names in display generators:

- `ctx.row.plan_id` (not `ctx.row.issue_number`)
- `ctx.row.plan_url` (not `ctx.row.issue_url`)

See display name generators in `src/erk/tui/commands/registry.py`.
