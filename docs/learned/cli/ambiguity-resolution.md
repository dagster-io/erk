---
title: Ambiguity Resolution Pattern for CLI Commands
read_when:
  - "implementing CLI commands that accept identifiers with multiple possible matches"
  - "designing CLI behavior for ambiguous input"
  - "displaying tables of options without interactive selection"
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
    user_output(f"Multiple branches found for plan #{issue_number}:\n")

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
        f"No local branch or open PR found for plan #{issue_number}\n\n"
        "This plan has not been implemented yet. To implement it:\n"
        f"  • Run: erk implement {issue_number}"
    )
    raise SystemExit(1)  # Exit code 1: actual error condition
```

## Implementation Example

The `erk plan co` command demonstrates all three cases:

```python
# src/erk/cli/commands/plan/checkout_cmd.py

# Case 1: Single local branch found
if len(local_branches) == 1:
    branch_name = local_branches[0]
    _checkout_branch(ctx, repo, branch_name=branch_name, ...)
    return

# Case 2: Multiple local branches found
if len(local_branches) > 1:
    _display_multiple_branches(issue_number, local_branches)
    raise SystemExit(0)

# Case 3: No local branches - check for PRs
prs = ctx.issues.get_prs_referencing_issue(repo.root, issue_number)
open_prs = [pr for pr in prs if pr.state == "OPEN"]

if len(open_prs) == 0:
    user_output(f"No local branch or open PR found for plan #{issue_number}...")
    raise SystemExit(1)

if len(open_prs) == 1:
    _checkout_pr(ctx, repo, pr_number=open_prs[0].number, ...)
    return

# Multiple PRs
_display_multiple_prs(issue_number, open_prs)
raise SystemExit(0)
```

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
- [List Formatting](list-formatting.md) - Table display patterns
