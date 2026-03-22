# Phase 5: Rename exec scripts from plan-* to pr-* (Nodes 5.1–5.5)

**Objective:** #9318 — Complete plan-to-PR terminology rename
**Nodes:** 5.1, 5.2, 5.3, 5.4, 5.5

## Context

This is Phase 5 of the plan-to-PR terminology rename objective. Phases 1–4 renamed core types, packages, context properties, CLI flags, and constants. Phase 5 renames the remaining `erk exec` scripts that still use "plan" in their filenames and command names. These 8 scripts are the last major source of "plan" terminology in the exec subsystem.

## Scope: 8 Script Renames

| Node | Old File | New File | Old Command | New Command |
|------|----------|----------|-------------|-------------|
| 5.1 | `add_plan_label.py` | `add_pr_label.py` | `add-plan-label` | `add-pr-label` |
| 5.1 | `add_plan_labels.py` | `add_pr_labels.py` | `add-plan-labels` | `add-pr-labels` |
| 5.2 | `detect_plan_from_branch.py` | `detect_pr_from_branch.py` | `detect-plan-from-branch` | `detect-pr-from-branch` |
| 5.3 | `get_plan_info.py` | `get_pr_info.py` | `get-plan-info` | `get-pr-info` |
| 5.3 | `get_plan_metadata.py` | `get_pr_metadata.py` | `get-plan-metadata` | `get-pr-metadata` |
| 5.4 | `register_one_shot_plan.py` | `register_one_shot_pr.py` | `register-one-shot-plan` | `register-one-shot-pr` |
| 5.5 | `update_plan_header.py` | `update_pr_header.py` | `update-plan-header` | `update-pr-header` |
| 5.5 | `validate_plan_content.py` | `validate_pr_content.py` | `validate-plan-content` | `validate-pr-content` |

## 9-Place Checklist (per command)

Follow `docs/learned/cli/command-rename-checklist.md` for each of the 8 scripts:

### 1. Script files — rename + update internals

**Base path:** `src/erk/cli/commands/exec/scripts/`

For each script:
- `git mv` old file to new file
- Update `@click.command(name="...")` to new kebab-case name
- Rename the main Click function (e.g., `add_plan_label` → `add_pr_label`)
- Rename internal helper functions (e.g., `_detect_plan_from_branch_impl` → `_detect_pr_from_branch_impl`)
- Update docstrings and help text that reference "plan" → "PR"
- Update class names where applicable (e.g., `PlanLabelItem` → `PrLabelItem` in add_plan_labels.py)

### 2. Exec registry — `src/erk/cli/commands/exec/group.py`

Update all 8 import lines and their corresponding `add_command()` registrations:
- Lines ~11-12: add_plan_label, add_plan_labels imports
- Line ~38: detect_plan_from_branch import
- Lines ~55-56: get_plan_info, get_plan_metadata imports
- Lines ~134-135: register_one_shot_plan import
- Line ~175: update_plan_header import
- Lines ~184-185: validate_plan_content import
- All corresponding `exec_group.add_command(...)` calls (~lines 197-198, 208, 216-217, 260, 276, 288)

### 3. Test files — rename + update imports

**Base path:** `tests/unit/cli/commands/exec/scripts/`

| Old Test File | New Test File |
|---------------|---------------|
| `test_add_plan_label.py` | `test_add_pr_label.py` |
| `test_add_plan_labels.py` | `test_add_pr_labels.py` |
| `test_detect_plan_from_branch.py` | `test_detect_pr_from_branch.py` |
| `test_get_plan_info.py` | `test_get_pr_info.py` |
| `test_get_plan_metadata.py` | `test_get_pr_metadata.py` |
| `test_register_one_shot_plan.py` | `test_register_one_shot_pr.py` |
| `test_update_plan_header.py` | `test_update_pr_header.py` |
| `test_validate_plan_content.py` | `test_validate_pr_content.py` |

For each test file:
- `git mv` to new name
- Update import paths (e.g., `from erk.cli.commands.exec.scripts.add_plan_label import ...`)
- Update test function names where they reference the old command name

### 4. Skill/command references — `.claude/skills/erk-exec/`

- `SKILL.md` (line ~46): update command name references
- `reference.md`: update all command name entries and descriptions

### 5. Slash command templates — `.claude/commands/`

Update references in:
- `erk/land.md` (lines ~93, 96: `get-plan-metadata`)
- `erk/learn.md` (lines ~140, 693: `get-plan-info`, `validate-plan-content`)
- `erk/plan-save.md` (line ~109: `get-plan-metadata`)
- `erk/replan.md` (lines ~48-49, 139, 397, 401, 405, 456, 468: multiple refs)
- `erk/system/consolidate-learn-plans-plan.md` (line ~54: `get-plan-info`)
- `erk/system/objective-plan-node.md` (line ~170: `get-plan-metadata`)

### 6. docs/learned/ references

- `docs/learned/cli/erk-exec-commands.md` (command reference table + detailed sections)
- Any other docs referencing these command names (grep to find)

### 7. CLI help text

Check if any command group help text or other command descriptions reference these command names.

### 8. CHANGELOG

Skip — per project constraints, CHANGELOG updates use `/local:changelog-update` after merge.

### 9. Workflow files — `.github/workflows/`

| File | Commands Referenced |
|------|-------------------|
| `one-shot.yml` (lines ~131, 222) | `update-plan-header`, `register-one-shot-plan` |
| `plan-implement.yml` (line ~309) | `update-plan-header` |
| `pr-address.yml` (lines ~54, 157) | `update-plan-header` |
| `pr-rebase.yml` (lines ~67, 165) | `update-plan-header` |
| `pr-rewrite.yml` (lines ~62, 140) | `update-plan-header` |

### Cross-reference: setup_impl.py

`src/erk/cli/commands/exec/scripts/setup_impl.py` (line ~36) imports `_detect_plan_from_branch_impl` from detect_plan_from_branch. Update to import from `detect_pr_from_branch`.

## Implementation Order

1. **Script files** — `git mv` all 8 scripts, update internals (functions, classes, decorators, docstrings)
2. **Cross-references** — Update setup_impl.py import
3. **Exec registry** — Update group.py imports and registrations
4. **Test files** — `git mv` all 8 test files, update imports and references
5. **Workflow files** — Update all `.github/workflows/*.yml` references
6. **Skills + commands** — Update `.claude/skills/` and `.claude/commands/` references
7. **Documentation** — Update `docs/learned/` references
8. **Regenerate exec reference docs** — Run `erk-dev gen-exec-reference-docs`

## Verification

1. **Stale reference check:** `rg "add-plan-label|add-plan-labels|detect-plan-from-branch|get-plan-info|get-plan-metadata|register-one-shot-plan|update-plan-header|validate-plan-content" --type py --type md --type yml .` — should return 0 matches outside CHANGELOG/historical docs
2. **Also check Python module names:** `rg "add_plan_label|detect_plan_from_branch|get_plan_info|get_plan_metadata|register_one_shot_plan|update_plan_header|validate_plan_content" --type py .` — should return 0 matches
3. **Run tests:** `make fast-ci` via devrun agent
4. **Regenerate docs:** `erk-dev gen-exec-reference-docs` via devrun agent
