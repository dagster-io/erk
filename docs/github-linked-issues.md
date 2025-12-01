# GitHub Linked Issues Feature

## Overview

GitHub provides a built-in feature for automatically linking pull requests to issues and closing issues when PRs are merged. This feature uses special keywords in PR descriptions and commit messages.

**Documentation source**: https://docs.github.com/en/issues/tracking-your-work-with-issues/linking-a-pull-request-to-an-issue

## Supported Keywords

GitHub recognizes **9 keywords** for automatic linking:

- `close`, `closes`, `closed`
- `fix`, `fixes`, `fixed`
- `resolve`, `resolves`, `resolved`

**Case handling:**

- Keywords are case-insensitive: `Closes`, `CLOSES`, `closes` all work
- Optional colon syntax: `Closes: #10`, `CLOSES #10`, `CLOSES: #10`

## Where Keywords Work

### 1. Pull Request Description (Primary)

Keywords in the PR body/description are recognized when the PR is created:

```markdown
Closes #123

## Implementation Complete

This PR implements the auth refactor.
```

### 2. Commit Messages

Keywords also work in commit messages:

```bash
git commit -m "Fix auth bug

Fixes #456"
```

**Note**: PRs with keywords in commits won't show as "linked" in GitHub's UI, but issues will still close on merge.

## Automatic Closure Behavior

### Critical Constraint: Default Branch Only

**Issues only auto-close when PR merges to the repository's default branch (master/main).**

- ✅ PR targets `master` → Issues close automatically on merge
- ❌ PR targets `feature-branch` → Keywords ignored, no linking, no auto-close

This is a hard constraint - there's no way to enable auto-close for non-default branches.

## Syntax

### Same Repository

```markdown
Closes #123
```

### Different Repository

```markdown
Fixes octo-org/octo-repo#100
```

### Multiple Issues

**Must repeat keyword for each issue:**

```markdown
Resolves #10, resolves #123, resolves octo-org/octo-repo#100
```

**This does NOT work:**

```markdown
Closes #10, #123 ❌ Only #10 will be linked
```

## Limitations

1. **Manual linking limit**: Up to 10 issues per PR
2. **Cannot unlink keyword-based links**: Must edit PR description to remove keyword
3. **Default branch only**: No auto-close for PRs to other branches
4. **No label filtering**: GitHub closes ALL referenced issues (can't filter by label)

## API Access

### Via GitHub CLI

**Query linked issues:**

```bash
gh pr view 123 --json closingIssuesReferences
```

**Output format:**

```json
{
  "closingIssuesReferences": [
    {
      "number": 123,
      "title": "Fix authentication bug",
      "url": "https://github.com/owner/repo/issues/123"
    }
  ]
}
```

**Extract just issue numbers:**

```bash
gh pr view 123 --json closingIssuesReferences --jq '.closingIssuesReferences[].number'
```

### In GitHub Actions

```yaml
- name: Get linked issues
  env:
    GH_TOKEN: ${{ github.token }}
    PR_NUMBER: ${{ github.event.pull_request.number }}
  run: |
    ISSUES=$(gh pr view $PR_NUMBER \
      --json closingIssuesReferences \
      --jq '.closingIssuesReferences[].number')

    for issue in $ISSUES; do
      echo "Linked issue: #$issue"
    done
```

## Use Cases

### 1. Add Comments to Auto-Closed Issues

GitHub closes the issues, but you can add attribution comments:

```yaml
- name: Comment on closed issues
  run: |
    ISSUES=$(gh pr view $PR_NUMBER --json closingIssuesReferences --jq '.closingIssuesReferences[].number')

    for issue in $ISSUES; do
      gh issue comment $issue \
        --body "✅ Closed by PR #$PR_NUMBER"
    done
```

### 2. Filter by Label Before Acting

Check if linked issues have specific labels:

```yaml
- name: Process plans only
  run: |
    ISSUES=$(gh pr view $PR_NUMBER --json closingIssuesReferences --jq '.closingIssuesReferences[].number')

    for issue in $ISSUES; do
      if gh issue view $issue --json labels \
        | jq -e '.labels[] | select(.name == "erk-plan")' > /dev/null; then

        echo "Issue #$issue is a plan"
        # Take action for plans
      fi
    done
```

### 3. Prevent Closure of Specific Issues

**Note**: You cannot prevent GitHub's auto-close. Alternative:

1. **Document convention**: Don't use closing keywords for certain issue types
2. **Reopen issues**: Detect and reopen issues that shouldn't have closed
3. **Use non-closing references**: `See #123`, `Related to #456`

## Comparison with Custom Parsing

| Approach              | Parsing      | Robustness        | Standard         | Flexibility     |
| --------------------- | ------------ | ----------------- | ---------------- | --------------- |
| **Linked Issues API** | GitHub       | ✅ Battle-tested  | ✅ Universal     | ⚠️ Limited      |
| **Frontmatter**       | Custom YAML  | ⚠️ Must implement | ❌ Custom format | ✅ Full control |
| **Regex**             | Custom regex | ❌ Fragile        | ⚠️ Semi-standard | ⚠️ Medium       |

## Best Practices

### 1. Use Standard Keywords

Stick to the most common keywords:

- `Closes #123` - Most widely recognized
- `Fixes #456` - Common for bug fixes
- `Resolves #789` - Common for feature requests

### 2. Place Keywords at Start of PR Body

```markdown
Closes #123

## Summary

Rest of PR description...
```

This makes links immediately visible in PR view.

### 3. One Keyword Per Issue

```markdown
Closes #123, fixes #456, resolves #789
```

Explicit keywords for each issue ensures proper linking.

### 4. Document Conventions

If using labels to filter which issues should close, document this:

```markdown
# PR Guidelines

Use "Closes #123" for:

- Issues labeled `erk-plan`
- Issues you want auto-closed

Use "See #123" for reference without closure.
```

## Known Issues / Edge Cases

1. **Multiple PRs referencing same issue**: Last merged PR wins, no conflict
2. **PR to non-default branch then merged to default**: Keywords parsed on initial PR creation, not on merge
3. **Editing PR description after merge**: Does not affect already-closed issues
4. **Issue in different repo**: Requires full syntax `owner/repo#123`

## Integration with erk Workflows

### Native Branch Linking (Preferred)

Erk uses GitHub's native branch-to-issue linking via `gh issue develop` instead of explicit `Closes #N` keywords:

```bash
gh issue develop --name my-branch --base main <issue_number>
```

**Benefits:**

- Branch appears in issue sidebar under "Development"
- PR automatically linked when branch is pushed
- Issue auto-closes on PR merge (no keywords needed)
- Cleaner PR bodies without boilerplate text

**Discovery:**

```bash
# Find branches linked to an issue
gh issue develop --list <issue_number>

# Find PRs linked via native linking
gh pr view <pr_number> --json closingIssuesReferences
```

See [github-branch-linking.md](agent/github-branch-linking.md) for complete documentation on native branch linking.

### Legacy: Keyword-Based Linking

The `Closes #N` keyword approach is still supported by GitHub but not used by erk workflows. This section documents the keyword approach for reference when working with external PRs or repositories not using native branch linking.

### For `erk-queue` Issues

The `dispatch-erk-queue.yml` workflow uses native branch linking via `gh issue develop` to connect branches to issues automatically.

## References

- [GitHub Docs: Linking a pull request to an issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/linking-a-pull-request-to-an-issue)
- [GitHub CLI: gh pr view](https://cli.github.com/manual/gh_pr_view)
- [GitHub GraphQL API: PullRequest.closingIssuesReferences](https://docs.github.com/en/graphql/reference/objects#pullrequest)
