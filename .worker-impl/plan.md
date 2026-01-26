# Plan: Reorganize Capabilities Structure

## Goal

Reorganize capabilities so that:
- **Core infrastructure** stays in `src/erk/core/capabilities/`
- **Individual implementations** move to `src/erk/capabilities/` organized by type in folders

## Target Structure

### `src/erk/core/capabilities/` (Infrastructure)

```
src/erk/core/capabilities/
├── __init__.py              # Package marker
├── base.py                  # ABC, types, dataclasses (unchanged)
├── detection.py             # Fast is_reminder_installed() (unchanged)
├── registry.py              # Registry functions (imports updated)
├── skill_capability.py      # Template base class (unchanged)
├── reminder_capability.py   # Template base class (unchanged)
└── review_capability.py     # Template base class (unchanged)
```

### `src/erk/capabilities/` (Implementations by Type)

```
src/erk/capabilities/
├── __init__.py
├── skills/
│   ├── __init__.py
│   ├── dignified_python.py          # DignifiedPythonCapability
│   └── fake_driven_testing.py       # FakeDrivenTestingCapability
├── reminders/
│   ├── __init__.py
│   ├── devrun.py                    # DevrunReminderCapability
│   ├── dignified_python.py          # DignifiedPythonReminderCapability
│   ├── explore_docs.py              # ExploreDocsReminderCapability
│   └── tripwires.py                 # TripwiresReminderCapability
├── reviews/
│   ├── __init__.py
│   ├── dignified_code_simplifier.py # DignifiedCodeSimplifierReviewDefCapability
│   ├── dignified_python.py          # DignifiedPythonReviewDefCapability
│   └── tripwires.py                 # TripwiresReviewDefCapability
├── workflows/
│   ├── __init__.py
│   ├── erk_impl.py                  # ErkImplWorkflowCapability
│   └── learn.py                     # LearnWorkflowCapability
├── agents/
│   ├── __init__.py
│   └── devrun.py                    # DevrunAgentCapability
├── code_reviews_system.py           # CodeReviewsSystemCapability (standalone)
├── erk_bash_permissions.py          # ErkBashPermissionsCapability (standalone)
├── hooks.py                         # HooksCapability (standalone)
├── learned_docs.py                  # LearnedDocsCapability (standalone)
├── ruff_format.py                   # RuffFormatCapability (standalone)
└── statusline.py                    # StatuslineCapability (standalone)
```

**Organization rationale:**
- Template-based capabilities (skills, reminders, reviews) grouped by type in folders
- Workflows and agents get their own folders (2+ implementations each or conceptually distinct)
- Standalone capabilities (unique implementations) remain at root level

## Implementation Steps

### Phase 1: Create New Package Structure (Additive)

1. Create directory structure:
   ```
   src/erk/capabilities/
   src/erk/capabilities/skills/
   src/erk/capabilities/reminders/
   src/erk/capabilities/reviews/
   src/erk/capabilities/workflows/
   src/erk/capabilities/agents/
   ```

2. Create `__init__.py` files for each directory (empty)

3. Create individual capability files:
   - 2 skill files
   - 4 reminder files
   - 3 review files
   - 2 workflow files
   - 1 agent file
   - 6 standalone files

### Phase 2: Update Registry

4. Update `src/erk/core/capabilities/registry.py` imports:
   ```python
   # Change from:
   from erk.core.capabilities.skills import DignifiedPythonCapability
   # To:
   from erk.capabilities.skills.dignified_python import DignifiedPythonCapability
   ```

### Phase 3: Update External Consumers

5. Update `src/erk/artifacts/sync.py`:
   ```python
   from erk.capabilities.hooks import HooksCapability
   ```

6. Update test imports in:
   - `tests/unit/core/test_capabilities.py`
   - `tests/unit/core/capabilities/test_code_reviews_system.py`
   - `tests/unit/core/capabilities/test_review_capability.py`
   - `tests/unit/core/capabilities/test_hooks.py`

7. Update `docs/learned/capabilities/adding-new-capabilities.md`

### Phase 4: Delete Old Files

8. Delete 11 implementation files from `src/erk/core/capabilities/`:
   - `skills.py`, `reminders.py`, `reviews.py`, `agents.py`
   - `workflows.py`, `code_reviews_system.py`, `hooks.py`
   - `permissions.py`, `statusline.py`, `ruff_format.py`, `learned_docs.py`

## File Mapping

| Old Location | New Location |
|--------------|--------------|
| `core/.../skills.py` (DignifiedPythonCapability) | `capabilities/skills/dignified_python.py` |
| `core/.../skills.py` (FakeDrivenTestingCapability) | `capabilities/skills/fake_driven_testing.py` |
| `core/.../reminders.py` (DevrunReminderCapability) | `capabilities/reminders/devrun.py` |
| `core/.../reminders.py` (DignifiedPythonReminderCapability) | `capabilities/reminders/dignified_python.py` |
| `core/.../reminders.py` (ExploreDocsReminderCapability) | `capabilities/reminders/explore_docs.py` |
| `core/.../reminders.py` (TripwiresReminderCapability) | `capabilities/reminders/tripwires.py` |
| `core/.../reviews.py` (DignifiedCodeSimplifierReviewDefCapability) | `capabilities/reviews/dignified_code_simplifier.py` |
| `core/.../reviews.py` (DignifiedPythonReviewDefCapability) | `capabilities/reviews/dignified_python.py` |
| `core/.../reviews.py` (TripwiresReviewDefCapability) | `capabilities/reviews/tripwires.py` |
| `core/.../workflows.py` (ErkImplWorkflowCapability) | `capabilities/workflows/erk_impl.py` |
| `core/.../workflows.py` (LearnWorkflowCapability) | `capabilities/workflows/learn.py` |
| `core/.../agents.py` (DevrunAgentCapability) | `capabilities/agents/devrun.py` |
| `core/.../code_reviews_system.py` | `capabilities/code_reviews_system.py` |
| `core/.../hooks.py` | `capabilities/hooks.py` |
| `core/.../permissions.py` | `capabilities/erk_bash_permissions.py` |
| `core/.../statusline.py` | `capabilities/statusline.py` |
| `core/.../ruff_format.py` | `capabilities/ruff_format.py` |
| `core/.../learned_docs.py` | `capabilities/learned_docs.py` |

## Critical Files

| File | Action |
|------|--------|
| `src/erk/core/capabilities/registry.py` | Update imports |
| `src/erk/core/capabilities/base.py` | Reference only (unchanged) |
| `src/erk/artifacts/sync.py` | Update HooksCapability import |
| `tests/unit/core/test_capabilities.py` | Update imports |

## Verification

1. Run `make fast-ci` after each phase
2. Run `erk init capability list` to verify all capabilities register
3. Grep for old import paths: `grep -r "erk.core.capabilities.skills" src/ tests/`