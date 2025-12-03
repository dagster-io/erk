---
title: CLI Output Styling Guide
read_when:
  - "styling CLI output"
  - "using colors in CLI"
  - "formatting terminal output"
---

# CLI Output Styling Guide

This guide defines the standard color scheme, emoji conventions, and output abstraction patterns for erk CLI commands.

## Color Conventions

Use consistent colors and styling for CLI output via `click.style()`:

| Element                  | Color            | Bold | Example                                             |
| ------------------------ | ---------------- | ---- | --------------------------------------------------- |
| Branch names             | `yellow`         | No   | `click.style(branch, fg="yellow")`                  |
| PR numbers               | `cyan`           | No   | `click.style(f"PR #{pr}", fg="cyan")`               |
| PR titles                | `bright_magenta` | No   | `click.style(title, fg="bright_magenta")`           |
| Plan titles              | `cyan`           | No   | `click.style(f"📋 {plan}", fg="cyan")`              |
| Success messages (✓)     | `green`          | No   | `click.style("✓ Done", fg="green")`                 |
| Section headers          | -                | Yes  | `click.style(header, bold=True)`                    |
| Current/active branches  | `bright_green`   | Yes  | `click.style(branch, fg="bright_green", bold=True)` |
| Paths (after completion) | `green`          | No   | `click.style(str(path), fg="green")`                |
| Paths (metadata)         | `white`          | Dim  | `click.style(str(path), fg="white", dim=True)`      |
| Error states             | `red`            | No   | `click.style("Error", fg="red")`                    |
| Dry run markers          | `bright_black`   | No   | `click.style("(dry run)", fg="bright_black")`       |
| Worktree/stack names     | `cyan`           | Yes  | `click.style(name, fg="cyan", bold=True)`           |

## Clickable Links (OSC 8)

The CLI supports clickable terminal links using OSC 8 escape sequences for PR numbers, plan IDs, and issue references.

### When to Use

Make IDs clickable when:

- A URL is available for the resource
- The ID is user-facing (e.g., PR numbers, plan IDs, issue numbers)
- Clicking would provide value (navigate to GitHub, external tracker, etc.)

### Implementation Pattern

**For simple text output (user_output):**

```python
# Format: \033]8;;URL\033\\text\033]8;;\033\\
id_text = f"#{identifier}"
if url:
    colored_id = click.style(id_text, fg="cyan")
    clickable_id = f"\033]8;;{url}\033\\{colored_id}\033]8;;\033\\"
else:
    clickable_id = click.style(id_text, fg="cyan")

user_output(f"Issue: {clickable_id}")
```

**For Rich tables:**

```python
from rich.table import Table

# Rich supports OSC 8 via markup syntax
id_text = f"#{identifier}"
if url:
    issue_id = f"[link={url}][cyan]{id_text}[/cyan][/link]"
else:
    issue_id = f"[cyan]{id_text}[/cyan]"

table.add_row(issue_id, ...)
```

### Styling Convention

- **Clickable IDs**: Use cyan color (`fg="cyan"`) to indicate interactivity
- **Non-clickable IDs**: Use cyan for consistency, but without OSC 8 wrapper
- This matches the existing PR link styling pattern

### Examples in Codebase

- `src/erk/core/display_utils.py` - `format_pr_info()` function (reference implementation)
- `src/erk/cli/commands/plan/list_cmd.py` - Clickable plan IDs in table
- `src/erk/cli/commands/plan/get.py` - Clickable plan ID in details
- `src/erk/status/renderers/simple.py` - Clickable issue numbers in status

### Terminal Compatibility

- Most modern terminals support OSC 8 (iTerm2, Terminal.app, Kitty, Alacritty, WezTerm, etc.)
- On unsupported terminals, links display as normal colored text
- No action required for graceful degradation

## Emoji Conventions

Standard emojis for CLI output:

- `✓` - Success indicators
- `✅` - Major success/completion
- `❌` - Errors/failures
- `📋` - Lists/plans
- `🗑️` - Deletion operations
- `⭕` - Aborted/cancelled
- `ℹ️` - Info notes

## Spacing Guidelines

- Use empty `click.echo()` for vertical spacing between sections
- Use `\n` prefix in strings for section breaks
- Indent list items with `  ` (2 spaces)

## Output Abstraction

**Use output abstraction for all CLI output to separate user messages from machine-readable data.**

### Functions

- `user_output()` - Routes to stderr for user-facing messages
- `machine_output()` - Routes to stdout for shell integration data

**Import:** `from erk_shared.output.output import user_output, machine_output`

### When to Use Each

| Use case                  | Function           | Rationale                   |
| ------------------------- | ------------------ | --------------------------- |
| Status messages           | `user_output()`    | User info, goes to stderr   |
| Error messages            | `user_output()`    | User info, goes to stderr   |
| Progress indicators       | `user_output()`    | User info, goes to stderr   |
| Success confirmations     | `user_output()`    | User info, goes to stderr   |
| Shell activation scripts  | `machine_output()` | Script data, goes to stdout |
| JSON output (--json flag) | `machine_output()` | Script data, goes to stdout |
| Paths for script capture  | `machine_output()` | Script data, goes to stdout |

### Example

```python
from erk_shared.output.output import user_output, machine_output

# User-facing messages
user_output(f"✓ Created worktree {name}")
user_output(click.style("Error: ", fg="red") + "Branch not found")

# Script/machine data
machine_output(json.dumps(result))
machine_output(str(activation_path))
```

## Reference Implementations

See these commands for examples:

- `src/erk/cli/commands/sync.py` - Uses custom `_emit()` helper
- `src/erk/cli/commands/checkout.py` - Uses both user_output() and machine_output()
- `src/erk/cli/commands/consolidate.py` - Uses both abstractions

## Error Message Guidelines

Use the `Ensure` class (from `erk.cli.ensure`) for all CLI validation errors. This provides consistent error styling and messaging.

### Error Message Format

All error messages should follow these principles:

1. **Action-oriented**: Tell the user what went wrong and what they should do
2. **User-friendly**: Avoid jargon, internal details, or stack traces
3. **Unique**: Specific enough to search documentation or identify the issue
4. **Concise**: Clear and brief, no redundant information

### Format Pattern

```
[Specific issue description] - [Suggested action or context]
```

**DO NOT** include "Error: " prefix - the `Ensure` class adds it automatically in red.

### Examples

| Good                                                                                             | Bad                       |
| ------------------------------------------------------------------------------------------------ | ------------------------- |
| `"Configuration file not found at ~/.erk/config.yml - Run 'erk init' to create it"`              | `"Error: Config missing"` |
| `"Worktree already exists at path {path} - Use --force to overwrite or choose a different name"` | `"Error: Path exists"`    |
| `"Branch 'main' has uncommitted changes - Commit or stash changes before proceeding"`            | `"Dirty worktree"`        |
| `"No child branches found - Already at the top of the stack"`                                    | `"Validation failed"`     |

### Common Validation Patterns

| Situation            | Error Message Template                                      |
| -------------------- | ----------------------------------------------------------- |
| Path doesn't exist   | `"{entity} not found: {path}"`                              |
| Path already exists  | `"{entity} already exists: {path} - {action}"`              |
| Git state invalid    | `"{branch/worktree} {state} - {required action}"`           |
| Missing config field | `"Required configuration '{field}' not set - {how to fix}"` |
| Invalid argument     | `"Invalid {argument}: {value} - {valid options}"`           |

### Using Ensure Methods

```python
from erk.cli.ensure import Ensure

# Basic invariant check
Ensure.invariant(
    condition,
    "Branch 'main' already has a worktree - Delete it first or use a different branch"
)

# Truthy check (returns value if truthy)
children = Ensure.truthy(
    ctx.graphite.get_child_branches(ctx.git, repo.root, current_branch),
    "Already at the top of the stack (no child branches)"
)

# Path existence check
Ensure.path_exists(
    ctx,
    wt_path,
    f"Worktree not found: {wt_path}"
)
```

### Decision Tree: Which Ensure Method to Use?

1. **Checking if a path exists?** → Use `Ensure.path_exists()`
2. **Need to return a value if truthy?** → Use `Ensure.truthy()`
3. **Any other boolean condition?** → Use `Ensure.invariant()`
4. **Complex multi-condition validation?** → Use sequential Ensure calls (see below)

### Complex Validation Patterns

For multi-step validations, use sequential Ensure calls with specific error messages:

```python
# Multi-condition validation - each check has specific error
Ensure.path_exists(ctx, wt_path, f"Worktree not found: {wt_path}")
Ensure.git_branch_exists(ctx, repo.root, branch)
Ensure.invariant(
    not has_uncommitted_changes,
    f"Branch '{branch}' has uncommitted changes - Commit or stash before proceeding"
)

# Conditional validation - only check if condition met
if not dry_run:
    Ensure.config_field_set(cfg, "github_token", "GitHub token required for this operation")
    Ensure.git_worktree_exists(ctx, wt_path, name)

# Validation with early return - fail fast on first error
Ensure.not_empty(name, "Worktree name cannot be empty")
Ensure.invariant(name not in (".", ".."), f"Invalid name '{name}' - directory references not allowed")
Ensure.invariant("/" not in name, f"Invalid name '{name}' - path separators not allowed")
```

**Design Principle:** Prefer simple sequential checks over complex validation abstractions. Each check should have a specific, actionable error message. This aligns with the LBYL (Look Before You Leap) philosophy and makes code easier to understand and debug.

**Exit Codes:** All Ensure methods use exit code 1 for validation failures. This is consistent across all CLI commands.

## Table Rendering Standards

When displaying tabular data, use Rich tables with these conventions.

### Header Naming

Use **lowercase, abbreviated headers** to minimize horizontal space:

| Full Name    | Header   | Notes                       |
| ------------ | -------- | --------------------------- |
| Plan         | `plan`   | Issue/plan identifier       |
| Pull Request | `pr`     | PR number with status emoji |
| Title        | `title`  | Truncate to ~50 chars       |
| Checks       | `chks`   | CI status emoji             |
| State        | `st`     | OPEN/CLOSED                 |
| Action       | `action` | Workflow action state       |
| Run ID       | `run-id` | GitHub Actions run ID       |
| Worktree     | `wt`     | Local worktree name         |
| Branch       | `branch` | Git branch name             |

### Column Order Convention

Order columns by importance and logical grouping:

1. **Identifier** (plan, pr, issue) - always first
2. **Related links** (pr if separate from identifier)
3. **Title/description** - human context
4. **Status indicators** (chks, st, action) - current state
5. **Technical IDs** (run-id) - for debugging/linking
6. **Location** (wt, path) - always last

### Color Scheme for Table Cells

| Element          | Rich Markup                  | When to Use            |
| ---------------- | ---------------------------- | ---------------------- |
| Identifiers      | `[cyan]#123[/cyan]`          | Plan IDs, PR numbers   |
| Clickable links  | `[link=URL][cyan]...[/link]` | IDs with URLs          |
| State: OPEN      | `[green]OPEN[/green]`        | Open issues/PRs        |
| State: CLOSED    | `[red]CLOSED[/red]`          | Closed issues/PRs      |
| Action: Pending  | `[yellow]Pending[/yellow]`   | Queued but not started |
| Action: Running  | `[blue]Running[/blue]`       | Currently executing    |
| Action: Complete | `[green]Complete[/green]`    | Successfully finished  |
| Action: Failed   | `[red]Failed[/red]`          | Execution failed       |
| Action: None     | `[dim]-[/dim]`               | No action applicable   |
| Worktree names   | `style="yellow"`             | Column-level style     |
| Placeholder      | `-`                          | No data available      |

### Table Setup Pattern

```python
from rich.console import Console
from rich.table import Table

table = Table(show_header=True, header_style="bold")
table.add_column("plan", style="cyan", no_wrap=True)
table.add_column("pr", no_wrap=True)
table.add_column("title", no_wrap=True)
table.add_column("chks", no_wrap=True)
table.add_column("st", no_wrap=True)
table.add_column("wt", style="yellow", no_wrap=True)

# Output to stderr (consistent with user_output)
console = Console(stderr=True, width=200)
console.print(table)
console.print()  # Blank line after table
```

### Reference Implementations

- `src/erk/cli/commands/plan/list_cmd.py` - Plan list table with all conventions

## See Also

- [script-mode.md](script-mode.md) - Script mode for shell integration (suppressing diagnostics)
