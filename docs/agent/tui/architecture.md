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

Abstract interface for fetching plan data. Follows the same ABC/Fake pattern as integrations.

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
| PR          | `pr_display`          | `#456 👀` with status emoji |
| Checks      | `checks_display`      | `✓` or `✗`                  |
| Worktree    | `worktree_name`       | Name or empty               |
| Local Impl  | `local_impl_display`  | `2h ago`                    |
| Remote Impl | `remote_impl_display` | `1d ago`                    |

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
