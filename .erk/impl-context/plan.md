# Plan: Objective #9109 Nodes 7.2 + 7.3 — Test Renames for Phases 5-6 + Directory Cleanup

Part of Objective #9109, Nodes 7.2 and 7.3

## Context

Phases 5-6 of objective #9109 renamed identifiers in source code (backend classes, method names, parameter names, type names). The corresponding test code was not updated at the time. Node 7.2 brings tests in line with the source. Node 7.3 deletes an empty leftover directory.

**Key scope constraint:** Many `plan_*` references in tests are CORRECT because the source still uses those names. Specifically:
- `plan_backend` (variable/property: `ctx.plan_backend`, `require_plan_backend()`) — **keep**
- `plan_store` (constructor kwarg: `ErkContext(plan_store=...)`) — **keep**
- `"plan_backend": "planned_pr"` (workflow input key) — **keep**
- `plan_numbers` (GitHub ABC param) — **keep**
- `SessionsForPlan` (class name in source) — **keep**
- `close_plan` (method name on CommandExecutor) — **keep** (only params renamed)
- `extract_plan_number` (source function) — **keep**
- `"plan_id"` in duplicate checker LLM format — **keep**

## Step 1: Fix Fake Command Executor (manual, 2 files)

The source ABC has `close_plan(pr_number, pr_url)` and `dispatch_to_queue(pr_number, pr_url)` but the fake still uses `plan_id`/`plan_url` params.

**File: `tests/fakes/gateway/command_executor.py`**
- `close_plan(plan_id: int, plan_url: str)` → `close_plan(pr_number: int, pr_url: str)`
- `dispatch_to_queue(plan_id: int, plan_url: str)` → `dispatch_to_queue(pr_number: int, pr_url: str)`
- `_closed_plans` → `_closed_prs` (internal tracking list)
- `closed_plans` property → `closed_prs` property
- Update all internal references (`plan_id` → `pr_number`, `plan_url` → `pr_url` in method bodies)

**File: `tests/unit/fakes/test_fake_command_executor.py`**
- Update `.closed_plans` → `.closed_prs` in assertions

## Step 2: Rename `create_plan_store_with_plans` using rename-swarm (16 files)

The test helper `create_plan_store_with_plans()` creates a `ManagedGitHubPrBackend` — the name "plan_store" is outdated.

**Rename:** `create_plan_store_with_plans` → `create_pr_backend_with_plans`

**Definition:** `tests/test_utils/plan_helpers.py`

**Callers (15 files):**
- `tests/commands/branch/test_checkout_cmd.py`
- `tests/commands/pr/test_log.py`
- `tests/commands/pr/test_view.py`
- `tests/commands/pr/test_close.py`
- `tests/commands/pr/test_duplicate_check.py`
- `tests/commands/test_top_level_commands.py`
- `tests/commands/workspace/test_delete.py`
- `tests/commands/implement/test_flags.py`
- `tests/commands/implement/test_model_flag.py`
- `tests/commands/implement/test_execution_modes.py`
- `tests/commands/implement/test_issue_mode.py`
- `tests/commands/implement/conftest.py`
- `tests/commands/dispatch/conftest.py`
- `tests/unit/cli/commands/pr/test_metadata_helpers.py`
- `tests/unit/cli/commands/pr/test_lifecycle_update.py`
- `tests/unit/cli/commands/branch/test_create_cmd.py`

**Approach:** Use `rename-swarm` skill. Launch haiku agents in parallel — one per file. Each agent reads the file, replaces `create_plan_store_with_plans` with `create_pr_backend_with_plans`, and updates the import.

**Boundary constraint for agents:** ONLY rename the function name `create_plan_store_with_plans` → `create_pr_backend_with_plans`. Do NOT rename `plan_store=` keyword arguments (that's the source's constructor param name). Do NOT rename `fake_plan_store` variables — these will be addressed separately if needed.

## Step 3: Rename `fake_plan_store` variable (2 files, manual or small swarm)

In callers of `create_pr_backend_with_plans`, the local variable `fake_plan_store` should be renamed to `fake_pr_backend` for consistency. The `plan_store=` kwarg stays as-is (matches source).

**Files:**
- `tests/commands/dispatch/conftest.py` (~2 occurrences + 1 kwarg usage)
- `tests/commands/workspace/test_delete.py` (~6 occurrences + 3 kwarg usages)

**Pattern:** `fake_plan_store` → `fake_pr_backend`, but `plan_store=fake_pr_backend` (kwarg stays).

## Step 4: Run ty + grep to find remaining mismatches

After the mechanical renames, run:
1. `ty` type checker scoped to `tests/` to find param name mismatches, stale type imports
2. `grep` for any remaining `plan_id` params in test fakes/utilities that should be `pr_number`
3. Fix any additional issues found

## Step 5: Node 7.3 — Delete empty plan_service directory

```bash
rm -rf packages/erk-shared/src/erk_shared/gateway/plan_service/
```

This directory contains only `__pycache__` — the actual code was moved to `pr_service/` in earlier phases.

## Verification

1. **Grep check:** `Grep(pattern="create_plan_store_with_plans")` returns 0 matches
2. **Grep check:** `Grep(pattern="closed_plans", path="tests/")` returns 0 matches (except comments)
3. **ty:** Clean type check on affected test directories
4. **Tests:** Run `pytest` scoped to:
   - `tests/unit/fakes/` (fake command executor tests)
   - `tests/unit/plan_store/` (backend interface tests)
   - `tests/commands/implement/` (uses create_pr_backend_with_plans)
   - `tests/commands/pr/` (uses create_pr_backend_with_plans)
   - `tests/commands/dispatch/` (uses fake_pr_backend)
   - `tests/commands/workspace/` (uses fake_pr_backend)
   - `tests/commands/branch/` (uses create_pr_backend_with_plans)
5. **Full CI:** `make fast-ci` for final validation
