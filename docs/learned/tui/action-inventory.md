---
title: TUI Action Command Inventory
read_when:
  - "adding actions to the dashboard"
  - "understanding TUI command execution patterns"
  - "replicating TUI functionality in another frontend"
---

# TUI Action Command Inventory

Complete inventory of all TUI commands, their availability predicates, execution patterns, and keyboard shortcuts. Essential for building alternate frontends that need to replicate TUI functionality.

## Command Categories

Commands are organized into 3 categories:

| Category | Emoji | Count | Purpose                                         |
| -------- | ----- | ----- | ----------------------------------------------- |
| ACTION   | ⚡    | 5     | Mutative operations (close, submit, land, etc.) |
| OPEN     | 🔗    | 3     | Browser navigation                              |
| COPY     | 📋    | 6     | Clipboard operations                            |

**Total:** 14 commands

## ACTION Commands (5)

Mutative operations that change state.

### 1. close_plan

**Display:** `erk plan close <issue_number>`
**Shortcut:** None
**Availability:** Always available
**Execution:** In-process HTTP (fast, <500ms)

Closes the plan issue and any linked PRs.

```python
is_available=lambda _: True
```

### 2. submit_to_queue

**Display:** `erk plan submit <issue_number>`
**Shortcut:** `s`
**Availability:** Plan has an issue URL
**Execution:** In-process HTTP (fast, <500ms)

Submits the plan to the remote implementation queue.

```python
is_available=lambda ctx: ctx.row.issue_url is not None
```

### 3. land_pr

**Display:** `erk land <pr_number>`
**Shortcut:** None
**Availability:** Plan has open PR with workflow run
**Execution:** Subprocess streaming (long-running, up to 600s)

Lands the PR (merges and cleans up).

```python
is_available=lambda ctx: (
    ctx.row.pr_number is not None
    and ctx.row.pr_state == "OPEN"
    and ctx.row.run_url is not None
)
```

**Execution Pattern:** Streaming subprocess with 600s timeout (10 minutes). Must handle multi-line output and status updates.

### 4. fix_conflicts_remote

**Display:** `erk launch pr-fix-conflicts --pr <pr_number>`
**Shortcut:** `5`
**Availability:** Plan has a PR
**Execution:** Subprocess streaming (long-running, up to 600s)

Launches remote conflict resolution for the PR.

```python
is_available=lambda ctx: ctx.row.pr_number is not None
```

**Execution Pattern:** Streaming subprocess with 600s timeout.

### 5. address_remote

**Display:** `erk launch pr-address --pr <pr_number>`
**Shortcut:** None
**Availability:** Plan has a PR
**Execution:** Subprocess streaming (long-running, up to 600s)

Launches remote PR review comment addressing.

```python
is_available=lambda ctx: ctx.row.pr_number is not None
```

**Execution Pattern:** Streaming subprocess with 600s timeout.

## OPEN Commands (3)

Browser navigation commands. All execute instantly by opening URLs.

### 6. open_issue

**Display:** `<issue_url>`
**Shortcut:** `i`
**Availability:** Plan has an issue URL
**Execution:** Browser launch (instant)

Opens the GitHub issue in the default browser.

```python
is_available=lambda ctx: ctx.row.issue_url is not None
```

### 7. open_pr

**Display:** `<pr_url>`
**Shortcut:** `p`
**Availability:** Plan has a PR URL
**Execution:** Browser launch (instant)

Opens the PR (GitHub or Graphite) in the default browser.

```python
is_available=lambda ctx: ctx.row.pr_url is not None
```

### 8. open_run

**Display:** `<run_url>`
**Shortcut:** `r`
**Availability:** Plan has a workflow run URL
**Execution:** Browser launch (instant)

Opens the GitHub Actions run page in the default browser.

```python
is_available=lambda ctx: ctx.row.run_url is not None
```

## COPY Commands (6)

Clipboard operations for command composition. All execute instantly.

### 9. copy_checkout

**Display:** `erk br co <branch>` or `erk pr co <pr_number>`
**Shortcut:** `c`
**Availability:** Plan has a worktree branch
**Execution:** Clipboard copy (instant)

Copies branch checkout command to clipboard.

```python
is_available=lambda ctx: ctx.row.worktree_branch is not None
```

**Display Logic:**

- If `worktree_branch` exists: `erk br co {worktree_branch}`
- Else if `pr_number` exists: `erk pr co {pr_number}`
- Else: `erk br co <branch>`

### 10. copy_pr_checkout

**Display:** `source "$(erk pr checkout <pr_number> --script)" && erk pr sync --dangerous`
**Shortcut:** `e`
**Availability:** Plan has a PR
**Execution:** Clipboard copy (instant)

Copies PR checkout + sync command to clipboard.

```python
is_available=lambda ctx: ctx.row.pr_number is not None
```

### 11. copy_prepare

**Display:** `erk prepare <issue_number>`
**Shortcut:** `1`
**Availability:** Always available
**Execution:** Clipboard copy (instant)

Copies prepare command to clipboard.

```python
is_available=lambda _: True
```

### 12. copy_prepare_activate

**Display:** `source "$(erk prepare <issue_number> --script)" && erk implement --dangerous`
**Shortcut:** `4`
**Availability:** Always available
**Execution:** Clipboard copy (instant)

Copies prepare + implement command to clipboard.

```python
is_available=lambda _: True
```

### 13. copy_submit

**Display:** `erk plan submit <issue_number>`
**Shortcut:** `3`
**Availability:** Always available
**Execution:** Clipboard copy (instant)

Copies submit command to clipboard.

```python
is_available=lambda _: True
```

### 14. copy_replan

**Display:** `erk plan replan <issue_number>`
**Shortcut:** `6`
**Availability:** Plan has an issue URL
**Execution:** Clipboard copy (instant)

Copies replan command to clipboard.

```python
is_available=lambda ctx: ctx.row.issue_url is not None
```

## Execution Patterns

Three execution patterns across all commands:

### In-Process HTTP (2 commands)

Fast operations that make HTTP calls and return immediately.

- `close_plan`
- `submit_to_queue`

**Characteristics:**

- Complete in <500ms
- No streaming output
- Simple success/failure feedback

### Subprocess Streaming (3 commands)

Long-running operations that stream output in real-time.

- `land_pr`
- `fix_conflicts_remote`
- `address_remote`

**Characteristics:**

- Run for up to 600 seconds (10 minutes)
- Stream output line-by-line
- Require progress indication
- Must handle cross-thread UI updates in Textual

### Browser Launch (3 commands)

Instant operations that open URLs in the default browser.

- `open_issue`
- `open_pr`
- `open_run`

**Characteristics:**

- Execute instantly
- No feedback needed (browser window opens)

### Clipboard Copy (6 commands)

Instant operations that copy text to the system clipboard.

- `copy_checkout`
- `copy_pr_checkout`
- `copy_prepare`
- `copy_prepare_activate`
- `copy_submit`
- `copy_replan`

**Characteristics:**

- Execute instantly
- Brief success notification (e.g., "Copied to clipboard")

## Command Context

All commands receive a `CommandContext` object containing:

```python
@dataclass(frozen=True)
class CommandContext:
    row: PlanRowData           # The selected plan row
    provider: PlanDataProvider # Data provider for executing actions
```

This gives commands access to:

- All 40 fields from the selected `PlanRowData` row
- The `PlanDataProvider` interface for fetching additional data
- Clipboard and browser launcher interfaces

## Dual-Handler Pattern

The TUI implements a dual-handler pattern for command execution:

1. **Main List Screen:** Executes commands from the plan table view
2. **Detail Modal:** Shows plan details and executes the same commands

Both handlers use the same `CommandDefinition` registry and availability predicates, ensuring consistency.

**Implementation Note:** The detail modal is being replaced with the right pane in the desktop dashboard, but the command execution logic remains the same.

## Keyboard Shortcuts

| Shortcut | Command               | Category |
| -------- | --------------------- | -------- |
| `s`      | submit_to_queue       | ACTION   |
| `5`      | fix_conflicts_remote  | ACTION   |
| `i`      | open_issue            | OPEN     |
| `p`      | open_pr               | OPEN     |
| `r`      | open_run              | OPEN     |
| `c`      | copy_checkout         | COPY     |
| `e`      | copy_pr_checkout      | COPY     |
| `1`      | copy_prepare          | COPY     |
| `3`      | copy_submit           | COPY     |
| `4`      | copy_prepare_activate | COPY     |
| `6`      | copy_replan           | COPY     |

**Note:** Not all commands have shortcuts. Some are only accessible via the command palette or context menus.

## Desktop Dashboard Implications

When implementing commands in the desktop dashboard:

1. **Availability Predicates:** Same logic applies for showing/hiding toolbar buttons and context menu items
2. **Execution Patterns:** Need different UI feedback for each pattern:
   - In-process: Brief loading indicator
   - Streaming: Drawer with live output
   - Browser: No feedback (window opens)
   - Clipboard: Toast notification
3. **No Keyboard Shortcuts Initially:** Desktop dashboard prioritizes GUI-native actions (toolbar, context menus). Add command palette later if needed.
4. **Right Pane Replaces Modal:** Detail view lives in the right pane, not a modal dialog

## Related Documentation

- [TUI Data Contract Reference](data-contract.md) - PlanRowData fields that commands operate on
- [TUI Command Execution](command-execution.md) - Implementation details of execution patterns
- [TUI Streaming Output](streaming-output.md) - Cross-thread UI updates for streaming commands
- [Desktop Dashboard Interaction Model](../desktop-dash/interaction-model.md) - How commands translate to desktop UI
