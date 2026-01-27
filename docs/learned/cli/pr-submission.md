---
title: Git-Only PR Submission Workflow
read_when:
  - "submitting PRs without Graphite"
  - "using /erk:git-pr-push command"
  - "understanding PR creation workflows"
---

# Git-Only PR Submission Workflow

Documentation for the git-only PR submission workflow as an alternative to Graphite.

## Table of Contents

- [When to Use Git-Only vs. Graphite](#when-to-use-git-only-vs-graphite)
- [Workflow Steps](#workflow-steps)
- [Reference: /erk:git-pr-push](#reference-erkgit-pr-push)
- [PR Validation](#pr-validation)

---

## When to Use Git-Only vs. Graphite

### Git-Only Workflow

Use git-only submission (`/erk:git-pr-push`) when:

- **Simpler workflow:** No stacks, single feature branch
- **Remote execution:** GitHub Actions workflows (Graphite not available)
- **Direct to main:** Branch directly off main/master
- **Quick submission:** No need for stack management

**Command:** `/erk:git-pr-push`

### Graphite Workflow

Use Graphite submission (`gt finalize`, `gt submit`) when:

- **Stacked changes:** Multiple dependent PRs
- **Local development:** Working in worktrees with Graphite
- **Stack management:** Need to restack, reorder, or split PRs
- **Complex dependencies:** PR depends on other PR

**Commands:** `gt finalize`, `gt submit`

---

## Workflow Steps

The git-only workflow follows this sequence:

### 1. Analyze Staged Changes

Verify what will be committed:

```bash
git status
git diff --cached
```

**Purpose:** Ensure correct files are staged.

### 2. Load Skill

Load `erk-diff-analysis` skill for commit message generation:

```
Use Skill tool to load: erk-diff-analysis
```

**Purpose:** Generate strategic, component-aware commit messages.

### 3. Generate Commit Message

Use skill to analyze changes and produce message:

**Skill analyzes:**

- Changed files
- Affected components
- Issue references
- Strategic framing

**Skill produces:**

```
Title: Add Context Preservation to Replan Workflow

Body:
Introduced Steps 6a-6b to prevent sparse plans...
Closes #6172
```

### 4. Create Commit

Commit with generated message:

```bash
git commit -m "$(cat <<'EOF'
Add Context Preservation to Replan Workflow

Introduced Steps 6a-6b to prevent sparse plans...

Closes #6172
EOF
)"
```

**Important:** Use HEREDOC format to preserve multi-line message.

### 5. Push to Remote

```bash
CURRENT_BRANCH=$(git branch --show-current)
git push -u origin "$CURRENT_BRANCH"
```

**Purpose:** Upload commit to GitHub.

### 6. Check for Existing PR

Before creating PR, check if one already exists:

```bash
EXISTING_PR=$(gh pr list --head "$CURRENT_BRANCH" --state all --json number -q '.[0].number')
```

**Purpose:** Prevent duplicate PR creation.

### 7. Create or Update PR

#### If No PR Exists

Create new draft PR:

```bash
gh pr create \
  --title "$COMMIT_TITLE" \
  --body "$PR_BODY" \
  --draft
```

#### If PR Already Exists

Update existing PR body:

```bash
gh pr edit "$EXISTING_PR" --body "$PR_BODY"
```

**Purpose:** Reuse PR, don't create duplicate.

### 8. Validate PR

Run PR validation checks:

```bash
erk pr check
```

**Validates:**

- Checkout footer exists
- Issue linkage is correct
- PR body format is valid

---

## Reference: /erk:git-pr-push

### Command Location

**File:** `.claude/commands/erk/git-pr-push.md`

### Command Synopsis

```bash
/erk:git-pr-push <description>
```

**Description:** Brief description of changes (used as PR title)

### Full Workflow in Command

The command orchestrates:

1. **Pre-flight checks:** Verify git status, staged changes
2. **Skill loading:** Load `erk-diff-analysis`
3. **Message generation:** Analyze diff, generate commit message
4. **Commit creation:** Create commit with proper attribution
5. **Push:** Upload to remote with `-u` flag
6. **PR detection:** Check for existing PR
7. **PR creation/update:** Create new or update existing
8. **Validation:** Run `erk pr check`

### Example Usage

```bash
# Stage changes
git add docs/learned/planning/*.md

# Submit with description
/erk:git-pr-push "Add context preservation documentation"
```

**Result:**

- Commit created with skill-generated message
- Pushed to `origin/<current-branch>`
- PR created or updated
- Validation confirms PR format

---

## PR Validation

### What `erk pr check` Validates

The validation command checks:

#### 1. Checkout Footer

PR body must include checkout instructions:

````markdown
## Checkout Instructions

```bash
gh pr checkout <PR_NUMBER>
```
````

**Why:** Enables easy local testing by reviewers.

#### 2. Issue Linkage

Commit message should include `Closes #N`:

```
Add Context Preservation Documentation

...

Closes #6172
```

**Why:** Auto-closes issue when PR merges.

#### 3. PR Body Format

PR body should have:

- Title (from commit title)
- Description (from commit body)
- Test plan section
- Checkout instructions footer

**Why:** Consistent PR format across project.

### Validation Failures

If validation fails:

```bash
erk pr check
```

**Output:**

```
ERROR: PR is missing checkout footer
ERROR: Commit message does not include "Closes #N"
```

**Resolution:** Fix issues and push again.

---

## PR Body Structure

### Standard Format

```markdown
# [PR Title]

[Commit message body - explains what and why]

## Test Plan

- [ ] CI passes
- [ ] Manual verification complete

---

## Checkout Instructions

\`\`\`bash
gh pr checkout [PR_NUMBER]
\`\`\`

<!-- Generated with Claude Code -->
```

### Components

| Section                 | Source                    | Purpose                  |
| ----------------------- | ------------------------- | ------------------------ |
| Title                   | Commit message first line | Brief summary of changes |
| Description             | Commit message body       | Detailed explanation     |
| Test Plan               | Template                  | Verification checklist   |
| Checkout Instructions   | Generated (standardized)  | Enable local review      |
| Claude Code Attribution | Template                  | Track auto-generated PRs |

---

## Comparison: Git-Only vs. Graphite

| Aspect          | Git-Only (`/erk:git-pr-push`) | Graphite (`gt submit`)          |
| --------------- | ----------------------------- | ------------------------------- |
| Stacking        | No                            | Yes (stacked PRs)               |
| Branch creation | Manual (`git branch`)         | Managed (`gt create`)           |
| PR creation     | `gh pr create`                | `gt submit`                     |
| Commit messages | Skill-generated               | User-written or skill-generated |
| Issue linking   | Automatic (`Closes #N`)       | Manual or via `gt finalize`     |
| PR body         | Auto-generated from commit    | Generated by Graphite           |
| Validation      | `erk pr check`                | Graphite checks                 |
| Use case        | Simple, remote execution      | Complex, local development      |
| Dependencies    | None (just git + gh CLI)      | Graphite tool required          |

---

## When PR Already Exists

### Detection

Command checks for existing PR:

```bash
gh pr list --head "$CURRENT_BRANCH" --state all --json number -q '.[0].number'
```

**Result:** PR number or empty string.

### Behavior

If PR exists:

1. **Update PR body:** Use `gh pr edit` to update description
2. **Skip creation:** Don't call `gh pr create`
3. **Validate:** Still run `erk pr check`

**Why:** Prevents duplicate PR errors, ensures PR is current.

---

## Integration with Plan Workflow

### Local Implementation

When implementing plan locally:

```bash
# After implementation complete
/erk:git-pr-push "Implement feature X from plan #123"
```

**Result:** PR created linking to plan issue.

### Remote Implementation

GitHub Actions uses git-only workflow:

1. Implementation completes in workflow
2. Changes staged
3. `/erk:git-pr-push` called
4. PR created/updated
5. Validation runs

**Why git-only:** Graphite not available in GitHub Actions.

---

## Summary

**Git-only PR submission workflow:**

1. ✅ Stage changes
2. ✅ Load `erk-diff-analysis` skill
3. ✅ Generate commit message (skill-based)
4. ✅ Create commit
5. ✅ Push to remote
6. ✅ Check for existing PR
7. ✅ Create or update PR
8. ✅ Validate PR format

**Key advantages:**

- No Graphite dependency
- Works in GitHub Actions
- Automatic duplicate prevention
- Skill-generated messages
- Consistent PR format

**Use when:** Simple workflow, remote execution, or no stacking needed.

---

## Related Documentation

- [PR Operations: Duplicate Prevention](pr-operations.md) - Duplicate PR detection patterns
- [Commit Message Generation](../workflows/commit-messages.md) - Skill-based commit messages
- [Git-PR-Push Command](../../../.claude/commands/erk/git-pr-push.md) - Full command reference
- [Graphite Worktree Stack](../../.claude/skills/gt-graphite/) - Graphite workflow mental model
