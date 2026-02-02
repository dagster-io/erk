---
title: Issue-PR Closing Integration
read_when:
  - linking PRs to issues for auto-close
  - understanding GitHub's auto-close keywords
  - debugging why issues didn't close when PR merged
---

# Issue-PR Closing Integration

GitHub automatically closes issues when PRs merge if the PR description contains linking keywords. Understanding this integration prevents manual issue cleanup and ensures proper issue tracking.

## Auto-Close Keywords

GitHub recognizes these keywords in PR descriptions:

| Keyword    | Example         |
| ---------- | --------------- |
| `close`    | `close #123`    |
| `closes`   | `closes #123`   |
| `closed`   | `closed #123`   |
| `fix`      | `fix #123`      |
| `fixes`    | `fixes #123`    |
| `fixed`    | `fixed #123`    |
| `resolve`  | `resolve #123`  |
| `resolves` | `resolves #123` |
| `resolved` | `resolved #123` |

**Case insensitive**: `Closes #123` and `closes #123` both work

## Syntax Requirements

### Issue Reference Format

```markdown
Fixes #123
```

**Components:**

- Keyword (`Fixes`)
- Space
- `#` symbol
- Issue number

**Valid:**

```markdown
Closes #123
Resolves #456
Fixes #789
```

**Invalid:**

```markdown
Closes#123 # Missing space
Closes 123 # Missing #
Closes issue 123 # Extra word
```

### Multiple Issues

Close multiple issues in one PR:

```markdown
Fixes #123
Closes #456
Resolves #789
```

Or comma-separated:

```markdown
Fixes #123, #456, #789
```

## Where to Place Keywords

### In PR Description (Required)

Keywords MUST be in the PR description (body), not the title:

```markdown
## Summary

Implements feature X

Fixes #123

## Test plan

- Run pytest
```

**Why:** GitHub only scans PR body, not title, for auto-close keywords.

### In Commit Messages (Not Sufficient)

Keywords in commit messages do NOT trigger auto-close:

```bash
# This will NOT close the issue
git commit -m "Implement feature X

Fixes #123"
```

**However:** When using `gh pr create --fill`, commit messages become the PR body, so keywords work indirectly.

## When Issues Are Closed

GitHub closes linked issues when:

1. ✅ PR is merged to default branch (usually `master` or `main`)
2. ✅ PR description contains linking keywords
3. ✅ Issue and PR are in same repository

**Timing:** Issues close immediately when PR merges (within seconds)

## Cross-Repository Linking

Link issues from other repositories:

```markdown
Fixes owner/repo#123
```

**Example:**

```markdown
Closes anthropics/claude-code#456
```

**Note:** You need write access to the target repository for auto-close to work.

## Debugging Auto-Close Failures

### Issue Didn't Close After PR Merged

**Check 1: Keywords in PR Description?**

```bash
# View PR body
gh pr view 123 --json body --jq .body
```

Look for linking keywords (`Fixes`, `Closes`, etc.)

**Check 2: Merged to Default Branch?**

```bash
# Check PR base branch
gh pr view 123 --json baseRefName --jq .baseRefName
```

Must be `master` or `main` (your default branch)

**Check 3: Issue in Same Repository?**

Cross-repo links require write access to target repo.

**Check 4: PR Merged (Not Closed)?**

```bash
# Check if PR was merged
gh pr view 123 --json merged --jq .merged
```

Closed PRs without merge won't close issues.

### False Positives (Issue Closed Unexpectedly)

**Cause:** Keyword in PR description without intention to close

**Example:**

```markdown
This PR fixes the tests.

See issue #123 for background. # Oops, contains "fixes ... #123"
```

**Prevention:** Avoid linking keywords when referencing issues without closing them:

```markdown
This PR fixes the tests.

See context in issue #123. # Safe: "See" is not a keyword
```

## Best Practices

### DO:

- ✅ Use linking keywords in PR descriptions
- ✅ Link issues at PR creation time (prevents forgetting)
- ✅ Use `gh pr create --fill` to include commit message keywords
- ✅ Verify issue closed after PR merges

### DON'T:

- ❌ Rely on keywords in commit messages alone
- ❌ Use linking keywords for related-but-not-fixed issues
- ❌ Forget to update PR description if issue reference changes
- ❌ Assume issue will close (verify!)

## Workflow Integration

### With erk Plans

When implementing erk plans:

```bash
# Create PR from plan
erk exec setup-impl-from-issue 123

# Plan implementation creates .impl/issue.json
# Use issue number in PR description:
gh pr create --title "Implement feature X" --body "$(cat <<'EOF'
## Summary
Implements feature X from plan

Fixes #123

## Test plan
- Run pytest
- Verify feature works
EOF
)"
```

The `Fixes #123` ensures the plan issue closes when PR merges.

### With Graphite

Graphite auto-includes issue references if PR title contains `#123`:

```bash
# PR title: "Implement feature X (#123)"
gt submit

# Graphite generates PR body including:
# Fixes #123
```

## Related Documentation

- [pr-submission-workflow.md](pr-submission-workflow.md) — Complete PR creation workflow
- [draft-pr-handling.md](draft-pr-handling.md) — Draft PR workflows
