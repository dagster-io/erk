---
title: Test File Organization Pattern
read_when:
  - "splitting a large test file into a test subdirectory"
  - "deciding whether a test file is too large"
  - "organizing tests for a complex module"
tripwires:
  - action: "creating a test file exceeding 500 lines"
    warning: "Consider splitting into a subdirectory module. See test-file-organization.md for the pattern and existing precedents."
    score: 5
---

# Test File Organization Pattern

When test files grow beyond ~500 lines, split them into a subdirectory module grouped by feature area.

## Threshold

Split when a test file exceeds approximately 500 lines. This keeps individual files navigable and makes it easier to run subsets of tests.

## Pattern

Convert `tests/path/test_module.py` into `tests/path/module/` with files grouped by feature:

```
tests/path/test_module.py (3,840 lines)
→
tests/path/module/
├── __init__.py          (empty)
├── test_core.py         (~200 lines)
├── test_actions.py      (~200 lines)
├── test_filtering.py    (~370 lines)
├── test_streaming.py    (~270 lines)
└── ...
```

## File Naming

Name files after the feature area they test, not after implementation details:

- `test_core.py` — fundamental behavior, initialization
- `test_actions.py` — user-triggered actions
- `test_filtering.py` — filter and search functionality
- `test_async_operations.py` — background operations
- `test_view_switching.py` — view navigation

## Existing Precedents

### `tests/tui/app/` (from `test_app.py`)

14 files organized by feature area:

| File                         | Focus                 |
| ---------------------------- | --------------------- |
| `test_core.py`               | Basic app behavior    |
| `test_actions.py`            | User actions          |
| `test_app_filtering.py`      | Filter functionality  |
| `test_async_operations.py`   | Background operations |
| `test_command_palette.py`    | Command palette       |
| `test_filter_mode.py`        | Filter mode           |
| `test_operation_tracking.py` | Operation tracking    |
| `test_plan_body_screen.py`   | Plan body screen      |
| `test_plan_detail_screen.py` | Plan detail screen    |
| `test_status_bar.py`         | Status bar            |
| `test_streaming.py`          | Streaming output      |
| `test_utils.py`              | Test utilities        |
| `test_view_switching.py`     | View switching        |

### `tests/unit/cli/commands/pr/submit_pipeline/`

Files named after pipeline stages:

- `test_prepare_state.py`, `test_extract_diff.py`, `test_finalize_pr.py`, etc.

### `tests/unit/cli/commands/exec/scripts/test_preprocess_session/` (from `test_preprocess_session.py`)

8 files organized by feature area (102 tests, split from 2,182-line monolith):

| File                          | Focus                           | Tests |
| ----------------------------- | ------------------------------- | ----- |
| `test_xml_escaping.py`        | XML escaping                    | 4     |
| `test_deduplication.py`       | Assistant message deduplication | 5     |
| `test_xml_generation.py`      | XML generation                  | 21    |
| `test_log_processing.py`      | Log file processing             | 6     |
| `test_agent_discovery.py`     | Agent discovery                 | 11    |
| `test_session_helpers.py`     | Session analysis and helpers    | 17    |
| `test_preprocess_workflow.py` | CLI and workflow integration    | 16    |
| `test_splitting.py`           | Token estimation and splitting  | 22    |

## Migration Steps

1. Create the directory: `mkdir tests/path/module/`
2. Create empty `__init__.py`
3. Move groups of related tests into separate files
4. Ensure shared fixtures are in a `conftest.py` within the directory
5. Verify all tests pass: `pytest tests/path/module/`
6. Remove the original file

## Related Documentation

- [Erk Test Reference](testing.md) — Test requirements and patterns
