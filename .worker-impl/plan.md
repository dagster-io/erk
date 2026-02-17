# Rename `objective-implement` to `objective-plan`

## Context

The `objective-implement` command/skill is misleading — it creates a *plan* from an objective node, not an implementation. Renaming to `objective-plan` better communicates what it does.

## Changes

### 1. Rename Claude skill file

- **Rename** `.claude/commands/erk/objective-implement.md` → `.claude/commands/erk/objective-plan.md`
- Update all internal references from `/erk:objective-implement` to `/erk:objective-plan`
- Update title, description, usage examples

### 2. Rename CLI command module (primary)

- **Rename** `src/erk/cli/commands/objective/implement_cmd.py` → `src/erk/cli/commands/objective/plan_cmd.py`
- Change `@click.command("implement")` → `@click.command("plan")`
- Remove `@alias("impl")` decorator (no alias)
- Rename function `implement_objective` → `plan_objective`
- Update docstring and all internal `/erk:objective-implement` → `/erk:objective-plan` string references
- Update module docstring

### 3. Update objective `__init__.py` registration

- **File:** `src/erk/cli/commands/objective/__init__.py`
- Update import from `implement_cmd` → `plan_cmd`, `implement_objective` → `plan_objective`
- Update `register_with_aliases` call

### 4. Rename codespace remote command

- **Rename** `src/erk/cli/commands/codespace/run/objective/implement_cmd.py` → `src/erk/cli/commands/codespace/run/objective/plan_cmd.py`
- Change `@click.command("implement")` → `@click.command("plan")`
- Rename function `run_implement` → `run_plan`
- Update all `erk objective implement` → `erk objective plan` strings
- Update module docstring

### 5. Update codespace objective `__init__.py`

- **File:** `src/erk/cli/commands/codespace/run/objective/__init__.py`
- Update import from `implement_cmd` → `plan_cmd`, `run_implement` → `run_plan`

### 6. Update one-shot dispatch comment

- **File:** `src/erk/cli/commands/one_shot_dispatch.py` (line 4)
- Update comment: `erk objective implement --one-shot` → `erk objective plan --one-shot`

### 7. Update exit plan mode hook

- **File:** `src/erk/cli/commands/exec/scripts/exit_plan_mode_hook.py` (line 540)
- Update comment: `/erk:objective-implement` → `/erk:objective-plan`

### 8. Update TUI references

- **File:** `src/erk/tui/app.py` (line 912)
  - `erk objective implement` → `erk objective plan`
- **File:** `src/erk/tui/commands/registry.py`
  - Rename `_display_one_shot_implement` → `_display_one_shot_plan` (line 120)
  - Rename `_display_copy_implement` → `_display_copy_plan` (line 142)
  - Update command strings: `erk objective implement` → `erk objective plan`
  - Update `name="erk objective implement"` → `name="erk objective plan"` (line 342)

### 9. Update test files

- **Rename** `tests/commands/objective/test_implement.py` → `tests/commands/objective/test_plan.py`
  - Update all `/erk:objective-implement` → `/erk:objective-plan` assertions
- **Rename** `tests/commands/objective/test_implement_one_shot.py` → `tests/commands/objective/test_plan_one_shot.py`
  - Update `/erk:objective-implement` → `/erk:objective-plan` assertions
- **File:** `tests/unit/core/test_interactive_claude.py`
  - Update `/erk:objective-implement` → `/erk:objective-plan` test strings

### 10. Update cross-referencing command docs

- `.claude/commands/erk/objective-inspect.md` — update `/erk:objective-implement` reference
- `.claude/commands/erk/objective-list.md` — update `/erk:objective-implement` reference
- `.claude/commands/erk/objective-create.md` — update `/erk:objective-implement` reference
- `.claude/commands/erk/plan-save.md` — update `/erk:objective-implement` references
- `.claude/commands/local/objective-view.md` — update `/erk:objective-implement` reference
- `docs/ref/slash-commands.md` — update TODO comment

### 11. Update learned docs

- `docs/learned/reference/objective-summary-format.md` — update all references
- `docs/learned/reference/index.md` — update reference
- `docs/learned/reference/tripwires.md` — update reference
- `docs/learned/objectives/objective-lifecycle.md` — update reference
- `docs/learned/hooks/erk.md` — update marker table reference
- `docs/learned/planning/session-deduplication.md` — update reference
- `docs/learned/planning/lifecycle.md` — update reference
- `docs/learned/planning/token-optimization-patterns.md` — update references

## Verification

1. Run `ruff check` and `ty check` via devrun to confirm no import errors
2. Run `pytest tests/commands/objective/` via devrun to confirm renamed tests pass
3. Run `pytest tests/unit/core/test_interactive_claude.py` via devrun
4. Grep for any remaining `objective-implement` or `objective_implement` or `implement_objective` references