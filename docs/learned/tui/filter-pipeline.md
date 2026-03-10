---
title: TUI Filter Pipeline Pattern
read_when:
  - "adding a new filter to the TUI dashboard"
  - "understanding how objective/stack/text filters interact"
  - "modifying the escape key behavior in the TUI"
tripwires:
  - action: "adding a new filter without updating the escape chain"
    warning: "New filter implementations must add an entry to `action_exit_app()` progressive escape chain. Missing entries leave filters stuck with no way for the user to clear them."
  - action: "changing filter application order in _apply_filter_and_sort()"
    warning: "Filter order is intentional: objective → stack → text → sort. Objective is broadest (cross-stack), stack is mid-level, text is narrowest. Changing order produces unexpected results."
  - action: "using a mutable set for _stack_filter_branches"
    warning: "Stack filter branches use frozenset[str] for immutability and efficient membership testing. Do not use set or list."
curated_in: erk-tui
---

# TUI Filter Pipeline Pattern

The TUI dashboard applies filters in a defined pipeline sequence: objective filter, stack filter, text filter, then sort. Each filter follows the same toggle pattern with state variables, toggle actions, and escape chain integration.

## Filter Pipeline

`_apply_filter_and_sort()` in `src/erk/tui/app.py` applies filters in sequence:

1. **Objective filter**: Filters rows matching `_objective_filter_issue`
2. **Stack filter**: Filters rows matching branches in `_stack_filter_branches`
3. **Text filter**: Applies text search query if `FilterMode.ACTIVE`
4. **Sort**: Sorts using `SortKey` (supports `BranchActivity` ordering)

## State Variables

State variables are defined in `src/erk/tui/app.py` for each filter:

- **Objective filter**: Stores the selected issue number (or `None` when inactive) and a display label for the status bar
- **Stack filter**: Stores branch names in the active stack (as a frozenset for immutability) and the head branch name for display
- **Text filter**: Stores the search query and active mode

Each filter has a state variable and optional label variable for status bar display.

## Toggle Pattern

Each filter follows the same pattern:

1. **State variable**: Stores filter criteria or `None` when inactive
2. **Label variable**: Stores display text for the status bar
3. **Toggle action**: Sets filter if inactive, clears if already active on the same item
4. **Clear method**: Resets state to `None` and reapplies the filter pipeline

Key bindings:

- `o`: `action_toggle_objective_filter()`
- `t`: `action_toggle_stack_filter()`

## Progressive Escape Chain

`action_exit_app()` in `src/erk/tui/app.py` clears filters in order (most specific first):

1. **Objective filter**: Clear if set, return
2. **Stack filter**: Clear if set, return
3. **Text content**: Clear text input if active, transition to `INACTIVE`
4. **Quit app**: `self.exit()`

Each step returns early, so pressing Escape repeatedly peels back one filter layer at a time.

## Gateway Query Delegation

`get_branch_stack(branch)` in the `PlanDataProvider` ABC returns `list[str] | None` — the ordered branch names in a Graphite stack, or `None` if the branch is not in a stack.

Called in `action_toggle_stack_filter()` to populate `_stack_filter_branches`.

## View Switching Clears Filters

When switching views in `src/erk/tui/app.py`, all objective and stack filters are cleared to prevent confusion across different data contexts.

## Related Documentation

- [TUI Streaming Output](streaming-output.md) — Cross-thread UI updates pattern
- [Modal Widget Embedding](modal-widget-embedding.md) — Objective filter in modal context
