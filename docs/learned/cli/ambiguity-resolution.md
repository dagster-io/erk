---
title: Ambiguity Resolution Pattern for CLI Commands
read_when:
  - "implementing CLI commands that accept identifiers with multiple possible matches"
  - "designing CLI behavior for ambiguous input"
  - "displaying tables of options without interactive selection"
last_audited: "2026-02-17 00:00 PT"
audit_result: clean
---

# Ambiguity Resolution Pattern

When a CLI command accepts an identifier that may match zero, one, or multiple results, use the "single → table → error" pattern for consistent user experience.

## Pattern Overview

```
┌─────────────────┐
│   Parse Input   │──► Validate identifier format
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Find Matches  │──► Search for matching resources
└────────┬────────┘
         │
    ┌────┴────┬─────────┐
    │         │         │
    ▼         ▼         ▼
 Single    Multiple    Zero
 Match     Matches    Matches
    │         │         │
    ▼         ▼         ▼
 Execute   Display    Display
Immediately  Table     Error
```

## Behavior Rules

### Single Match: Execute Immediately

When exactly one resource matches, act without prompting:

```python
if len(matches) == 1:
    # Act immediately
    checkout_branch(matches[0])
    return
```

### Multiple Matches: Display Table, Exit

When multiple resources match, show a table and exit. Do NOT prompt for selection (erk CLI is non-interactive by design):

```python
if len(matches) > 1:
    user_output(f"Multiple branches found for plan #{plan_number}:\n")

    table = Table(show_header=True, header_style="bold")
    table.add_column("branch", style="yellow", no_wrap=True)

    for branch in sorted(matches):
        table.add_row(branch)

    console = Console(stderr=True)
    console.print(table)

    # Guide user to be more specific
    user_output(
        "Use a more specific command:\n"
        "  • erk wt create <branch-name>"
    )
    raise SystemExit(0)  # Exit code 0: informational, not an error
```

### Zero Matches: Display Helpful Error

When no resources match, explain what was searched and suggest alternatives:

```python
if len(matches) == 0:
    user_output(
        f"No local branch or open PR found for plan #{plan_number}\n\n"
        "This plan has not been implemented yet. To implement it:\n"
        f"  • Run: erk implement {plan_number}"
    )
    raise SystemExit(1)  # Exit code 1: actual error condition
```

## Implementation Example

<!-- Source: src/erk/cli/commands/pr/checkout_cmd.py, _checkout_plan -->

The `erk pr co` command demonstrates all three cases. See `_checkout_plan()` in `src/erk/cli/commands/pr/checkout_cmd.py`: queries open PRs referencing the issue via `ctx.issues.get_prs_referencing_issue()`, then dispatches on zero (exit 1), one (checkout immediately), or multiple (display table, exit 0).

## Exit Codes

| Condition                      | Exit Code | Rationale                           |
| ------------------------------ | --------- | ----------------------------------- |
| Single match (success)         | 0         | Operation completed                 |
| Multiple matches (table shown) | 0         | Informational, user can refine      |
| Zero matches (error)           | 1         | Nothing to do, user action required |

## Key Principles

1. **No interactive prompts:** Erk CLI commands don't prompt for input (except explicit confirmation flows)
2. **Guide to specificity:** When showing multiple options, tell users which command to use with a specific value
3. **Fail early, fail clearly:** Validate input format before searching for matches
4. **Rich tables for lists:** Use `rich.table.Table` for consistent formatting

## Anti-Patterns

### Don't: Use Interactive Selection

```python
# BAD - erk CLI is non-interactive
choice = questionary.select("Choose a branch:", choices=branches).ask()
```

### Don't: Pick Arbitrarily

```python
# BAD - confusing behavior
if len(matches) > 1:
    # Just use the first one... user won't know why
    return matches[0]
```

### Don't: Error on Multiple Matches

```python
# BAD - unhelpful
if len(matches) > 1:
    raise SystemExit("Error: ambiguous input")
```

## Related Documentation

- [GitHub URL Parsing](../architecture/github-parsing.md) - Input parsing patterns
- [Output Styling](output-styling.md) - Console output conventions
