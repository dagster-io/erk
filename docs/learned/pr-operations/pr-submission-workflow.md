---
title: PR Submission Workflow (Git-Only Path)
read_when:
  - creating PRs via git commands and gh CLI
  - understanding the git-only PR submission path
  - debugging PR creation workflows
---

# PR Submission Workflow (Git-Only Path)

When creating PRs without Graphite (`gt`), use the git-only path: direct git commands + GitHub CLI (`gh pr create`). This workflow is simpler but requires manual branch management.

## When to Use Git-Only Path

Use this path when:

- Not using Graphite stacking
- Simple feature branch workflow (branch directly from master)
- One-off PR creation
- Graphite not installed or not desired

**Alternative:** For stacked PRs and advanced branch management, use Graphite (`gt submit`).

## Complete Git-Only Workflow

### 1. Create Feature Branch

```bash
# From master or current branch
git checkout -b feature-name
```

### 2. Make Changes and Commit

```bash
# Stage changes
git add .

# Commit with message
git commit -m "Implement feature X

- Detail 1
- Detail 2

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### 3. Push Branch

```bash
# Push to remote, set upstream
git push -u origin feature-name
```

### 4. Create PR via gh CLI

```bash
# Create PR with auto-generated title/body from commits
gh pr create --fill

# Or create with custom title/body
gh pr create --title "Add feature X" --body "$(cat <<'EOF'
## Summary
- Implements feature X
- Fixes issue #123

## Test plan
- Run pytest
- Verify UI renders correctly

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

### 5. Verify PR Created

```bash
# Check PR status
gh pr view

# Check PR checks
gh pr checks
```

## PR Creation Options

### Auto-Fill from Commits

```bash
gh pr create --fill
```

**Uses:**

- First commit message as PR title
- Remaining commits as PR body

**Best for:** Single-commit PRs or well-formatted commit messages

### Custom Title and Body

```bash
gh pr create \
  --title "PR title here" \
  --body "PR description here"
```

**Best for:** Multi-commit PRs needing consolidated description

### Interactive Mode

```bash
gh pr create
```

**Prompts for:**

- PR title
- PR body
- Base branch
- Draft status

**Best for:** Manual PR creation with guided prompts

## Draft PRs

Create as draft for work-in-progress:

```bash
gh pr create --fill --draft
```

Convert to ready for review:

```bash
gh pr ready
```

## PR Checks and Validation

After PR creation, validate with erk:

```bash
erk pr check
```

This verifies:

- PR description contains required sections
- PR is linked to issue (if required)
- PR title follows conventions

## Updating Existing PR

### Push Additional Commits

```bash
# Make changes
git add .
git commit -m "Address review feedback"

# Push to update PR
git push
```

### Update PR Title/Body

```bash
# Edit PR details
gh pr edit

# Or update specific field
gh pr edit --title "New title"
gh pr edit --body "New body"
```

## Common Issues

### Issue: PR Already Exists for Branch

**Error:**

```
a pull request for branch "feature-name" into branch "master" already exists
```

**Cause:** Branch already has an open PR

**Fix:**

```bash
# View existing PR
gh pr view

# Or list all PRs for this branch
gh pr list --head feature-name
```

### Issue: Push Rejected (Branch Diverged)

**Error:**

```
Updates were rejected because the tip of your current branch is behind
```

**Cause:** Remote branch was force-pushed or modified

**Fix:**

```bash
# Pull remote changes
git pull --rebase origin feature-name

# Or force push (if you own the branch)
git push --force-with-lease origin feature-name
```

### Issue: No Upstream Branch Set

**Error:**

```
fatal: The current branch has no upstream branch
```

**Fix:**

```bash
# Push with upstream
git push -u origin feature-name
```

## Comparison: Git-Only vs Graphite

| Feature                | Git-Only          | Graphite (`gt`)      |
| ---------------------- | ----------------- | -------------------- |
| Stacked PRs            | Manual branching  | Automatic stacking   |
| Branch management      | git commands      | gt track, gt untrack |
| PR submission          | gh pr create      | gt submit            |
| Branch synchronization | git pull --rebase | gt sync              |
| Complexity             | Simple            | More powerful        |

Use git-only for simple cases, Graphite for complex stacking workflows.

## Related Documentation

- [gh](../../.claude/skills/gh/SKILL.md) — GitHub CLI mental model and commands
- [pr-operations.md](pr-operations.md) — Duplicate PR prevention and detection
- [draft-pr-handling.md](draft-pr-handling.md) — Draft PR workflows
