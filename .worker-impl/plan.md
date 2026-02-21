# Plan: Rename TargetInfo.issue_number → plan_number (Phase 1)

Part of Objective #7724, Node 1.1 (+ 1.2, 1.3 for shippable unit)

## Context

Objective #7724 renames `issue_number` to `plan_number` across plan-related code. The `TargetInfo` class in `implement_shared.py` uses `issue_number` as a field name and `"issue_number"`/`"issue_url"` as target_type discriminator values, but these represent *plan* identifiers, not generic issue numbers. Phase 1 renames the core type and its immediate consumers so the code is shippable after this PR.

## Changes

### 1. `src/erk/cli/commands/implement_shared.py` (Node 1.1)

**TargetInfo class** (line 408-417):
- Rename field `issue_number: str | None` → `plan_number: str | None`
- Rename target_type values: `"issue_number"` → `"plan_number"`, `"issue_url"` → `"plan_url"`
- `"file_path"` stays unchanged
- Update docstring to reflect new names

**detect_target_type()** (line 420-445):
- Update all `TargetInfo(...)` constructor calls: `issue_number=` → `plan_number=`
- Update all `target_type=` string values: `"issue_number"` → `"plan_number"`, `"issue_url"` → `"plan_url"`
- Update docstring comment about return values

### 2. `src/erk/cli/commands/implement.py` (Node 1.2)

Lines 410-428 reference `TargetInfo` fields and target_type values:
- `target_info.issue_number` → `target_info.plan_number` (lines 414, 420, 428)
- `"issue_number"` → `"plan_number"` in string comparisons (lines 413, 419)
- `"issue_url"` → `"plan_url"` in string comparisons (lines 413, 419)
- `"file_path"` stays unchanged (line 415)

### 3. Tests (Node 1.3)

**`tests/commands/implement/test_target_detection.py`:**
- Update all `target_info.issue_number` assertions → `target_info.plan_number`
- Update all `target_info.target_type == "issue_number"` assertions → `"plan_number"`
- Update all `target_info.target_type == "issue_url"` assertions → `"plan_url"`

**`tests/unit/cli/commands/test_implement_shared.py`:**
- No changes needed (tests `extract_plan_from_current_branch` and `validate_flags`, not `TargetInfo`)

## Verification

1. Run scoped tests: `pytest tests/commands/implement/test_target_detection.py tests/unit/cli/commands/test_implement_shared.py`
2. Run type checker on changed files: `ty check src/erk/cli/commands/implement_shared.py src/erk/cli/commands/implement.py`
3. Grep for any remaining references to old field/value names: `rg "issue_number|issue_url" src/erk/cli/commands/implement_shared.py src/erk/cli/commands/implement.py tests/commands/implement/test_target_detection.py`