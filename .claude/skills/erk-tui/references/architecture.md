---
name: erk-tui-architecture
description: TUI layered architecture, mixin patterns, directory structure, and design principles
---

# TUI Architecture

**Read this when**: Understanding the TUI's layered design, mixin structure, directory layout, or overall data flow.

## Layered Architecture

The TUI follows a strict 5-layer architecture. Data flows downward; user actions flow upward.

```
┌─────────────────────────────────────────────────────┐
│  Action Layer                                        │
│  Commands, keyboard bindings, command palette        │
│  Operates on selected rows via PlanRowData fields    │
├─────────────────────────────────────────────────────┤
│  Widget Layer                                        │
│  PlanDataTable, RunDataTable, ViewBar, StatusBar     │
│  Renders pre-formatted display strings               │
├─────────────────────────────────────────────────────┤
│  Filter Layer                                        │
│  PlanFilters (frozen dataclass)                      │
│  Controls what data appears via server/client filters│
├─────────────────────────────────────────────────────┤
│  Display Layer                                       │
│  PlanRowData (frozen dataclass, 47+ fields)          │
│  Pre-formatted *_display strings + raw identifiers   │
├─────────────────────────────────────────────────────┤
│  Data Layer                                          │
│  PlanDataProvider ABC → Real / Fake implementations  │
│  Fetches from GitHub API, assembles row data         │
└─────────────────────────────────────────────────────┘
```

**Assembly pipeline in `_build_row_data()`**: Merges data from four sources:

1. `Plan` object (parsed from GitHub issue)
2. PR linkages (GraphQL query)
3. Worktree filesystem scan
4. Plan header metadata

## Mixin Architecture

`ErkDashApp` uses mixins for logical grouping of functionality:

```python
class ErkDashApp(
    FilterMixin,
    CommandMixin,
    NavigationMixin,
    App[None],
):
    ...
```

**Critical constraint**: Textual's `_MessagePumpMeta` metaclass scans `class.__dict__` (not MRO) for `@on()` decorated event handlers during class creation. Handlers on mixin classes are **silently ignored** — they never fire.

**Rule**: All `@on(...)` decorated methods MUST live on the concrete `ErkDashApp` class. Mixins provide helper methods and action implementations only.

**Type safety in mixins**: Use `TYPE_CHECKING` guard to import `ErkDashApp` without circular imports:

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from erk.tui.app import ErkDashApp
```

## Directory Structure

```
src/erk/tui/
├── app.py                    # ErkDashApp (concrete class, event handlers)
├── mixins/                   # Logical groupings (filter, command, navigation)
├── commands/
│   └── registry.py           # CommandDefinition entries, display formatters
├── data/
│   └── types.py              # PlanRowData, PlanFilters, ViewMode, ViewConfig
├── formatting/
│   └── ci_checks.py          # Shared CI check formatting
├── screens/                  # Modal screens (detail, body, help, one-shot)
├── styles/                   # CSS files for Textual widgets
└── widgets/
    ├── plan_table.py         # PlanDataTable
    └── ...                   # ViewBar, StatusBar, etc.

packages/erk-shared/.../plan_data_provider/
├── abc.py                    # PlanDataProvider ABC
├── real.py                   # RealPlanDataProvider
└── fake.py                   # FakePlanDataProvider + make_plan_row()
```

## Design Principles

1. **Format at fetch time**: All `*_display` fields are computed in `RealPlanDataProvider._build_row_data()`. The widget layer renders pre-formatted strings without transformation.

2. **Frozen data**: `PlanRowData` and `PlanFilters` are frozen dataclasses. Use `dataclasses.replace()` for any modifications.

3. **Provider ABC boundary**: The `PlanDataProvider` ABC lives in `erk-shared` (not `src/erk/tui/`). This enables the fake to be co-located with the real implementation in the shared package.

4. **Thread safety**: Background operations use `@work(thread=True)`. All UI updates from worker threads go through `call_from_thread()`.

5. **View isolation**: Plans, Learn, and Objectives have independent label queries and independent caches. Switching views may trigger re-fetch if the label tuple cache is cold.

## Runs Tab

The Runs tab uses a parallel architecture:

- `RunRowData`: Frozen dataclass with run_id, status, conclusion, pr_number, branch, checks_display
- `RunDataTable`: Separate widget from `PlanDataTable`
- **Branch resolution**: PR `head_branch` is authoritative (falls back to `run.branch` only if not master/main — after merge+deletion, `run.branch` becomes master)

## Source Documents

Distilled from: `tui/architecture`, `tui/modal-screen-pattern`, `tui/modal-widget-embedding`, `tui/runs-tab-architecture`
