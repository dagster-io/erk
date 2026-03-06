# Split test_capabilities.py into subpackage

## Context

`tests/unit/core/test_capabilities.py` is 1,972 lines (~18k tokens) — the 3rd largest Python file in the project. It contains 100+ test functions across 24 logical sections testing the entire capability system. A `tests/unit/core/capabilities/` subpackage already exists with 3 files (`test_hooks.py`, `test_code_reviews_system.py`, `test_review_capability.py`), establishing the pattern.

## Plan

Delete `test_capabilities.py` and distribute its tests into new files under `tests/unit/core/capabilities/`. Each file maps to a capability type or infrastructure concern.

### Target file layout

```
tests/unit/core/capabilities/
├── __init__.py                    (exists)
├── test_code_reviews_system.py    (exists, unchanged)
├── test_review_capability.py      (exists, unchanged)
├── test_hooks.py                  (exists — MERGE new tests into it)
├── test_base.py                   (NEW — ~100 lines)
├── test_registry.py               (NEW — ~170 lines)
├── test_learned_docs.py           (NEW — ~240 lines)
├── test_skills.py                 (NEW — ~80 lines)
├── test_workflows.py              (NEW — ~250 lines)
├── test_agents.py                 (NEW — ~45 lines)
├── test_permissions.py            (NEW — ~125 lines)
├── test_statusline.py             (NEW — ~95 lines)
├── test_ruff_format.py            (NEW — ~215 lines)
├── test_reminders.py              (NEW — ~190 lines)
└── test_managed_artifacts.py      (NEW — ~145 lines)
```

### File contents mapping

| New file | Sections from test_capabilities.py (line ranges) | What it tests |
|---|---|---|
| `test_base.py` | CapabilityResult (47-58), CapabilityArtifact (306-317), CapabilityScope (958-1005), Preflight (1006-1029), Custom capability registration (318-387) | Core data structures, scope enum, preflight, `_TestCapability` helper class |
| `test_registry.py` | Registry functions (59-91), Required capabilities (1264-1360), get_managed_artifacts/is_capability_managed (1912-1972) | `get_capability`, `list_capabilities`, `list_required_capabilities`, `get_managed_artifacts`, `is_capability_managed` |
| `test_learned_docs.py` | LearnedDocs (92-265), LearnedDocs uninstall (266-305) | `LearnedDocsCapability` install, uninstall, artifacts |
| `test_skills.py` | Skill capabilities (388-453) | Bundled skill capabilities, `codex_portable_skills` |
| `test_workflows.py` | Workflows (454-537), OneShot (538-590), PrAddress (591-643), PrRebase (644-696) | All 5 workflow capabilities |
| `test_agents.py` | Agent capabilities (697-739) | `DevrunAgentCapability` |
| `test_permissions.py` | Permission capabilities (740-863) | `ErkBashPermissionsCapability` |
| `test_statusline.py` | Statusline (864-957) | `StatuslineCapability` |
| `test_hooks.py` | Hooks (1030-1263) — merge with existing file | `HooksCapability` — add non-duplicate tests to existing file |
| `test_ruff_format.py` | RuffFormat (1361-1575) | `RuffFormatCapability` |
| `test_reminders.py` | is_reminder_installed (1576-1649), ReminderCapability (1650-1829) | `is_reminder_installed` detection + `ReminderCapability` base class |
| `test_managed_artifacts.py` | ManagedArtifact property (1830-1911) | `managed_artifacts` property on individual capabilities |

### Hooks merge strategy

The existing `test_hooks.py` (336 lines, 16 tests) tests marker-based detection and hook update behavior. The `test_capabilities.py` hooks section (1030-1263, ~12 tests) tests basic install/artifacts/registration. Merge non-duplicate tests from `test_capabilities.py` into the existing file, keeping the existing file's tests as-is and appending new ones.

### Steps

1. Create each new file with the appropriate imports and test functions extracted from `test_capabilities.py`
2. For `test_hooks.py`: read existing file, identify duplicates between old and new, merge non-duplicates
3. Delete `test_capabilities.py`
4. Run `uv run pytest tests/unit/core/capabilities/` to verify all tests pass
5. Run `uv run pytest tests/unit/core/test_capabilities.py` to verify it no longer exists (expected error)

## Verification

- `uv run pytest tests/unit/core/capabilities/ -v` — all tests pass
- Total test count matches original: count tests before and after
- `ruff check tests/unit/core/capabilities/` — no lint errors
- `ty check tests/unit/core/capabilities/` — no type errors
