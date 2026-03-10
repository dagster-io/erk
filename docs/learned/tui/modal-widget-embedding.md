---
title: Modal Widget Embedding Pattern
read_when:
  - "reusing PlanDataTable in a modal screen"
  - "embedding complex widgets in Textual modal screens"
  - "handling null safety for optional gateway fields in TUI"
tripwires:
  - action: "passing id= kwarg to PlanDataTable constructor"
    warning: "PlanDataTable does not support the id= keyword argument. Use CSS selectors or widget references instead."
  - action: "accessing optional gateway fields without null checks in TUI event handlers"
    warning: "Gateway fields like plan_body or objective_content may be None. Always check before accessing in event handlers."
  - action: "implementing on_key() in a modal without calling event.prevent_default() and event.stop()"
    warning: "Modal on_key() must call event.prevent_default() and event.stop() BEFORE any logic. Without this, keystrokes leak to the underlying view and trigger unintended actions."
  - action: "implementing modal dismiss with an inverted key check condition"
    warning: "Dismiss-on-unhandled pattern: if event.key not in (bound_keys): self.dismiss(). Using the inverted condition (if key in bound_keys: dismiss) is a common bug that dismisses on valid keys instead of unrecognized ones."
curated_in: erk-tui
---

# Modal Widget Embedding Pattern

Pattern for reusing complex widgets (like PlanDataTable) inside modal screens. Based on the ObjectivePlansScreen implementation that embeds PlanDataTable in a modal dialog.

## The Pattern

When a screen needs to display a subset of data using an existing table widget:

1. **Create the modal screen** extending `ModalScreen` or `Screen`
2. **Instantiate the widget** without custom ID (PlanDataTable limitation)
3. **Configure the widget** for the modal context (different columns, filtered data)
4. **Handle events** from the embedded widget within the modal screen

## PlanDataTable ID Limitation

`PlanDataTable` does not accept an `id=` keyword argument in its constructor. This means:

- Cannot use `self.query_one("#my-table")` to find it
- Use direct widget references or `self.query_one(PlanDataTable)` instead

## Null Safety for Optional Fields

When working with data from gateway responses in event handlers:

```python
# Gateway fields may be None
if row_data.plan_body is not None:
    self.show_plan_content(row_data.plan_body)
else:
    self.notify("Plan content not available")
```

Always guard optional fields before use — modal screens often operate on partially-loaded data.

## Event Handler Testing

Testing event handlers in Textual modal screens:

1. Mount the screen in a test app
2. Simulate the event (key press, click)
3. Assert on the resulting state or pushed screen

## Source Code

- `src/erk/tui/app.py` — `action_toggle_objective_filter()` implements the inline objective filter

## Related Documentation

- [TUI View Switching](view-switching.md) — How PlanDataTable is used in the main app
