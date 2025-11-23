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

## Canonical Workflow (GitHub-First)

**GitHub issues are the canonical source for all erk plans**, enabling full traceability and integration with GitHub's PR workflow.

### 1. Create a Plan

Start by creating an enriched plan from your conversation:

```bash
/erk:save-context-enriched-plan
```

This creates a plan file at the repository root (e.g., `my-feature-plan.md`).

### 2. Create Worktree from Plan

Create a dedicated worktree for implementing the plan:

```bash
/erk:create-wt-from-plan-file
```

**This workflow now automatically:**

- Creates a GitHub issue from the plan file
- Applies the `erk-plan` label
- Creates a worktree from the issue
- Links the worktree to the issue via `.impl/issue.json`
- Posts a workflow comment to the issue

The worktree is created with:

- `.impl/plan.md` - Implementation plan from issue body
- `.impl/progress.md` - Progress tracking with checkboxes
- `.impl/issue.json` - GitHub issue metadata (number, URL, title)

### 3. Switch to Worktree

Navigate to the newly created worktree:

```bash
erk checkout <branch-name>
```

### 4. Execute the Plan

Run the implementation command:

```bash
/erk:implement-plan
```

The agent reads `.impl/plan.md`, executes each phase, and updates `.impl/progress.md` as steps complete.

### 5. Submit PR

When implementation is complete, submit a PR that references the issue:

```bash
/git:push-pr
```

The PR can include `Closes #123` to auto-close the issue when merged.

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

## Important Notes

- **Never commit `.impl/` folders** - They're in `.gitignore` for a reason
- **Safe to delete after implementation** - Once the work is committed, `.impl/` can be removed
- **One plan per worktree** - Each worktree has its own `.impl/` folder

## .worker-impl/ Folders (Future)

`.worker-impl/` folders are purposely meant to be checked into git (not covered in this guide).

## Alternative Workflows

### Create Worktree from Existing Issue

If you already have a GitHub issue with the `erk-plan` label:

```bash
/erk:create-wt-from-plan-issue 123
```

Or with a GitHub URL:

```bash
/erk:create-wt-from-plan-issue https://github.com/owner/repo/issues/123
```

### Create Worktree Using CLI Directly

You can also use the `erk` CLI directly:

```bash
erk create --from-issue 123 --json --stay
```

This is useful for scripting or when you want more control over the process.

## Command Comparison

| Command                           | Source            | Creates Issue? | Creates Worktree? | Requires GitHub? |
| --------------------------------- | ----------------- | -------------- | ----------------- | ---------------- |
| `/erk:save-context-enriched-plan` | Conversation      | ❌ No          | ❌ No             | ❌ No            |
| `/erk:create-wt-from-plan-file`   | Plan file on disk | ✅ Yes (auto)  | ✅ Yes            | ✅ Yes           |
| `/erk:create-wt-from-plan-issue`  | GitHub issue      | ❌ No          | ✅ Yes            | ✅ Yes           |
| `/erk:implement-plan`             | Current `.impl/`  | ❌ No          | ❌ No             | ❌ No            |
| `erk create --from-issue`         | GitHub issue      | ❌ No          | ✅ Yes            | ✅ Yes           |

## Troubleshooting

### "gh CLI not authenticated"

**Symptom**: Error when creating worktree from plan file or issue.

**Solution**:

```bash
gh auth login
```

Follow the prompts to authenticate with GitHub.

### "Failed to create issue"

**Symptom**: Issue creation fails when running `/erk:create-wt-from-plan-file`.

**Troubleshooting steps**:

1. Check GitHub connectivity:

   ```bash
   gh auth status
   ```

2. Verify repository has issues enabled:

   ```bash
   gh repo view
   ```

3. Check GitHub API rate limits:
   ```bash
   gh api rate_limit
   ```

### "Issue must have 'erk-plan' label"

**Symptom**: Error when creating worktree from issue.

**Solution**: Add the label to the issue:

```bash
gh issue edit 123 --add-label erk-plan
```

Or create issues using the proper workflow which applies the label automatically:

```bash
/erk:create-wt-from-plan-file
```

### "gh CLI not found"

**Symptom**: `erk create --from-issue` fails with "gh CLI not found".

**Solution**: Install GitHub CLI:

```bash
brew install gh
```

Or visit: https://cli.github.com/

## Commands Reference

- `/erk:save-context-enriched-plan` - Create enriched plan from conversation
- `/erk:create-wt-from-plan-file` - Create GitHub issue + worktree from plan on disk
- `/erk:create-wt-from-plan-issue` - Create worktree from existing GitHub issue
- `/erk:implement-plan` - Execute plan in current worktree
- `erk create --from-issue <number>` - CLI command to create worktree from issue
