# Textual Dash - Interactive TUI for erk

## Purpose

Textual Dash provides an interactive terminal UI for the `erk dash` command, enabling keyboard-driven navigation through plan lists with quick actions. It's an alternative to the static table output and watch mode, optimized for users managing many plans.

**Invocation**: `erk dash -i` or `erk dash --interactive`

## Architecture Overview

```
src/erk/tui/
├── AGENTS.md              # This file
├── TEXTUAL_QUIRKS.md      # API quirks and workarounds (READ THIS)
├── __init__.py
├── app.py                 # ErkDashApp - main Textual application
├── data/
│   ├── __init__.py
│   ├── provider.py        # PlanDataProvider ABC + RealPlanDataProvider
│   └── types.py           # PlanRowData, PlanFilters dataclasses
├── widgets/
│   ├── __init__.py
│   ├── plan_table.py      # PlanDataTable - DataTable subclass
│   └── status_bar.py      # StatusBar - footer with stats and hints
└── styles/
    └── dash.tcss          # Textual CSS styles
```

## Key Components

### ErkDashApp (`app.py`)

The main Textual `App` subclass. Responsibilities:

- Compose layout (Header, PlanDataTable, StatusBar)
- Handle keyboard bindings (q, r, Enter, o, p, i, ?, j/k)
- Manage auto-refresh timer and countdown
- Coordinate data loading via workers

**Key bindings**:
| Key | Action |
|-----|--------|
| `q` / `Esc` | Quit |
| `r` | Refresh data (resets countdown) |
| `Enter` / `o` | Open issue in browser |
| `p` | Open PR in browser |
| `i` | Show implement command |
| `?` | Show help overlay |
| `j` / `k` | Vim-style navigation |

### PlanDataProvider (`data/provider.py`)

ABC defining data fetching interface. Enables testing with fakes.

- `PlanDataProvider` - Abstract base class
- `RealPlanDataProvider` - Production implementation wrapping `PlanListService`

The provider transforms `PlanListData` from the service layer into `PlanRowData` tuples optimized for table display.

### PlanRowData (`data/types.py`)

Immutable dataclass containing:

- Raw data for actions (issue_number, issue_url, pr_number, pr_url)
- Pre-formatted display strings (title, pr_display, checks_display, etc.)

### PlanDataTable (`widgets/plan_table.py`)

DataTable subclass with:

- Row selection mode (not cell selection)
- Column setup based on filter flags
- Cursor position preservation on refresh
- Left/right arrow disabled (row mode only)

### StatusBar (`widgets/status_bar.py`)

Footer widget showing:

- Plan count
- Last update time with fetch duration
- Countdown to next refresh
- Key binding hints

## Data Flow

```
1. erk dash -i
   └── _run_interactive_mode()
       └── Creates RealPlanDataProvider with ErkContext
       └── Creates ErkDashApp(provider, filters, interval)
       └── app.run()

2. On mount:
   └── run_worker(_load_data())
       └── provider.fetch_plans(filters)  # In executor thread
       └── _update_table(rows, time, duration)
           └── table.populate(rows)
           └── status_bar.set_plan_count()
           └── status_bar.set_last_update()

3. Auto-refresh (every N seconds):
   └── _tick_countdown() decrements counter
   └── When 0: action_refresh()
       └── Resets countdown
       └── run_worker(_load_data())

4. User actions:
   └── Enter/o → action_open_issue() → click.launch(url)
   └── p → action_open_pr() → click.launch(url)
   └── r → action_refresh() → reload data
```

## Testing Strategy

Tests live in `tests/tui/`:

- `test_plan_table.py` - Unit tests for table widget and row conversion
- `test_app.py` - Textual pilot-based integration tests

**Fake infrastructure** in `tests/fakes/plan_data_provider.py`:

- `FakePlanDataProvider` - Returns canned data, tracks fetch count
- `make_plan_row()` - Helper to create test PlanRowData

**Testing pattern**:

```python
@pytest.mark.asyncio
async def test_something(self) -> None:
    provider = FakePlanDataProvider([make_plan_row(123, "Test")])
    app = ErkDashApp(provider, PlanFilters.default(), refresh_interval=0)

    async with app.run_test() as pilot:
        await pilot.pause()  # Wait for async load
        # assertions...
```

## Important: Read TEXTUAL_QUIRKS.md

Before modifying this code, read `TEXTUAL_QUIRKS.md` which documents:

- DataTable `cursor_type` initialization pattern
- Naming conflicts to avoid (`_filters`)
- Cursor position preservation on `clear()`
- Enter key handling via `RowSelected` event
- `action_quit` override issues
- Footer vs custom StatusBar conflicts
- Async data loading patterns
- pytest-asyncio configuration

## Design Decisions

### Why Row Selection Mode?

Cell selection adds complexity (left/right navigation) without benefit for this use case. Users care about selecting a plan, not a specific column.

### Why Separate PlanDataProvider?

1. **Testability**: FakePlanDataProvider enables fast tests without API calls
2. **Separation of concerns**: TUI code doesn't know about PlanListService internals
3. **Future flexibility**: Could add caching, filtering, or alternative data sources

### Why No Footer Widget?

Textual's built-in `Footer` shows BINDINGS but conflicts with custom status bars. Our `StatusBar` provides richer information (countdown, timing, messages) in a single line.

### Why `-i` Implies `-a`?

Interactive mode benefits from seeing all columns. Users navigating with keyboard want full context without remembering to add flags.

## Adding Features

### New Key Binding

1. Add to `BINDINGS` list in `ErkDashApp`
2. Implement `action_*` method
3. Update status bar hints in `StatusBar._update_display()`
4. Update help screen in `HelpScreen.compose()`

### New Column

1. Add field to `PlanRowData` in `types.py`
2. Update `RealPlanDataProvider._build_row_data()` to populate it
3. Add column in `PlanDataTable._setup_columns()` (check filter flags)
4. Add value in `PlanDataTable._row_to_values()`
5. Update `make_plan_row()` helper in test fakes

### New Status Bar Info

1. Add field and setter to `StatusBar`
2. Update `_update_display()` to include in output
3. Call setter from `ErkDashApp` at appropriate time
