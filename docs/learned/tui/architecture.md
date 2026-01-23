---
title: TUI Architecture Overview
read_when:
  - "understanding TUI structure"
  - "implementing TUI components"
  - "working with TUI data providers"
---

# TUI Architecture Overview

The erk TUI is built with Textual and follows a layered architecture separating data fetching, filtering, and rendering.

## Directory Structure

```
src/erk/tui/
├── app.py              # Main Textual App (ErkDashApp)
├── data/               # Data layer
│   ├── provider.py     # ABC + Real data providers
│   └── types.py        # Data types (PlanRowData, PlanFilters)
├── filtering/          # Filter layer
│   ├── logic.py        # Filter application logic
│   └── types.py        # Filter types
├── commands/           # Command execution layer
│   ├── executor.py     # ABC for command execution
│   ├── real_executor.py # Production executor
│   ├── provider.py     # Command provider
│   ├── registry.py     # Command registration
│   └── types.py        # Command types
└── widgets/            # UI components
    ├── plan_table.py   # Plan list table
    ├── status_bar.py   # Status bar component
    └── command_output.py # Command output display
```

## Data Layer

### PlanDataProvider (ABC)

Abstract interface for fetching plan data. Follows the same ABC/Fake pattern as gateways.

```python
class PlanDataProvider(ABC):
    @property
    @abstractmethod
    def repo_root(self) -> Path: ...

    @property
    @abstractmethod
    def clipboard(self) -> Clipboard: ...

    @property
    @abstractmethod
    def browser(self) -> BrowserLauncher: ...

    @abstractmethod
    def fetch_plans(self, filters: PlanFilters) -> list[PlanRowData]: ...

    @abstractmethod
    def close_plan(self, issue_number: int, issue_url: str) -> list[int]: ...

    @abstractmethod
    def submit_to_queue(self, issue_number: int, issue_url: str) -> None: ...
```

### RealPlanDataProvider

Production implementation that:

1. Uses `PlanListService` to fetch data from GitHub
2. Builds worktree mapping from local filesystem
3. Transforms `IssueInfo` → `Plan` → `PlanRowData`
4. Applies filtering before returning

### PlanRowData

Frozen dataclass containing both:

- **Display strings**: Pre-formatted for rendering (`pr_display`, `checks_display`, `run_state_display`)
- **Raw data**: For actions and sorting (`pr_number`, `issue_number`, timestamps)

This separation ensures:

- Table rendering is fast (no formatting during render)
- Actions have access to raw IDs/URLs
- Data is immutable (consistent table state)

### PlanFilters

Frozen dataclass specifying query filters:

```python
@dataclass(frozen=True)
class PlanFilters:
    labels: tuple[str, ...]      # Filter by labels
    state: str | None            # "open", "closed", or None
    run_state: str | None        # Filter by workflow run state
    limit: int | None            # Max results
    show_prs: bool               # Include PR data
    show_runs: bool              # Include workflow run data
```

## Command Execution Layer

See [Command Execution](command-execution.md) for detailed patterns on:

- Sync vs streaming execution
- Background thread handling
- Cross-thread UI updates

### Key Pattern: Exit-with-Command

TUI can request command execution after exit (see [Erk Architecture](../architecture/erk-architecture.md#tui-exit-with-command-pattern)):

```python
# In TUI modal
app.exit_command = "erk implement 123"
self.app.exit()

# In CLI after app.run()
if app.exit_command:
    os.execvp(args[0], args)
```

## Widget Layer

### PlanTable

DataTable subclass displaying plans with columns:

| Column      | Source                | Format                      |
| ----------- | --------------------- | --------------------------- |
| Issue       | `issue_number`        | `#123` link                 |
| Title       | `title`               | Truncated to 50 chars       |
| Objective   | `objective_display`   | `#42` or `-`                |
| PR          | `pr_display`          | `#456 👀` with status emoji |
| Checks      | `checks_display`      | `✓` or `✗`                  |
| Worktree    | `worktree_name`       | Name or empty               |
| Local Impl  | `local_impl_display`  | `2h ago`                    |
| Remote Impl | `remote_impl_display` | `1d ago`                    |

### Adding a New Column to the Plan Table

When adding a column to the plan table, follow this pattern across three layers:

#### 1. Data Layer: Extend PlanRowData

Add both raw and display fields to `src/erk/tui/data/types.py`:

```python
@dataclass(frozen=True)
class PlanRowData:
    # ... existing fields ...
    objective_issue: int | None      # Raw data for actions
    objective_display: str           # Pre-formatted for rendering
```

#### 2. Data Provider: Extract and Format

In `_build_row_data()`, extract the data and pre-format for display:

```python
# Extract objective from plan metadata
objective_issue: int | None = None
if plan.body:
    objective_issue = extract_plan_header_objective_issue(plan.body)

# Pre-format for display
objective_display = f"#{objective_issue}" if objective_issue is not None else "-"

# Include in PlanRowData
return PlanRowData(
    # ... other fields ...
    objective_issue=objective_issue,
    objective_display=objective_display,
)
```

#### 3. Widget Layer: Track Column Index and Render

In `src/erk/tui/widgets/plan_table.py`:

**Track column index:**

```python
class PlanDataTable(DataTable):
    def __init__(self, plan_filters: PlanFilters) -> None:
        # ... existing code ...
        self._objective_column_index: int | None = None
        self._pr_column_index: int | None = None
        # ... other indices ...

    def _setup_columns(self) -> None:
        col_index = 0
        self.add_column("plan", key="plan")
        col_index += 1
        self.add_column("title", key="title")
        col_index += 1

        # NEW: Add objective column
        self.add_column("obj", key="objective")
        self._objective_column_index = col_index
        col_index += 1

        # Existing columns follow
        if self._plan_filters.show_prs:
            self.add_column("pr", key="pr")
            self._pr_column_index = col_index
            col_index += 1
```

**Render cell with conditional styling:**

```python
def _row_to_values(self, row: PlanRowData) -> tuple[str | Text, ...]:
    # Format objective cell with conditional styling
    objective_cell: str | Text = row.objective_display
    if row.objective_issue is not None:
        objective_cell = Text(row.objective_display, style="cyan underline")

    # Build values list in column order
    values: list[str | Text] = [plan_cell, row.title, objective_cell]
    # ... add remaining columns ...
    return tuple(values)
```

**Handle clicks (if clickable):**

```python
def on_click(self, event: Click) -> None:
    # Check objective column - post event if objective issue exists
    if self._objective_column_index is not None and col_index == self._objective_column_index:
        if row_index < len(self._rows) and self._rows[row_index].objective_issue is not None:
            self.post_message(self.ObjectiveClicked(row_index))
            event.prevent_default()
            event.stop()
            return
    # ... handle other columns ...
```

#### 4. Update Tests

- Add parameter to `make_plan_row()` factory function
- Update column count assertions (all indices shift when a column is inserted)
- Add tests for click handling if the column is interactive

**Why Column Indices Matter:**

When a new column is inserted (e.g., objective column after title), all subsequent column indices shift:

- Before: Plan (0), Title (1), PR (2), Checks (3)
- After: Plan (0), Title (1), Objective (2), PR (3), Checks (4)

Any code that checks `col_index == 2` for PR clicks now needs to check `col_index == 3`. This is why column indices must be tracked and updated systematically throughout the widget and test code.

### Cell Rendering Patterns

#### Conditional Styling for Interactive Cells

Interactive cells use conditional styling based on data availability:

```python
def _row_to_values(self, row: PlanRowData) -> list[str | Text]:
    # Non-clickable: return string
    if row.objective_issue is None:
        objective_cell = row.objective_display  # "-"
    else:
        # Clickable: return styled Text
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

This pattern provides visual feedback to users: only underlined cells respond to clicks. See [Interaction Patterns](interaction-patterns.md) for the complete click-to-open pattern.

### Status Bar

Shows:

- Current filter state
- Refresh status
- Keyboard shortcut hints

## Testing Strategy

### Unit Testing TUI Components

Use fake providers instead of mocking:

```python
class FakePlanDataProvider(PlanDataProvider):
    def __init__(self, plans: list[PlanRowData]) -> None:
        self._plans = plans
        self._closed_plans: list[int] = []

    def fetch_plans(self, filters: PlanFilters) -> list[PlanRowData]:
        # Apply filters to in-memory plans
        return [p for p in self._plans if matches_filter(p, filters)]

    def close_plan(self, issue_number: int, issue_url: str) -> list[int]:
        self._closed_plans.append(issue_number)
        return []  # No PRs in fake
```

### Testing Async Operations

See [Textual Async Testing](textual-async.md) for patterns on testing async TUI code.

## Design Principles

1. **Frozen Data Types**: All data types are frozen dataclasses to ensure immutability during table rendering
2. **Pre-formatted Display**: Format strings at fetch time, not render time
3. **ABC Providers**: Use ABC/Fake pattern for testability (same as integrations)
4. **Layered Architecture**: Data → Filtering → Rendering separation

## Related Documentation

- [Command Execution](command-execution.md) - Sync vs streaming execution patterns
- [Streaming Output](streaming-output.md) - Real-time command output display
- [Textual Async](textual-async.md) - Async testing patterns
- [Erk Architecture](../architecture/erk-architecture.md) - Exit-with-command pattern
