---
title: GitHub API Diagnostics
last_audited: "2026-02-04 05:48 PT"
audit_result: clean
read_when:
  - debugging GitHub API failures
  - investigating repository-specific API issues
  - GitHub CLI commands returning unexpected errors
tripwires:
  - action: "assuming GitHub API failures are transient without repository-specific testing"
    warning: "Test with a control repository first. Some GitHub bugs affect specific repos but not others. Follow the 3-step diagnostic methodology."
---

# GitHub API Diagnostics

This document describes the diagnostic methodology for investigating repository-specific GitHub API failures.

## Problem

GitHub API failures can be:

1. **Transient** - Network issues, rate limiting, temporary service degradation
2. **Credential-related** - Invalid token, insufficient permissions
3. **Repository-specific** - Bugs in GitHub's backend that affect some repositories but not others

The third category is the hardest to diagnose because the API works fine in general, just not for your specific repository.

## Three-Step Diagnostic Methodology

### Step 1: Reproduce with Direct API Call

Use `gh api` to isolate the failure from erk's code:

```bash
# Example: Codespace machines endpoint
gh api "/repos/OWNER/REPO/codespaces/machines" --jq '.machines'
```

**Expected outcomes:**

- ✅ Success → The issue is in erk's code, not GitHub's API
- ❌ HTTP 500/400 → Potential repository-specific GitHub bug (proceed to Step 2)
- ❌ HTTP 401/403 → Credential or permission issue (fix auth first)
- ❌ HTTP 404 → Endpoint doesn't exist or repository name is wrong

### Step 2: Test with Control Repository

Create a minimal test repository and try the same API call:

```bash
# Create a test repo (or use an existing small repo)
gh repo create test-repo-api-debug --private --confirm

# Try the same API call against the test repo
gh api "/repos/YOUR_USERNAME/test-repo-api-debug/codespaces/machines" --jq '.machines'
```

**Expected outcomes:**

- ✅ Success on test repo + ❌ Failure on original repo → **Repository-specific bug confirmed**
- ❌ Failure on both → General API issue (check GitHub status, rate limits)

### Step 3: Find REST API Workaround

If the bug is repository-specific and GitHub CLI doesn't work, check for alternative REST API endpoints:

1. **Search GitHub REST API docs** for alternative endpoints
2. **Try direct POST/GET** instead of specialized CLI commands
3. **Check if the operation can be split** into multiple API calls

**Example: Codespace machines endpoint bug** (PR #6663)

```bash
# BROKEN: gh codespace create fails with HTTP 500
gh codespace create --repo OWNER/REPO --machine basicLinux32gb

# WORKAROUND: Use REST API direct POST with repository ID
REPO_ID=$(gh api repos/OWNER/REPO --jq .id)
gh api user/codespaces -X POST \
  -f ref=main \
  -f repository_id="$REPO_ID" \
  -f machine="basicLinux32gb"
```

**Key insight**: Repository-specific bugs often affect high-level convenience commands (like `gh codespace create`) but not lower-level REST endpoints (like `POST /user/codespaces`).

## Case Study: GitHub Machines Endpoint HTTP 500

**Context**: PR #6663 fixed `erk codespace setup` failures caused by GitHub's machines endpoint returning HTTP 500 for specific repositories.

### Diagnostic Process

1. **Step 1**: Reproduced with `gh api repos/OWNER/REPO/codespaces/machines` → HTTP 500
2. **Step 2**: Created test repository → Same call returned HTTP 200 with machine list
3. **Step 3**: Found workaround using `POST /user/codespaces` with `repository_id` parameter

### Root Cause

GitHub's `/repos/{owner}/{repo}/codespaces/machines` endpoint has a bug affecting certain repositories (likely related to repository size, age, or configuration). The bug does not affect all repositories.

### Solution Pattern

1. **Add repository ID helper** - `_get_repo_id()` function to fetch repository ID
2. **Replace convenience command** - Use direct REST API POST instead of `gh codespace create`
3. **Document the workaround** - Add to github-cli-limits.md for future reference

**Code reference**: `src/erk/cli/commands/codespace/setup_cmd.py`

## When to Use This Methodology

Use this diagnostic approach when:

- ✅ GitHub API call fails in your repository
- ✅ The failure is consistent (not transient)
- ✅ Credentials and permissions are correct
- ✅ The GitHub status page shows no incidents
- ✅ The same code works in other projects/repositories

## Common Repository-Specific Issues

### 1. Machines Endpoint HTTP 500

**Symptom**: `gh codespace create` fails with HTTP 500 when fetching machine types

**Workaround**: Use `POST /user/codespaces` with `repository_id` instead of repo name

**Reference**: PR #6663, github-cli-limits.md

### 2. Large Repository GraphQL Timeouts

**Symptom**: GraphQL queries timeout for repositories with >10k issues/PRs

**Workaround**: Use REST API with pagination instead of GraphQL

**Reference**: github-api-rate-limits.md

### 3. Large PR Diff Failures

**Symptom**: `gh pr diff` returns HTTP 406 for PRs with >300 files

**Workaround**: Use REST API `/repos/{owner}/{repo}/pulls/{number}/files` with pagination

**Reference**: github-cli-limits.md

## Related Documentation

- [GitHub CLI Limits](github-cli-limits.md) - Known gh command limitations and workarounds
- [GitHub API Rate Limits](github-api-rate-limits.md) - GraphQL vs REST rate limiting
- [Codespace Patterns](../cli/codespace-patterns.md) - Codespace setup implementation

## Prevention

When implementing new GitHub API integrations:

1. **Test with multiple repositories** - Don't assume success in one repo means success in all
2. **Prefer REST over GraphQL** - REST has better rate limits and fewer bugs
3. **Implement fallbacks** - If a high-level command fails, try lower-level alternatives
4. **Document workarounds** - Add to github-cli-limits.md when bugs are discovered
