---
name: erk-tui-commands
description: Command registration, dual-handler pattern, categories, view-aware filtering
---

# TUI Command System

**Read this when**: Adding or modifying TUI commands, working with the command palette, or implementing command execution.

## 3-Place Registration

Adding a command requires updating THREE places in `src/erk/tui/commands/registry.py`:

1. **Display formatter** (`_display_*()` function): Generates context-aware display name
2. **CommandDefinition entry**: ID, category, availability predicate, display getter, launch key
3. **Action inventory**: Appears in correct category group, alphabetically sorted

`launch_key` field on `CommandDefinition` is the single source of truth for Launch modal key bindings.

## Category Semantics

| Category | Icon | Behavior                      | Examples                |
| -------- | ---- | ----------------------------- | ----------------------- |
| `ACTION` | ⚡   | Mutative, may be long-running | close, dispatch, land   |
| `OPEN`   | 🔗   | Browser navigation, instant   | open issue, open PR     |
| `COPY`   | 📋   | Clipboard write, instant      | copy URL, copy checkout |

**Rule**: Instant operations belong in OPEN or COPY, not ACTION.

## Dual-Handler Pattern

Commands are defined once in the registry but executed in TWO contexts:

1. **Main list** → `ErkDashApp.execute_palette_command()` (accesses `self._provider` directly)
2. **Detail modal** → `PlanDetailScreen.execute_command()` (uses injected `CommandExecutor`)

This duplication in execution handlers is intentional. The asymmetry exists because:

- The app operates at the app level (managing screens, toasts)
- The modal is scoped to a single plan
- Different APIs are available in each context

**Two providers share one registry**:

- `MainListCommandProvider`: Resolves `CommandContext` from table's selected row, reads `view_mode` dynamically
- `PlanCommandProvider`: Resolves from detail screen's `_row` field, hardcodes `view_mode=ViewMode.PLANS`

## Three-Layer Validation

Commands that depend on nullable `PlanRowData` fields require validation at three levels:

1. **Registry predicate** (`is_available` lambda): Controls palette visibility
2. **Handler guard** (LBYL check in execute method): Re-validates before use
3. **App-level helper** (optional): Encapsulates all guards and fallbacks

**Why three?** Predicates can become stale, keyboard shortcuts bypass the palette, and type narrowing doesn't persist across method boundaries.

## Availability Tiers

| Tier               | Predicate                     | Examples                                            |
| ------------------ | ----------------------------- | --------------------------------------------------- |
| Always             | `lambda _: True`              | `close_plan` (only needs `plan_id`, always present) |
| Needs plan URL     | `plan_url is not None`        | `open_issue`                                        |
| Needs local branch | `worktree_branch is not None` | `copy_checkout`                                     |
| Needs PR           | `pr_number is not None`       | `open_pr`, `rebase_remote`                          |
| Compound           | Multiple fields non-null      | `land_pr`                                           |

**Anti-pattern**: Writing `is_available=lambda _: True` for a command that uses `ctx.row.pr_number`. The command appears when `pr_number` is None, causing runtime errors.

## View-Aware Filtering

View mode and data availability are two independent filter dimensions.

**View predicates**:

- `_is_plan_view(ctx)`: True when NOT in Objectives view (Plans or Learn)
- `_is_objectives_view(ctx)`: True when in Objectives view

**Shortcut reuse**: Plan and objective commands safely reuse shortcuts because view predicates guarantee mutual exclusivity. Example: `s` maps to "Dispatch to Queue" (Plans) and "Implement (One-Shot)" (Objectives).

**Backend as third dimension**: `plan_backend` field on `CommandContext` enables backend-specific filtering.

## Clipboard Text Generation

`get_copy_text(command_id, row, view_mode)` in `registry.py` is the ONLY place clipboard text is generated.

Display name generators on `CommandDefinition` are canonical. `get_copy_text()` looks up the command and delegates to its display generator. Both main list and detail screen call this same function.

**Anti-pattern**: Duplicating display name logic in app.py or detail screens.

## Dual-Handler Asymmetries

Despite sharing command definitions, the two contexts have critical differences:

| Aspect             | MainListCommandProvider                                     | PlanCommandProvider                                                 |
| ------------------ | ----------------------------------------------------------- | ------------------------------------------------------------------- |
| Context resolution | Returns `CommandContext \| None` (no row selected)          | Returns `CommandContext` (always has `_row`)                        |
| Dispatch target    | `ErkDashApp.execute_palette_command()` via `self._provider` | `PlanDetailScreen.execute_command()` via injected `CommandExecutor` |
| ViewMode           | Reads `_view_mode` dynamically (supports Objectives)        | Hardcodes `ViewMode.PLANS` (detail is always plan context)          |

The dispatch duplication is intentional — app-level concerns (managing screens, toasts) differ from modal-level concerns (using executor, dismissing).

**When this breaks**: Commands needing two-step push-then-execute (push detail screen, then stream) only work at app level. Commands like `close_plan` have different orchestration per context (modal dismisses first, then delegates).

## Command Execution Strategies

Two execution strategies, chosen by `repo_root` availability:

| Context              | Strategy             | Reason                       |
| -------------------- | -------------------- | ---------------------------- |
| TUI with `repo_root` | Streaming subprocess | User needs progress feedback |
| TUI without context  | Disabled/notify      | Cannot execute safely        |
| Unit tests           | FakeCommandExecutor  | Fast, deterministic          |
| Script mode          | Executor pattern     | Simpler, no UI               |

`repo_root` acts as a capability marker on `PlanDetailScreen.__init__()`. Present → streaming execution available. Absent → commands disabled.

**stdin deadlock**: Child processes inherit TUI's stdin. If a child prompts for input, both TUI and child block on the same TTY. **Always** use `stdin=subprocess.DEVNULL`. This means commands requiring confirmation must be handled via TUI dialogs first, then run with `--force`/`--yes`.

## CommandPalette Integration

`get_system_commands()` must be overridden on the **App class**, not Screen class. Textual calls `app.get_system_commands(screen)` — it never calls this method on screens.

```python
# WRONG — never called by Textual
class MyModalScreen(ModalScreen):
    def get_system_commands(self, screen): ...

# CORRECT — override on App
class MyApp(App):
    def get_system_commands(self, screen): ...
```

## Keyboard Shortcut Inventory

Key groups in `ErkDashApp.BINDINGS` (`src/erk/tui/app.py`):

- **Navigation**: j/k (vim-style), escape (quit)
- **View Switching**: 1/2/3 (direct), left/right (cycle)
- **Filters**: o (objective), t (stack), / (text), s (sort)
- **Item Actions**: enter/space (detail), p (open PR/objective), n (open run), c (comments), h (checks), v (view body), l (launch menu), i (implement), x (one-shot prompt)
- **System**: ctrl+p (command palette), r (refresh), ? (help), q/escape (quit)

**Launch keys** (ACTION commands only, from `CommandDefinition.launch_key` in registry.py):

- Plans: c (close), d (dispatch), l (land), r (rebase), a (address), w (rewrite), m (cmux)
- Objectives: c (close), s (one-shot), k (check)

**Naming convention**: `action_<verb>_<noun>` (e.g., `action_close_plan`, `action_open_pr`)

**Priority binding for DataTable override**: Use `priority=True` on arrow key bindings so screen handlers fire before DataTable's defaults. See `ObjectiveNodesScreen` for reference.
