---
title: CLI Output Styling Guide
read_when:
  - "styling CLI output"
  - "using colors in CLI"
  - "formatting terminal output"
tripwires:
  - action: "using click.confirm() after user_output()"
    warning: "Use ctx.console.confirm() for testability, or user_confirm() if no context available. Direct click.confirm() after user_output() causes buffering hangs because stderr isn't flushed."
  - action: "displaying user-provided text in Rich CLI tables"
    warning: "Use `escape_markup(value)` for user data. Brackets like `[text]` are interpreted as Rich style tags and will disappear."
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

## Clipboard Copy (OSC 52)

The CLI supports automatic clipboard copy using OSC 52 escape sequences. When emitted, supported terminals copy the text to the system clipboard silently.

### When to Use

Copy text to clipboard when:

- Providing a command the user should paste and run
- The command is long/complex and manual copying would be error-prone
- There's a clear "primary" command among multiple options

### Implementation Pattern

```python
import click

from erk.core.display_utils import copy_to_clipboard_osc52
from erk_shared.output.output import user_output

# Display command with hint
cmd = f"source {script_path}"
clipboard_hint = click.style("(copied to clipboard)", dim=True)
user_output(f"  {cmd}  {clipboard_hint}")

# Emit invisible OSC 52 sequence
user_output(copy_to_clipboard_osc52(cmd), nl=False)
```

### Terminal Compatibility

- Supported: iTerm2, Kitty, Alacritty, WezTerm, Terminal.app (macOS 13+)
- Unsupported terminals silently ignore the sequence (no errors)
- No action required for graceful degradation

### Reference Implementation

- `src/erk/cli/activation.py` - `print_activation_instructions()` function
- `src/erk/core/display_utils.py` - `copy_to_clipboard_osc52()` function

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

## Confirmation Prompts

When prompting users for confirmation, use the right abstraction based on context availability.

### Pattern Hierarchy

**For testable code (preferred)**: Use `ctx.console.confirm()` when you have ErkContext

```python
# Uses FakeConsole in tests, InteractiveConsole in production
user_output("Warning: This operation is destructive!")
if ctx.console.confirm("Are you sure?"):
    perform_dangerous_operation()
```

- Enables FakeConsole to intercept confirmations in tests
- InteractiveConsole handles stderr flushing automatically

**Fallback**: Use `user_confirm()` when ErkContext is not available

```python
from erk_shared.output import user_output, user_confirm

user_output("Warning: This operation is destructive!")
if user_confirm("Are you sure?"):
    perform_dangerous_operation()
```

- Standalone function that flushes stderr before click.confirm()
- Use when writing utility code without context access

**Never**: Use raw `click.confirm()` after `user_output()`

```python
# ❌ WRONG: Causes buffering hangs
user_output("Warning: This operation is destructive!")
if click.confirm("Are you sure?"):  # stderr not flushed!
    perform_dangerous_operation()
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
    ctx.branch_manager.get_child_branches(repo.root, current_branch),
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

## Ensure Migration Decisions

When migrating existing `user_output() + SystemExit(1)` patterns to use the `Ensure` class, follow this decision tree to determine the right approach.

### Decision Tree for Migration

1. **If error has a boolean condition** → Use `Ensure.invariant()`

   ```python
   # Before:
   if not condition:
       user_output(click.style("Error: ", fg="red") + "Something is wrong")
       raise SystemExit(1)

   # After:
   Ensure.invariant(condition, "Something is wrong")
   ```

2. **If error returns a value when truthy** → Use `Ensure.truthy()`

   ```python
   # Before:
   result = get_something()
   if not result:
       user_output(click.style("Error: ", fg="red") + "No results found")
       raise SystemExit(1)

   # After:
   result = Ensure.truthy(get_something(), "No results found")
   ```

3. **If error checks for None specifically** → Use `Ensure.not_none()`

   ```python
   # Before:
   value = might_return_none()
   if value is None:
       user_output(click.style("Error: ", fg="red") + "Value is required")
       raise SystemExit(1)

   # After:
   value = Ensure.not_none(might_return_none(), "Value is required")
   ```

4. **If error has a specialized type** (PR, branch, session) → Use typed unwrapper

   ```python
   # Before:
   pr = ctx.github.get_pr_for_branch(branch)
   if isinstance(pr, PRNotFound):
       user_output(click.style("Error: ", fg="red") + f"No PR for {branch}")
       raise SystemExit(1)

   # After:
   pr = Ensure.unwrap_pr(ctx.github.get_pr_for_branch(branch), f"No PR for {branch}")
   ```

5. **If error has no clear condition or needs custom flow** → Keep as direct pattern

### When NOT to Migrate

**Pattern: Fallthrough/catch-all errors with no clear boolean condition**

Some errors occur as the "else" case after multiple checks have been exhausted. There's no meaningful boolean condition to express - the error state IS the remaining case.

```python
# Example from navigation_helpers.py - NOT a migration candidate
if on_trunk:
    # Handle trunk case
    ...
elif has_parent:
    # Handle parent case
    ...
else:
    # Fallthrough: not on trunk, no parent - no clear condition to check
    user_output(
        click.style("Error: ", fg="red")
        + "Could not determine parent branch from Graphite metadata"
    )
    raise SystemExit(1)
```

**Why not migrate:** Using `Ensure.invariant(True, ...)` or wrapping with an artificial condition would be misleading. The error isn't about a condition being false - it's about reaching a catch-all state.

**Pattern: Errors with complex multi-line remediation messages**

When the error message spans multiple lines with detailed instructions, the `Ensure` API may not accommodate the formatting needs cleanly.

**Pattern: Errors that need conditional additional output before exit**

If code needs to emit additional context (tables, lists, suggestions) before exiting, the direct pattern provides more control.

### Migration Checklist

When migrating a `user_output() + SystemExit(1)` pattern:

1. **Identify the error condition** - Is there a clear boolean/truthy/None check?
2. **Choose the right Ensure method** - Use the decision tree above
3. **Write the error message** - Follow the Error Message Guidelines (no "Error: " prefix)
4. **Test behavior is unchanged** - Error should trigger at the same conditions
5. **Check for fallthrough cases** - If this is a catch-all, don't migrate

### Good Migration Examples

From `navigation_helpers.py` (PR #5187):

```python
# Before:
if not children:
    user_output(click.style("Error: ", fg="red") + "Already at the top...")
    raise SystemExit(1)

# After:
children = Ensure.truthy(
    ctx.branch_manager.get_child_branches(...),
    "Already at the top of the stack (no child branches)"
)
```

The migration works because:

- There's a clear truthy condition (`children`)
- The return value is used (`children` variable)
- The error message is a single line

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

## Rich Markup Escaping in CLI Tables

When displaying user-provided text in Rich CLI tables (via `console.print(table)`), bracket sequences like `[text]` are interpreted as Rich style tags.

### The Problem

```python
from rich.table import Table
from rich.console import Console

table = Table()
table.add_column("Title")
# WRONG: User title with brackets disappears
table.add_row("[erk-learn] Fix the bug")
# Result: "Fix the bug" (prefix invisible)
```

### The Solution: escape_markup()

Use `escape_markup()` for CLI Rich output:

```python
from rich.markup import escape as escape_markup

# CORRECT: escape_markup() escapes bracket characters
table.add_row(escape_markup("[erk-learn] Fix the bug"))
# Result: "[erk-learn] Fix the bug" (fully visible)
```

### Cross-Component Comparison

| Context          | Solution           | Import                                |
| ---------------- | ------------------ | ------------------------------------- |
| TUI DataTable    | `Text(value)`      | `from rich.text import Text`          |
| CLI Rich tables  | `escape_markup()`  | `from rich.markup import escape`      |
| Plain CLI output | No escaping needed | Use `click.echo()` or `user_output()` |

**Why the difference:**

- **TUI DataTable**: `Text()` disables markup parsing for the entire cell
- **CLI Rich tables**: `escape_markup()` escapes special characters but allows markup elsewhere in the string (useful for combining styled and user text)

### When to Apply

Escape user data that may contain:

- **Plan titles** - `[erk-learn]`, `[erk-plan]` prefixes
- **Branch names** - May have brackets from naming conventions
- **Issue titles** - User-provided content with arbitrary brackets
- **File paths** - Directory names with brackets

### Reference Implementation

See `src/erk/tui/widgets/clickable_link.py` for `escape_markup()` usage patterns.

## See Also

- [script-mode.md](script-mode.md) - Script mode for shell integration (suppressing diagnostics)
- [DataTable Rich Markup Escaping](../textual/datatable-markup-escaping.md) - TUI-specific markup escaping
