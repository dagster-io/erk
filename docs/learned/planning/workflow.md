---
title: Planning Workflow
read_when:
  - "using .erk/impl-context/ folders"
  - "understanding plan file structure"
  - "implementing plans"
last_audited: "2026-03-05 00:00 PT"
audit_result: clean
---

# Planning Workflow

This guide explains the `.erk/impl-context/` protocol used in erk for managing implementation plans.

## Overview

Erk uses `.erk/impl-context/<branch>/` directories to track implementation progress for plans executed locally by agents.

## .erk/impl-context/ Directories

**Purpose**: Track implementation progress for plans executed locally.

**Characteristics**:

- Branch-scoped (multiple impl directories possible, one per branch)
- Briefly committed during plan-save, then cleaned up
- Created by planning commands
- Contains `plan.md`, `progress.md`, and `ref.json`

### Location

The impl directory is branch-scoped under `.erk/impl-context/`:

```
{worktree_root}/.erk/impl-context/<branch>/
```

**Path Resolution**:

```python
impl_dir = resolve_impl_dir()  # from erk.impl_folder
```

**Structure**:

```
.erk/impl-context/<branch>/
├── plan.md         # Immutable implementation plan
├── progress.md     # Mutable progress tracking (checkboxes)
└── ref.json        # GitHub plan reference (plan_id, plan_url)
```

## Local Implementation Workflow

### 1. Create a Plan

Create a plan using Claude's ExitPlanMode tool. This stores the plan in session logs.

### 2. Choose Your Workflow

When exiting plan mode, the hook presents options based on your current branch context.

#### Option 1: "Create new branch and planned PR" (always available)

Creates a new branch, saves the plan to GitHub as a draft PR, then exits plan mode:

```bash
/erk:plan-save          # run by agent after user chooses this option
```

The plan PR branch is stacked on the current branch if on a feature branch, otherwise created from trunk. After exit, the agent implements on the new branch. Use when you want a tracked plan PR with full lifecycle management.

#### Option 2: "Implement without saving" (always available, NEW)

Implements directly on the current branch **without** creating a plan PR or saving to GitHub:

- Creates the `exit-plan-mode-hook.implement-now.marker` marker file
- Calls ExitPlanMode
- Implements changes directly on the current branch
- Optionally runs `erk pr submit` when done

Use for small changes or experiments where GitHub tracking overhead isn't worth it.

#### Option 3: "Make current empty branch a planned PR" (conditional — hidden on trunk)

Only shown when **both** conditions are met:

- Current branch has **no commits** ahead of trunk
- Current branch is **not** `master` or `main`

Saves the plan to GitHub using the current branch as the plan PR branch (instead of creating a new one):

```bash
/erk:plan-save --current-branch    # run by agent after user chooses this option
```

This converts the current branch into the plan PR branch directly.

> **⚠️ WARNING:** If you are on `master` or `main`, option 3 is hidden and the hook displays a warning: "We strongly discourage implementing directly on the trunk branch. Consider saving the plan and implementing in a dedicated worktree instead."

#### Option 4: "View/Edit the Plan"

For reviewing or refining the plan:

- Opens plan in editor (non-terminal editors) or displays plan in session
- Loop back to choose another option
- Best when you need to refine before committing to save or implement

#### Statusline Context Display

The hook displays current context before presenting options:

```
(wt:erk-slot-01) (br:feature-x) (pr:#123) (plan:#456)
```

- `wt:` — current worktree name
- `br:` — current branch name
- `pr:` — PR number if current branch has an associated PR
- `plan:` — plan number if an impl-context plan is active

### 3. Implement from Existing Issue (Alternative)

If you have an issue number from a previously saved plan:

```bash
erk implement <issue-number>
```

This command:

- Sets up the impl directory under `.erk/impl-context/<branch>/` with plan content from the issue
- Links to the GitHub issue for progress tracking

## Plan Save Workflow

When a user saves their plan to GitHub (via `/erk:plan-save`), the workflow should end cleanly without additional prompts.

### Flow Diagram

```
┌─────────────────────┐
│  Plan Mode          │
│  (plan created)     │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Exit Plan Mode Hook │
│ "What would you     │
│ like to do?"        │
└─────────┬───────────┘
          │
    ┌─────┼──────────────┬─────────────┐
    │     │              │             │
    ▼     ▼              ▼             ▼
┌────────────────┐ ┌──────────────┐ ┌──────────┐
│ Create new     │ │Implement     │ │View/Edit │
│ branch + PR    │ │without saving│ │ (4)      │
│ (1)            │ │ (2)          │ │          │
└───┬────────────┘ └──────┬───────┘ └────┬─────┘
    │    [3: Make current  │              │
    │     empty branch PR] │              │
    │    (hidden on trunk) │              │
    │                      │              │
    ▼                      ▼              │
┌───────────────┐  ┌──────────────┐      │
│plan-save      │  │Create marker │      │
│creates plan PR│  │ExitPlanMode  │      │
│exits plan mode│  │Impl directly │      │
└───────┬───────┘  └──────────────┘      │
        │                                │
        ▼                                │
┌───────┐                       ┌────────┘
│ STOP  │  ← Do NOT call        │ (loop back)
│(plan  │    ExitPlanMode        │
│mode)  │    again               ▼
└───────┘
```

### Key Principle: Don't Call ExitPlanMode After Saving

After saving to GitHub:

1. The marker file `exit-plan-mode-hook.plan-saved.marker` is created
2. Success message is displayed with next steps
3. **Session stays in plan mode** - no ExitPlanMode call

Why? ExitPlanMode shows a plan approval dialog. After saving, this dialog:

- Serves no purpose (plan is already saved)
- Requires unnecessary user interaction
- Confuses the workflow

### Safety Net: Hook Blocks ExitPlanMode

If ExitPlanMode is called anyway (e.g., by mistake), the `exit-plan-mode-hook` detects the plan-saved marker and blocks with a "session complete" message. The marker is **preserved** (not deleted) so subsequent ExitPlanMode calls continue to be blocked.

See `src/erk/cli/commands/exec/scripts/exit_plan_mode_hook.py` for the full implementation.

## Progress Tracking

The `progress.md` file in the impl directory tracks completion status:

```markdown
---
completed_nodes: 3
total_nodes: 5
---

# Progress Tracking

- [x] 1. First step (completed)
- [x] 2. Second step (completed)
- [x] 3. Third step (completed)
- [ ] 4. Fourth step
- [ ] 5. Fifth step
```

The front matter enables progress indicators in `erk status` output.

## 🔴 Line Number References Are DISALLOWED in Implementation Plans

Line numbers drift as code changes, causing implementation failures. Use durable alternatives instead.

### The Rule

- 🔴 **DISALLOWED**: Line number references in implementation steps
- ✅ **REQUIRED**: Use function names, behavioral descriptions, or structural anchors
- **Why**: Line numbers become stale as code evolves, leading to confusion and incorrect implementations

### Allowed Alternatives

Use these durable reference patterns instead of line numbers:

- ✅ **Function/class names**: `Update validate_user() in src/auth.py`
- ✅ **Behavioral descriptions**: `Add null check before processing payment`
- ✅ **File paths + context**: `In the payment loop in src/billing.py, add retry logic`
- ✅ **Contextual anchors**: `At the start of process_order(), add validation`
- ✅ **Structural references**: `In the User class constructor, initialize permissions`

### Exception: Historical Context Only

Line numbers ARE allowed in "Context & Understanding" or "Planning Artifacts" sections when documenting historical research:

- Must include commit hash: `Examined auth.py lines 45-67 (commit: abc123)`
- These are historical records, not implementation instructions
- Provides breadcrumb trail for understanding research process

### Examples

**❌ WRONG - Fragile line number references:**

```markdown
1. Modify lines 120-135 in billing.py to add retry logic
2. Update line 89 in auth.py with new validation
3. Change lines 200-215 in api.py to handle errors
```

**✅ RIGHT - Durable behavioral references:**

```markdown
1. Update calculate_total() in src/billing.py to include retry logic
2. Add null check to validate_user() in src/auth.py before database query
3. Modify process_request() in src/api.py to handle timeout errors gracefully
```

**✅ ALLOWED - Historical context with commit hash:**

```markdown
## Context & Understanding

### Planning Artifacts

During planning, examined the authentication flow:

- Reviewed auth.py lines 45-67 (commit: a1b2c3d) - shows current EAFP pattern
- Checked validation.py lines 12-25 (commit: a1b2c3d) - demonstrates LBYL approach
```

## Important Notes

- **Never commit `.erk/impl-context/` permanently** - It is briefly committed during plan-save, then cleaned up
- **Safe to delete after implementation** - Once the work is committed, the impl directory can be removed
- **One plan per branch (branch-scoped)** - Each branch has its own impl directory under `.erk/impl-context/<branch>/`

## Remote Implementation via GitHub Actions

### How Changes Are Detected

The workflow uses a **dual-check** approach to detect implementation changes:

1. **Pre-implementation**: Captures `git rev-parse HEAD` before the agent runs
2. **Post-implementation**: Checks both uncommitted changes AND new commits
3. **Result**: Changes exist if either channel has changes

This dual-check prevents false negatives when agents commit their work without leaving uncommitted changes. See [Plan-Implement Change Detection](../ci/plan-implement-change-detection.md) for details.

### Submitting for Remote Implementation

For automated implementation via GitHub Actions, use `erk pr submit`:

```bash
erk pr submit <issue-number>
```

This command:

- Validates the issue has the `erk-plan` label
- Verifies the issue is OPEN (not closed)
- Triggers the `plan-implement.yml` GitHub Actions workflow via direct workflow dispatch
- Displays the workflow run URL

The GitHub Actions workflow will:

1. Create a dedicated branch from trunk
2. Set up the `.erk/impl-context/` folder with the plan from the issue
3. Create a draft PR
4. Execute the implementation automatically
5. Mark the PR as ready for review

**Monitor workflow progress:**

```bash
# List workflow runs
gh run list --workflow=plan-implement.yml

# Watch latest run
gh run watch
```

## Commands Reference

### Plan Creation and Saving

- `/erk:plan-save` - Save the current session's plan to GitHub as an issue (no implementation)

### Implementation

- `/erk:plan-implement` - Save plan to GitHub AND implement (full workflow: save → setup → implement → CI → PR)
- `erk implement <issue>` - Implement plan from existing GitHub issue in current directory
