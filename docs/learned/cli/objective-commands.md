---
title: Objective Commands
read_when:
  - "working with erk objective commands"
  - "implementing objective reconcile functionality"
  - "understanding auto-advance objectives"
tripwires:
  - action: "displaying user-provided text in Rich CLI tables without escaping"
    warning: "Use `escape_markup(value)` for user data in Rich tables. Brackets like `[text]` are interpreted as style tags and will disappear."
---

# Objective Commands

The `erk objective` command group manages erk objectives - high-level goals that track multiple related plans.

## Command Overview

| Command                   | Alias | Description                        |
| ------------------------- | ----- | ---------------------------------- |
| `erk objective reconcile` | `rec` | Reconcile auto-advance objectives  |
| `erk objective list`      | `ls`  | List open objectives               |
| `erk objective create`    | -     | Create a new objective             |
| `erk objective next-plan` | `np`  | Create plan from an objective step |

## Next-Plan Command

The `erk objective next-plan` command launches Claude in plan mode to create an implementation plan from an objective step.

### Usage

```bash
# Create plan from objective issue
erk objective next-plan 6423

# Using alias
erk objective np 6423

# From GitHub URL
erk objective next-plan https://github.com/owner/repo/issues/6423
```

### Arguments

| Argument    | Description                          |
| ----------- | ------------------------------------ |
| `ISSUE_REF` | Objective issue number or GitHub URL |

### Behavior

1. **Validates Claude CLI**: Checks that `claude` command is available
2. **Launches Claude**: Starts Claude Code in plan mode with `/erk:objective-next-plan <issue_ref>`
3. **Permission Mode**: Automatically sets `--permission-mode plan`
4. **Config Integration**: Respects `[interactive-claude]` settings from `~/.erk/config.toml`

### Permission Mode

The command always launches Claude in **plan mode** (`--permission-mode plan`), regardless of config file settings. This ensures the agent creates a plan document rather than immediately implementing.

**Implementation pattern:**

```python
config = ic_config.with_overrides(
    permission_mode_override="plan",
    model_override=None,
    dangerous_override=None,
    allow_dangerous_override=None,
)
```

The `with_overrides()` method conditionally overrides config values:

- Setting to a value (like `"plan"`) forces that mode
- Setting to `None` preserves the config file value

### Codespace Variant

For remote execution, use `erk codespace run objective next-plan`:

```bash
# Execute on remote codespace
erk codespace run objective next-plan 6423
```

The remote variant follows the same permission model as the local command.

### Related Slash Command

After launching, Claude executes `/erk:objective-next-plan` which:

1. Fetches the objective issue
2. Analyzes the roadmap
3. Guides the user through planning an implementation for a step
4. Saves the plan to a GitHub issue

See `.claude/commands/erk/objective-next-plan.md` for the slash command implementation.

## Reconcile Command

The `erk objective reconcile` command analyzes objectives and determines next actions (typically creating plans for pending steps).

### Usage

```bash
# Reconcile all auto-advance objectives
erk objective reconcile

# Target a specific objective (positional argument)
erk objective reconcile 123

# Preview without executing
erk objective reconcile --dry-run
erk objective reconcile 123 --dry-run
```

### Arguments and Flags

| Argument/Flag | Description                                        |
| ------------- | -------------------------------------------------- |
| `OBJECTIVE`   | Optional issue number to target specific objective |
| `--dry-run`   | Show planned actions without executing             |

### Validation (LBYL Pattern)

The positional objective argument uses Look Before You Leap validation:

1. **Check existence**: `issue_exists(repo_root, number)` before fetching
2. **Check labels**: Verify `erk-objective` label exists
3. **Fail early**: Exit with clear error if validation fails

This pattern prevents cryptic errors from `get_issue()` on non-existent issues.

### Output Format

The command displays a Rich table with columns:

| Column   | Content                                            |
| -------- | -------------------------------------------------- |
| `#`      | Objective issue number                             |
| `Title`  | Objective title (user-provided, needs escaping)    |
| `Action` | Determined action (`create_plan`, `skip`, `error`) |
| `Step`   | Target step ID or `-`                              |
| `Reason` | (dry-run) Why this action was chosen               |
| `Result` | (live) Execution result or error                   |

### Rich Markup Escaping

When displaying user-provided titles in Rich tables, bracket sequences like `[text]` are interpreted as Rich style tags. Always escape user data:

```python
from rich.markup import escape as escape_markup

# WRONG: User title with brackets disappears
table.add_row(f"#{issue.number}", issue.title, ...)

# CORRECT: Escape user data
table.add_row(f"#{issue.number}", escape_markup(issue.title), ...)
```

See [CLI Output Styling Guide](output-styling.md#rich-markup-escaping-in-cli-tables) for complete details.

## Auto-Advance Objectives

An **auto-advance objective** is an objective issue with both labels:

- `erk-objective`
- `auto-advance`

The reconcile command processes these automatically when run without a specific objective argument.

## Session-Based Idempotency

Some objective commands support session-based deduplication to prevent double-execution during retries.

### Behavior with `--session-id`

When `--session-id` is provided:

1. The command checks if it already ran for this session
2. If previously executed, returns early with `skipped_duplicate: true`
3. If not, executes normally and records the session

### JSON Response with Deduplication

```json
{
  "success": true,
  "skipped_duplicate": true,
  "message": "Already executed in this session"
}
```

### Scope

Session-based deduplication is:

- **Within session**: Same session ID gets deduplicated
- **Cross-session**: Different sessions execute independently
- **Opt-in**: Only active when `--session-id` is provided

This prevents issues like duplicate plan creation when hooks retry or Claude retries a blocked command.

## Related Documentation

- [CLI Output Styling Guide](output-styling.md) - Table formatting and Rich escaping
- [LBYL Gateway Pattern](../architecture/lbyl-gateway-pattern.md) - Existence checking pattern
- [Gateway ABC Implementation](../architecture/gateway-abc-implementation.md) - `issue_exists()` method
