---
title: One-Shot Workflow
read_when:
  - "using erk one-shot command"
  - "understanding one-shot remote execution"
  - "debugging one-shot workflow failures"
  - "working with one-shot.yml"
tripwires:
  - action: "modifying one-shot branch naming convention"
    warning: "Branch format is `oneshot-{slug}-{MM-DD-HHMM}` (no plan issue) or `P{N}-{slug}-{MM-DD-HHMM}` (when plan_issue_number is provided). The workflow and CLI both depend on these prefixes for identification."
  - action: "assuming one-shot plan and implementation run in the same Claude session"
    warning: "They run in separate sessions. The plan is written to `.impl/plan.md` and the implementer reads it fresh. No context carries over."
last_audited: "2026-02-16 14:25 PT"
audit_result: clean
---

# One-Shot Workflow

Single-command dispatch for autonomous remote planning and implementation. The user provides a natural language prompt, and erk handles branch creation, planning, and implementation via GitHub Actions.

## Architecture Overview

```
User (Local CLI)
    |
    v
erk one-shot "prompt"
    | (creates branch, draft PR, triggers workflow)
    v
GitHub Actions: one-shot.yml
    |
    +-- plan job (Claude session 1)
    |   |  Read prompt -> Explore codebase -> Write plan -> Save as GitHub issue
    |   |  Register plan with erk exec register-one-shot-plan
    |   v
    +-- implement job (Claude session 2, depends on plan)
        |  Delegates to plan-implement.yml (standard implementation)
        v
    PR ready for review
```

## CLI Command

**File:** `src/erk/cli/commands/one_shot.py`

```bash
erk one-shot "Add a --verbose flag to the plan submit command" --model sonnet
```

**Responsibilities:**

1. Validates prompt and optional model parameter
2. Generates branch name via `generate_branch_name()` in `one_shot_dispatch.py`: `P{N}-{slug}-{MM-DD-HHMM}` when `plan_issue_number` is provided, otherwise `oneshot-{slug}-{MM-DD-HHMM}`
3. Creates branch from trunk, writes prompt to `.worker-impl/task.md`, and commits
4. Pushes branch to remote
5. Creates a draft PR with prompt in description
6. Triggers the `one-shot.yml` GitHub Actions workflow
7. Restores the original branch after workflow trigger (even on error)

**Model shortcuts:** `haiku`/`h`, `sonnet`/`s`, `opus`/`o`

## GitHub Actions Workflow

**File:** `.github/workflows/one-shot.yml`

Two-phase design with separate jobs:

### Plan Job

1. **Setup:** Checkout repo, configure auth (GitHub token, Anthropic API key), install tools (uv, erk, claude, prettier)
2. **Write prompt:** Creates `.impl/task.md` with the user's prompt
3. **Detect trunk:** Identifies main/master branch
4. **Run planning:** Executes `/erk:one-shot-plan` Claude command
5. **Validate outputs:** Checks `.impl/plan.md` and `.impl/plan-result.json` exist
6. **Register plan:** Runs `erk exec register-one-shot-plan` with issue/PR metadata
7. **Output:** Exports `issue_number` and `issue_title` for the implement job

### Implement Job

- Depends on plan job success
- Only runs if `issue_number` is not empty
- Delegates to `plan-implement.yml` reusable workflow
- Passes through: issue number, branch, PR number, model, submitter

### Error Handling

- Plan job uses `continue-on-error: false` for critical steps
- Best-effort cleanup with `if: always()` for non-critical steps
- Implementation job only starts if planning produced a valid issue

## Remote Planning Command

**File:** `.claude/commands/erk/one-shot-plan.md`

Runs in a fresh Claude session inside GitHub Actions:

1. Read `.impl/task.md` (prompt from workflow)
2. Load AGENTS.md project context and scan docs/learned/
3. Explore codebase with Glob/Grep for relevant files
4. Write comprehensive plan to `.impl/plan.md`
5. Save plan as GitHub issue via `erk exec plan-save-to-issue --format json`
6. Parse JSON result, write `.impl/plan-result.json` with issue metadata

**Key constraint:** This command does planning only. No implementation. The plan must be self-contained because a separate Claude session implements it.

## Key Design Decisions

### Separation of Planning and Implementation

The planner and implementer run in separate Claude sessions. This means:

- No context bleeds from exploration to implementation
- The plan must be self-contained and explicit
- Implementation follows the standard `/erk:plan-implement` flow

### Branch Naming

`oneshot-{slug}-{MM-DD-HHMM}` format is used when no plan issue exists. When `plan_issue_number` is provided, the `P{N}-{slug}-{MM-DD-HHMM}` format is used instead, matching plan-based branches.

### Original Branch Restoration

The CLI always restores the user's original branch after triggering the workflow, even on error. This prevents the user from being stranded on a one-shot branch.

## Related Documentation

- [Plan Lifecycle](../planning/lifecycle.md) - Standard plan lifecycle (one-shot enters at Phase 3)
- [Plan Implement Command](../planning/workflow.md) - Implementation workflow details
