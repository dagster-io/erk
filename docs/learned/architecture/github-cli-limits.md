---
title: GitHub CLI Limits
read_when:
  - "using gh pr diff in production code"
  - "working with large pull requests (300+ files)"
  - "encountering HTTP 406 errors from gh CLI"
  - "implementing PR file discovery"
  - "working with GitHub codespaces in code"
  - "implementing codespace operations"
tripwires:
  - action: "using gh pr diff --name-only in production code"
    warning: "For PRs with 300+ files, gh pr diff fails with HTTP 406. Use REST API with pagination instead."
  - action: "using gh codespace start"
    warning: "gh codespace start does not exist. Use REST API POST /user/codespaces/{name}/start via gh api instead."
---

# GitHub CLI Limits

The GitHub CLI has undocumented size limits that cause failures on large PRs. This document covers the limitations and workarounds.

## The Problem

`gh pr diff --name-only` fails on PRs with 300+ files:

```bash
gh pr diff 123 --name-only
# Error: HTTP 406: Not Acceptable (https://api.github.com/...)
```

This happens because `gh pr diff` requests the entire diff in a single API call without pagination support. GitHub's API rejects requests for diffs that are too large.

## The Solution: REST API with Pagination

Use the GitHub REST API `/repos/{owner}/{repo}/pulls/{pr}/files` endpoint, which supports pagination:

```bash
gh api \
  --paginate \
  --jq '.[].filename' \
  "repos/{owner}/{repo}/pulls/${PR_NUMBER}/files"
```

### Key Differences

| Method                             | Pagination         | Size Limit | Failure Mode   |
| ---------------------------------- | ------------------ | ---------- | -------------- |
| `gh pr diff --name-only`           | No                 | ~300 files | HTTP 406 error |
| `gh api repos/.../pulls/.../files` | Yes (`--paginate`) | No limit   | None           |

## Implementation Pattern

See `src/erk/commands/exec/discover_reviews.py` for the production implementation:

```python
# DON'T: Use gh pr diff (fails on large PRs)
result = subprocess.run(["gh", "pr", "diff", pr_number, "--name-only"])

# DO: Use REST API with pagination
files = github.list_pr_files(pr_number=pr_number)
```

The `GitHubGateway.list_pr_files()` method handles pagination automatically.

## Why This Matters

PR #6119 fixed a bug where `erk exec discover-reviews` failed on large PRs. The original implementation used `gh pr diff`, which worked fine on small PRs but broke silently on large ones.

This is a production tripwire: code that works in testing (small PRs) fails in production (large refactors).

## gh codespace start Does Not Exist

The GitHub CLI does not provide a `gh codespace start` command. Attempting to use it fails:

```bash
gh codespace start mycodespace
# Error: unknown command "start" for "gh codespace"
```

### The Solution: REST API

Use the REST API endpoint `/user/codespaces/{name}/start` via `gh api`:

```bash
gh api \
  --method POST \
  "user/codespaces/${CODESPACE_NAME}/start"
```

This returns JSON with the codespace state. The operation is asynchronous - the codespace may still be starting when the API call returns.

### Implementation Pattern

See `src/erk/gateway/codespace/real.py` for the production implementation:

```python
# DON'T: Use gh codespace start (does not exist)
subprocess.run(["gh", "codespace", "start", name])

# DO: Use REST API
result = subprocess.run([
    "gh", "api",
    "--method", "POST",
    f"user/codespaces/{name}/start"
])
```

## GH-API-AUDIT Annotation Convention

To track GitHub CLI commands that should be audited for potential REST/GraphQL API replacements, use the `GH-API-AUDIT` annotation:

```python
# GH-API-AUDIT: [REST/GraphQL] - [operation description]
subprocess.run(["gh", "pr", "view", pr_number])
```

### Format

- **`REST`**: Operation has a known REST API endpoint
- **`GraphQL`**: Operation may be better served by GraphQL
- **Operation description**: Brief explanation of what the command does

### Examples from Codebase

```python
# GH-API-AUDIT: REST - Get PR number from branch
result = subprocess.run(["gh", "pr", "view", "--json", "number"])

# GH-API-AUDIT: GraphQL - Fetch issue comments
result = subprocess.run(["gh", "issue", "view", issue_number, "--json", "comments"])
```

### Purpose

This convention identifies 66+ locations in the gateway code where we're using `gh` CLI commands that could potentially be replaced with direct REST or GraphQL API calls for better performance, error handling, or functionality.

## GitHub Machines Endpoint HTTP 500 Bug

### Problem

The GitHub API endpoint `/repos/{owner}/{repo}/codespaces/machines` returns HTTP 500 for certain repositories, even when the repository exists and credentials are valid.

This is a **repository-specific bug** in GitHub's backend - the same API call works fine for some repositories but consistently fails for others.

### Diagnostic Process

The bug was discovered through systematic testing:

1. **Direct API test**: `gh api repos/OWNER/REPO/codespaces/machines` → HTTP 500
2. **Control test**: Created new test repository → Same API call returns HTTP 200
3. **Conclusion**: Bug affects specific repositories, not all repositories

**See**: [GitHub API Diagnostics](github-api-diagnostics.md) for complete diagnostic methodology.

### Workaround: Use REST API with Repository ID

Instead of fetching machines list via the broken endpoint, use direct codespace creation with `repository_id`:

```bash
# BROKEN: gh codespace create uses machines endpoint internally
gh codespace create --repo OWNER/REPO --machine basicLinux32gb
# Fails with: HTTP 500 from machines endpoint

# WORKAROUND: Use REST API with repository_id
REPO_ID=$(gh api repos/OWNER/REPO --jq .id)
gh api user/codespaces -X POST \
  -f ref=main \
  -F repository_id="$REPO_ID" \
  -f machine="basicLinux32gb"
```

### Implementation Pattern

See `src/erk/cli/commands/codespace/setup_cmd.py` for production implementation:

```python
def _get_repo_id(owner: str, repo: str) -> int:
    """Fetch repository ID via REST API."""
    result = subprocess.run(
        ["gh", "api", f"repos/{owner}/{repo}", "--jq", ".id"],
        capture_output=True,
        text=True,
        check=True
    )
    return int(result.stdout.strip())

# Use repository_id instead of repo name
repo_id = _get_repo_id(owner, repo)
subprocess.run([
    "gh", "api", "user/codespaces", "-X", "POST",
    "-f", "ref=main",
    "-F", f"repository_id={repo_id}",
    "-f", f"machine={machine_type}"
])
```

### Why This Works

The REST API endpoint `POST /user/codespaces` accepts `repository_id` as an alternative to repository name. This bypasses the broken machines endpoint entirely.

**Key insight**: Repository-specific GitHub bugs often affect high-level convenience commands but not lower-level REST endpoints.

### Constants

The default machine type for codespace creation is defined as:

```python
DEFAULT_MACHINE_TYPE = "basicLinux32gb"
```

This constant is used when no machine type is explicitly specified.

**Code reference**: `src/erk/cli/commands/codespace/setup_cmd.py`

**Related**: [Codespace Patterns](../cli/codespace-patterns.md) - Codespace setup implementation details

## Related Documentation

- [GitHub API Diagnostics](github-api-diagnostics.md) - Repository-specific diagnostic methodology
- [Universal Tripwires](../universal-tripwires.md) - Lists the gh pr diff tripwire
- [Gateway ABC Implementation](gateway-abc-implementation.md) - How GitHubGateway abstracts this
- [Codespace Patterns](../cli/codespace-patterns.md) - Codespace setup patterns
