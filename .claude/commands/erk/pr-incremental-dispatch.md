---
description: Dispatch a local plan against an existing PR for remote implementation
---

# /erk:pr-incremental-dispatch

## Goal

Dispatch a plan written in plan mode against an existing PR's branch for remote AI implementation, without creating a separate planned PR.

## Steps

### 1. Find the plan file

Search for the most recent plan file in `~/.claude/plans/` (same as plan-save discovery). Store the path as `PLAN_FILE`.

If no plan file found, tell the user to write a plan in plan mode first and stop.

### 2. Get PR context

If `$ARGUMENTS` contains a PR number, use that. Otherwise, run:

```bash
gh pr view --json number,title,headRefName
```

to get the current branch's PR. If no PR found, ask the user to specify one and stop.

Store the PR number as `PR_NUMBER`.

### 3. Confirm with user

Show the user:

- Plan title (first `# ` heading from the plan file)
- PR number and title
- "Dispatching plan against PR #NNNN (branch: xxx). Proceed?"

Wait for confirmation before continuing.

### 4. Run dispatch

```bash
erk exec incremental-dispatch --plan-file "$PLAN_FILE" --pr $PR_NUMBER --format json
```

### 5. Display results

Parse the JSON output and display:

- PR URL
- Workflow URL
- Any errors
