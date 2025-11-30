# Planning Workflow

This guide explains the `.impl/` folder protocol used in erk for managing implementation plans.

## Overview

Erk uses `.impl/` folders to track implementation progress for plans executed locally by agents.

## .impl/ Folders

**Purpose**: Track implementation progress for plans executed locally.

**Characteristics**:

- NOT tracked in git (in `.gitignore`)
- Created by planning commands
- Contains `plan.md`, `progress.md`, and optional `issue.json`
- Lives in worktree directory during implementation
- Never committed to repository

**Structure**:

```
.impl/
├── plan.md         # Immutable implementation plan
├── progress.md     # Mutable progress tracking (checkboxes)
└── issue.json      # Optional GitHub issue reference
```

## Local Implementation Workflow

### 1. Create a Plan

Create a plan using Claude's ExitPlanMode tool. This stores the plan in session logs.

### 2. Create Plan as GitHub Issue

Use `/erk:craft-plan` to create a plan and save it directly to a GitHub issue:

```bash
/erk:craft-plan
```

This command guides you through creating a plan and saves it as a GitHub issue with the `erk-plan` label. The issue becomes the source of truth.

### 4. Implement from Issue

Use the unified `erk implement` command to create a worktree and start implementation:

```bash
erk implement <issue-number>
```

This command:

- Creates a dedicated worktree for the issue
- Sets up the `.impl/` folder with plan content from the issue
- Links the worktree to the GitHub issue for progress tracking
- Automatically switches to the new worktree

### 5. Execute the Plan (if not auto-implemented)

If you didn't use `erk implement` (which auto-implements), run the implementation command manually:

```bash
/erk:plan-implement
```

The agent reads `.impl/plan.md`, executes each phase, and updates `.impl/progress.md` as steps complete.

## Progress Tracking

The `.impl/progress.md` file tracks completion status:

```markdown
---
completed_steps: 3
total_steps: 5
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

- **Never commit `.impl/` folders** - They're in `.gitignore` for a reason
- **Safe to delete after implementation** - Once the work is committed, `.impl/` can be removed
- **One plan per worktree** - Each worktree has its own `.impl/` folder

## Remote Implementation via GitHub Actions

For automated implementation via GitHub Actions, use `erk submit`:

```bash
erk submit <issue-number>
```

This command:

- Validates the issue has the `erk-plan` label
- Verifies the issue is OPEN (not closed)
- Triggers the `dispatch-erk-queue.yml` GitHub Actions workflow via direct workflow dispatch
- Displays the workflow run URL

The GitHub Actions workflow will:

1. Find the existing branch and PR (created by `erk submit`)
2. Reconstruct `.impl/` from the GitHub issue
3. Execute the implementation automatically
4. Mark the PR as ready for review

**Monitor workflow progress:**

```bash
# List workflow runs
gh run list --workflow=dispatch-erk-queue.yml

# Watch latest run
gh run watch
```

## Commands Reference

### Plan Creation

- `/erk:craft-plan` - Create a plan interactively and save to GitHub issue

### Implementation (Issue-Based)

- `erk implement <issue>` - Create worktree and implement plan from GitHub issue
- `/erk:plan-implement` - Execute plan in current worktree (called by `erk implement`)
