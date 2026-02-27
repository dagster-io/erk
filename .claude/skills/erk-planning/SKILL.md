---
name: erk-planning
description: >
  This skill documents plan management in erk. Use when creating, updating,
  or working with erk-plan GitHub PRs. Covers plan structure, the planning
  workflow, and when to update vs create new plans.
---

# Erk Planning Skill

## When to Load

Load this skill when user mentions:

- "update plan", "update the plan"
- "modify the plan", "change the plan"
- "edit the plan"

**When these triggers fire and a plan was saved in this session:**

1. Check for `plan-saved-issue.marker` in session scratch:
   ```bash
   erk exec marker read --session-id <session-id> plan-saved-issue
   ```
2. If found (exit code 0), invoke `/local:plan-update <issue-number>` with the marker content
3. If not found (exit code 1), ask user for issue number

## Overview

Erk-plans are GitHub PRs that track implementation plans. They have a two-part structure:

- **PR body**: Machine-readable metadata (timestamps, comment IDs, dispatch info)
- **First comment**: Human-readable plan content in a `plan-body` metadata block

This separation keeps metadata parseable while plan content remains readable.

## Plan Structure

```
PR #123: "Add feature X [erk-plan]"
├── Body (metadata only):
│   <!-- erk:metadata-block:plan-header -->
│   created_at: 2025-01-05T12:00:00Z
│   created_by: username
│   plan_comment_id: 456789
│   <!-- /erk:metadata-block:plan-header -->
│
│   ## Commands
│   - `erk implement 123`
│   - `erk pr dispatch 123`
│
└── Comment #456789 (first comment, plan content):
    <!-- erk:metadata-block:plan-body -->
    <details open><summary>Plan</summary>

    # Add feature X

    ## Implementation Steps
    1. Step one
    2. Step two

    </details>
    <!-- /erk:metadata-block:plan-body -->
```

## Quick Reference

### Creating a Plan

After writing a plan in plan mode:

```bash
# Via slash command (recommended)
/erk:plan-save

# Via CLI
erk exec plan-save --format display --session-id="<session-id>"
```

### Updating an Existing Plan

When you need to modify a plan that's already saved to GitHub:

```bash
# Via slash command
/local:plan-update 123

# Via CLI
erk exec plan-update --plan-number 123 --session-id="<session-id>"
```

**When to update vs create new:**

| Scenario                                     | Action                       |
| -------------------------------------------- | ---------------------------- |
| Minor corrections (typos, clarifications)    | Update existing              |
| Adding details discovered during exploration | Update existing              |
| Plan is fundamentally wrong/obsolete         | Create new via `/erk:replan` |
| Significant scope change                     | Create new, close old        |

### The Update Workflow

1. **Fetch existing plan** (if not in local files):

   ```bash
   gh pr view 123 --comments --json comments
   ```

   Extract content from `plan-body` block in first comment.

2. **Enter plan mode** and make modifications

3. **Update the issue**:

   ```bash
   /local:plan-update 123
   ```

4. **Optionally add a comment** explaining what changed:
   ```bash
   gh pr comment 123 --body "Updated plan: added step 3 for edge case handling"
   ```

## Plan Mode Integration

When exiting plan mode with an existing linked issue (e.g., from `.erk/impl-context/<branch>/ref.json`), consider:

1. **Update existing**: If iterating on the same plan
2. **Save as new**: If this is a fresh plan unrelated to the linked issue
3. **Implement directly**: If changes are ready to code

The `plan-update` command finds plan content from:

1. `--plan-path` flag (explicit file path)
2. Session scratch storage (via `--session-id`)
3. `~/.claude/plans/` directory (latest plan file)

## Related Commands

| Command                 | Purpose                              |
| ----------------------- | ------------------------------------ |
| `/erk:plan-save`        | Create new plan PR from current plan |
| `/local:plan-update`    | Update existing plan                 |
| `/erk:plan-implement`   | Save plan and immediately implement  |
| `/erk:replan`           | Analyze and recreate obsolete plan   |
| `erk implement <issue>` | Implement a saved plan               |

## Resources

### references/

- `workflow.md` - Complete update workflow with examples
