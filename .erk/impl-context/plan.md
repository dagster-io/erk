# Plan: Split `tests/tui/test_app.py` into a subpackage

## Context

`tests/tui/test_app.py` is 3,107 lines with 30 test classes and 2 standalone functions.
It has grown organically as features were added to the TUI app. The file is hard to navigate
and slow to scan. Other parts of the codebase (e.g., `tests/commands/workspace/create/` with
11 focused files) demonstrate the pattern of splitting into subpackages by feature area.

## Target structure

Replace `tests/tui/test_app.py` with `tests/tui/app/` subpackage:

```
tests/tui/app/
├── __init__.py                     # Required (project convention)
├── test_app_basics.py              # ~130 lines
├── test_status_bar.py              # ~90 lines
├── test_filter_mode.py             # ~165 lines
├── test_stack_filter.py            # ~200 lines
├── test_objective_filter.py        # ~165 lines
├── test_plan_detail.py             # ~270 lines
├── test_plan_body.py               # ~245 lines
├── test_command_palette.py         # ~335 lines
├── test_streaming_commands.py      # ~260 lines
├── test_view_switching.py          # ~395 lines
├── test_actions.py                 # ~170 lines
├── test_async_pr_actions.py        # ~350 lines
└── test_async_plan_actions.py      # ~285 lines
```

## Class-to-file mapping

### `test_app_basics.py` (~130 lines)
Core app lifecycle: composition, data loading, navigation, refresh.
- `TestErkDashAppCompose` (L27–45)
- `TestErkDashAppDataLoading` (L47–92)
- `TestErkDashAppNavigation` (L95–135)
- `TestErkDashAppRefresh` (L138–158)

### `test_status_bar.py` (~90 lines)
StatusBar widget + utility helpers.
- `TestStatusBar` (L161–218)
- `TestBuildGithubUrl` (L1467–1480)
- `test_display_name_plans_view` (L1993–1998)
- `test_display_name_non_plans_view` (L2001–2009)

### `test_filter_mode.py` (~165 lines)
Text filter via `/` key.
- `TestFilterMode` (L259–420)

### `test_stack_filter.py` (~200 lines)
Graphite stack filter via `t` key.
- `TestStackFilter` (L2742–2941)

### `test_objective_filter.py` (~165 lines)
Objective filter via `o` key.
- `TestObjectiveFilter` (L2944–3108)

### `test_plan_detail.py` (~270 lines)
Plan detail modal (space key) + copy shortcuts.
- `TestPlanDetailScreen` (L423–572)
- `TestPlanDetailScreenCopyActions` (L575–689)

### `test_plan_body.py` (~245 lines)
Plan body screen (v key) with async content loading.
- `TestPlanBodyScreen` (L1224–1464)

### `test_command_palette.py` (~335 lines)
Command palette from main list and all palette command variants.
- `TestClosePlanViaCommandPalette` (L221–256)
- `TestCommandPaletteFromMain` (L692–758)
- `TestCommandPaletteFromMainCopyVariants` (L761–819)
- `TestExecutePaletteCommandLandPR` (L822–870)
- `TestExecutePaletteCommandFixConflictsRemote` (L873–959)
- `TestExecutePaletteCommandCodespaceRunPlan` (L1876–1908)

### `test_streaming_commands.py` (~260 lines)
Streaming command timeout + in-process close plan.
- `TestStreamingCommandTimeout` (L962–1138)
- `TestClosePlanInProcess` (L1141–1222)

### `test_view_switching.py` (~395 lines)
View switching (1/2/3 keys, arrow keys, caching, stale fetch).
- `TestViewSwitching` (L1483–1873)

### `test_actions.py` (~170 lines)
Keyboard-triggered actions (launch, view comments).
- `TestActionLaunch` (L2012–2098)
- `TestActionViewComments` (L1910–1988)

### `test_async_pr_actions.py` (~350 lines)
Async subprocess actions for PR operations.
- `TestAddressRemoteAsync` (L2101–2165)
- `TestFixConflictsRemoteAsync` (L2168–2266)
- `TestLandPrAsync` (L2269–2448)

### `test_async_plan_actions.py` (~285 lines)
Async subprocess actions for plan/objective operations.
- `TestDispatchToQueueAsync` (L2451–2543)
- `TestCloseObjectiveAsync` (L2546–2608)
- `TestCheckObjectiveAsync` (L2611–2674)
- `TestOneShotPlanAsync` (L2677–2739)

## Implementation steps

1. Create `tests/tui/app/__init__.py` (empty)
2. Create each of the 13 test files, moving classes verbatim with their imports
3. Each file gets only the imports it needs (no shared conftest needed — tests construct providers inline)
4. Delete `tests/tui/test_app.py`
5. Delete `tests/tui/__pycache__/test_app.cpython-313-pytest-9.0.2.pyc`

## What stays the same

- All test class names, method names, and test bodies remain **identical** (pure move, no refactoring)
- No conftest.py needed — each test constructs its own `FakePlanDataProvider`/`ErkDashApp`
- Existing sibling files (`test_plan_table.py`, `test_view_bar.py`) and subdirectories (`commands/`, `data/`, etc.) are untouched

## Verification

```bash
uv run pytest tests/tui/app/ -v        # All 13 new files pass
uv run pytest tests/tui/ -v            # Full TUI suite still passes
uv run pytest tests/tui/test_app.py    # Should fail (file deleted)
```
