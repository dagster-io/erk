---
description: "GitHub CLI mental model and command reference"
url: "https://cli.github.com/"
---

# GitHub CLI (`gh`) Mental Model

**Last Updated**: 2025-10-13

A comprehensive guide to understanding GitHub CLI's mental model, command structure, and integration patterns.

---

## Table of Contents

- [What is GitHub CLI?](#what-is-github-cli)
- [Core Mental Model](#core-mental-model)
- [Terminology](#terminology)
- [Authentication & Configuration](#authentication--configuration)
- [Command Reference](#command-reference)
- [Workflow Patterns](#workflow-patterns)
- [Erk Integration](#erk-integration)
- [Practical Examples](#practical-examples)
- [Key Insights for AI Agents](#key-insights-for-ai-agents)
- [Additional Resources](#additional-resources)

---

## What is GitHub CLI?

GitHub CLI (`gh`) is the official command-line tool for GitHub. It brings pull requests, issues, releases, and other GitHub concepts to the terminal.

### The Problem It Solves

Without `gh`, working with GitHub requires:

1. Switching to browser for PR operations
2. Manual URL construction
3. Context switching between terminal and web
4. No scriptable GitHub workflows

With `gh`, you can:

- Create, view, and merge PRs from terminal
- Manage issues without leaving your editor
- Script GitHub workflows
- Query GitHub API with built-in authentication

### Core Philosophy

**GitHub in your terminal.** `gh` mirrors GitHub's web interface structure but optimized for CLI workflows and automation.

---

## Core Mental Model

### The Three-Layer Architecture

GitHub CLI operates on three conceptual layers:

```
┌─────────────────────────────────────────┐
│   High-Level Commands (pr, issue, repo) │  ← User-friendly, porcelain commands
├─────────────────────────────────────────┤
│   REST API & GraphQL Layer (gh api)     │  ← Direct API access
├─────────────────────────────────────────┤
│   Git Integration & Auth                │  ← Credentials, git protocol
└─────────────────────────────────────────┘
```

#### Layer 1: High-Level Commands (Porcelain)

These are the commands you use daily: `gh pr create`, `gh issue list`, etc.

**Mental model**: Think of these as "GitHub workflows made CLI-native"

- Each command maps to a common GitHub workflow
- Designed for interactive use and scripting
- Automatically handle common cases (current branch, repo detection)

#### Layer 2: API Access (`gh api`)

Direct access to GitHub's REST and GraphQL APIs.

**Mental model**: Think of this as "curl for GitHub with auth built-in"

- Full API access for advanced use cases
- Automatic authentication and token management
- Supports both REST endpoints and GraphQL queries
- Used when porcelain commands don't cover your needs

#### Layer 3: Git Integration

How `gh` connects to your local git repository.

**Mental model**: Think of this as "smart repo detection"

- Reads git remotes to determine GitHub repository
- Uses current branch to infer PR context
- Integrates with git credentials

### The Resource Model

GitHub CLI organizes around GitHub's core resources:

```
Repository (owner/name)
├── Pull Requests (pr)
│   ├── Number (e.g., #123)
│   ├── Branch (e.g., feature-branch)
│   └── URL (e.g., https://github.com/owner/repo/pull/123)
├── Issues (issue)
│   ├── Number (e.g., #456)
│   └── URL
├── Releases (release)
├── Actions (run, workflow, cache)
└── Projects (project)
```

**Key insight**: Most `gh` commands follow this pattern:

```bash
gh <resource> <action> [identifier] [flags]
```

Examples:

- `gh pr view 123` - view pull request #123
- `gh issue create` - create a new issue
- `gh repo fork` - fork the current repository

### Context Resolution

`gh` is **context-aware**. It automatically determines:

1. **Repository**: From git remote (or `-R` flag)
2. **Pull Request**: From current branch (or explicit number/URL)
3. **Authentication**: From stored credentials

This means you can often omit arguments:

```bash
# In a repo with a remote and on a branch with a PR:
gh pr view     # ← Automatically finds the PR for your current branch
gh pr merge    # ← Merges the current branch's PR
```

---

## Terminology

### Core Concepts

| Term           | Definition                                      | Example                                 |
| -------------- | ----------------------------------------------- | --------------------------------------- |
| **Repository** | A GitHub repository, identified by `owner/repo` | `cli/cli`                               |
| **Remote**     | Git remote URL pointing to GitHub               | `origin` → `git@github.com:cli/cli.git` |
| **PR**         | Pull Request - a request to merge changes       | PR #123                                 |
| **Head**       | The branch containing your changes              | `feature-branch`                        |
| **Base**       | The branch you want to merge into               | `main`                                  |
| **Draft**      | A PR marked as "work in progress"               | Draft PR                                |
| **Review**     | Approval/change requests on a PR                | Approved, Changes Requested             |
| **Check**      | CI/CD status check on a PR                      | GitHub Actions, CircleCI                |
| **State**      | Current status of PR/issue                      | open, closed, merged                    |

### Resource Identifiers

GitHub CLI accepts resources in multiple formats:

**Pull Requests & Issues:**

```bash
gh pr view 123                                    # By number
gh pr view feature-branch                         # By branch name
gh pr view https://github.com/owner/repo/pull/123 # By URL
gh pr view owner:feature-branch                   # By owner:branch (for forks)
```

**Repositories:**

```bash
gh repo view cli/cli                              # By owner/repo
gh repo view https://github.com/cli/cli           # By URL
gh repo view                                      # Current repo (from git remote)
```

### JSON Fields

When using `--json`, GitHub CLI provides structured data. Common fields:

| Field               | Type   | Description                |
| ------------------- | ------ | -------------------------- |
| `number`            | int    | PR or issue number         |
| `title`             | string | Title text                 |
| `body`              | string | Description text           |
| `state`             | string | `OPEN`, `CLOSED`, `MERGED` |
| `headRefName`       | string | Head branch name           |
| `baseRefName`       | string | Base branch name           |
| `author`            | object | Author login and info      |
| `url`               | string | Full GitHub URL            |
| `isDraft`           | bool   | Draft PR status            |
| `statusCheckRollup` | array  | CI/CD check status         |
| `reviews`           | array  | Review information         |
| `labels`            | array  | Labels applied             |

---

## Authentication & Configuration

### Authentication Flow

```bash
# First time setup - interactive login
gh auth login

# Check authentication status
gh auth status

# Refresh credentials (e.g., to add scopes)
gh auth refresh -s read:org,repo,workflow
```

**What happens during `gh auth login`:**

1. Prompts for GitHub.com or GitHub Enterprise
2. Asks for authentication method (browser or token)
3. Requests permission scopes
4. Stores credentials securely in system keyring

### Authentication Storage

```
Credentials stored in:
- macOS: Keychain
- Linux: libsecret or encrypted file
- Windows: Credential Manager
```

**Token scopes** determine what `gh` can do:

- `repo`: Full repo access (required for most operations)
- `read:org`: Read organization data
- `workflow`: Trigger GitHub Actions
- `gist`: Manage gists
- `project`: Manage projects

### Configuration

View current configuration:

```bash
gh config list
```

Common config options:

```bash
gh config set git_protocol https    # Use HTTPS for git operations
gh config set editor vim             # Set default editor
gh config set prompt enabled         # Enable interactive prompts
gh config set browser firefox        # Set browser for --web flag
```

Configuration file location: `~/.config/gh/config.yml`

### Repository Context

`gh` determines the repository from:

1. `-R owner/repo` flag (highest priority)
2. `GH_REPO` environment variable
3. Git remote named `origin`
4. Git remote named `upstream`

**Override for specific command:**

```bash
gh pr list -R cli/cli
```

**Set default repo for directory:**

```bash
gh repo set-default cli/cli
```

---

## Command Reference

### Pull Request Commands (`gh pr`)

The most commonly used `gh` commands revolve around pull requests.

#### `gh pr list` - List Pull Requests

```bash
# Basic listing
gh pr list                           # Open PRs in current repo
gh pr list --state all               # All PRs (open, closed, merged)
gh pr list --state merged            # Only merged PRs

# Filtering
gh pr list --author @me              # Your PRs
gh pr list --author username         # Specific author
gh pr list --label bug               # PRs with "bug" label
gh pr list --base main               # PRs targeting main branch
gh pr list --head feature-branch     # PRs from feature-branch

# Searching (advanced)
gh pr list --search "status:success"             # Successful checks
gh pr list --search "review:required"            # Needs review
gh pr list --search "status:success review:required"  # Both

# Limiting results
gh pr list --limit 50                # Show 50 PRs (default 30)

# JSON output
gh pr list --json number,title,state,headRefName
gh pr list --json number,title --jq '.[].number'  # Just PR numbers
```

**JSON fields available:** additions, assignees, author, autoMergeRequest, baseRefName, baseRefOid, body, changedFiles, closed, closedAt, comments, commits, createdAt, deletions, files, fullDatabaseId, headRefName, headRefOid, headRepository, headRepositoryOwner, id, isCrossRepository, isDraft, labels, latestReviews, maintainerCanModify, mergeCommit, mergeStateStatus, mergeable, mergedAt, mergedBy, milestone, number, potentialMergeCommit, projectCards, projectItems, reactionGroups, reviewDecision, reviewRequests, reviews, state, statusCheckRollup, title, updatedAt, url

#### `gh pr create` - Create Pull Request

```bash
# Interactive (prompts for title and body)
gh pr create

# Quick creation with title and body
gh pr create --title "Fix bug" --body "This fixes the bug"

# Auto-fill from commits
gh pr create --fill                  # Uses last commit for title/body
gh pr create --fill-first            # Uses first commit
gh pr create --fill-verbose          # Uses all commits for body

# Draft PR
gh pr create --draft

# With reviewers and assignees
gh pr create --reviewer username1,username2
gh pr create --reviewer myorg/team-name
gh pr create --assignee @me

# With labels and milestone
gh pr create --label bug,urgent
gh pr create --milestone "Sprint 23"

# Target specific branches
gh pr create --base develop          # Target develop instead of main
gh pr create --head user:feature     # Explicitly specify head branch

# Open browser to create PR
gh pr create --web

# Using template file
gh pr create --template .github/pull_request_template.md

# Dry run (see what would be created)
gh pr create --dry-run --title "Test" --body "Test body"
```

**Body file from stdin:**

```bash
cat pr-description.md | gh pr create --body-file -
```

#### `gh pr view` - View Pull Request

```bash
# View current branch's PR
gh pr view

# View specific PR
gh pr view 123
gh pr view https://github.com/owner/repo/pull/123
gh pr view feature-branch

# In browser
gh pr view --web
gh pr view 123 --web

# With comments
gh pr view 123 --comments

# JSON output
gh pr view 123 --json title,body,state,author
gh pr view 123 --json state --jq '.state'

# Pretty output with template
gh pr view 123 --json number,title,author \
  --template '{{.number}}: {{.title}} by {{.author.login}}'
```

#### `gh pr checkout` - Checkout Pull Request

```bash
# Checkout PR by number
gh pr checkout 123

# Checkout with custom branch name
gh pr checkout 123 --branch my-review-branch

# Force update existing branch
gh pr checkout 123 --force

# Detached HEAD (no branch)
gh pr checkout 123 --detach

# With submodules
gh pr checkout 123 --recurse-submodules
```

**What happens:**

1. Fetches the PR's head branch
2. Creates/updates local branch
3. Checks out the branch

#### `gh pr merge` - Merge Pull Request

```bash
# Interactive merge (prompts for method)
gh pr merge

# Merge strategies
gh pr merge --merge                  # Create merge commit
gh pr merge --squash                 # Squash and merge
gh pr merge --rebase                 # Rebase and merge

# Auto-merge (when checks pass)
gh pr merge --auto

# Disable auto-merge
gh pr merge --disable-auto

# Custom commit message
gh pr merge --squash --subject "Fix: Bug fix" --body "Details..."

# Delete branch after merge
gh pr merge --delete-branch

# Admin override (bypass requirements)
gh pr merge --admin

# Require head commit match (safety check)
gh pr merge --match-head-commit abc123
```

#### `gh pr status` - Show PR Status

```bash
gh pr status                         # PRs for current repo
```

Shows:

- Pull requests assigned to you
- Pull requests that mention you
- Pull requests you created

#### `gh pr checks` - View CI Status

```bash
gh pr checks                         # Current branch's PR
gh pr checks 123                     # Specific PR

# Watch checks in real-time
gh pr checks --watch
```

#### Other PR Commands

```bash
# Close PR
gh pr close 123
gh pr close 123 --delete-branch

# Reopen PR
gh pr reopen 123

# Mark as ready for review
gh pr ready 123

# Add comment
gh pr comment 123 --body "LGTM!"

# Review PR
gh pr review 123 --approve
gh pr review 123 --request-changes --body "Please fix..."
gh pr review 123 --comment --body "Looks good but minor suggestions"

# Edit PR
gh pr edit 123 --title "New title"
gh pr edit 123 --body "New description"
gh pr edit 123 --add-label bug
gh pr edit 123 --remove-label wip

# View diff
gh pr diff 123

# Update PR branch
gh pr update-branch 123              # Merge base into PR branch

# Lock/unlock conversation
gh pr lock 123
gh pr unlock 123
```

### Issue Commands (`gh issue`)

Very similar to PR commands, but for issues.

```bash
# List issues
gh issue list
gh issue list --state all
gh issue list --author @me
gh issue list --assignee @me
gh issue list --label bug
gh issue list --search "is:open label:bug"

# Create issue
gh issue create
gh issue create --title "Bug report" --body "Description"
gh issue create --label bug,urgent
gh issue create --assignee @me
gh issue create --web

# View issue
gh issue view 456
gh issue view 456 --web
gh issue view 456 --comments
gh issue view 456 --json title,body,state

# Edit issue
gh issue edit 456 --title "New title"
gh issue edit 456 --add-label help-wanted

# Close/reopen
gh issue close 456
gh issue reopen 456

# Comment
gh issue comment 456 --body "Thanks for reporting"

# Develop (link branch to issue)
gh issue develop 456 --checkout

# Transfer to another repo
gh issue transfer 456 owner/other-repo

# Pin/unpin
gh issue pin 456
gh issue unpin 456

# Lock/unlock
gh issue lock 456
gh issue unlock 456

# Delete (careful!)
gh issue delete 456
```

### Repository Commands (`gh repo`)

```bash
# View repository
gh repo view
gh repo view cli/cli
gh repo view --web

# Clone repository
gh repo clone cli/cli
gh repo clone cli/cli custom-directory

# Create repository
gh repo create my-project                    # Create in current directory
gh repo create owner/my-project              # Create remote only
gh repo create --public                      # Public repo
gh repo create --private                     # Private repo
gh repo create --template owner/template     # From template

# Fork repository
gh repo fork
gh repo fork cli/cli
gh repo fork --clone                         # Fork and clone

# List repositories
gh repo list                                 # Your repos
gh repo list owner                           # Specific user/org
gh repo list --limit 100

# Edit repository settings
gh repo edit --description "My awesome project"
gh repo edit --homepage https://example.com
gh repo edit --enable-issues
gh repo edit --enable-wiki=false

# Archive/unarchive
gh repo archive owner/repo
gh repo unarchive owner/repo

# Rename
gh repo rename new-name

# Delete (careful!)
gh repo delete owner/repo

# Sync fork
gh repo sync                                 # Sync fork with upstream

# Set default repo for directory
gh repo set-default owner/repo

# Deploy keys
gh repo deploy-key list
gh repo deploy-key add key.pub --title "CI Key"
gh repo deploy-key delete <key-id>
```

### API Commands (`gh api`)

Direct access to GitHub's REST and GraphQL APIs.

#### REST API Access

```bash
# GET request
gh api repos/cli/cli/releases

# With placeholders
gh api repos/{owner}/{repo}/releases          # Auto-fills from current repo

# POST request
gh api repos/cli/cli/issues -f title="Bug" -f body="Description"

# Explicit method
gh api -X PATCH repos/cli/cli -f description="New description"

# Custom headers
gh api repos/cli/cli -H "Accept: application/vnd.github.v3.raw+json"

# Query parameters (for GET)
gh api -X GET search/issues -f q='repo:cli/cli is:open'

# Request body from file
gh api repos/cli/cli/issues --input issue.json

# Include response headers
gh api repos/cli/cli -i

# Pagination (fetch all pages)
gh api --paginate repos/cli/cli/issues

# Filter with jq
gh api repos/cli/cli/issues --jq '.[].title'

# Template output
gh api repos/cli/cli/issues --template '{{range .}}{{.title}}{{"\n"}}{{end}}'

# Nested parameters
gh api gists -F 'files[myfile.txt][content]=@myfile.txt'

# Cache responses
gh api repos/cli/cli --cache 3600s           # Cache for 1 hour
```

#### GraphQL Access

```bash
# Basic GraphQL query
gh api graphql -f query='
query {
  viewer {
    login
    name
  }
}'

# With variables
gh api graphql -F owner='{owner}' -F name='{repo}' -f query='
query($name: String!, $owner: String!) {
  repository(owner: $owner, name: $name) {
    releases(last: 3) {
      nodes { tagName }
    }
  }
}
'

# Paginated GraphQL query
gh api graphql --paginate -f query='
query($endCursor: String) {
  viewer {
    repositories(first: 100, after: $endCursor) {
      nodes { nameWithOwner }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
'

# Combine pages into single array
gh api graphql --paginate --slurp -f query='...'
```

### Workflow Commands (`gh run`, `gh workflow`)

```bash
# List workflow runs
gh run list
gh run list --workflow=ci.yml
gh run list --branch=main
gh run list --status=failure

# View run details
gh run view 123456
gh run view --log                            # Show logs

# Watch run in progress
gh run watch 123456

# Re-run workflow
gh run rerun 123456
gh run rerun 123456 --failed                 # Re-run failed jobs only

# Cancel run
gh run cancel 123456

# Delete run
gh run delete 123456

# List workflows
gh workflow list

# View workflow
gh workflow view ci.yml

# Enable/disable workflow
gh workflow enable ci.yml
gh workflow disable ci.yml

# Trigger workflow
gh workflow run ci.yml
gh workflow run ci.yml -f param=value        # With inputs
```

### Authentication Commands (`gh auth`)

```bash
# Login
gh auth login                                # Interactive
gh auth login --with-token < token.txt       # From token

# Check status
gh auth status

# Refresh token (add scopes)
gh auth refresh -s read:org,repo,workflow

# Setup git integration
gh auth setup-git

# Get token (for scripts)
gh auth token

# Switch accounts
gh auth switch

# Logout
gh auth logout
```

### Other Commands

```bash
# Search
gh search repos "language:python stars:>1000"
gh search issues "is:open label:bug"
gh search prs "is:merged author:octocat"

# Gist management
gh gist create file.txt
gh gist list
gh gist view abc123
gh gist edit abc123
gh gist delete abc123

# Aliases
gh alias set pv 'pr view'                    # Create alias
gh alias list                                # List aliases

# Extensions
gh extension install owner/gh-extension
gh extension list
gh extension upgrade --all

# Completion
gh completion -s bash > /etc/bash_completion.d/gh
gh completion -s zsh > /usr/local/share/zsh/site-functions/_gh
```

---

## Workflow Patterns

### Pattern 1: Creating a PR

**Standard workflow:**

```bash
# 1. Make changes and commit
git add .
git commit -m "Fix bug"

# 2. Push branch
git push -u origin feature-branch

# 3. Create PR with autofill
gh pr create --fill

# Or, all in one step (gh will push for you if needed)
gh pr create --fill
```

**Advanced: Create draft PR, then mark ready:**

```bash
gh pr create --draft --fill
# ... continue working ...
gh pr ready
```

### Pattern 2: Reviewing PRs

**Quick review workflow:**

```bash
# 1. List PRs needing review
gh pr list --search "review-requested:@me"

# 2. View PR details
gh pr view 123

# 3. Checkout and test locally
gh pr checkout 123
# ... run tests, verify changes ...

# 4. Submit review
gh pr review 123 --approve
# or
gh pr review 123 --request-changes --body "Please fix X"

# 5. Return to main branch
git checkout main
```

**View PR checks before reviewing:**

```bash
gh pr view 123
gh pr checks 123
gh pr diff 123
gh pr view 123 --comments
```

### Pattern 3: Merging PRs

**Safe merge workflow:**

```bash
# 1. Check PR status
gh pr status

# 2. View the PR
gh pr view 123

# 3. Check CI status
gh pr checks 123

# 4. Merge (interactive method selection)
gh pr merge 123

# Or specify merge strategy
gh pr merge 123 --squash --delete-branch
```

**Auto-merge when checks pass:**

```bash
gh pr merge 123 --auto --squash
```

### Pattern 4: Working with Forks

**Fork and contribute workflow:**

```bash
# 1. Fork repository
gh repo fork owner/repo --clone

# 2. Create feature branch
git checkout -b feature-branch

# 3. Make changes and commit
# ...

# 4. Push to your fork
git push -u origin feature-branch

# 5. Create PR to upstream
gh pr create --repo owner/repo
```

**Sync fork with upstream:**

```bash
gh repo sync
```

### Pattern 5: Scripting with `gh`

**Get all open PRs as JSON:**

```bash
gh pr list --state open --json number,title,author,createdAt \
  --jq '.[] | "\(.number): \(.title) by \(.author.login)"'
```

**Find PRs with failing checks:**

```bash
gh pr list --json number,statusCheckRollup \
  --jq '.[] | select(.statusCheckRollup[].conclusion == "failure") | .number'
```

**Close all stale PRs:**

```bash
# Get PRs not updated in 90 days
gh pr list --state open --json number,updatedAt --limit 1000 \
  --jq '.[] | select(.updatedAt | fromdateiso8601 < (now - 90*86400)) | .number' \
  | xargs -I {} gh pr close {}
```

**Batch operations:**

```bash
# Add label to multiple PRs
for pr in 123 124 125; do
  gh pr edit $pr --add-label needs-review
done
```

### Pattern 6: Finding Information

**Find which PR introduced a commit:**

```bash
gh pr list --search "<commit-sha>" --state merged
```

**List your pending PRs across all repos:**

```bash
gh search prs "is:open author:@me"
```

**Find PRs by label:**

```bash
gh pr list --label bug --state all
```

### Pattern 7: CI/CD Integration

**Wait for checks to pass in CI script:**

```bash
#!/bin/bash
PR_NUMBER=$1

while true; do
  STATUS=$(gh pr view $PR_NUMBER --json statusCheckRollup \
    --jq '.statusCheckRollup[].conclusion')

  if echo "$STATUS" | grep -q "FAILURE"; then
    echo "Checks failed"
    exit 1
  elif echo "$STATUS" | grep -qv "SUCCESS"; then
    echo "Waiting for checks..."
    sleep 30
  else
    echo "All checks passed"
    break
  fi
done
```

**Auto-merge after successful deploy:**

```bash
#!/bin/bash
# In CI after deploy succeeds
gh pr merge $PR_NUMBER --squash --auto
```

---

## Erk Integration

### How Erk Uses `gh`

Erk integrates with GitHub CLI to enhance the worktree workflow by providing PR status information directly in the worktree listing.

#### 1. PR Information Retrieval

**File**: `src/erk/github_ops.py:GitHubOps.get_prs()`

**Command executed:**

```bash
gh pr list --state all --json number,headRefName,url,state,isDraft,statusCheckRollup
```

**What it does:**

- Fetches ALL PRs (open, closed, merged) for the repository
- Retrieves structured JSON data with key fields
- Parses into `PullRequestInfo` dataclass
- Returns dict mapping `branch_name → PullRequestInfo`

**JSON fields used:**

```python
{
  "number": 123,
  "headRefName": "feature-branch",
  "url": "https://github.com/owner/repo/pull/123",
  "state": "OPEN",  # or "CLOSED", "MERGED"
  "isDraft": false,
  "statusCheckRollup": [
    {"conclusion": "SUCCESS", "name": "ci/test"}
  ]
}
```

#### 2. Display in `erk ls`

**File**: `src/erk/commands/list.py`

When you run `erk ls`, you see:

```
feature-1    feature/amazing-feature      PR #123 ✓
feature-2    feature/bug-fix              PR #124 (draft)
feature-3    feature/experimental         (no PR)
```

**Status indicators:**

- `✓` - All checks passing
- `✗` - Some checks failing
- `⋯` - Checks pending
- `(draft)` - Draft PR
- `(closed)` - Closed PR
- `(merged)` - Merged PR

#### 3. Cleanup with Sync (`erk sync`)

**File**: `src/erk/commands/sync.py`

Uses PR state to identify cleanup candidates:

- Worktrees with merged PRs → Safe to delete
- Worktrees with closed PRs → Prompt user
- Worktrees without PRs → Skip

Use `erk sync --dry-run` to preview cleanup candidates without removal.

#### 4. Error Handling

Erk gracefully handles `gh` unavailability:

- If `gh` not installed → Silent fallback (no PR info shown)
- If not authenticated → Silent fallback
- If API fails → Continue without PR data

This ensures `erk` works even without GitHub CLI.

#### 5. Authentication Requirements

Erk relies on existing `gh` authentication:

```bash
# User must authenticate first
gh auth login

# Then erk automatically uses those credentials
erk ls
```

No separate authentication needed - leverages `gh` token storage.

---

## Practical Examples

### Example 1: Daily PR Workflow

```bash
# Morning: Check what needs attention
gh pr status

# See PRs needing your review
gh pr list --search "review-requested:@me"

# Review a PR
gh pr view 456
gh pr checkout 456
# ... test locally ...
gh pr review 456 --approve

# Check your own PRs
gh pr list --author @me

# View checks on your PR
gh pr checks
```

### Example 2: Feature Development

```bash
# Start feature
git checkout -b feature/new-thing
# ... write code ...
git commit -m "Implement new thing"

# Create draft PR
gh pr create --draft --fill

# Continue development
# ... more commits ...
git push

# Mark ready when done
gh pr ready

# After review, merge
gh pr merge --squash --delete-branch
```

### Example 3: Hotfix Workflow

```bash
# Create hotfix branch
git checkout -b hotfix/critical-bug

# Fix and commit
# ...
git commit -m "Fix critical bug"

# Create PR with reviewers immediately
gh pr create \
  --title "HOTFIX: Critical bug fix" \
  --body "Fixes production issue XYZ" \
  --reviewer team-lead,ops-team \
  --label hotfix,urgent

# Watch checks
gh pr checks --watch

# Once approved, merge immediately
gh pr merge --squash --delete-branch
```

### Example 4: Managing Stale PRs

```bash
# Find old PRs
gh pr list --state open --json number,title,updatedAt \
  --jq '.[] | select(.updatedAt | fromdateiso8601 < (now - 2592000))
       | "\(.number): \(.title) (updated: \(.updatedAt))"'

# Close specific PR with comment
gh pr close 789 --comment "Closing due to inactivity. Please reopen if still relevant."

# Or update PR branch to trigger CI
gh pr update-branch 789
```

### Example 5: Release Management

```bash
# List recent releases
gh release list --limit 10

# Create release from tag
git tag v1.2.3
git push origin v1.2.3
gh release create v1.2.3 --generate-notes

# Create release with assets
gh release create v1.2.3 \
  --title "Version 1.2.3" \
  --notes "See CHANGELOG.md for details" \
  ./dist/*.tar.gz

# View release
gh release view v1.2.3

# Download release assets
gh release download v1.2.3
```

### Example 6: Advanced Searching

```bash
# Find all PRs you authored that are merged
gh search prs "is:merged author:@me"

# Find open PRs with failing checks
gh search prs "is:open is:pr status:failure"

# Find PRs with specific label across org
gh search prs "org:myorg label:security"

# Find issues assigned to you across all repos
gh search issues "is:open assignee:@me"
```

### Example 7: Templated Output

```bash
# Custom PR list format
gh pr list --json number,title,author,updatedAt \
  --template '{{range .}}{{printf "#%-4d" .number}} {{.title | truncate 60}} by {{.author.login}}{{"\n"}}{{end}}'

# PR status with checks
gh pr view 123 --json title,statusCheckRollup \
  --template '{{.title}}{{"\n"}}Checks:{{"\n"}}{{range .statusCheckRollup}}  {{.name}}: {{.conclusion}}{{"\n"}}{{end}}'

# List with custom formatting
gh pr list --json number,title,updatedAt \
  --template '{{range .}}{{tablerow (printf "#%v" .number | autocolor "green") (.title | truncate 50) (timeago .updatedAt)}}{{end}}{{tablerender}}'
```

### Example 8: GraphQL Power Queries

```bash
# Get repository statistics
gh api graphql -f query='
query {
  repository(owner: "cli", name: "cli") {
    stargazerCount
    forkCount
    issues {
      totalCount
    }
    pullRequests {
      totalCount
    }
  }
}'

# Get PR review stats
gh api graphql -f owner='cli' -f name='cli' -f query='
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    pullRequests(first: 100, states: MERGED) {
      nodes {
        number
        reviews {
          totalCount
        }
        comments {
          totalCount
        }
      }
    }
  }
}'
```

---

## Key Insights for AI Agents

### When to Use `gh` vs Git

**Use `gh` for:**

- Creating/viewing/merging PRs
- Managing issues
- Viewing CI status
- Accessing GitHub-specific features (labels, reviews, projects)

**Use `git` for:**

- Branch operations (checkout, merge, rebase)
- Commit operations
- Push/pull/fetch
- Local repository operations

**Use both together:**

```bash
git checkout -b feature     # Git for branches
git commit -m "Fix"         # Git for commits
gh pr create --fill         # gh for PR creation
```

### Context-Aware Operations

`gh` automatically detects context:

```bash
# These are equivalent if you're on feature-branch with PR #123:
gh pr view
gh pr view 123
gh pr view feature-branch

# These are equivalent in a repo with remote:
gh pr list
gh pr list -R owner/repo
```

**Implication for agents**: Often don't need to specify PR numbers or repo - `gh` infers from context.

### JSON Output for Scripting

**Always use `--json` when scripting:**

```bash
# Bad (fragile, human-readable format)
gh pr list | grep "my-branch"

# Good (structured, parseable)
gh pr list --json headRefName,number \
  --jq '.[] | select(.headRefName == "my-branch") | .number'
```

**Available JSON fields**: Use `--json` without fields to see available options:

```bash
gh pr list --json
```

### Error Handling

`gh` returns non-zero exit codes on failure:

```bash
if gh pr view 123 &>/dev/null; then
  echo "PR exists"
else
  echo "PR not found or error"
fi
```

**Common exit codes:**

- `0` - Success
- `1` - General error
- `2` - Command not found
- `4` - Authentication error

### Rate Limiting

GitHub API has rate limits:

- **Authenticated**: 5,000 requests/hour
- **Unauthenticated**: 60 requests/hour

`gh` automatically handles authentication, so you get higher limits.

**Check rate limit:**

```bash
gh api rate_limit
```

### Pagination Considerations

**Default limits:**

- `gh pr list` - 30 results
- `gh issue list` - 30 results

**Get more results:**

```bash
gh pr list --limit 100                # Up to 100 results
gh pr list --limit 1000               # Up to 1000 results

# Get ALL results (may be slow)
gh api --paginate repos/{owner}/{repo}/pulls
```

### Best Practices for Agents

1. **Check for `gh` availability** before using:

   ```bash
   if command -v gh &>/dev/null; then
     gh pr list
   else
     echo "gh not installed"
   fi
   ```

2. **Use `--json` for reliable parsing**:

   ```bash
   gh pr list --json number,title
   ```

3. **Prefer explicit repo specification** when operating on non-current repos:

   ```bash
   gh pr list -R owner/repo
   ```

4. **Handle authentication errors gracefully**:

   ```bash
   if ! gh auth status &>/dev/null; then
     echo "Not authenticated. Run: gh auth login"
     exit 1
   fi
   ```

5. **Use specific PR identifiers** when possible:

   ```bash
   # Explicit
   gh pr view 123

   # Implicit (context-dependent)
   gh pr view
   ```

6. **Combine `gh api` with `jq`** for complex queries:

   ```bash
   gh api repos/{owner}/{repo}/pulls --jq '.[].number'
   ```

7. **Cache API responses** when appropriate:
   ```bash
   gh api repos/{owner}/{repo} --cache 3600s
   ```

---

## Additional Resources

- **Official Docs**: https://cli.github.com/manual/
- **GitHub REST API**: https://docs.github.com/en/rest
- **GitHub GraphQL API**: https://docs.github.com/en/graphql
- **Search Syntax**: https://docs.github.com/en/search-github/searching-on-github/searching-issues-and-pull-requests
- **jq Manual**: https://jqlang.github.io/jq/manual/
- **Exit Codes**: Run `gh help exit-codes`
- **Environment Variables**: Run `gh help environment`
