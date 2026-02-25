# Plan: Rename issue_number → plan_number in misc exec scripts + tests

**Objective:** #7724, Nodes 4.1 + 4.2

## Context

Objective #7724 renames `issue_number` → `plan_number` across plan-related code to clarify domain terminology. Phases 1-3 (PRs #7849, #7896, #7908, #8122) established the mechanical rename pattern. Phase 4 targets miscellaneous exec scripts and their tests.

## Scope

**11 source files** to rename (of the 13 listed in the objective):
- `update_dispatch_info.py` — **does not exist**, skip
- `get_closing_text.py` — **already migrated** (uses `plan_id`), only test fixtures need updating

**13 test files** to update (12 standard + 1 format migration).

## Rename Pattern (established in prior phases)

For each file, mechanically rename:

1. **Python identifiers**: `issue_number` → `plan_number`, `issue_url` → `plan_url`
2. **Click arguments**: `@click.argument("issue_number")` → `@click.argument("plan_number")`
3. **Click options**: `--issue-number` → `--plan-number`
4. **JSON output keys**: `"issue_number"` → `"plan_number"`, `"issue_url"` → `"plan_url"`
5. **Function names**: `_extract_issue_number()` → `_extract_plan_number()` (in track_learn_evaluation.py only)
6. **Docstrings/comments**: Update terminology references
7. **Error messages**: "issue number" → "plan number", "Issue #N" → "Plan #N"

### Cross-cutting boundary rule

When a callee function's parameter hasn't been renamed yet (different phase), keep the old keyword arg name:
- `build_pr_body_footer(issue_number=plan_number)` — callee in `erk-shared`, out of scope
- `write_dispatch_metadata(issue_number=plan_number)` — callee in `pr/metadata_helpers.py`, Phase 6

## Implementation Steps

### Step 1: Rename source files (high-occurrence first)

| # | File | Occurrences | Notes |
|---|------|-------------|-------|
| 1 | `src/erk/cli/commands/exec/scripts/exit_plan_mode_hook.py` | 13 | `plan_issue_number` field in HookInput dataclass — rename to just `plan_number` or keep as `plan_issue_number`? See decision below |
| 2 | `src/erk/cli/commands/exec/scripts/track_learn_evaluation.py` | 13 | Also rename `_extract_issue_number()` → `_extract_plan_number()` |
| 3 | `src/erk/cli/commands/exec/scripts/register_one_shot_plan.py` | 9 | Cross-cutting: passes to `write_dispatch_metadata(issue_number=...)` |
| 4 | `src/erk/cli/commands/exec/scripts/close_issue_with_comment.py` | 7 | JSON output key + Click argument |
| 5 | `src/erk/cli/commands/exec/scripts/ci_update_pr_body.py` | 6 | Cross-cutting: passes to `build_pr_body_footer(issue_number=...)` |
| 6 | `src/erk/cli/commands/exec/scripts/get_plan_metadata.py` | 6 | Click argument + MetadataSuccess dataclass field |
| 7 | `src/erk/cli/commands/exec/scripts/get_pr_body_footer.py` | 5 | Cross-cutting: passes to `build_pr_body_footer(issue_number=...)` |
| 8 | `src/erk/cli/commands/exec/scripts/get_pr_for_plan.py` | 4 | Click argument |
| 9 | `src/erk/cli/commands/exec/scripts/create_plan_from_context.py` | 3 | JSON keys: both `issue_number` and `issue_url` |
| 10 | `src/erk/cli/commands/exec/scripts/store_tripwire_candidates.py` | 3 | Click option `--issue` with dest `issue_number` |
| 11 | `src/erk/cli/commands/exec/scripts/update_pr_description.py` | 1 | Cross-cutting: passes to `_build_pr_body(issue_number=...)` |

### Decision: `exit_plan_mode_hook.py` naming

The field `plan_issue_number` already contains "plan" prefix, making `plan_plan_number` nonsensical. **Rename to `plan_number`** to match the target naming convention. This affects:
- `HookInput.plan_issue_number` → `HookInput.plan_number`
- `_compute_statusline(plan_issue_number=...)` → `_compute_statusline(plan_number=...)`
- All references and the `for_test()` factory

### Step 2: Update test files

| # | Test File | Occurrences | Notes |
|---|-----------|-------------|-------|
| 1 | `tests/unit/cli/commands/exec/scripts/test_exit_plan_mode_hook.py` | 25+ | Rename `plan_issue_number=` kwargs |
| 2 | `tests/unit/cli/commands/exec/scripts/test_ci_update_pr_body.py` | 13 | `issue_number=` kwargs |
| 3 | `tests/unit/cli/commands/exec/scripts/test_get_closing_text.py` | 10 | **Format migration**: `issue.json` fixtures → `plan-ref.json` format |
| 4 | `tests/unit/cli/commands/exec/scripts/test_track_learn_evaluation.py` | 5 | JSON output assertions |
| 5 | `tests/unit/cli/commands/exec/scripts/test_close_issue_with_comment.py` | 4 | JSON output assertions + variable names |
| 6 | `tests/unit/cli/commands/exec/scripts/test_get_plan_metadata.py` | 4 | JSON output assertions |
| 7 | `tests/unit/cli/commands/exec/scripts/test_create_plan_from_context.py` | 2 | `issue_number` and `issue_url` assertions |
| 8 | `tests/unit/cli/commands/exec/scripts/test_get_pr_body_footer.py` | 2 | Test function names + keyword args |
| 9 | `tests/unit/cli/commands/exec/scripts/test_register_one_shot_plan.py` | 2 | Comments only |
| 10 | `tests/unit/cli/commands/exec/scripts/test_get_pr_for_plan.py` | 0 | Verify no changes needed |
| 11 | `tests/unit/cli/commands/exec/scripts/test_store_tripwire_candidates.py` | 0 | Verify no changes needed |
| 12 | `tests/unit/cli/commands/exec/scripts/test_update_pr_description.py` | 0 | Verify no changes needed |

### Step 3: Handle get_closing_text test fixture migration

`test_get_closing_text.py` creates `.impl/issue.json` with old-format keys. The source now reads `plan-ref.json` via `read_plan_ref()`. Update test fixtures to create `plan-ref.json` instead:

**Old format** (`issue.json`):
```json
{"issue_number": 776, "issue_url": "https://...", "created_at": "...", "synced_at": "..."}
```

**New format** (`plan-ref.json`) — check `read_plan_ref()` for exact schema:
```json
{"provider": "github", "plan_id": "776", "url": "https://..."}
```

### Step 4: Verify callers of renamed CLI arguments

After renaming Click arguments/options, check if any shell scripts, hooks, or commands invoke these exec scripts with the old argument names:
- `grep -r "issue-number" .claude/ scripts/ src/erk/`
- Particularly check hooks that call `get-plan-metadata`, `get-pr-body-footer`, `register-one-shot-plan`, `store-tripwire-candidates`

## Verification

1. **Run affected tests**: `uv run pytest tests/unit/cli/commands/exec/scripts/ -x`
2. **Run type checker**: `uv run ty check src/erk/cli/commands/exec/scripts/`
3. **Grep for remnants**: `grep -r "issue_number" src/erk/cli/commands/exec/scripts/` — should show only cross-cutting calls to functions in other phases
4. **Run full fast-ci**: Confirm no regressions
