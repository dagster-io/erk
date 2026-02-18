---
title: CLI Output Styling Guide
last_audited: "2026-02-16 00:00 PT"
audit_result: clean
read_when:
  - "styling CLI output"
  - "using colors in CLI"
  - "formatting terminal output"
tripwires:
  - action: "using click.confirm() after user_output()"
    warning: "Use ctx.console.confirm() for testability, or user_confirm() if no context available. Direct click.confirm() after user_output() causes buffering hangs because stderr isn't flushed."
  - action: "displaying user-provided text in Rich CLI tables"
    warning: "Use `escape_markup(value)` for user data. Brackets like `[text]` are interpreted as Rich style tags and will disappear."
  - action: "writing multi-line error messages in Ensure method calls"
    warning: "Use implicit string concatenation with \\n at end of first string. Line 1 is the primary error, line 2+ is remediation context. Do NOT use \\n\\n (double newline) — Ensure handles spacing."
  - action: "using Python format strings with :N width specifiers for CLI output containing emoji"
    warning: "Use Rich tables instead — emoji have variable terminal widths (typically 2 cells) which break fixed-width alignment. See the Rich Tables for Variable-Width Characters section below."
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
- `src/erk/cli/commands/plan/view.py` - Clickable plan ID in details
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

## Async Progress Output Patterns

When orchestrating multi-step async operations (like `trigger-async-learn`), use a hierarchical output structure to show progress clearly.

### Hierarchical Indentation

Use consistent indentation to show the relationship between actions and their details:

| Level      | Indentation | Content                              | Example                                     |
| ---------- | ----------- | ------------------------------------ | ------------------------------------------- |
| Action     | 0 spaces    | Top-level operation being performed  | `📋 Discovering sessions...`                |
| Detail     | 3-4 spaces  | Summary information about the action | `   Found 2 session(s): 1 planning, 1 impl` |
| Sub-detail | 5+ spaces   | Item-level details                   | `     📝 planning: abc123 (local)`          |

### Emoji as Semantic Type Indicators

Emojis serve as visual type indicators for different stages of async workflows:

| Emoji | Meaning       | When to Use                        | Example                                     |
| ----- | ------------- | ---------------------------------- | ------------------------------------------- |
| 📋    | Discovery     | Finding/listing resources          | `📋 Discovering sessions...`                |
| 🔍    | Search        | Looking up specific items          | `🔍 Getting PR for plan...`                 |
| 🔄    | Processing    | Transforming or preprocessing data | `🔄 Preprocessing planning session...`      |
| 📂    | Directory ops | Creating directories               | `📂 Created learn-6545`                     |
| 💬    | Comments      | Fetching comments or discussions   | `💬 Fetching review comments...`            |
| ☁️    | Upload        | Uploading to remote services       | `☁️ Uploading to gist...`                   |
| 📄    | File output   | Writing files to disk              | `   📄 planning-session.xml (12,345 chars)` |
| 🔗    | Links         | Generated URLs or references       | `   🔗 https://gist.github.com/...`         |

**Rule:** Use consistent emoji prefixes in subprocess progress output. Pass empty string `""` for no prefix.

### Context-Aware Emoji Selection

For session processing, choose emoji based on session type:

```python
# From trigger_async_learn.py:230-232
prefix = "planning" if sid == planning_session_id else "impl"
emoji = "📝" if prefix == "planning" else "🔧"
session_line = click.style(f"     {emoji} {prefix}: {sid} ({source_type})", dim=True)
```

| Context                 | Emoji | Usage                         |
| ----------------------- | ----- | ----------------------------- |
| Planning sessions       | 📝    | `📝 planning: abc123 (local)` |
| Implementation sessions | 🔧    | `🔧 impl: def456 (gist)`      |

### Output Routing

**Critical:** All progress output goes to **stderr**, JSON output goes to **stdout**.

```python
# From trigger_async_learn.py:100-102
message = click.style(f"{prefix}{description}...", fg="cyan")
click.echo(message, err=True)  # Note: err=True
```

This allows shell scripts to parse JSON from stdout without interference from progress messages.

### Example: Full Async Progress Flow

**From:** `src/erk/cli/commands/exec/scripts/trigger_async_learn.py`

```
📋 Discovering sessions...
   Found 2 session(s): 1 planning, 1 impl
     📝 planning: abc123 (local)
     🔧 impl: def456 (local)
📂 Created learn-6545
🔄 Preprocessing planning session...
   Original: 45,678 chars → Compressed: 12,345 chars (72.97% reduction)
   📄 planning-session.xml (12,345 chars)
🔄 Preprocessing impl session...
   ⏭️  Session filtered (empty/warmup), skipping
🔍 Getting PR for plan...
💬 Fetching review comments...
   📄 pr-review-comments.json
💬 Fetching discussion comments...
   📄 pr-discussion-comments.json
☁️ Uploading to gist...
   🔗 https://gist.github.com/... (4 file(s), 23,456 chars)
```

**Final stdout (after all stderr):**

```json
{
  "success": true,
  "issue_number": 6545,
  "workflow_triggered": true,
  "run_id": "12345678",
  "workflow_url": "https://...",
  "gist_url": "https://..."
}
```

### Styling Conventions for Async Progress

| Element         | Style             | Example                                          |
| --------------- | ----------------- | ------------------------------------------------ |
| Action messages | Cyan              | `click.style(f"📋 {description}...", fg="cyan")` |
| Summary details | Dimmed            | `click.style(f"   Found {n} items", dim=True)`   |
| File names      | Dimmed            | `click.style(f"   📄 {filename}", dim=True)`     |
| URLs            | Blue, underlined  | `click.style(url, fg="blue", underline=True)`    |
| Stats/metadata  | Dimmed, in parens | `click.style(f"({count} files)", dim=True)`      |

### Related Patterns

- [Output Abstraction](#output-abstraction) - When to use `user_output()` vs `machine_output()`
- [Emoji Conventions](#emoji-conventions) - Standard emoji meanings

## Progress Callbacks

For operations using the callback progress pattern, bind the callback to CLI output at the command layer.

### Binding Pattern

Use a lambda to convert progress strings to styled CLI output. See `sync.py` in `src/erk/cli/commands/docs/` for the reference implementation.

The lambda should:

- Apply cyan styling for consistency with other progress output
- Route to stderr (`err=True`) to avoid interfering with machine-readable stdout

For silent operation (validation, testing), pass a no-op lambda (`lambda _: None`).

### Progress Granularity Guidelines

Choose progress granularity based on the number of items being processed:

| Item Count | Strategy         | Example                                         |
| ---------- | ---------------- | ----------------------------------------------- |
| <10        | Per-item         | "Processing file 1/5..."                        |
| 10-100     | Milestone-based  | "Scanning...", "Generating...", "Finalizing..." |
| >100       | Percentage/count | "Processing... 45% (450/1000)"                  |

Per-file progress for large operations creates visual noise and can slow execution. Milestone-based progress at operation boundaries provides adequate feedback without overwhelming the user.

Example: `erk docs sync` processes ~55 files but reports only 6 milestones (one per pipeline stage).

### Related Patterns

- [Callback Progress Pattern](../architecture/callback-progress-pattern.md) - Operations layer pattern
- [Async Progress Output Patterns](#async-progress-output-patterns) - Full async progress conventions

## Spacing Guidelines

- Use empty `click.echo()` for vertical spacing between sections
- Use `\n` prefix in strings for section breaks
- Indent list items with `  ` (2 spaces)

## Plan Context Feedback Pattern

When displaying plan context information in CLI commands, use this standardized feedback pattern for consistency across plan-aware operations.

### Pattern Components

The pattern consists of three elements:

1. **Plan incorporation message** (when plan found):
   - Format: `"   Incorporating plan from issue #{issue_number}"`
   - Style: Green text (`fg="green"`)
2. **Objective link message** (when objective available):
   - Format: `"   Linked to {objective_summary}"`
   - Style: Green text (`fg="green"`)
3. **No plan message** (when plan not found):
   - Format: `"   No linked plan found"`
   - Style: Dimmed text (`dim=True`)
4. **Separator**: Blank line after feedback

### Implementation

```python
import click

if plan_context is not None:
    click.echo(
        click.style(
            f"   Incorporating plan from issue #{plan_context.issue_number}",
            fg="green",
        )
    )
    if plan_context.objective_summary is not None:
        click.echo(click.style(f"   Linked to {plan_context.objective_summary}", fg="green"))
else:
    click.echo(click.style("   No linked plan found", dim=True))
click.echo("")
```

### Usage Examples

**With Plan and Objective:**

```
   Incorporating plan from issue #6386
   Linked to [objective] Improve PR operations feedback

```

**With Plan Only:**

```
   Incorporating plan from issue #6172

```

**Without Plan:**

```
   No linked plan found

```

### Commands Using This Pattern

This pattern is currently used in:

- `erk pr submit` - During PR submission (`src/erk/cli/commands/pr/submit_pipeline.py:466-472`)
- `erk pr rewrite` - When generating PR descriptions (`src/erk/cli/commands/pr/rewrite_cmd.py:_execute_pr_rewrite`)

### Design Rationale

**Why standardize this pattern:**

- **Consistency**: Users see the same feedback format across all plan-aware operations
- **Transparency**: Makes plan context detection explicit and visible
- **Graceful degradation**: Provides clear feedback when no plan is found
- **Visual hierarchy**: Green for success/presence, dim for absence

**Future commands that incorporate plan context should follow this convention.**

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
from erk_shared.output.output import user_output, user_confirm

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

- `src/erk/cli/commands/checkout_helpers.py` - Uses user_output() for sync status
- `src/erk/cli/commands/stack/consolidate_cmd.py` - Uses user_output() for error messages

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

### Multi-line Error Messages

For errors that need both a primary message and remediation context, use implicit string concatenation with `\n`:

```python
github_id = Ensure.not_none(
    repo.github,
    "Not a GitHub repository\n"
    "This command requires the repository to have a GitHub remote configured.",
)
```

**Convention:**

- Line 1: Primary error description (concise, specific)
- Newline separator via `\n` at end of first string
- Line 2+: Remediation guidance or additional context

**DO NOT** use `\n\n` (double newline) — the Ensure class already handles spacing in its error output formatting.

This pattern was established in the admin.py migration (PR #6860) and applies to all Ensure method calls where the error benefits from remediation context.

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

### UserFacingCliError for Mid-Function Errors

For errors that occur mid-function where `Ensure` precondition checks don't fit, use `UserFacingCliError`:

```python
from erk.cli.ensure import UserFacingCliError

# CLI-layer consumer pattern for discriminated unions
push_result = ctx.git.remote.push_to_remote(repo.root, "origin", branch)
if isinstance(push_result, PushError):
    raise UserFacingCliError(push_result.message)
```

**When to use:**

- **Mid-logic errors**: Errors discovered during execution, not preconditions
- **Discriminated union errors**: When consuming `Result | Error` types from gateway layer
- **After operations fail**: When an operation returns an error variant

**Relationship to Ensure:**

- `Ensure`: For precondition checks at function entry (LBYL)
- `UserFacingCliError`: For errors during execution (e.g., git push fails)
- Both produce the same styled output (`Error: ` prefix in red)
- Both exit with code 1
- Ensure uses `UserFacingCliError` internally

**Decision guide:**

- Precondition validation → Use `Ensure` methods
- Mid-function operation errors → Raise `UserFacingCliError`
- Complex multi-step operations → Mix both (Ensure upfront, UserFacingCliError for failures)

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

4. **If error has no clear condition or needs custom flow** → Keep as direct pattern

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

## Rich Tables for Variable-Width Characters

### Problem Statement

Python format strings assume fixed character width, but emoji have variable terminal widths. A format string like `f"{text:30}"` counts characters, not terminal cells. Emoji typically consume 2 terminal cells:

- Checkmark emoji = 2 cells
- Cycle arrows emoji = 2 cells
- Hourglass emoji = 2 cells
- ASCII characters = 1 cell

This causes columns to appear misaligned whenever emoji are present. The misalignment is silent — code runs without errors but output looks wrong.

### Solution: Rich Tables with cell_len()

Rich tables use `cell_len()` from `rich.cells` to calculate actual terminal width. Import the necessary components and let Rich handle alignment automatically.

**Import:** `from rich.cells import cell_len`

When manually calculating column widths (e.g., for pre-computed widths), use `cell_len(string)` instead of `len(string)`. This ensures emoji-containing strings are measured correctly.

### Pre-Computed Column Widths Pattern

When rendering multiple Rich tables in sequence (e.g., one per phase), each table calculates its own column widths independently. This results in misalignment between tables. Pre-compute maximum column widths across ALL data before rendering any tables.

<!-- Source: src/erk/cli/commands/objective/view_cmd.py, view_objective -->

**Pattern:** Calculate max widths by iterating all data before creating tables, then pass `min_width` to each column. See `view_objective()` in `src/erk/cli/commands/objective/view_cmd.py` for the complete implementation (grep for `max_id_width`, `max_status_width`, or `min_width`).

### When to Use

- Any CLI output with emoji or unicode characters requiring column alignment
- Multiple tables that should visually align as a single logical table
- Status indicators, progress displays, or any output with variable-width symbols

## Migrating from click.style() to Rich Markup

When migrating CLI output to Rich tables, status indicators need Rich markup format instead of click-styled strings.

### Mapping Table

| click.style() call               | Rich Markup equivalent    |
| -------------------------------- | ------------------------- |
| `click.style(text, fg="green")`  | `[green]{text}[/green]`   |
| `click.style(text, fg="yellow")` | `[yellow]{text}[/yellow]` |
| `click.style(text, dim=True)`    | `[dim]{text}[/dim]`       |

### Function Signature Changes

Functions that previously returned click-styled strings now return Rich markup strings. The return type stays `str`, but the content format changes.

<!-- Source: src/erk/cli/commands/objective/view_cmd.py, _format_node_status -->

See `_format_node_status()` in `src/erk/cli/commands/objective/view_cmd.py` for an example migration from click.style() to Rich markup.

### Escaping User Content

Use `escape()` from `rich.markup` for user-provided content that may contain brackets. Unescaped brackets like `[foo]` are interpreted as Rich style tags and disappear from output.

**Pattern:** Import `escape` from `rich.markup`, then wrap user content: `f"[yellow]status {escape(user_text)}[/yellow]"`

## Rich Markup Approach for Clickable Links

When using Rich tables, use Rich's link markup instead of raw OSC 8 escape sequences.

**Pattern:** `[link=URL]display text[/link]`

**Advantages over raw OSC 8:**

- Rich handles terminal compatibility automatically
- More readable than escape codes
- Consistent with Rich's styling approach elsewhere

<!-- Source: src/erk/cli/commands/objective/view_cmd.py, _format_ref_link -->

**Helper function pattern:** Create functions that convert GitHub refs (e.g., `#6871`) to clickable Rich markup. See `_format_ref_link()` and `_extract_repo_base_url()` in `src/erk/cli/commands/objective/view_cmd.py` for the implementation pattern.

**When to choose Rich markup over raw OSC 8:**

- Output is rendered via Rich Console or Table
- Need consistent styling with other Rich components
- Want automatic terminal capability detection

**When to use raw OSC 8 instead:** Output goes through `click.echo()` or `user_output()` where Rich rendering is not involved.

## See Also

- [DataTable Rich Markup Escaping](../textual/datatable-markup-escaping.md) - TUI-specific markup escaping
- [Help Text Formatting](help-text-formatting.md) - Using `\b` for code examples and bulleted lists in Click docstrings
