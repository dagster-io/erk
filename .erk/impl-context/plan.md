# Plan: Add Branch-Based Plan Detection to `/erk:plan-implement`

## Context

When running `/erk:plan-implement` with no arguments and no `.impl/` folder, the command falls through to "save current plan from plan mode" (Step 1c). But if you're already on a plan branch (e.g., `plnd/add-print-statement-02-23-1041`), the command should detect the associated plan and set up `.impl/` automatically — just like `erk implement -d` does.

The `erk implement` CLI command has this detection via `ctx.plan_backend.resolve_plan_id_for_branch()`, but the slash command has no equivalent step. This means users must either pass an explicit issue number or run `erk implement -d` first to get `.impl/` set up before the slash command works.

## Change

**File:** `.claude/commands/erk/plan-implement.md`

Add a new step **1b-branch** between the existing Step 1b (`.impl/` exists) and Step 1c (fall back to plan-save). This step:

1. Gets the current branch name via `git branch --show-current`
2. Tries to extract a plan number using two methods:
   - **Issue-based branches** (`P{number}-slug`): regex extraction from the branch name
   - **Draft-PR branches** (`plnd/slug-timestamp`): query `gh pr view --json number -q .number` to find the associated PR
3. If a plan number is found, calls `erk exec setup-impl-from-issue <number>` then proceeds to impl-init
4. If no plan number is detected, falls through to Step 1c (save current plan) as before

### Exact edit location

Insert after line 127 (`If it fails or returns "valid": false, continue to Step 2.`) and before line 129 (`#### 1c. Fall back to saving current plan`):

```markdown
#### 1b-branch. Detect plan from current branch

If no `.impl/` folder exists, try to detect the plan from the current branch name:

```bash
# Get current branch
BRANCH=$(git branch --show-current)

# Try issue-based detection: P{number}-slug or {number}-slug
PLAN_NUMBER=$(echo "$BRANCH" | grep -oE '^[Pp]?([0-9]+)-' | grep -oE '[0-9]+' | head -1)

# If not found, try draft-PR detection: look for an associated PR
if [ -z "$PLAN_NUMBER" ]; then
  PLAN_NUMBER=$(gh pr view --json number -q .number 2>/dev/null || echo "")
fi
```

If `PLAN_NUMBER` is non-empty:

1. Display: "Auto-detected plan #PLAN_NUMBER from branch"
2. Set up from the detected plan:
   ```bash
   erk exec setup-impl-from-issue <PLAN_NUMBER>
   ```
3. Run impl-init:
   ```bash
   erk exec impl-init --json
   ```
4. Proceed to Step 2d.

If `PLAN_NUMBER` is empty, continue to Step 1c.
```

Also update:
- **Description** (line 2): Add "current branch" to the description
- **Prerequisites** (line 20-23): Add "A plan branch checked out" as a valid prerequisite
- **Usage examples** (line 28): Update the no-arg comment to mention branch detection

## Verification

1. Check out a plan branch (e.g., `plnd/add-print-statement-02-23-1041`) without `.impl/`
2. Run `/erk:plan-implement` with no arguments
3. Confirm it auto-detects the plan number from the branch and sets up `.impl/`
4. Verify the implementation proceeds normally after detection
