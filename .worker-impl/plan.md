# Plan: Eliminate `.worker-impl/` — Consolidate on `.erk/impl-context/`

## Context

The codebase currently has two git-committed staging directories for plan content:
- **`.worker-impl/`** — used by `erk plan submit` (issue-based and draft-PR submit paths) to stage plan content before remote implementation
- **`.erk/impl-context/`** — used by `plan_save.py` (draft-PR plan save) and `trigger_async_learn.py` to stage plan/learn materials on branches

Both serve the same purpose (temporary committed staging that gets cleaned up before implementation), but use different metadata formats (`plan-ref.json` vs `ref.json`), different module structures, and different cleanup patterns. This consolidation eliminates `.worker-impl/` entirely, reducing surface area and simplifying the codebase.

## Design Decisions

1. **Metadata format**: Standardize on `ref.json` (the `.erk/impl-context/` format). It's lighter-weight and the `plan-` prefix is redundant inside a purpose-specific directory. Add a `ref.json` fallback path to `read_plan_ref()` so existing consumers work transparently.

2. **Module structure**: Create a new `impl_context.py` module mirroring the `worker_impl_folder.py` API (`create/remove/exists`), then delete the old module. Clean git history vs in-place rename.

3. **No README.md**: `.worker-impl/` wrote a README.md. The new module won't — it's unnecessary for a staging directory removed before implementation.

4. **No backward compatibility**: Per project constraints, we break immediately. In-flight branches with `.worker-impl/` will need manual cleanup.

---

## Implementation Steps

### Step 1: Create `impl_context.py` module (additive)

**New file**: `packages/erk-shared/src/erk_shared/impl_context.py`

Create with three functions matching `worker_impl_folder.py` API:
- `create_impl_context(plan_content, plan_id, url, repo_root, *, provider, objective_id) → Path` — creates `.erk/impl-context/` with `plan.md` and `ref.json`
- `remove_impl_context(repo_root) → None` — removes `.erk/impl-context/` via `shutil.rmtree`
- `impl_context_exists(repo_root) → bool` — LBYL existence check

Key differences from `worker_impl_folder.py`:
- Target dir: `.erk/impl-context/` (uses `IMPL_CONTEXT_DIR` from `draft_pr_lifecycle.py`)
- Metadata: writes `ref.json` directly (not via `save_plan_ref` which writes `plan-ref.json`)
- No README.md

**New file**: `tests/packages/erk_shared/test_impl_context.py` — port 14 tests from `test_worker_impl_folder.py`

### Step 2: Add `ref.json` fallback to `read_plan_ref()` (additive)

**File**: `packages/erk-shared/src/erk_shared/impl_folder.py`

In `read_plan_ref()` (~line 204), after the `plan-ref.json` check and before the `issue.json` fallback, add a `ref.json` fallback that maps the lighter format to `PlanRef`.

Update `has_plan_ref()` (~line 241) to also check for `ref.json`.

### Step 3: Update `submit.py` — primary consumer

**File**: `src/erk/cli/commands/submit.py`

- Replace import of `worker_impl_folder` functions with `impl_context` functions
- In `_submit_draft_pr_plan` (lines 448-465): use `impl_context_exists`, `remove_impl_context`, `create_impl_context`, stage `.erk/impl-context`
- In `_create_branch_and_pr` (lines 723-739): same replacements
- Update user output strings from `.worker-impl/` to `.erk/impl-context/`

### Step 4: Replace `create_worker_impl_from_issue.py` exec script

**Rename**: `src/erk/cli/commands/exec/scripts/create_worker_impl_from_issue.py` → `create_impl_context_from_plan.py`

- Change command name to `create-impl-context-from-plan`
- Import from `erk_shared.impl_context`
- Call `create_impl_context()` instead of `create_worker_impl_folder()`
- Update output JSON keys (`impl_context_path` instead of `worker_impl_path`)

**File**: `src/erk/cli/commands/exec/group.py` — update import and registration

**Rename test**: `tests/unit/cli/commands/exec/scripts/test_create_worker_impl_from_issue.py` → `test_create_impl_context_from_plan.py`

### Step 5: Update fallback consumers (3 exec scripts)

These scripts check `.impl/` first, then fall back to `.worker-impl/`. Change fallback to `.erk/impl-context/`.

**File**: `src/erk/cli/commands/exec/scripts/impl_init.py`
- Line 57: `.erk/impl-context` instead of `.worker-impl`
- Line 58: `impl_type = "impl-context"` instead of `"worker-impl"`
- Line 63: update error message

**File**: `src/erk/cli/commands/exec/scripts/impl_signal.py`
- Lines 184, 296: `.erk/impl-context` instead of `.worker-impl`

**File**: `src/erk/cli/commands/exec/scripts/get_closing_text.py`
- Line 72: `.erk/impl-context` instead of `.worker-impl`

### Step 6: Update `one_shot_dispatch.py`

**File**: `src/erk/cli/commands/one_shot_dispatch.py`

- Line 245: commit to `.erk/impl-context/prompt.md` instead of `.worker-impl/prompt.md`
- Lines 335-339: update truncation message

### Step 7: Update workflow files

**File**: `.github/workflows/plan-implement.yml`
- Line 149: `rm -rf .erk/impl-context` (was `.worker-impl`)
- Line 150: `erk exec create-impl-context-from-plan "$PLAN_ID"` (was `create-worker-impl-from-issue`)
- Line 161: `git add .erk/impl-context` (was `.worker-impl`)
- Line 197: `cp -r .erk/impl-context .impl` (was `.worker-impl`)
- Lines 215-216: remove the `.worker-impl/` block (already handled by `.erk/impl-context/` block)
- Line 314: remove `.worker-impl/` from grep filter, use `.erk/impl-context/` instead
- Lines 412-413: remove `.worker-impl/` block

**File**: `.github/workflows/one-shot.yml`
- Lines 106-109: `.erk/impl-context/prompt.md` instead of `.worker-impl/prompt.md`

**File**: `.github/workflows/pr-address.yml`
- Lines 75-76: remove `.worker-impl/` cleanup block (`.erk/impl-context/` block already handles it)

**File**: `.github/workflows/ci.yml`
- Line 7: remove `.worker-impl/**` from `paths-ignore` (`.erk/impl-context/**` already there or add it)
- Line 32: change action ref from `check-worker-impl` to `check-impl-context`

### Step 8: Replace composite action

**Rename**: `.github/actions/check-worker-impl/action.yml` → `.github/actions/check-impl-context/action.yml`
- Check for `.erk/impl-context` instead of `.worker-impl`
- Update name, description, output messages

### Step 9: Delete old files

- `packages/erk-shared/src/erk_shared/worker_impl_folder.py`
- `tests/packages/erk_shared/test_worker_impl_folder.py`
- `src/erk/cli/commands/exec/scripts/create_worker_impl_from_issue.py`
- `tests/unit/cli/commands/exec/scripts/test_create_worker_impl_from_issue.py`
- `.github/actions/check-worker-impl/action.yml`

### Step 10: Update ancillary source references

- `src/erk/agent_docs/operations.py` line 93: `.worker-impl/` → `.erk/impl-context/`
- `src/erk/cli/commands/exec/scripts/generate_pr_summary.py`: update comments
- `src/erk/cli/commands/exec/scripts/ci_update_pr_body.py`: update comments
- `.claude/commands/erk/plan-implement.md` line 287: update reference
- `.claude/skills/erk-exec/reference.md`: rename command entry
- `Makefile`: already has `clear_impl_context` target; remove any `.worker-impl` references
- `validate_plan_linkage` docstring in `impl_folder.py` line 259: `.worker-impl/` → `.erk/impl-context/`

### Step 11: Update tests referencing `.worker-impl`

- `tests/commands/plan/test_submit.py`
- `tests/commands/submit/test_multiple_issues.py`
- `tests/commands/one_shot/test_one_shot_dispatch.py`
- `tests/unit/cli/commands/exec/scripts/test_impl_init.py`
- `tests/unit/cli/commands/exec/scripts/test_impl_signal.py`
- `tests/unit/cli/commands/exec/scripts/test_get_closing_text.py`

### Step 12: Update documentation

- `docs/learned/planning/impl-context.md`
- `docs/learned/planning/lifecycle.md`
- `docs/learned/planning/worktree-cleanup.md`
- `docs/learned/architecture/impl-folder-lifecycle.md`
- Other `docs/learned/` files with `.worker-impl` references

---

## Verification

1. Run `rg 'worker.impl|worker_impl' src/ tests/ packages/ .github/ .claude/` — should return zero matches
2. Run `make fast-ci` — all unit tests pass
3. Run `make all-ci` — all tests including integration pass
4. Verify `.github/actions/check-impl-context/action.yml` exists and `.github/actions/check-worker-impl/` is deleted
