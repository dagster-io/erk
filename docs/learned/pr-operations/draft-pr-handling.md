---
title: Draft PR Handling
read_when:
  - creating or working with draft PRs
  - understanding when to use draft status
  - converting between draft and ready for review
---

# Draft PR Handling

GitHub draft PRs signal work-in-progress. Understanding when to use draft status and how to manage transitions prevents premature reviews and CI waste.

## What is a Draft PR?

A draft PR is a pull request marked as "not ready for review":

- Visible in PR list with "Draft" label
- Cannot be merged (merge button disabled)
- Code review requests are blocked
- CI may run (depending on workflow configuration)

## When to Use Draft Status

Create PRs as draft when:

1. **Work is incomplete**
   - Implementation in progress
   - Tests not yet written
   - Known failing CI checks

2. **Seeking early feedback**
   - Architecture review before full implementation
   - API design discussion
   - UX feedback on visual changes

3. **CI validation before review**
   - Want to verify CI passes before requesting reviews
   - Iterating on fixes based on CI feedback

4. **Stacked PR dependencies**
   - Base PR not merged yet
   - Dependent PR shouldn't be reviewed until base is ready

## When NOT to Use Draft Status

Skip draft for:

- Simple, obvious changes (typo fixes, doc updates)
- Changes ready for immediate review
- Hotfixes and urgent fixes
- PRs that CI-block unnecessarily (tests are expensive)

## Creating Draft PRs

### Via gh CLI

```bash
# Create draft from command line
gh pr create --fill --draft
```

### Via Graphite

```bash
# Graphite auto-creates draft if base PR is draft
gt submit --draft
```

### Via GitHub Web UI

When creating PR manually:

- Check "Create as draft" checkbox at bottom of PR form
- Or change dropdown next to "Create pull request" button

## Converting Draft to Ready

### Via gh CLI

```bash
# Mark PR ready for review
gh pr ready
```

### Via GitHub Web UI

- Click "Ready for review" button at bottom of PR page

### Automatic Conversion

Some workflows automatically convert draft to ready when:

- All CI checks pass
- All review comments resolved
- Specific label added

## CI Behavior with Draft PRs

### Erk's CI Configuration

Erk skips some CI steps for draft PRs:

```yaml
# .github/workflows/ci.yml
if: github.event.pull_request.draft != true
```

**Skipped for drafts:**

- Expensive test suites
- Full lint/type checking
- Deployment previews

**Always runs for drafts:**

- Basic validation
- Fast smoke tests
- Security scans

### Rationale

**Why skip CI on drafts:**

- Saves CI minutes/costs
- Prevents review notification spam
- Allows iterating without CI pressure

**Why run some CI on drafts:**

- Catch critical errors early
- Validate basic correctness
- Security checks shouldn't wait

## Draft PR Workflow Pattern

### 1. Create as Draft

```bash
git checkout -b feature-branch
# ... make changes ...
git commit -m "WIP: Implement feature"
git push -u origin feature-branch
gh pr create --fill --draft
```

### 2. Iterate Until CI Passes

```bash
# Check CI status
gh pr checks

# Make fixes
git commit -m "Fix lint errors"
git push

# Repeat until green
```

### 3. Mark Ready for Review

```bash
# When satisfied with CI and code
gh pr ready
```

### 4. Request Reviews

```bash
# Request specific reviewers
gh pr edit --add-reviewer @username

# Or let CODEOWNERS handle it automatically
```

## Draft PR Best Practices

### DO:

- ✅ Use draft for work-in-progress
- ✅ Convert to ready when CI passes and code is review-ready
- ✅ Use draft for early feedback ("Does this approach make sense?")
- ✅ Keep draft PRs updated with base branch (rebase/merge)

### DON'T:

- ❌ Leave PRs as draft indefinitely (creates stale PRs)
- ❌ Use draft to avoid CI (fix the issues instead)
- ❌ Create draft PRs for trivial changes (overhead not worth it)
- ❌ Request reviews on draft PRs (they'll be ignored)

## Checking Draft Status

### Via gh CLI

```bash
# View PR details (shows draft status)
gh pr view

# List draft PRs
gh pr list --draft
```

### Via erk Commands

```bash
# Check PR validation (includes draft status check)
erk pr check
```

## Draft PRs in Stacked Workflows

When using Graphite stacking:

- **Base PR is draft** → Dependent PRs auto-created as draft
- **Base PR marked ready** → Dependent PRs remain draft until manually marked ready
- **Merge base PR** → Dependent PRs can now be marked ready

**Pattern:**

```bash
# Create stack
gt create feature-base
gt create feature-dependent --onto feature-base

# Submit as drafts
gt submit --draft  # Both PRs created as draft

# Mark base ready
gh pr ready  # On base PR

# After base merges, mark dependent ready
gh pr ready  # On dependent PR
```

## Related Documentation

- [pr-submission-workflow.md](pr-submission-workflow.md) — Complete PR creation workflow
- [pr-operations.md](pr-operations.md) — PR duplicate prevention
