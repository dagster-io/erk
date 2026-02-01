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

| Command                                | Alias | Description                                  |
| -------------------------------------- | ----- | -------------------------------------------- |
| `erk objective reconcile`              | `rec` | Reconcile auto-advance objectives            |
| `erk objective list`                   | `ls`  | List open objectives                         |
| `erk objective create`                 | -     | Create a new objective                       |
| `erk objective next-plan`              | -     | Create plan for next objective step (local)  |
| `erk codespace run objective next-plan`| -     | Create plan for next objective step (remote) |

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

## Remote Objective Execution via Codespaces

Long-running objective workflows (like `next-plan`, which can take 10+ minutes) can be dispatched to GitHub Codespaces for background execution. This enables fire-and-forget operation where the command returns immediately while execution continues remotely.

### Local vs Remote Execution

**Local execution:**
```bash
erk objective next-plan 42
```
- Runs in current terminal
- Blocks until complete (10+ minutes)
- Shows live progress and output
- User cannot use terminal during execution

**Remote execution:**
```bash
erk codespace run objective next-plan 42
```
- Dispatches to GitHub Codespace
- Returns immediately (fire-and-forget)
- Execution continues in background on codespace
- Output logged to `/tmp/erk-run.log` on codespace
- User retains control of local terminal

### When to Use Remote Execution

**Good use cases:**
- Long-running plan creation (10+ minutes)
- Parallel processing of multiple objectives
- Batch operations during off-hours
- When you need to continue local work immediately

**Not ideal for:**
- Quick operations where you want immediate feedback
- When you need to see live progress
- Debugging workflows (harder to monitor output)

### Command Signature

```bash
erk codespace run objective next-plan ISSUE_REF [--codespace NAME]
```

**Arguments:**
- `ISSUE_REF`: Objective issue number or URL

**Options:**
- `--codespace`, `-c`: Codespace name (defaults to configured default)

### Examples

```bash
# Use default codespace
erk codespace run objective next-plan 42

# Use specific codespace
erk codespace run objective next-plan 42 -c my-dev-codespace

# With GitHub URL
erk codespace run objective next-plan https://github.com/owner/repo/issues/42
```

### Checking Execution Progress

Output is logged to `/tmp/erk-run.log` on the codespace:

```bash
# SSH to codespace
erk codespace connect

# View logs
cat /tmp/erk-run.log

# Follow live progress
tail -f /tmp/erk-run.log
```

### How It Works

1. **Environment setup**: The command automatically syncs code and dependencies on the codespace
2. **Background execution**: Uses `nohup` to detach from SSH session
3. **Output logging**: All output redirected to `/tmp/erk-run.log`
4. **Immediate return**: Local command returns as soon as SSH dispatch succeeds

See [Codespace Remote Execution](../erk/codespace-remote-execution.md) for architecture details.

## Related Documentation

- [CLI Output Styling Guide](output-styling.md) - Table formatting and Rich escaping
- [LBYL Gateway Pattern](../architecture/lbyl-gateway-pattern.md) - Existence checking pattern
- [Gateway ABC Implementation](../architecture/gateway-abc-implementation.md) - `issue_exists()` method
