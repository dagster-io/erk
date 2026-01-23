---
title: TUI Interaction Patterns
read_when:
  - "adding clickable cells to TUI tables"
  - "implementing message-driven interactions in Textual"
  - "handling click events in TUI widgets"
---

# TUI Interaction Patterns

Patterns for implementing interactive cells and message-driven behaviors in the erk TUI.

## Overview

The erk TUI uses a message-driven architecture for communication between widgets and the app. This enables loose coupling between UI components and central command handling.

## Click-to-Open Pattern

Used by objective, PR, and issue cells. A standard pattern for clickable table cells that open URLs in the browser.

### Pattern Components

#### 1. Message Class

Define a message class nested inside the widget. The message carries just enough data to identify what was clicked:

```python
class PlanDataTable(DataTable):
    class ObjectiveClicked(Message):
        """Posted when user clicks objective column on a row with an objective issue."""
        def __init__(self, row_index: int) -> None:
            super().__init__()
            self.row_index = row_index
```

Keep messages minimal—just enough to identify the source. Other data retrieval happens in the handler.

#### 2. Click Detection in Widget

In the widget's `on_click()` handler, detect which column was clicked and validate:

```python
@on(DataTable.RowSelected)
def on_click(self, event: Click) -> None:
    # Determine column by checking stored column index
    if self._objective_column_index is None or col_index != self._objective_column_index:
        return

    # Validate data exists before posting message
    row = self._rows[row_index] if row_index < len(self._rows) else None
    if row is None or row.objective_issue is None:
        return

    # Post message for app to handle
    self.post_message(self.ObjectiveClicked(row_index))
```

**Validation Requirements:**

1. Column index matches expected column
2. Row index is within bounds
3. Data field is not None (e.g., `objective_issue is not None`)

#### 3. App-Level Event Handler

The app handles the message with an `@on` decorator. The handler performs side effects (browser launch, status feedback):

```python
@on(PlanDataTable.ObjectiveClicked)
def on_objective_clicked(self, event: PlanDataTable.ObjectiveClicked) -> None:
    """Handle click on objective cell - open objective issue in browser."""
    if event.row_index < len(self._rows):
        row = self._rows[event.row_index]
        if row.objective_issue is not None and row.issue_url:
            # Construct URL and open in browser
            objective_url = _build_github_url(row.issue_url, "issues", row.objective_issue)
            self._provider.browser.launch(objective_url)

            # Provide user feedback
            if self._status_bar is not None:
                self._status_bar.set_message(f"Opened objective #{row.objective_issue}")
```

### Why This Pattern?

- **Separation of concerns:** Widget detects clicks, app handles actions
- **Testability:** Message posting can be verified without side effects
- **Extensibility:** New click behaviors can be added in app without changing widget

## Cell Styling Convention

Interactive cells use conditional styling to signal to users that they're clickable:

```python
def _row_to_values(self, row: PlanRowData) -> list[str | Text]:
    # Non-clickable: return as string
    if row.objective_issue is None:
        objective_cell = row.objective_display  # "-"
    else:
        # Clickable: wrap in Text with styling
        objective_cell = Text(row.objective_display, style="cyan underline")

    return [..., objective_cell, ...]
```

**Styling Conventions:**

| Cell Type     | Has Data       | No Data |
| ------------- | -------------- | ------- |
| Objective     | cyan underline | "-"     |
| PR            | cyan underline | "-"     |
| Issue         | cyan underline | N/A     |
| Non-clickable | plain string   | "-"     |

This pattern provides visual feedback: only underlined cells respond to clicks.

## Status Bar Feedback

After performing a click action, provide feedback to the user via the status bar:

```python
self._status_bar.set_message(f"Opened objective #{row.objective_issue}")
```

**Format Convention:** `"Opened <thing> #<number>"`

Examples:
- "Opened objective #42"
- "Opened PR #156"
- "Opened issue #789"

## Message Pattern (General)

Textual uses a message-driven architecture. Messages are the primary way widgets communicate with the app.

### Defining Messages

Messages are nested classes inside widgets:

```python
class PlanDataTable(DataTable):
    class ObjectiveClicked(Message):
        def __init__(self, row_index: int) -> None:
            self.row_index = row_index
            super().__init__()

    class PRClicked(Message):
        def __init__(self, row_index: int) -> None:
            self.row_index = row_index
            super().__init__()
```

### Posting Messages

Widgets post messages when events occur:

```python
# In widget event handler
self.post_message(self.ObjectiveClicked(row_index))
```

### Handling Messages

The app handles messages with `@on` decorators:

```python
# In app class
@on(PlanDataTable.ObjectiveClicked)
def on_objective_clicked(self, event: PlanDataTable.ObjectiveClicked) -> None:
    # Handle the event
    pass

@on(PlanDataTable.PRClicked)
def on_pr_clicked(self, event: PlanDataTable.PRClicked) -> None:
    # Handle the event
    pass
```

### Message Data Design

Keep message data minimal—just identification:

- `row_index` for table row actions
- `command_id` for command completions
- `modal_result` for modal confirmations

Don't pass entire data objects. Handlers can retrieve data they need from the app state.

## Related Topics

- [architecture.md](architecture.md) - Overall TUI architecture and data flow
- [plan-row-data.md](plan-row-data.md) - PlanRowData field reference
- [adding-commands.md](adding-commands.md) - How to add new TUI commands
