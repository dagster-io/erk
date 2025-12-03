---
title: GitHub Branch Linking
read_when:
  - "linking branches to issues"
  - "using gh issue develop"
  - "understanding branch-issue relationships"
---

# GitHub Native Branch Linking

GitHub provides native branch-to-issue linking through the `gh issue develop` command. This feature creates a formal relationship between a branch and an issue, visible in the issue sidebar under "Development".

## What `gh issue develop` Does

When called successfully, `gh issue develop` performs these operations:

1. **Creates branch on GitHub remote** (not just locally)
2. **Links branch to issue** in GitHub's database (visible in issue sidebar)
3. **Fetches branch locally** (creates remote-tracking ref)
4. **Does NOT checkout branch** (unless `--checkout` flag is used)

Example output:

```
github.com/owner/repo/tree/my-branch
From https://github.com/owner/repo
 * [new branch]          my-branch -> origin/my-branch
```

## Basic Commands

```bash
# Create a linked branch
gh issue develop --name my-branch --base main <issue_number>

# Create and checkout the linked branch
gh issue develop --name my-branch --base main --checkout <issue_number>

# List branches linked to an issue
gh issue develop --list <issue_number>
```

## Key Behaviors

### Branch Links Persist Through Normal Operations

Once created, the link survives:

- Pushing new commits to the linked branch
- Creating a local tracking branch and pushing
- Force pushes to the branch

```bash
# These operations preserve the link:
gh issue develop --name test-branch --base main 123
git fetch origin test-branch
git checkout -B test-branch origin/test-branch
git commit --allow-empty -m "test"
git push origin test-branch
gh issue develop --list 123  # Still shows test-branch
```

### Cannot Link to Pre-existing Branches

**Critical limitation**: `gh issue develop` fails if a branch with the same name already exists on the remote:

```bash
# Create branch without gh issue develop
git checkout -b my-branch origin/main
git push origin my-branch

# Now try gh issue develop with same name - FAILS
gh issue develop --name my-branch --base main 123
# OUTPUT:
# github.com/owner/repo/tree/       <- NOTE: empty branch name!
# fatal: bad config variable 'branch..gh-merge-base'
# failed to run git: exit status 128
# Exit code: 1
```

**Side effects of this failure:**

- Creates corrupted git config entry: `[branch ""]` with `gh-merge-base = main`
- Does NOT create the GitHub branch link
- Returns exit code 1

### Calling Twice Also Fails

Even for a branch that was created by `gh issue develop`, calling it again with the same branch name fails with the same error.

```bash
# First call - succeeds
gh issue develop --name test-branch --base main 123

# Second call - fails!
gh issue develop --name test-branch --base main 123
# Same error as above
```

**Implication**: Always check for existing linked branches before calling `gh issue develop`.

## Verifying Branch Links

### Via CLI

```bash
gh issue develop --list <issue_number>
```

### Via GraphQL API

```bash
gh api graphql -f query='
query {
  repository(owner: "OWNER", name: "REPO") {
    issue(number: 123) {
      linkedBranches(first: 10) {
        nodes {
          ref { name }
        }
      }
    }
  }
}'
```

### Via Issue Timeline

When `gh issue develop` creates a link, it appears as a "connected" event in the issue timeline. This is distinct from:

- **"referenced"**: Someone mentioned the issue in a commit message
- **"cross-referenced"**: A PR references the issue (e.g., "Closes #123")

If you only see "referenced" and "cross-referenced" events but no "connected" event, then `gh issue develop` was never successfully called.

```bash
# Check issue timeline for connection events
gh api /repos/OWNER/REPO/issues/<number>/timeline | jq '.[] | select(.event == "connected")'
```

## Cleaning Up Corrupted Git Config

If `gh issue develop` fails due to a pre-existing branch, it may leave corrupted config:

```bash
# Remove the corrupted entry
git config --unset 'branch..gh-merge-base'
```

## Best Practices

1. **Check for existing branches** before calling `gh issue develop`
2. **Check for existing links** via `gh issue develop --list` before creating new ones
3. **Use unique branch names** (e.g., include timestamps) to avoid collisions
4. **Handle failures gracefully** - the command can fail for various reasons
5. **Clean up corrupted config** after failures

## Relationship to Pull Requests

Branch linking and PR references are separate mechanisms:

- **Branch link**: Created by `gh issue develop`, visible in issue sidebar
- **PR reference**: Created when PR description contains "Closes #123" or similar

A PR can reference an issue without the branch being linked, and vice versa. For automated workflows that need to discover branches from issues, rely on branch linking rather than PR references.
