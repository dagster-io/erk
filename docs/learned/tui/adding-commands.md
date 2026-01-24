---
title: Adding Commands to TUI
read_when:
  - "adding a new command to the TUI command palette"
  - "implementing TUI actions with streaming output"
  - "understanding the dual-handler pattern for TUI commands"
tripwires:
  - action: "generating TUI commands that depend on optional PlanRowData fields"
    warning: "Implement three-layer validation: registry predicate → handler guard → app-level helper. Never rely on registry predicate alone."
---

# Adding Commands to TUI

Step-by-step guide for adding new commands to the TUI command palette.

## Architecture: The Dual-Handler Pattern

Commands in the TUI follow a **dual-handler pattern**:

1. **Registry** (`registry.py`) - Defines command metadata and availability predicates
2. **Handlers** - Implement the actual command logic in two locations:
   - `ErkDashApp.execute_palette_command()` - Main list context
   - `PlanDetailScreen.execute_command()` - Detail modal context

This pattern exists because commands need different behavior depending on where they're invoked. The main list has direct access to the data provider, while the detail modal has a pre-selected row and an executor.

## Step 1: Add CommandDefinition to Registry

In `src/erk/tui/commands/registry.py`, add a `CommandDefinition`:

```python
from erk.tui.commands.types import CommandCategory, CommandDefinition

CommandDefinition(
    id="land_pr",  # Unique identifier
    name="Land PR",  # Display name (used as fallback if no get_display_name)
    description="Merge PR and clean up worktree",  # Brief description
    category=CommandCategory.ACTION,  # Determines emoji prefix (⚡)
    shortcut="l",  # Optional keyboard shortcut (single char) or None
    is_available=lambda ctx: ctx.row.pr_number is not None and ctx.row.exists_locally,
    get_display_name=lambda ctx: f"erk land {ctx.row.pr_number}",  # Dynamic name
)
```

**Command Categories** (from `CommandCategory` enum):

| Category                 | Emoji | Use For                                   |
| ------------------------ | ----- | ----------------------------------------- |
| `CommandCategory.ACTION` | ⚡    | Mutative operations (close, submit, land) |
| `CommandCategory.OPEN`   | 🔗    | Browser navigation (open issue, PR, run)  |
| `CommandCategory.COPY`   | 📋    | Clipboard operations (copy commands)      |

The emoji is automatically prepended via `CATEGORY_EMOJI` mapping in `registry.py`.

**Dynamic Display Names** with `get_display_name`:

- If provided, returns context-aware name (e.g., `"erk land 456"`)
- If `None`, falls back to static `name` field
- Displayed in palette as: `⚡ erk land 456`

**Availability predicates** use `CommandContext.row` (a `PlanRowData` instance). See [plan-row-data.md](plan-row-data.md) for field reference.

## Step 2: Add Handler in Main List

In `src/erk/tui/app.py`, add handling in `ErkDashApp.execute_palette_command()`:

```python
elif command_id == "land_pr":
    if row.pr_number is not None:
        # For simple actions:
        self._provider.some_action(row.issue_number)
        self.notify("Action completed")
        self.action_refresh()

        # OR for streaming output (like submit_to_queue):
        # See Step 2b below
```

## Step 2b: Streaming Output Pattern

For long-running commands that need live output (like `submit_to_queue`, `land_pr`):

```python
elif command_id == "land_pr":
    if row.pr_url:
        executor = RealCommandExecutor(
            browser_launch=self._provider.browser.launch,
            clipboard_copy=self._provider.clipboard.copy,
            close_plan_fn=self._provider.close_plan,
            notify_fn=self.notify,
            refresh_fn=self.action_refresh,
            submit_to_queue_fn=self._provider.submit_to_queue,
        )
        detail_screen = PlanDetailScreen(
            row,
            clipboard=self._provider.clipboard,
            browser=self._provider.browser,
            executor=executor,
            repo_root=self._provider.repo_root,
        )
        self.push_screen(detail_screen)
        # Trigger streaming command after screen mounts
        detail_screen.call_after_refresh(
            lambda: detail_screen.run_streaming_command(
                ["erk", "pr", "land", str(row.pr_number)],
                cwd=self._provider.repo_root,
                title=f"Landing PR #{row.pr_number}",
            )
        )
```

## Step 3: Add Handler in Detail Modal

In `PlanDetailScreen.execute_command()`, add handling:

```python
elif command_id == "land_pr":
    if row.pr_url and self._repo_root is not None:
        # Use streaming output for long commands
        self.run_streaming_command(
            ["erk", "pr", "land", str(row.pr_number)],
            cwd=self._repo_root,
            title=f"Landing PR #{row.pr_number}",
        )
        # Don't dismiss - user must press Esc after completion
```

## Step 4: Add Registry Tests

In `tests/tui/commands/test_registry.py`, add tests for availability:

```python
def test_land_pr_available_when_pr_and_local_worktree() -> None:
    """land_pr should be available when PR exists and worktree is local."""
    row = make_plan_row(123, "Test", pr_number=456, exists_locally=True)
    ctx = CommandContext(row=row)
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "land_pr" in cmd_ids


def test_land_pr_not_available_when_no_pr() -> None:
    """land_pr should not be available when no PR."""
    row = make_plan_row(123, "Test", exists_locally=True)
    ctx = CommandContext(row=row)
    commands = get_available_commands(ctx)
    cmd_ids = [cmd.id for cmd in commands]
    assert "land_pr" not in cmd_ids
```

## Command Patterns

### Simple Action (Like `close_plan`)

```python
# Registry
CommandDefinition(
    id="close_plan",
    name="Action: Close Plan",
    description="Close issue and linked PRs",
    shortcut=None,  # No shortcut for destructive actions
    is_available=lambda _: True,
)

# Handler
elif command_id == "close_plan":
    if row.issue_url:
        closed_prs = executor.close_plan(row.issue_number, row.issue_url)
        executor.notify(f"Closed plan #{row.issue_number}")
        executor.refresh_data()
        self.dismiss()
```

### Streaming Command (Like `submit_to_queue`)

```python
# Registry
CommandDefinition(
    id="submit_to_queue",
    name="Action: Submit to Queue",
    description="Submit plan for remote AI implementation",
    shortcut="s",
    is_available=lambda ctx: ctx.row.issue_url is not None,
)

# Handler - uses run_streaming_command for live output
elif command_id == "submit_to_queue":
    if row.issue_url and self._repo_root is not None:
        self.run_streaming_command(
            ["erk", "plan", "submit", str(row.issue_number)],
            cwd=self._repo_root,
            title=f"Submitting Plan #{row.issue_number}",
        )
```

### Copy Command (Like `copy_checkout`)

```python
# Registry
CommandDefinition(
    id="copy_checkout",
    name="Copy: erk co <worktree>",
    description="Copy checkout command",
    shortcut="c",
    is_available=lambda ctx: ctx.row.exists_locally,
)

# Handler
elif command_id == "copy_checkout":
    cmd = f"erk co {row.worktree_name}"
    executor.copy_to_clipboard(cmd)
    executor.notify(f"Copied: {cmd}")
```

## Key Files

| File                                  | Purpose                                                        |
| ------------------------------------- | -------------------------------------------------------------- |
| `src/erk/tui/commands/registry.py`    | Command definitions and availability predicates                |
| `src/erk/tui/commands/types.py`       | `CommandDefinition`, `CommandContext` types                    |
| `src/erk/tui/app.py`                  | Handler implementations in `ErkDashApp` and `PlanDetailScreen` |
| `tests/tui/commands/test_registry.py` | Registry unit tests                                            |

## Null Guard Patterns for Optional Fields

Commands that depend on optional `PlanRowData` fields (like `pr_number`, `pr_url`, `issue_url`) require **three-layer validation** to prevent `None` errors:

### Layer 1: Registry Availability Predicate

The registry predicate controls whether the command appears in the palette. This filters the UI but isn't sufficient alone.

```python
# In registry.py
CommandDefinition(
    id="land_pr",
    name="Action: Land PR",
    # Layer 1: Hide command when no PR
    is_available=lambda ctx: ctx.row.pr_number is not None,
)
```

### Layer 2: Handler Guard Check

The handler must validate **again** before using the field. The registry predicate only runs when building the palette, but handlers can be called through other paths (keyboard shortcuts, programmatic invocation).

```python
# In app.py execute_palette_command()
elif command_id == "land_pr":
    # Layer 2: Guard before using pr_number
    if row.pr_number is not None:
        self.run_streaming_command(["erk", "pr", "land", str(row.pr_number)])
```

### Layer 3: App-Level Helper Pattern (Optional)

For complex commands, extract validation into a helper that encapsulates all guards:

```python
def _copy_checkout_command(self, row: PlanRowData) -> None:
    """Copy checkout command with proper fallback chain."""
    # Layer 3: Encapsulated validation
    if row.worktree_name:
        cmd = f"erk br co {row.worktree_name}"
    elif row.pr_number is not None:
        cmd = f"erk pr co {row.pr_number}"
    else:
        cmd = f"erk br co {row.pr_head_branch or 'unknown'}"

    self._provider.clipboard.copy(cmd)
```

### Why Three Layers?

1. **Registry predicate** can become stale if data changes between palette open and command execution
2. **Keyboard shortcuts** may bypass the palette entirely
3. **Type narrowing** doesn't persist across method boundaries - Python can't prove the field is still non-None

### Common Optional Fields

| Field           | Type | Null When |
| --------------- | ---- | --------- | ---------------------------- |
| `pr_number`     | `int | None`     | No PR linked to plan         |
| `pr_url`        | `str | None`     | No PR linked to plan         |
| `issue_url`     | `str | None`     | Plan not yet saved to GitHub |
| `worktree_name` | `str | None`     | No local worktree exists     |
| `run_url`       | `str | None`     | No GitHub Actions run        |

## Remote Workflow Commands

Remote workflow commands dispatch GitHub Actions workflows instead of executing locally. Examples include `fix_conflicts_remote` and `address_remote`.

### Characteristics

- **Trigger mechanism**: Call `erk pr <action>-remote <pr_number>` CLI command
- **Execution model**: Local CLI triggers GitHub workflow dispatch, actual work happens remotely
- **Output pattern**: Uses streaming subprocess to show dispatch status and workflow URL
- **No local modifications**: The command only triggers remote execution, doesn't change local state

### Registry Pattern

```python
CommandDefinition(
    id="address_remote",
    name="Address Remote",
    description="Launch remote PR review addressing",
    category=CommandCategory.ACTION,
    shortcut=None,  # Remote commands typically don't have shortcuts
    is_available=lambda ctx: ctx.row.pr_number is not None,
    get_display_name=lambda ctx: f"erk pr address-remote {ctx.row.pr_number}",
)
```

### Handler Pattern

Remote workflow handlers use streaming subprocess execution with the CLI command:

```python
elif command_id == "address_remote":
    if row.pr_number is not None and self._repo_root is not None:
        self.run_streaming_command(
            ["erk", "pr", "address-remote", str(row.pr_number)],
            cwd=self._repo_root,
            title=f"Address Remote PR #{row.pr_number}",
        )
```

### Key Differences from Local Streaming Commands

| Aspect        | Local Streaming        | Remote Workflow                      |
| ------------- | ---------------------- | ------------------------------------ |
| Execution     | Runs in subprocess     | Triggers GitHub Actions              |
| Duration      | Full command time      | Only dispatch time                   |
| Output        | Command output         | Dispatch confirmation + workflow URL |
| State changes | May modify local files | No local modifications               |

### Model Parameter Passing

Remote workflows that spawn Claude agents may need model selection. The pattern:

1. CLI command accepts `--model` flag
2. Workflow dispatch passes model as input parameter
3. Remote agent uses specified model

For TUI commands needing model selection, add a dialog before dispatch or use a sensible default.

## Related Topics

- [plan-row-data.md](plan-row-data.md) - Field reference for availability predicates
- [streaming-output.md](streaming-output.md) - Streaming output panel details
- [command-palette.md](command-palette.md) - Command palette implementation
- [command-execution.md](command-execution.md) - Execution strategy decision matrix
